#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `playwright`.

Purpose
-------
Pin the playwright.sync_api surface that bin/headless_browser_cloak.py
imports. A playwright upgrade that renamed the exception types or removed
`BrowserContext` / `Page` from `sync_api` would break the headless browser
backend at import time. This test pins the import-time symbol surface only;
it does NOT launch a browser (that needs downloaded binaries and is covered
by test_headless_browser_cloak.py).

cloakbrowser owns the Playwright instance internally and returns a ready
BrowserContext, so production code no longer touches `sync_playwright` /
`Playwright` / `chromium.launch_persistent_context` directly — only the four
symbols below are imported.

Reference call sites (production code):
    bin/headless_browser_cloak.py:21  from playwright.sync_api import Error as PlaywrightError
    bin/headless_browser_cloak.py:22  from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    bin/headless_browser_cloak.py:23  from playwright.sync_api import BrowserContext, Page
"""

import unittest

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Page, TimeoutError as PlaywrightTimeoutError


class PlaywrightImportSurfaceTest(unittest.TestCase):
    def test_error_types_are_exceptions(self) -> None:
        # bin/headless_browser_cloak.py:21-22 -- Error / TimeoutError
        self.assertTrue(issubclass(PlaywrightError, Exception))
        self.assertTrue(issubclass(PlaywrightTimeoutError, Exception))

    def test_context_and_page_are_classes(self) -> None:
        # bin/headless_browser_cloak.py:23 -- type hints / runtime objects
        for cls in (BrowserContext, Page):
            self.assertTrue(isinstance(cls, type), f"{cls!r} is not a class")


if __name__ == "__main__":
    unittest.main()
