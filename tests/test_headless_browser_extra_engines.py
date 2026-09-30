#!/usr/bin/env python

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import requests

from bin.headless_browser import _import_engine_class, _resolve_engine_order
from bin.headless_browser_flaresolverr import HeadlessBrowserFlaresolverr
from bin.headless_browser_nodriver import HeadlessBrowserNodriver
from bin.headless_browser_patchright import HeadlessBrowserPatchright
from bin.headless_browser_rebrowser_playwright import HeadlessBrowserRebrowserPlaywright


class _BrowserTestCase(unittest.TestCase):
    def _make_browser(self, browser_cls, **kwargs):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda key, default="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(key, default)
            options = {"dir_path": Path(tempfile.gettempdir()), "timeout": 5}
            options.update(kwargs)
            return browser_cls(**options)


class TestExtraEngineFacade(_BrowserTestCase):
    def test_explicit_engine_order_accepts_extra_engines(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda key, default="": ("patchright,nodriver,flaresolverr,rebrowser_playwright" if key == "FM_HEADLESS_BACKEND" else default)
            self.assertEqual(_resolve_engine_order(), ["patchright", "nodriver", "flaresolverr", "rebrowser_playwright"])

    def test_extra_engine_modules_are_registered(self):
        expected = {"patchright": HeadlessBrowserPatchright, "nodriver": HeadlessBrowserNodriver, "flaresolverr": HeadlessBrowserFlaresolverr, "rebrowser_playwright": HeadlessBrowserRebrowserPlaywright}
        for name, engine_cls in expected.items():
            with self.subTest(engine=name):
                self.assertIs(_import_engine_class(name), engine_cls)


class TestPlaywrightCompatibleEngines(_BrowserTestCase):
    def _assert_launch_contract(self, module_name, browser_cls):
        browser = self._make_browser(browser_cls, blob_to_dataurl=True)
        manager = MagicMock()
        context = manager.chromium.launch.return_value.new_context.return_value
        page = context.new_page.return_value
        playwright_factory = MagicMock()
        playwright_factory.return_value.start.return_value = manager

        with patch(f"{module_name}.sync_playwright", playwright_factory):
            session = browser._launch_session()

        self.assertIs(session["playwright"], manager)
        self.assertIs(session["context"], context)
        self.assertIs(session["page"], page)
        manager.chromium.launch.assert_called_once_with(headless=True)
        context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)

        browser_cls._close_session(session)
        context.close.assert_called_once()
        manager.chromium.launch.return_value.close.assert_called_once()
        manager.stop.assert_called_once()

    def test_patchright_launches_playwright_compatible_session(self):
        self._assert_launch_contract("bin.headless_browser_patchright", HeadlessBrowserPatchright)

    def test_rebrowser_launches_playwright_compatible_session(self):
        self._assert_launch_contract("bin.headless_browser_rebrowser_playwright", HeadlessBrowserRebrowserPlaywright)

    def test_patchright_converts_driver_error_to_empty_result(self):
        browser = self._make_browser(HeadlessBrowserPatchright)
        with patch("bin.headless_browser_patchright.HeadlessBrowserBase.make_request", side_effect=RuntimeError("patchright driver failed")):
            self.assertEqual(browser.make_request("https://example.com"), "")

    def test_rebrowser_converts_driver_error_to_empty_result(self):
        browser = self._make_browser(HeadlessBrowserRebrowserPlaywright)
        with patch("bin.headless_browser_rebrowser_playwright.HeadlessBrowserBase.make_request", side_effect=RuntimeError("rebrowser driver failed")):
            self.assertEqual(browser.make_request("https://example.com"), "")

    def test_engine_login_errors_are_converted_to_false(self):
        for module_name, browser_cls in (("bin.headless_browser_patchright", HeadlessBrowserPatchright), ("bin.headless_browser_rebrowser_playwright", HeadlessBrowserRebrowserPlaywright)):
            with self.subTest(engine=module_name):
                browser = self._make_browser(browser_cls)
                with patch(f"{module_name}.HeadlessBrowserBase.login", side_effect=RuntimeError("driver failed")):
                    self.assertFalse(browser.login({}))

    def test_launch_failure_closes_started_resources(self):
        for module_name, browser_cls in (("bin.headless_browser_patchright", HeadlessBrowserPatchright), ("bin.headless_browser_rebrowser_playwright", HeadlessBrowserRebrowserPlaywright)):
            with self.subTest(engine=module_name):
                browser = self._make_browser(browser_cls)
                manager = MagicMock()
                browser_instance = manager.chromium.launch.return_value
                browser_instance.new_context.side_effect = RuntimeError("context failed")
                factory = MagicMock()
                factory.return_value.start.return_value = manager
                with patch(f"{module_name}.sync_playwright", factory):
                    with self.assertRaisesRegex(RuntimeError, "context failed"):
                        browser._launch_session()
                browser_instance.close.assert_called_once()
                manager.stop.assert_called_once()

    def test_launch_session_reports_missing_optional_dependency(self):
        for module_name, browser_cls in (("bin.headless_browser_patchright", HeadlessBrowserPatchright), ("bin.headless_browser_rebrowser_playwright", HeadlessBrowserRebrowserPlaywright)):
            with self.subTest(engine=module_name):
                browser = self._make_browser(browser_cls)
                with patch(f"{module_name}.sync_playwright", None):
                    with self.assertRaises(ImportError):
                        browser._launch_session()

    def test_close_session_swallows_cleanup_errors(self):
        for browser_cls in (HeadlessBrowserPatchright, HeadlessBrowserRebrowserPlaywright):
            with self.subTest(engine=browser_cls.__name__):
                manager = MagicMock()
                browser = MagicMock()
                context = MagicMock()
                context.close.side_effect = RuntimeError("context close failed")
                browser.close.side_effect = RuntimeError("browser close failed")
                manager.stop.side_effect = RuntimeError("manager stop failed")
                browser_cls._close_session({"playwright": manager, "browser": browser, "context": context})
                context.close.assert_called_once()
                browser.close.assert_called_once()
                manager.stop.assert_called_once()


class TestNodriverEngine(_BrowserTestCase):
    def test_embedded_turnstile_is_not_a_challenge_page(self):
        html = '<html><body><iframe src="https://challenges.cloudflare.com/widget"></iframe></body></html>'
        self.assertFalse(HeadlessBrowserNodriver._contains_cloudflare_challenge(html))

    def test_make_request_returns_rendered_html(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.evaluate = AsyncMock(return_value=False)
        tab.get_content = AsyncMock(return_value="<html><body>ok</body></html>")
        driver = MagicMock()
        driver.get = AsyncMock(return_value=tab)
        nodriver_module = MagicMock()
        nodriver_module.start = AsyncMock(return_value=driver)

        with patch("bin.headless_browser_nodriver.nodriver", nodriver_module), patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")):
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html><body>ok</body></html>")
        driver.get.assert_awaited_once_with("https://example.com")
        driver.stop.assert_called_once()

    def test_make_request_blocks_unsafe_url_without_starting_browser(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        with patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(False, "private address")), patch("bin.headless_browser_nodriver.nodriver") as driver:
            self.assertEqual(browser.make_request("http://127.0.0.1"), "")
        driver.start.assert_not_called()

    def test_make_request_converts_runtime_errors_to_empty_result(self):
        browser = self._make_browser(HeadlessBrowserNodriver)

        def fail_and_close(coroutine):
            coroutine.close()
            raise RuntimeError("driver failed")

        with patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")), patch("bin.headless_browser_nodriver.asyncio.run", side_effect=fail_and_close):
            self.assertEqual(browser.make_request("https://example.com"), "")

    def test_fetch_rejects_unsafe_referer_and_stops_browser(self):
        browser = self._make_browser(HeadlessBrowserNodriver, headers={"Referer": "http://127.0.0.1"})
        driver = MagicMock()
        driver.get = AsyncMock()
        nodriver_module = MagicMock()
        nodriver_module.start = AsyncMock(return_value=driver)
        with patch("bin.headless_browser_nodriver.nodriver", nodriver_module), patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(False, "private address")):
            self.assertEqual(asyncio.run(browser._fetch("https://example.com")), "")
        driver.get.assert_not_called()
        driver.stop.assert_called_once()

    def test_fetch_uses_safe_referer_and_optional_page_transforms(self):
        browser = self._make_browser(HeadlessBrowserNodriver, headers={"Referer": "https://referrer.example"}, copy_images_from_canvas=True, simulate_scrolling=True, blob_to_dataurl=True)
        tab = MagicMock()
        tab.evaluate = AsyncMock(side_effect=[None, None, 0, None, None, None])
        tab.get_content = AsyncMock(return_value="<html>ok</html>")
        driver = MagicMock()
        driver.get = AsyncMock(side_effect=[MagicMock(), tab])
        nodriver_module = MagicMock()
        nodriver_module.start = AsyncMock(return_value=driver)
        with (
            patch("bin.headless_browser_nodriver.nodriver", nodriver_module),
            patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")),
            patch("bin.headless_browser_nodriver.time", SimpleNamespace(monotonic=MagicMock(return_value=0))),
            patch("bin.headless_browser_nodriver.asyncio.sleep", new=AsyncMock()),
        ):
            result = asyncio.run(browser._fetch("https://example.com"))
        self.assertEqual(result, "<!DOCTYPE html><html>ok</html>")
        self.assertEqual(driver.get.await_args_list[0].args, ("https://referrer.example",))
        self.assertEqual(driver.get.await_args_list[1].args, ("https://example.com",))
        self.assertIn(unittest.mock.call(browser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT, await_promise=True), tab.evaluate.await_args_list)
        self.assertIn(unittest.mock.call(browser.CONVERTING_BLOB_TO_DATAURL_SCRIPT, await_promise=True), tab.evaluate.await_args_list)
        driver.stop.assert_called_once()

    def test_wait_for_cloudflare_returns_none_after_timeout(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.get_content = AsyncMock(return_value="<title>Just a moment...</title>")
        with patch("bin.headless_browser_nodriver.Env.get", return_value="1"), patch("bin.headless_browser_nodriver.time", SimpleNamespace(monotonic=MagicMock(side_effect=[0, 2]))), patch("bin.headless_browser_nodriver.asyncio.sleep", new=AsyncMock()):
            self.assertIsNone(asyncio.run(browser._wait_for_cloudflare_html(tab)))

    def test_wait_for_cloudflare_returns_resolved_page(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.get_content = AsyncMock(side_effect=["<title>Just a moment...</title>", "<html>ready</html>"])
        with patch("bin.headless_browser_nodriver.Env.get", return_value="1"), patch("bin.headless_browser_nodriver.time", SimpleNamespace(monotonic=MagicMock(return_value=0))), patch("bin.headless_browser_nodriver.asyncio.sleep", new=AsyncMock()):
            self.assertEqual(asyncio.run(browser._wait_for_cloudflare_html(tab)), "<html>ready</html>")

    def test_scroll_handles_invalid_height_and_scrolls_back_to_top(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.evaluate = AsyncMock(return_value="invalid")
        asyncio.run(browser._scroll(tab))
        self.assertEqual(tab.evaluate.await_count, 1)

        tab.evaluate = AsyncMock(side_effect=[1400, None, None, None, None, None, None])
        with patch("bin.headless_browser_nodriver.time", SimpleNamespace(monotonic=MagicMock(return_value=0))), patch("bin.headless_browser_nodriver.asyncio.sleep", new=AsyncMock()):
            asyncio.run(browser._scroll(tab))
        self.assertIn(unittest.mock.call("window.scrollTo(0, 0); null"), tab.evaluate.await_args_list)

    def test_fetch_rejects_unresolved_challenge_and_stops_browser(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.get_content = AsyncMock(return_value="<title>Just a moment...</title>")
        driver = MagicMock()
        driver.get = AsyncMock(return_value=tab)
        nodriver_module = MagicMock()
        nodriver_module.start = AsyncMock(return_value=driver)
        with (
            patch("bin.headless_browser_nodriver.nodriver", nodriver_module),
            patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")),
            patch("bin.headless_browser_nodriver.Env.get", return_value="1"),
            patch("bin.headless_browser_nodriver.time", SimpleNamespace(monotonic=MagicMock(side_effect=[0, 2]))),
            patch("bin.headless_browser_nodriver.asyncio.sleep", new=AsyncMock()),
        ):
            self.assertEqual(asyncio.run(browser._fetch("https://example.com")), "")
            driver.stop.assert_called_once()

    def test_fetch_rejects_challenge_that_reappears_after_page_transforms(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        tab = MagicMock()
        tab.get_content = AsyncMock(side_effect=["<html>ready</html>", "<title>Just a moment...</title>"])
        tab.evaluate = AsyncMock(return_value=None)
        driver = MagicMock()
        driver.get = AsyncMock(return_value=tab)
        nodriver_module = MagicMock()
        nodriver_module.start = AsyncMock(return_value=driver)
        with patch("bin.headless_browser_nodriver.nodriver", nodriver_module), patch("bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")):
            self.assertEqual(asyncio.run(browser._fetch("https://example.com")), "")
        driver.stop.assert_called_once()

    def test_fetch_reports_missing_nodriver(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        with patch("bin.headless_browser_nodriver.nodriver", None):
            with self.assertRaises(ImportError):
                asyncio.run(browser._fetch("https://example.com"))

    def test_login_is_not_supported(self):
        browser = self._make_browser(HeadlessBrowserNodriver)
        self.assertFalse(browser.login({}))


class TestFlaresolverrEngine(_BrowserTestCase):
    def test_embedded_turnstile_is_not_a_challenge_page(self):
        html = '<html><body><iframe src="https://challenges.cloudflare.com/widget"></iframe></body></html>'
        self.assertFalse(HeadlessBrowserFlaresolverr._contains_cloudflare_challenge(html))

    def test_make_request_returns_solution_html(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        response = MagicMock()
        response.json.return_value = {"status": "ok", "solution": {"response": "<html><body>ok</body></html>"}}

        with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch("bin.headless_browser_flaresolverr.requests.post", return_value=response) as mock_post:
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html><body>ok</body></html>")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["cmd"], "request.get")
        self.assertEqual(payload["url"], "https://example.com")
        self.assertEqual(payload["maxTimeout"], 5000)

    def test_make_request_rejects_unsolved_challenge_html(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        response = MagicMock()
        response.json.return_value = {"status": "ok", "solution": {"response": "<html><title>Just a moment...</title></html>"}}

        with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch("bin.headless_browser_flaresolverr.requests.post", return_value=response):
            self.assertEqual(browser.make_request("https://example.com"), "")

    def test_service_url_requires_absolute_http_url(self):
        with patch("bin.headless_browser_flaresolverr.Env.get", return_value="ftp://service"):
            with self.assertRaises(ValueError):
                HeadlessBrowserFlaresolverr._service_url()

    def test_make_request_includes_optional_session_and_normalizes_doctype(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        response = MagicMock()
        response.json.return_value = {"status": "ok", "solution": {"response": "  <!doctype html><html>ok</html>"}}
        with (
            patch("bin.headless_browser_flaresolverr.Env.get", side_effect=lambda k, d="": " session-1 " if k == "FM_FLARESOLVERR_SESSION" else d),
            patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")),
            patch("bin.headless_browser_flaresolverr.requests.post", return_value=response) as post,
        ):
            self.assertEqual(browser.make_request("https://example.com"), "  <!doctype html><html>ok</html>")
        self.assertEqual(post.call_args.kwargs["json"]["session"], "session-1")

    def test_make_request_rejects_unsafe_url(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(False, "private address")), patch("bin.headless_browser_flaresolverr.requests.post") as post:
            self.assertEqual(browser.make_request("http://127.0.0.1"), "")
        post.assert_not_called()

    def test_make_request_returns_empty_for_service_errors_and_invalid_payloads(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        cases = (requests.RequestException("service unavailable"), ValueError("invalid JSON"), TypeError("bad response"))
        for error in cases:
            with self.subTest(error=type(error).__name__):
                with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch("bin.headless_browser_flaresolverr.requests.post", side_effect=error):
                    self.assertEqual(browser.make_request("https://example.com"), "")
        for payload in ({"status": "error", "message": "not solved"}, {"status": "ok", "solution": []}, {"status": "ok", "solution": {"response": 3}}, {"status": "ok", "solution": {"response": ""}}):
            with self.subTest(payload=payload):
                response = MagicMock()
                response.json.return_value = payload
                with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch("bin.headless_browser_flaresolverr.requests.post", return_value=response):
                    self.assertEqual(browser.make_request("https://example.com"), "")

    def test_login_is_not_supported(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        self.assertFalse(browser.login({}))


if __name__ == "__main__":
    unittest.main()
