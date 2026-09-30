#!/usr/bin/env python

import contextlib
import io
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bin import patch_playwright_pageerror as patcher


class TestPatchPlaywrightPageerror(unittest.TestCase):
    def test_patch_file_guards_fields_and_preserves_original_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coreBundle.js"
            original = "url: pageError.location.url, line: pageError.location.lineNumber, column: pageError.location?.columnNumber,\n"
            path.write_text(original, encoding="utf-8")

            self.assertEqual(patcher.patch_file(path), 3)
            patched = path.read_text(encoding="utf-8")
            self.assertIn('url: (pageError.location?.url ?? "")', patched)
            self.assertIn("line: (pageError.location?.lineNumber ?? 0)", patched)
            self.assertIn("column: (pageError.location?.columnNumber ?? 0)", patched)
            self.assertEqual(path.with_suffix(".js.orig").read_text(encoding="utf-8"), original)

            self.assertEqual(patcher.patch_file(path), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), patched)
            self.assertEqual(path.with_suffix(".js.orig").read_text(encoding="utf-8"), original)

    def test_patch_file_does_not_create_backup_without_matching_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coreBundle.js"
            path.write_text("const harmless = true;", encoding="utf-8")

            self.assertEqual(patcher.patch_file(path), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "const harmless = true;")
            self.assertFalse(path.with_suffix(".js.orig").exists())

    def test_patch_file_normalizes_optional_chain_and_repeated_parentheses(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coreBundle.js"
            path.write_text("a: (((pageError.location?.url))), b: pageError.location?.lineNumber ?? 0,", encoding="utf-8")

            self.assertEqual(patcher.patch_file(path), 2)
            self.assertEqual(path.read_text(encoding="utf-8"), 'a: (pageError.location?.url ?? ""), b: (pageError.location?.lineNumber ?? 0),')

    def test_find_bundles_scans_workspace_versions_in_sorted_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home = Path(temp_dir)
            workspace = home / "workspace"
            expected = [workspace / name / ".venv/lib/python3.12/site-packages/playwright/driver/package/lib/coreBundle.js" for name in ("alpha", "zeta")]
            for path in expected:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            with patch.object(Path, "home", return_value=home):
                self.assertEqual(patcher.find_bundles(), expected)

    def test_main_reports_no_bundles(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(patcher, "find_bundles", return_value=[]), patch("sys.argv", ["patch_playwright_pageerror.py"]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            self.assertEqual(patcher.main(), 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("no coreBundle.js found", stderr.getvalue())

    def test_main_patches_existing_paths_and_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "coreBundle.js"
            missing = Path(temp_dir) / "missing.js"
            existing.write_text("url: pageError.location.url,", encoding="utf-8")
            stdout = io.StringIO()
            with patch("sys.argv", ["patch_playwright_pageerror.py", str(existing), str(missing)]), contextlib.redirect_stdout(stdout):
                self.assertEqual(patcher.main(), 0)
            output = stdout.getvalue()
            self.assertIn("patched (1)", output)
            self.assertIn("skip (missing)", output)
            self.assertIn("total occurrences guarded: 1", output)

    def test_main_uses_default_bundle_scan(self):
        stdout = io.StringIO()
        with patch.object(patcher, "find_bundles", return_value=[]), patch("sys.argv", ["patch_playwright_pageerror.py"]), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(patcher.main(), 1)

    def test_script_entrypoint_exits_with_main_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "coreBundle.js"
            target.write_text("url: pageError.location.url,", encoding="utf-8")
            stdout = io.StringIO()
            with patch("sys.argv", [str(patcher.__file__), str(target)]), contextlib.redirect_stdout(stdout):
                with self.assertRaises(SystemExit) as raised:
                    runpy.run_path(str(patcher.__file__), run_name="__main__")
            self.assertEqual(raised.exception.code, 0)
            self.assertIn("total occurrences guarded: 1", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
