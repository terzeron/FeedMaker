#!/usr/bin/env python

# Backward-compat shim. The stealth-browser engine was split into:
#   - bin.headless_browser              — common base + engine-selection facade
#   - bin.headless_browser_cloakbrowser — cloakbrowser (Chromium) engine
#   - bin.headless_browser_camoufox     — camoufox (Firefox) engine
# Import HeadlessBrowser from bin.headless_browser going forward. This module remains so
# any lingering `from bin.headless_browser_cloak import ...` keeps working.

from bin.headless_browser import (  # noqa: F401
    HeadlessBrowser,
    HeadlessBrowserBase,
    PlaywrightError,
    PlaywrightTimeoutError,
)
