#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `playwright`.

Purpose
-------
Pin the playwright.sync_api surface bin/headless_browser_playwright.py
(and the cloak variant) import. A playwright upgrade that renames the
exception types, drops `sync_playwright`, or removes `BrowserContext` /
`Page` / `Playwright` from `sync_api` would break the headless browser
backend at import time. This test pins the import-time symbol surface
only; it does NOT launch a browser (that needs downloaded binaries and
is covered by test_headless_browser_playwright.py).

Reference call sites (production code):
    bin/headless_browser_playwright.py:21  from playwright.sync_api import Error as PlaywrightError
    bin/headless_browser_playwright.py:22  from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    bin/headless_browser_playwright.py:23  from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright
    bin/headless_browser_playwright.py:377 playwright = sync_playwright().start()
    bin/headless_browser_playwright.py:378 playwright.chromium.launch_persistent_context(...)
    bin/headless_browser_playwright.py:266 cache["playwright"].stop()
"""

import unittest

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Page, Playwright, TimeoutError as PlaywrightTimeoutError, sync_playwright


class PlaywrightImportSurfaceTest(unittest.TestCase):
    def test_error_types_are_exceptions(self) -> None:
        # bin/headless_browser_playwright.py:21-22 -- Error / TimeoutError
        self.assertTrue(issubclass(PlaywrightError, Exception))
        self.assertTrue(issubclass(PlaywrightTimeoutError, Exception))

    def test_context_page_playwright_are_classes(self) -> None:
        # bin/headless_browser_playwright.py:23 -- type hints / runtime objects
        for cls in (BrowserContext, Page, Playwright):
            self.assertTrue(isinstance(cls, type), f"{cls!r} is not a class")

    def test_sync_playwright_is_callable(self) -> None:
        # bin/headless_browser_playwright.py:377 -- sync_playwright().start()
        self.assertTrue(callable(sync_playwright))

    def test_started_playwright_exposes_chromium_and_stop(self) -> None:
        # Pin chromium.launch_persistent_context + stop() without launching a
        # browser: start() only spawns the driver process, no binary needed.
        playwright = sync_playwright().start()
        try:
            self.assertTrue(hasattr(playwright, "chromium"))
            self.assertTrue(hasattr(playwright.chromium, "launch_persistent_context"))
            self.assertTrue(callable(playwright.stop))
        finally:
            playwright.stop()


if __name__ == "__main__":
    unittest.main()
