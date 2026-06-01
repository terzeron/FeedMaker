#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `cloakbrowser`.

Purpose
-------
Pin the cloakbrowser surface bin/headless_browser_cloak.py imports for
its stealth-Chromium crawling backend. Production imports
`launch_persistent_context` and relies on the cloakbrowser-patched
context whose `close()` also stops the bundled Playwright instance. A
cloakbrowser upgrade that renames or drops `launch_persistent_context`
would break the cloak backend at import time. This test pins the import
surface only; it does NOT launch the patched Chromium binary (covered by
test_headless_browser_cloak.py).

Reference call sites (production code):
    bin/headless_browser_cloak.py:31  from cloakbrowser import launch_persistent_context
"""

import unittest

import cloakbrowser


class CloakbrowserImportSurfaceTest(unittest.TestCase):
    def test_launch_persistent_context_is_importable(self) -> None:
        # bin/headless_browser_cloak.py:31 -- from cloakbrowser import launch_persistent_context
        from cloakbrowser import launch_persistent_context

        self.assertTrue(callable(launch_persistent_context))

    def test_launch_persistent_context_is_a_module_attribute(self) -> None:
        self.assertTrue(hasattr(cloakbrowser, "launch_persistent_context"))


if __name__ == "__main__":
    unittest.main()
