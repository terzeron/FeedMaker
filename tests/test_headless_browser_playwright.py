#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.headless_browser_playwright import HeadlessBrowser


class TestHeadlessBrowserPlaywright(unittest.TestCase):
    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser_playwright.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            defaults = dict(dir_path=Path(tempfile.gettempdir()), timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowser(**defaults)

    def _build_session_mocks(self):
        mock_page = MagicMock()
        mock_page.url = "about:blank"
        mock_page.content.return_value = "<html>ok</html>"
        mock_page.locator.return_value.first = MagicMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies.return_value = []

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch_persistent_context.return_value = mock_context

        mock_sync = MagicMock()
        mock_sync.start.return_value = mock_playwright
        return mock_sync, mock_playwright, mock_context, mock_page

    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_login_success(self, mock_sync_playwright):
        browser = self._make_browser()
        mock_sync, _mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_context.cookies.return_value = [{"name": "sid", "value": "abc"}]

        id_locator = MagicMock()
        pw_locator = MagicMock()
        submit_locator = MagicMock()

        def locator_side_effect(selector):
            locator = MagicMock()
            if selector == "input[type='text'], input[type='email'], input[type='tel']":
                locator.first = id_locator
            elif selector == "input[type='password']":
                locator.first = pw_locator
            elif selector == "button[type='submit'], input[type='submit']":
                locator.first = submit_locator
            else:
                raise AssertionError(selector)
            return locator

        mock_page.locator.side_effect = locator_side_effect

        with patch.object(browser, "_write_cookies_to_file") as mock_write:
            result = browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"})

        self.assertTrue(result)
        mock_page.goto.assert_called_once()
        id_locator.wait_for.assert_called_once()
        id_locator.fill.assert_called_once_with("tester")
        pw_locator.fill.assert_called_once_with("secret")
        submit_locator.click.assert_called_once()
        mock_write.assert_called_once_with(mock_context)

    @patch("bin.headless_browser_playwright.URLSafety.check_url", return_value=(False, "blocked"))
    def test_make_request_blocked(self, mock_check):
        browser = self._make_browser()
        self.assertEqual(browser.make_request("https://blocked.example.com"), "")

    @patch("bin.headless_browser_playwright.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_make_request_with_all_options(self, mock_sync_playwright, mock_check):
        browser = self._make_browser(copy_images_from_canvas=True, simulate_scrolling=True, blob_to_dataurl=True, headers={"User-Agent": "test", "Referer": "https://referer.example.com"})
        mock_sync, _mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync

        result = browser.make_request("https://example.com")

        self.assertEqual(result, "<html>ok</html>")
        self.assertEqual(mock_page.goto.call_count, 2)
        self.assertTrue(any(call.args[0] == browser.SETTING_PLUGINS_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.SETTING_LANGUAGES_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.GETTING_METADATA_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.SIMULATING_SCROLLING_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_BLOB_TO_DATAURL_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertEqual(mock_page.wait_for_selector.call_count, 5)
        mock_context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)
        self.assertTrue(any(call.args[0] == 60000 for call in mock_page.set_default_timeout.call_args_list))
        self.assertEqual(mock_page.set_default_timeout.call_args_list[-1].args[0], browser.timeout * 1000)

    def test_read_cookies_from_file_normalizes_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text(json.dumps([{"name": "sid", "value": "abc", "domain": ".example.com", "expiry": 1234}]), encoding="utf-8")
            mock_context = MagicMock()

            browser._read_cookies_from_file(mock_context)

            cookies = mock_context.add_cookies.call_args.args[0]
            self.assertEqual(cookies[0]["expires"], 1234)
            self.assertNotIn("expiry", cookies[0])
            self.assertEqual(cookies[0]["path"], "/")

    @patch("bin.headless_browser_playwright.HeadlessBrowser.cleanup_all_sessions")
    def test_cleanup_all_drivers_alias(self, mock_cleanup):
        HeadlessBrowser.cleanup_all_drivers()
        mock_cleanup.assert_called_once()

    @patch("bin.headless_browser_playwright.sys.exit", side_effect=SystemExit(0))
    @patch("bin.headless_browser_playwright.HeadlessBrowser.cleanup_all_drivers")
    def test_handle_sigterm_cleans_up_and_exits(self, mock_cleanup, mock_exit):
        from bin.headless_browser_playwright import _handle_sigterm

        with self.assertRaises(SystemExit):
            _handle_sigterm(signal.SIGTERM, object())

        mock_cleanup.assert_called_once()
        mock_exit.assert_called_once_with(0)


if __name__ == "__main__":
    unittest.main()
