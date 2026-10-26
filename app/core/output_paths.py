"""Portable output names; business names and document numbers remain unchanged."""
import os
from pathlib import Path
import re
import tempfile


class DocumentOutputError(ValueError):
    """A document could not be saved; safe to show to the local user."""


def _units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def _component(value: str, suffix: str, budget: int) -> str:
    # Windows separators, reserved characters and control characters.
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", str(value)).strip().rstrip(". ")
    value = value or "未命名"
    if value.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
        *(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in "123456789¹²³"),
    }:
        value = "_" + value
    available = budget - _units(suffix)
    if available < 1:
        raise DocumentOutputError("输出路径过长，请将 ConfigM 安装到更短的本地目录后重试。")
    chars = []
    used = 0
    for char in value:
        size = _units(char)
        if used + size > available:
            break
        chars.append(char)
        used += size
    return ("".join(chars).rstrip(". ") or "_") + suffix


def document_path(root: Path, project_name: str, phase_name: str, document_name: str,
                  project_id: int, phase_id: int, record_id: int) -> Path:
    """Stable IDs prevent collisions after sanitizing, truncating or case folding."""
    if any(type(value) is not int or value < 1 for value in (project_id, phase_id, record_id)):
        raise DocumentOutputError("记录缺少有效标识，无法确定输出路径。")
    root = root.resolve()
    suffixes = (f"_p{project_id}", f"_s{phase_id}", f"_d{record_id}.docx")
    # Conservative UTF-16 budget also accommodates common Windows Office tools.
    available = 240 - _units(str(root)) - 3
    budgets = [50, 45, 100]
    minima = [_units(suffix) + 1 for suffix in suffixes]
    if available < sum(minima):
        raise DocumentOutputError("输出路径过长，请将 ConfigM 安装到更短的本地目录后重试。")
    while sum(budgets) > available:
        index = max(range(3), key=lambda i: budgets[i] - minima[i])
        budgets[index] -= 1
    names = [_component(value, suffix, budget) for value, suffix, budget in
             zip((project_name, phase_name, document_name), suffixes, budgets)]
    result = root.joinpath(*names)
    if not result.resolve().is_relative_to(root):
        raise DocumentOutputError("输出路径超出 generated 目录，请检查输出目录是否包含符号链接。")
    return result


def save_document(template, path: Path) -> None:
    """Close a same-directory temp file before rendering; preserve old output on error."""
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".cm-", suffix=".tmp", dir=path.parent)
        temporary = Path(name)
        os.close(fd)
        template.save(str(temporary))
        os.replace(temporary, path)
    except PermissionError as exc:
        raise DocumentOutputError("无法保存文档：请关闭占用输出文件的 Word 或其他程序，并确认安装目录可写后重试。") from exc
    except OSError as exc:
        raise DocumentOutputError("无法保存文档：请检查本地目录权限、可用磁盘空间及安装路径长度后重试。") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
