#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import shutil
import signal
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from bin.headless_browser_playwright import HeadlessBrowser, PlaywrightError, PlaywrightTimeoutError


class TestHeadlessBrowserPlaywright(unittest.TestCase):
    def setUp(self):
        HeadlessBrowser.cleanup_all_sessions()

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

    def test_get_cookie_dir_non_writable(self):
        browser = self._make_browser(dir_path=Path("/nonexistent/readonly"))
        with patch("os.access", return_value=False):
            result = browser._get_cookie_dir()
        self.assertIn("fm_cookies", str(result))
        self.assertTrue(result.exists())

    def test_options_hash_and_cached_session_paths(self):
        options = {"headless": True, "profile_dir": "/tmp/p1"}
        session = {"page": MagicMock(url="about:blank"), "context": MagicMock(), "playwright": MagicMock()}
        HeadlessBrowser._set_cached_session(session, options)
        self.assertIs(HeadlessBrowser._get_cached_session(options), session)

        other = {"headless": False, "profile_dir": "/tmp/p1"}
        self.assertIsNone(HeadlessBrowser._get_cached_session(other))

        HeadlessBrowser._set_cached_session(session, options)
        type(session["page"]).url = PropertyMock(side_effect=RuntimeError("dead"))
        self.assertIsNone(HeadlessBrowser._get_cached_session(options))

    def test_cleanup_cached_session_tolerates_close_errors(self):
        session = {"page": MagicMock(), "context": MagicMock(), "playwright": MagicMock()}
        session["context"].close.side_effect = RuntimeError("close failed")
        session["playwright"].stop.side_effect = RuntimeError("stop failed")
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"

        HeadlessBrowser._cleanup_cached_session()

        self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_session_cache", None))

    def test_cleanup_aliases_and_all_sessions(self):
        profile_dir = tempfile.mkdtemp()
        HeadlessBrowser._all_profile_dirs.add(profile_dir)
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            HeadlessBrowser._cleanup_cached_driver()
            HeadlessBrowser.cleanup_all_drivers()
            self.assertEqual(mock_cleanup.call_count, 2)

        session = {"page": MagicMock(), "context": MagicMock(), "playwright": MagicMock()}
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"
        HeadlessBrowser.cleanup_all_sessions()
        self.assertFalse(Path(profile_dir).exists())

    def test_del_does_not_touch_playwright(self):
        # __del__가 Playwright API를 호출하면 GC 타이밍에 따라 sync 루프 안에서
        # context.close()가 호출되어 deadlock된다. 명시적 cleanup만 사용해야 한다.
        browser = self._make_browser()
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            browser.__del__()
            mock_cleanup.assert_not_called()

    def test_recycle_session_preserves_profile_dirs(self):
        profile_dir = tempfile.mkdtemp()
        HeadlessBrowser._all_profile_dirs.add(profile_dir)
        session = {"page": MagicMock(), "context": MagicMock(), "playwright": MagicMock()}
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"
        try:
            HeadlessBrowser.recycle_session()
            self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_session_cache", None))
            self.assertTrue(Path(profile_dir).exists(), "profile dir must survive recycle_session for cookie persistence")
            self.assertIn(profile_dir, HeadlessBrowser._all_profile_dirs)
        finally:
            HeadlessBrowser._all_profile_dirs.discard(profile_dir)
            shutil.rmtree(profile_dir, ignore_errors=True)

    @patch("bin.headless_browser_playwright.sync_playwright", None)
    def test_launch_session_import_error(self):
        browser = self._make_browser()
        with self.assertRaises(ImportError):
            browser._launch_session()

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

    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_login_success_with_named_fields_and_submit_fallback(self, mock_sync_playwright):
        browser = self._make_browser()
        mock_sync, _mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_context.cookies.return_value = [{"name": "sid", "value": "abc"}]

        id_locator = MagicMock()
        pw_locator = MagicMock()
        submit_locator = MagicMock()
        submit_locator.click.side_effect = PlaywrightError("click fail")

        def locator_side_effect(selector):
            locator = MagicMock()
            if selector == '[name="user\\"name"]':
                locator.first = id_locator
            elif selector == '[name="password"]':
                locator.first = pw_locator
            elif selector == "button[type='submit'], input[type='submit']":
                locator.first = submit_locator
            else:
                raise AssertionError(selector)
            return locator

        mock_page.locator.side_effect = locator_side_effect
        mock_page.wait_for_function.side_effect = PlaywrightTimeoutError("stay")

        result = browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret", "id_field": 'user"name', "password_field": "password"})

        self.assertTrue(result)
        pw_locator.press.assert_called_once_with("Enter")

    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_login_field_lookup_failure_and_runtime_error(self, mock_sync_playwright):
        browser = self._make_browser()
        mock_sync, _mock_playwright, _mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_page.locator.side_effect = PlaywrightTimeoutError("missing")
        self.assertFalse(browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

        browser2 = self._make_browser()
        with patch.object(browser2, "_get_or_create_session", side_effect=RuntimeError("boom")):
            self.assertFalse(browser2.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_login_no_cookies_after_submit(self, mock_sync_playwright):
        browser = self._make_browser()
        mock_sync, _mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_context.cookies.return_value = []

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
        self.assertFalse(browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

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

        def evaluate_side_effect(script, *_args, **_kwargs):
            s = str(script)
            if "scrollHeight" in s:
                return 1000
            if "outerHTML" in s:
                return "<html>ok</html>"
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html>ok</html>")
        self.assertEqual(mock_page.goto.call_count, 3)  # referer + main URL + about:blank
        self.assertTrue(any(call.args[0] == browser.SETTING_PLUGINS_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.SETTING_LANGUAGES_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.GETTING_METADATA_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_BLOB_TO_DATAURL_SCRIPT for call in mock_page.evaluate.call_args_list))
        # scroll uses time.sleep() now; verify scrollTo was called via evaluate
        scroll_calls = [c for c in mock_page.evaluate.call_args_list if c.args and "scrollTo" in str(c.args[0])]
        self.assertGreater(len(scroll_calls), 0)
        # scroll creates completion marker via evaluate instead of via SIMULATING_SCROLLING_SCRIPT
        self.assertTrue(any(browser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING in str(call.args[0]) for call in mock_page.evaluate.call_args_list))
        # 2 _wait_for_cloudflare invocations (referer + main) each iterate over
        # _CLOUDFLARE_CHALLENGE_SELECTORS, plus 3 completion-marker waits.
        cf_selectors = len(browser._CLOUDFLARE_CHALLENGE_SELECTORS)
        self.assertEqual(mock_page.wait_for_selector.call_count, 2 * cf_selectors + 3)
        mock_context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)

    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_launch_session_and_register_handlers(self, mock_sync_playwright):
        browser = self._make_browser(blob_to_dataurl=True)
        mock_sync, mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync

        session = browser._launch_session()

        self.assertIs(session["page"], mock_page)
        mock_playwright.chromium.launch_persistent_context.assert_called_once()
        mock_context.set_default_timeout.assert_called_once_with(browser.timeout * 1000)
        mock_context.set_default_navigation_timeout.assert_called_once_with(browser.timeout * 1000)
        mock_context.on.assert_called_once()
        mock_context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)
        mock_page.on.assert_called_once()

    def test_register_dialog_handlers_swallows_errors(self):
        page = MagicMock()
        page.on.side_effect = RuntimeError("no handler")
        HeadlessBrowser._register_dialog_handlers(page)
        page.on.assert_called_once()

    def test_get_or_create_session_reuses_and_relaunches(self):
        browser = self._make_browser()
        mock_page = MagicMock()
        session = {"page": mock_page, "context": MagicMock(), "playwright": MagicMock()}
        with patch.object(browser, "_build_session_options", return_value={"x": 1}), patch.object(HeadlessBrowser, "_get_cached_session", return_value=session):
            reused, created = browser._get_or_create_session()
        self.assertIs(reused, session)
        self.assertFalse(created)

        browser2 = self._make_browser()
        bad_session = {"page": MagicMock(), "context": MagicMock(), "playwright": MagicMock()}
        bad_session["page"].set_default_timeout.side_effect = RuntimeError("dead")
        new_session = {"page": MagicMock(), "context": MagicMock(), "playwright": MagicMock()}
        with patch.object(browser2, "_build_session_options", return_value={"x": 2}), patch.object(HeadlessBrowser, "_get_cached_session", return_value=bad_session), patch.object(browser2, "_launch_session", return_value=new_session) as mock_launch, patch.object(HeadlessBrowser, "_set_cached_session") as mock_set:
            reused, created = browser2._get_or_create_session()
        self.assertIs(reused, new_session)
        self.assertTrue(created)
        mock_launch.assert_called_once()
        mock_set.assert_called_once()

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

    def test_read_cookies_from_file_removes_empty_expires(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text(json.dumps([{"name": "sid", "value": "abc", "domain": ".example.com", "expires": ""}]), encoding="utf-8")
            mock_context = MagicMock()

            browser._read_cookies_from_file(mock_context)

            cookies = mock_context.add_cookies.call_args.args[0]
            self.assertNotIn("expires", cookies[0])

    def test_read_cookies_missing_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            mock_context = MagicMock()
            browser._read_cookies_from_file(mock_context)
            mock_context.add_cookies.assert_not_called()

            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text("{bad json", encoding="utf-8")
            browser._read_cookies_from_file(mock_context)
            self.assertFalse(cookie_file.exists())

    def test_quote_attr_and_wait_helpers(self):
        browser = self._make_browser()
        self.assertEqual(browser._quote_attr('a"b\\c'), 'a\\"b\\\\c')

        page = MagicMock()
        page.wait_for_selector.side_effect = PlaywrightTimeoutError("cf timeout")
        browser._wait_for_cloudflare(page)
        browser._wait_for_marker(page, "marker")

    @patch("bin.headless_browser_playwright.sync_playwright")
    @patch("bin.headless_browser_playwright.URLSafety.check_url")
    def test_make_request_referer_blocked_and_navigation_errors(self, mock_check, mock_sync_playwright):
        browser = self._make_browser(headers={"User-Agent": "test", "Referer": "https://referer.example.com"})
        mock_sync, _mock_playwright, _mock_context, _mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_check.side_effect = [(True, ""), (False, "blocked referer")]
        self.assertEqual(browser.make_request("https://example.com"), "")

        browser2 = self._make_browser()
        mock_sync2, _mp2, _mc2, page2 = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync2
        mock_check.side_effect = [(True, "")]
        page2.goto.side_effect = PlaywrightTimeoutError("timeout")
        self.assertEqual(browser2.make_request("https://example.com"), "")

        browser3 = self._make_browser()
        mock_sync3, _mp3, _mc3, page3 = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync3
        mock_check.side_effect = [(True, "")]
        page3.goto.side_effect = PlaywrightError("network")
        self.assertEqual(browser3.make_request("https://example.com"), "")

    @patch("bin.headless_browser_playwright.sync_playwright")
    @patch("bin.headless_browser_playwright.URLSafety.check_url", return_value=(True, ""))
    def test_make_request_scrolling_timeout_outer_error_and_finally_invalidation(self, mock_check, mock_sync_playwright):
        browser = self._make_browser(simulate_scrolling=True)
        mock_sync, _mock_playwright, mock_context, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync
        mock_page.evaluate.return_value = "<html>ok</html>"
        with patch.object(browser, "_run_scrolling_script", side_effect=PlaywrightTimeoutError("scroll timeout")):
            self.assertEqual(browser.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")

        browser2 = self._make_browser()
        with patch.object(browser2, "_get_or_create_session", side_effect=RuntimeError("boom")):
            self.assertEqual(browser2.make_request("https://example.com"), "")

        browser3 = self._make_browser()
        mock_sync3, _mp3, _mc3, page3 = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync3
        # 3 main-page evaluates + outerHTML returns "<html>ok</html>" + localStorage.clear raises
        page3.evaluate.side_effect = [None, None, None, "<html>ok</html>", RuntimeError("dead storage")]
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            self.assertEqual(browser3.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")
        self.assertGreaterEqual(mock_cleanup.call_count, 1)
        HeadlessBrowser._cleanup_cached_session()  # cleanup was mocked above; explicitly clean up for next sub-test

        browser4 = self._make_browser()
        mock_sync4, _mp4, _mc4, page4 = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync4
        page4.goto.side_effect = RuntimeError("weird failure")
        self.assertEqual(browser4.make_request("https://example.com"), "")
        HeadlessBrowser._cleanup_cached_session()  # page4.goto always raises; clean up stale session

        browser5 = self._make_browser()
        mock_sync5, _mp5, _mc5, page5 = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync5
        # 3 main-page evaluates + outerHTML returns "<html>ok</html>" + two clear() calls raise PlaywrightError
        page5.evaluate.side_effect = [None, None, None, "<html>ok</html>", PlaywrightError("clear failed"), PlaywrightError("clear failed")]
        self.assertEqual(browser5.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")

    def test_wait_until_default_is_domcontentloaded(self):
        browser = self._make_browser()
        self.assertEqual(browser.wait_until, "domcontentloaded")

    def test_wait_until_custom_value_stored(self):
        browser = self._make_browser(wait_until="load")
        self.assertEqual(browser.wait_until, "load")

    @patch("bin.headless_browser_playwright.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_wait_until_passed_to_goto(self, mock_sync_playwright, mock_check):
        browser = self._make_browser(wait_until="domcontentloaded")
        mock_sync, _mp, _mc, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync

        browser.make_request("https://example.com")

        goto_calls = mock_page.goto.call_args_list
        # about:blank 제외, 실제 URL goto 호출에 wait_until이 전달됐는지 확인
        url_goto_calls = [c for c in goto_calls if c.args and c.args[0] != "about:blank"]
        self.assertTrue(all(c.kwargs.get("wait_until") == "domcontentloaded" for c in url_goto_calls))

    @patch("bin.headless_browser_playwright.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_playwright.sync_playwright")
    def test_wait_until_load_passed_to_goto(self, mock_sync_playwright, mock_check):
        browser = self._make_browser(wait_until="load")
        mock_sync, _mp, _mc, mock_page = self._build_session_mocks()
        mock_sync_playwright.return_value = mock_sync

        browser.make_request("https://example.com")

        goto_calls = mock_page.goto.call_args_list
        url_goto_calls = [c for c in goto_calls if c.args and c.args[0] != "about:blank"]
        self.assertTrue(all(c.kwargs.get("wait_until") == "load" for c in url_goto_calls))

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


class TestRunScrollingScript(unittest.TestCase):
    """_run_scrolling_script: Python-controlled scroll loop"""

    def setUp(self):
        HeadlessBrowser.cleanup_all_sessions()

    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser_playwright.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            defaults = dict(dir_path=Path(tempfile.gettempdir()), simulate_scrolling=True, timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowser(**defaults)

    def _make_page(self, scroll_height=0):
        """Return a mock page whose evaluate() returns scroll_height for scrollHeight queries."""
        mock_page = MagicMock()

        def evaluate_side_effect(script, *args, **kwargs):
            if "scrollHeight" in script:
                return scroll_height
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect
        mock_page.wait_for_timeout.return_value = None
        return mock_page

    def _marker_was_created(self, mock_page):
        marker_id = HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING
        return any(marker_id in str(call.args[0]) for call in mock_page.evaluate.call_args_list if call.args)

    def test_zero_height_skips_scroll_creates_marker(self):
        """scrollHeight=0 → skip down loop, skip up loop, create marker."""
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=0)

        browser._run_scrolling_script(mock_page)

        scroll_calls = [c for c in mock_page.evaluate.call_args_list if "scrollTo" in str(c.args[0])]
        self.assertEqual(len(scroll_calls), 0, "no scrollTo expected when page height is 0")
        self.assertTrue(self._marker_was_created(mock_page))

    def test_finite_height_scrolls_down_and_up(self):
        """scrollHeight=700 → at least one down step and one up step."""
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=700)

        browser._run_scrolling_script(mock_page)

        all_evaluate_scripts = [str(c.args[0]) for c in mock_page.evaluate.call_args_list if c.args]
        self.assertTrue(any("scrollTo" in s for s in all_evaluate_scripts))
        # time.sleep() replaces wait_for_timeout; no wait_for_timeout calls expected
        self.assertTrue(self._marker_was_created(mock_page))

    def test_playwright_error_during_scroll_still_creates_marker(self):
        """PlaywrightError mid-scroll via evaluate() → finally block creates marker."""
        browser = self._make_browser()
        mock_page = MagicMock()

        def evaluate_side_effect(script, *args, **kwargs):
            if "scrollHeight" in script:
                return 1000
            if "scrollTo" in script:
                raise PlaywrightError("page closed")
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        browser._run_scrolling_script(mock_page)

        self.assertTrue(self._marker_was_created(mock_page))

    def test_playwright_timeout_during_scroll_still_creates_marker(self):
        """PlaywrightTimeoutError mid-scroll via evaluate() → finally block creates marker."""
        browser = self._make_browser()
        mock_page = MagicMock()

        def evaluate_side_effect(script, *args, **kwargs):
            if "scrollHeight" in script:
                return 1000
            if "scrollTo" in script:
                raise PlaywrightTimeoutError("timeout")
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        browser._run_scrolling_script(mock_page)

    def test_time_limit_exits_scroll_down_early(self):
        """Monotonic time jumps past MAX_SCROLL_SECS → down loop exits after first step."""
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=100_000)

        # Simulate: start=0, first check still OK (0<20), second check already over (25>20)
        time_seq = [0, 0, 25]
        with patch("bin.headless_browser_playwright.time.monotonic", side_effect=time_seq + [0, 25]):
            browser._run_scrolling_script(mock_page)

        down_calls = [c for c in mock_page.evaluate.call_args_list if c.args and "scrollTo" in str(c.args[0]) and "scrollHeight" not in str(c.args[0])]
        self.assertEqual(len(down_calls), 1, "exactly one down step before timeout")
        self.assertTrue(self._marker_was_created(mock_page))

    def test_marker_creation_failure_is_swallowed(self):
        """evaluate() in finally raises → no exception escapes _run_scrolling_script."""
        browser = self._make_browser()
        mock_page = MagicMock()
        mock_page.evaluate.side_effect = PlaywrightError("dead page")
        mock_page.wait_for_timeout.return_value = None

        # Must not raise
        browser._run_scrolling_script(mock_page)

    def test_scroll_payload_explicitly_returns_null(self):
        # xtoon처럼 window.scrollTo가 async 함수로 오버라이드된 사이트에서
        # page.evaluate가 Promise를 받아 무한 대기하지 않도록, 스크롤 페이로드는
        # 명시적으로 null을 리턴해야 한다 (Promise hang 방지의 핵심 invariant).
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=700)

        browser._run_scrolling_script(mock_page)

        scroll_payloads = [str(c.args[0]) for c in mock_page.evaluate.call_args_list if c.args and "scrollTo" in str(c.args[0]) and "scrollHeight" not in str(c.args[0])]
        self.assertGreater(len(scroll_payloads), 0, "expected at least one scroll payload")
        for payload in scroll_payloads:
            self.assertIn("return null", payload, "scroll payload must explicitly return null so Playwright never awaits a Promise")

    def test_scroll_loop_bounded_by_max_scroll_secs(self):
        # 무한 스크롤 페이지에서 DOM이 폭증하지 않도록 한 방향 스크롤이
        # _MAX_SCROLL_SECS를 초과하면 즉시 중단되어야 한다.
        self.assertLessEqual(HeadlessBrowser._MAX_SCROLL_SECS, 10, "_MAX_SCROLL_SECS should stay small to avoid huge DOM accumulation on infinite-scroll pages")


if __name__ == "__main__":
    unittest.main()
