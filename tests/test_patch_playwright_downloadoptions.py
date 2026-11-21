#!/usr/bin/env python

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bin import patch_playwright_downloadoptions as patcher

PRISTINE = """            downloadsDir: this._browser.options.downloadsPath,
              // TODO(time:12/2026): remove.
              legacyInterceptor: !!process.env.PLAYWRIGHT_FIREFOX_LEGACY_DOWNLOADS
            }
"""


class TestPatchPlaywrightDownloadOptions(unittest.TestCase):
    def test_patch_file_makes_legacy_interceptor_conditional_and_keeps_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coreBundle.js"
            path.write_text(PRISTINE, encoding="utf-8")

            self.assertEqual(patcher.patch_file(path), 1)
            patched = path.read_text(encoding="utf-8")
            self.assertNotIn("legacyInterceptor: !!", patched)
            self.assertIn("...(process.env.PLAYWRIGHT_FIREFOX_LEGACY_DOWNLOADS ? { legacyInterceptor: true } : {})", patched)
            self.assertEqual(path.with_suffix(".js.orig-downloadoptions").read_text(encoding="utf-8"), PRISTINE)

            self.assertEqual(patcher.patch_file(path), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), patched)

    def test_patch_file_leaves_unrelated_bundle_untouched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "coreBundle.js"
            path.write_text("const harmless = true;", encoding="utf-8")

            self.assertEqual(patcher.patch_file(path), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "const harmless = true;")
            self.assertFalse(path.with_suffix(".js.orig-downloadoptions").exists())

    def test_main_reports_no_bundles(self):
        stderr = io.StringIO()
        with patch.object(patcher, "find_bundles", return_value=[]), patch("sys.argv", ["patch_playwright_downloadoptions.py"]), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertEqual(patcher.main(), 1)
        self.assertIn("no coreBundle.js found", stderr.getvalue())

    def test_main_patches_existing_paths_and_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = Path(temp_dir) / "coreBundle.js"
            existing.write_text(PRISTINE, encoding="utf-8")
            stdout = io.StringIO()
            with patch("sys.argv", ["patch_playwright_downloadoptions.py", str(existing), str(Path(temp_dir) / "missing.js")]), contextlib.redirect_stdout(stdout):
                self.assertEqual(patcher.main(), 0)
            self.assertIn("patched (1)", stdout.getvalue())
            self.assertIn("skip (missing)", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
