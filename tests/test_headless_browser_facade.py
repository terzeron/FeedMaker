#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.headless_browser import HeadlessBrowser, _import_engine_class, _load_engine_class, _resolve_engine_order


class TestHeadlessBrowserFacade(unittest.TestCase):
    def test_default_engine_order_camoufox_first(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": d
            self.assertEqual(_resolve_engine_order(), ["camoufox", "cloakbrowser"])

    def test_env_override_engine_order(self):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": "cloakbrowser" if k == "FM_HEADLESS_BACKEND" else d
            self.assertEqual(_resolve_engine_order(), ["cloakbrowser"])

    def test_import_engine_class_returns_none_for_unknown_name(self):
        # Nothing raises on an unrecognized engine name — that keeps a bogus
        # FM_HEADLESS_BACKEND value from crashing module import.
        self.assertIsNone(_import_engine_class("nonexistent-engine"))

    def test_installed_engines_are_registered_eagerly(self):
        # The registry is populated once at module load (a lazy per-call import raced under
        # the extractor's thread pool with "partially initialized module").
        for name in ("camoufox", "cloakbrowser"):
            with self.subTest(engine=name):
                self.assertIsNotNone(_load_engine_class(name))

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

    def test_make_request_returns_empty_when_no_engine_instantiates(self):
        # The engine class loads but construction yields nothing usable: the loop must skip
        # it instead of calling make_request on None, and report failure with an empty body.
        facade = self._facade()
        facade._engine_order = ["camoufox", "cloakbrowser"]
        with patch("bin.headless_browser._load_engine_class", return_value=object), patch.object(facade, "_engine", return_value=None):
            result = facade.make_request("https://example.com")
        self.assertEqual(result, "")

    def test_make_request_returns_empty_when_every_engine_fails(self):
        # Last engine's empty result is returned as-is; only the non-final engines are recycled.
        recycle_calls: list[str] = []

        class FakeCamoufox:
            @classmethod
            def recycle_session(cls):
                recycle_calls.append("camoufox")

            def make_request(self, url, download_file=None):
                return ""

        class FakeCloak:
            @classmethod
            def recycle_session(cls):
                recycle_calls.append("cloakbrowser")

            def make_request(self, url, download_file=None):
                return ""

        facade = self._facade()
        facade._engine_order = ["camoufox", "cloakbrowser"]
        engines = {"camoufox": FakeCamoufox(), "cloakbrowser": FakeCloak()}
        with patch("bin.headless_browser._load_engine_class", return_value=object), patch.object(facade, "_engine", side_effect=lambda n: engines[n]):
            result = facade.make_request("https://example.com")

        self.assertEqual(result, "")
        self.assertEqual(recycle_calls, ["camoufox"])

    def test_getattr_refuses_private_names_without_loading_engines(self):
        # __getattr__ delegates public reads to the primary engine, but must raise for
        # underscore names — otherwise an internal attribute lookup during __init__ recurses.
        facade = self._facade()
        with patch("bin.headless_browser._load_engine_class") as mock_loader:
            with self.assertRaises(AttributeError):
                getattr(facade, "_no_such_internal_attr")
            mock_loader.assert_not_called()

    def test_engine_returns_none_when_class_unavailable(self):
        facade = self._facade()
        with patch("bin.headless_browser._load_engine_class", return_value=None):
            self.assertIsNone(facade._engine("camoufox"))

    def test_primary_raises_when_no_engine_is_installed(self):
        # Neither camoufox nor cloakbrowser importable → an explicit ImportError naming the
        # remedy, not an opaque AttributeError from a None engine.
        facade = self._facade()
        with patch("bin.headless_browser._load_engine_class", return_value=None):
            with self.assertRaises(ImportError):
                _ = facade._primary

    def test_login_delegates_to_primary_engine(self):
        facade = self._facade()
        config = {"login_url": "https://example.com/login"}
        primary = MagicMock()
        primary.login.return_value = True
        with patch.object(facade, "_engine", return_value=primary):
            self.assertTrue(facade.login(config))
        primary.login.assert_called_once_with(config)

    def test_get_cookie_dir_delegates_to_primary_engine(self):
        # crawler's login-skip check reads the facade's cookie dir; it must resolve to the
        # primary engine's jar location, not the facade's own (nonexistent) one.
        facade = self._facade()
        primary = MagicMock()
        primary._get_cookie_dir.return_value = Path(tempfile.gettempdir()) / "primary_jar"
        with patch.object(facade, "_engine", return_value=primary):
            self.assertEqual(facade._get_cookie_dir(), Path(tempfile.gettempdir()) / "primary_jar")

    def test_backward_compat_shim_reexports_public_names(self):
        # bin.headless_browser_cloak is a shim kept for lingering imports; it must expose the
        # same objects as the real module, not copies.
        import bin.headless_browser as real
        import bin.headless_browser_cloak as shim

        self.assertIs(shim.HeadlessBrowser, real.HeadlessBrowser)
        self.assertIs(shim.HeadlessBrowserBase, real.HeadlessBrowserBase)
        self.assertIs(shim.PlaywrightError, real.PlaywrightError)
        self.assertIs(shim.PlaywrightTimeoutError, real.PlaywrightTimeoutError)

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
