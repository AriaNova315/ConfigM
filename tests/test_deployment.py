"""Run with: python -m unittest discover -s tests -v. Never imports the real app."""
import importlib.util
import os
from pathlib import Path
from ntpath import isreserved
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("output_paths", ROOT / "app/core/output_paths.py")
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)


class OutputPathTests(unittest.TestCase):
    def test_windows_names_length_collisions_and_original_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "generated"
            value = 'CON. /\\:*?"<>|\x00' + "😀中文" * 200
            output = paths.document_path(root, value, "NUL. ", value, 1, 2, 3)
            self.assertLessEqual(len(str(output).encode("utf-16-le")) // 2, 240)
            self.assertEqual(output.suffix, ".docx")
            self.assertEqual(len(output.relative_to(root.resolve()).parts), 3)
            for component in output.relative_to(root.resolve()).parts:
                self.assertIsNone(re.search(r'[<>:"/\\|?*\x00-\x1f]', component))
                self.assertFalse(isreserved(component))
                self.assertEqual(component, component.rstrip(". "))
            one = paths.document_path(root, "a:b", "x", "A", 1, 2, 3)
            two = paths.document_path(root, "a?b", "X", "a", 4, 5, 6)
            self.assertNotEqual(str(one).casefold(), str(two).casefold())
            self.assertIn("CON", value)  # Inputs are never rewritten.

    def test_short_budget_and_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / ("a" * 220)
            with self.assertRaisesRegex(paths.DocumentOutputError, "路径过长"):
                paths.document_path(root, "a", "b", "c", 1, 2, 3)
            root = Path(tmp) / "generated"
            output = paths.document_path(root, "../..", "C:\\bad", "../x", 1, 2, 3)
            self.assertTrue(output.resolve().is_relative_to(root.resolve()))

    def test_collision_ids_survive_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a = paths.document_path(root, "a" * 500, "b" * 500, "c" * 500, 1, 2, 3)
            b = paths.document_path(root, "a" * 500, "b" * 500, "c" * 500, 1, 2, 4)
            self.assertNotEqual(a, b)
            self.assertTrue(a.name.endswith("_d3.docx"))

    def test_failed_replace_preserves_previous_file_and_cleans_temp(self):
        class Template:
            def save(self, path):
                Path(path).write_bytes(b"new")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "file.docx"
            target.write_bytes(b"old")
            with patch.object(paths.os, "replace", side_effect=PermissionError("locked")):
                with self.assertRaisesRegex(paths.DocumentOutputError, "关闭"):
                    paths.save_document(Template(), target)
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(list(Path(tmp).iterdir()), [target])
            paths.save_document(Template(), target)
            self.assertEqual(target.read_bytes(), b"new")


class CleanApplicationTests(unittest.TestCase):
    def test_clean_start_core_flow_and_seven_templates(self):
        # Copy code/resources only: never configm.db, profiles or generated.
        with tempfile.TemporaryDirectory(prefix="configm-离线 空格-") as tmp:
            clean = Path(tmp)
            for name in ("app", "templates", "resources"):
                shutil.copytree(ROOT / name, clean / name, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
            (clean / ".deployment-test").touch()
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(clean)}
            result = subprocess.run([sys.executable, str(ROOT / "tests/smoke_worker.py")],
                                    cwd=clean, env=env, text=True, capture_output=True, timeout=90)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout.strip())
