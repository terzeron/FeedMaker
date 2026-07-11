#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.headless_browser import HeadlessBrowser, _resolve_engine_order


class TestHeadlessBrowserFacade(unittest.TestCase):
    def test_default_engine_order_camoufox_first(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": d
            self.assertEqual(_resolve_engine_order(), ["camoufox", "cloakbrowser"])

    def test_env_override_engine_order(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": "cloakbrowser" if k == "FM_HEADLESS_BACKEND" else d
            self.assertEqual(_resolve_engine_order(), ["cloakbrowser"])

    def test_cookie_file_tracks_primary_engine(self):
        self.assertEqual(HeadlessBrowser.COOKIE_FILE, "cookies.camoufox.json")

    def _facade(self):
        return HeadlessBrowser(dir_path=Path(tempfile.gettempdir()), timeout=5)

    def test_make_request_returns_primary_result_without_fallback(self):
        facade = self._facade()
        primary = MagicMock()
        primary.make_request.return_value = "<html>ok</html>"
        with patch.object(facade, "_engine", return_value=primary), patch("bin.headless_browser._load_engine_class", return_value=object):
            facade._engine_order = ["camoufox", "cloakbrowser"]
            result = facade.make_request("https://example.com")
        self.assertEqual(result, "<html>ok</html>")
        self.assertEqual(primary.make_request.call_count, 1)

    def test_make_request_falls_back_and_tears_down_primary(self):
        # Regression: only one playwright-sync instance can be live per thread, so the failed
        # primary engine's session MUST be recycled before the fallback engine launches.
        recycle_calls: list[str] = []

        class FakeCamoufox:
            @classmethod
            def recycle_session(cls):
                recycle_calls.append("camoufox")

            def make_request(self, url, download_file=None):
                return ""  # primary fails → triggers fallback

        class FakeCloak:
            @classmethod
            def recycle_session(cls):
                recycle_calls.append("cloakbrowser")

            def make_request(self, url, download_file=None):
                return "<html>fallback</html>"

        facade = self._facade()
        facade._engine_order = ["camoufox", "cloakbrowser"]
        engines = {"camoufox": FakeCamoufox(), "cloakbrowser": FakeCloak()}
        with patch("bin.headless_browser._load_engine_class", return_value=object), patch.object(facade, "_engine", side_effect=lambda n: engines[n]):
            result = facade.make_request("https://example.com")

        self.assertEqual(result, "<html>fallback</html>")
        # only the failed primary was torn down before falling back; the successful fallback is kept
        self.assertEqual(recycle_calls, ["camoufox"])

    def test_cleanup_all_drivers_cleans_both_engines(self):
        cam_cls = MagicMock()
        cloak_cls = MagicMock()

        def loader(name):
            return {"camoufox": cam_cls, "cloakbrowser": cloak_cls}.get(name)

        with patch("bin.headless_browser._load_engine_class", side_effect=loader):
            HeadlessBrowser.cleanup_all_drivers()
        cam_cls.cleanup_all_sessions.assert_called_once()
        cloak_cls.cleanup_all_sessions.assert_called_once()


if __name__ == "__main__":
    unittest.main()
