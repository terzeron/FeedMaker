#!/usr/bin/env python

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from bin.headless_browser import _import_engine_class, _resolve_engine_order
from bin.headless_browser_flaresolverr import HeadlessBrowserFlaresolverr
from bin.headless_browser_nodriver import HeadlessBrowserNodriver
from bin.headless_browser_patchright import HeadlessBrowserPatchright
from bin.headless_browser_rebrowser_playwright import HeadlessBrowserRebrowserPlaywright


class _BrowserTestCase(unittest.TestCase):
    def _make_browser(self, browser_cls, **kwargs):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda key, default="": {
                "FM_CRAWLER_ALLOW_PRIVATE_IPS": "false",
                "FM_CRAWLER_ALLOWED_HOSTS": "",
            }.get(key, default)
            options = {"dir_path": Path(tempfile.gettempdir()), "timeout": 5}
            options.update(kwargs)
            return browser_cls(**options)


class TestExtraEngineFacade(_BrowserTestCase):
    def test_explicit_engine_order_accepts_extra_engines(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda key, default="": (
                "patchright,nodriver,flaresolverr,rebrowser_playwright"
                if key == "FM_HEADLESS_BACKEND"
                else default
            )
            self.assertEqual(
                _resolve_engine_order(),
                ["patchright", "nodriver", "flaresolverr", "rebrowser_playwright"],
            )

    def test_extra_engine_modules_are_registered(self):
        expected = {
            "patchright": HeadlessBrowserPatchright,
            "nodriver": HeadlessBrowserNodriver,
            "flaresolverr": HeadlessBrowserFlaresolverr,
            "rebrowser_playwright": HeadlessBrowserRebrowserPlaywright,
        }
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
        self._assert_launch_contract(
            "bin.headless_browser_rebrowser_playwright",
            HeadlessBrowserRebrowserPlaywright,
        )

    def test_patchright_converts_driver_error_to_empty_result(self):
        browser = self._make_browser(HeadlessBrowserPatchright)
        with patch(
            "bin.headless_browser_patchright.HeadlessBrowserBase.make_request",
            side_effect=RuntimeError("patchright driver failed"),
        ):
            self.assertEqual(browser.make_request("https://example.com"), "")

    def test_rebrowser_converts_driver_error_to_empty_result(self):
        browser = self._make_browser(HeadlessBrowserRebrowserPlaywright)
        with patch(
            "bin.headless_browser_rebrowser_playwright.HeadlessBrowserBase.make_request",
            side_effect=RuntimeError("rebrowser driver failed"),
        ):
            self.assertEqual(browser.make_request("https://example.com"), "")


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

        with patch("bin.headless_browser_nodriver.nodriver", nodriver_module), patch(
            "bin.headless_browser_nodriver.URLSafety.check_url", return_value=(True, "")
        ):
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html><body>ok</body></html>")
        driver.get.assert_awaited_once_with("https://example.com")
        driver.stop.assert_called_once()


class TestFlaresolverrEngine(_BrowserTestCase):
    def test_embedded_turnstile_is_not_a_challenge_page(self):
        html = '<html><body><iframe src="https://challenges.cloudflare.com/widget"></iframe></body></html>'
        self.assertFalse(HeadlessBrowserFlaresolverr._contains_cloudflare_challenge(html))

    def test_make_request_returns_solution_html(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        response = MagicMock()
        response.json.return_value = {
            "status": "ok",
            "solution": {"response": "<html><body>ok</body></html>"},
        }

        with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch(
            "bin.headless_browser_flaresolverr.requests.post", return_value=response
        ) as mock_post:
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html><body>ok</body></html>")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["cmd"], "request.get")
        self.assertEqual(payload["url"], "https://example.com")
        self.assertEqual(payload["maxTimeout"], 5000)

    def test_make_request_rejects_unsolved_challenge_html(self):
        browser = self._make_browser(HeadlessBrowserFlaresolverr)
        response = MagicMock()
        response.json.return_value = {
            "status": "ok",
            "solution": {"response": "<html><title>Just a moment...</title></html>"},
        }

        with patch("bin.headless_browser_flaresolverr.URLSafety.check_url", return_value=(True, "")), patch(
            "bin.headless_browser_flaresolverr.requests.post", return_value=response
        ):
            self.assertEqual(browser.make_request("https://example.com"), "")


if __name__ == "__main__":
    unittest.main()
