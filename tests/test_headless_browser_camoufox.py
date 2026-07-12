#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.headless_browser_camoufox import HeadlessBrowserCamoufox


class TestHeadlessBrowserCamoufox(unittest.TestCase):
    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": "", "FM_CAMOUFOX_GEOIP": "true"}.get(k, d)
            defaults = dict(dir_path=Path(tempfile.gettempdir()), timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowserCamoufox(**defaults)

    def test_cookie_file_is_camoufox_specific(self):
        # Separate jar from the cloakbrowser (Chromium) engine — no cross-contamination.
        self.assertEqual(HeadlessBrowserCamoufox.COOKIE_FILE, "cookies.camoufox.json")

    def test_no_persistent_profile_dir(self):
        # camoufox launches a fresh non-persistent browser; no shared Chromium user_data_dir.
        browser = self._make_browser()
        self.assertIsNone(browser._profile_dir)

    def test_own_session_cache_namespace(self):
        # Must NOT share the base class's thread-local, or a cached camoufox session would
        # collide with a cached cloakbrowser session.
        from bin.headless_browser import HeadlessBrowserBase

        self.assertIsNot(HeadlessBrowserCamoufox._thread_local, HeadlessBrowserBase._thread_local)

    def test_close_session_unwinds_via_exit_not_stop(self):
        # Regression: teardown MUST call cam.__exit__ (which stops the sync-playwright
        # event loop). A wrong cam.stop() left the loop running and broke the next launch
        # with "Playwright Sync API inside the asyncio loop".
        cam = MagicMock()
        self.assertFalse(hasattr(cam, "stop") and callable(getattr(type(cam), "stop", None)))
        cache = {"playwright": cam, "context": MagicMock(), "page": MagicMock()}
        HeadlessBrowserCamoufox._close_session(cache)
        cam.__exit__.assert_called_once_with(None, None, None)

    def test_close_session_unwinds_exit_even_when_browser_close_fails(self):
        # Camoufox.__exit__ closes browser before stopping Playwright's sync manager.
        # If browser.close() raises, the manager cleanup must still run or fallback to a
        # second sync engine fails with "Playwright Sync API inside the asyncio loop".
        class FakeCamoufox:
            def __init__(self):
                self.browser = MagicMock()
                self.browser.close.side_effect = RuntimeError("close failed")
                self.exit_calls = 0

            def __exit__(self, *args):
                self.exit_calls += 1
                self.exit_args = args

        cam = FakeCamoufox()
        browser = cam.browser

        HeadlessBrowserCamoufox._close_session({"playwright": cam, "context": MagicMock(), "page": MagicMock()})

        browser.close.assert_called_once()
        self.assertIsNone(cam.browser)
        self.assertEqual(cam.exit_calls, 1)
        self.assertEqual(cam.exit_args, (None, None, None))

    @patch("bin.headless_browser_camoufox.Camoufox")
    def test_launch_session_uses_no_viewport(self, mock_camoufox_cls):
        # no_viewport avoids the camoufox/playwright juggler setDefaultViewport schema error.
        browser = self._make_browser()
        cam = MagicMock()
        mock_camoufox_cls.return_value = cam
        page = MagicMock()
        cam.start.return_value.new_page.return_value = page

        session = browser._launch_session()

        cam.start.return_value.new_page.assert_called_once_with(no_viewport=True)
        self.assertIs(session["playwright"], cam)
        self.assertIs(session["page"], page)

    @patch("bin.headless_browser_camoufox.Camoufox")
    def test_launch_session_error_tears_down_camoufox(self, mock_camoufox_cls):
        # If page setup fails after start(), the wrapper must be unwound via __exit__ so the
        # loop is released; otherwise the next launch is poisoned.
        browser = self._make_browser()
        cam = MagicMock()
        mock_camoufox_cls.return_value = cam
        cam.start.return_value.new_page.side_effect = RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            browser._launch_session()
        cam.__exit__.assert_called_once_with(None, None, None)


if __name__ == "__main__":
    unittest.main()
