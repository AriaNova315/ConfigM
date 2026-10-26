"""Package an explicit source/resource allowlist, never the working directory wholesale."""
import argparse
import hashlib
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"app": {".py", ".html", ".js", ".css", ".md", ".txt"},
               "templates": {".docx"}, "resources": {".xlsx"}, "docs": {".md"},
               "scripts": {".py"}, "tests": {".py"}}
FILES = ["run.py", "start.cmd", "requirements.txt", "requirements-win.lock.txt",
         "README.md", "CLAUDE.md", ".gitignore", ".gitattributes", "build_templates.py"]


def delivery_files(root=ROOT):
    files = [root / name for name in FILES]
    files.extend(root.glob("*.md"))
    for directory, extensions in DIRECTORIES.items():
        files.extend(p for p in (root / directory).rglob("*")
                     if p.is_file() and p.suffix in extensions
                     and "__pycache__" not in p.parts and not p.name.startswith("~$"))
    for p in sorted(set(files)):
        if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Missing or unsafe delivery resource: {p}")
        yield p


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New .zip file outside the source directories")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.suffix.lower() != ".zip":
        parser.error("output must end in .zip")
    files = list(delivery_files())
    if output in files:
        parser.error("output is a source file")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement of a previous delivery.
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        manifest = []
        for p in files:
            relative = p.relative_to(ROOT).as_posix()
            content = p.read_bytes()
            archive.writestr(relative, content)
            manifest.append(f"{hashlib.sha256(content).hexdigest()}  {relative}")
        archive.writestr("MANIFEST-SHA256.txt", "\n".join(manifest) + "\n")
    print(f"Created {output} ({len(files)} source/resource files; no business data)")
    print("SHA256:", hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
