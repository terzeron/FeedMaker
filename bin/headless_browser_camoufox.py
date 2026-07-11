#!/usr/bin/env python

import threading
from typing import Any

from bin.feed_maker_util import Env
from bin.headless_browser import ENGINE_COOKIE_FILES, LOGGER, HeadlessBrowserBase

try:
    from camoufox.sync_api import Camoufox
except ImportError:  # pragma: no cover - exercised when camoufox is unavailable.
    Camoufox = None


class HeadlessBrowserCamoufox(HeadlessBrowserBase):
    """Stealth engine backed by camoufox's patched Firefox. Its Firefox build clears
    the Cloudflare managed challenge on tkor*/toonkor mirrors that the cloakbrowser
    Chromium (v146) no longer solves.

    Unlike the cloakbrowser engine it does NOT use a persistent on-disk profile:
    launch_persistent_context trips a viewport-schema bug in the camoufox/playwright
    juggler build, so we launch a fresh non-persistent browser per session and persist
    only the cookie jar (via the base COOKIE_FILE logic). That also means there is no
    shared Chromium SingletonLock to manage."""

    COOKIE_FILE = ENGINE_COOKIE_FILES["camoufox"]

    # Own cache registry so a cached camoufox session never collides with a cached
    # cloakbrowser session in the shared classmethod cache.
    _thread_local = threading.local()
    _all_profile_dirs: set[str] = set()

    def _launch_session(self) -> dict[str, Any]:
        if Camoufox is None:
            raise ImportError("camoufox is not installed; run `pip install camoufox[geoip]` and `python -m camoufox fetch`")

        # os="windows" keeps the fingerprint consistent with DEFAULT_USER_AGENT; camoufox
        # synthesizes the matching font/navigator surface at the binary level (no external
        # Windows fonts required). geoip=True aligns the spoofed timezone/locale with the
        # outbound IP. Toggle geoip off with FM_CAMOUFOX_GEOIP=false if the GeoIP db is absent.
        use_geoip = Env.get("FM_CAMOUFOX_GEOIP", "true").strip().lower() not in ("0", "false", "no", "off")
        cam = Camoufox(headless=not self.disable_headless, humanize=True, locale="ko-KR", os="windows", geoip=use_geoip)
        browser = cam.start()
        try:
            # no_viewport avoids Browser.setDefaultViewport, which the camoufox/playwright
            # juggler build rejects ("property viewport.isMobile ... not described in this scheme").
            page = browser.new_page(no_viewport=True)
            context = page.context
            context.set_default_timeout(self.timeout * 1000)
            context.set_default_navigation_timeout(self.timeout * 1000)
            self._read_cookies_from_file(context)
            context.on("page", self._register_dialog_handlers)
            if self.blob_to_dataurl:
                context.add_init_script(self.BLOB_INTERCEPTOR_INIT_SCRIPT)
            self._register_dialog_handlers(page)
        except Exception:
            self._stop_camoufox(cam)
            raise
        # "playwright" holds the Camoufox wrapper that owns the browser+Playwright; the
        # camoufox _close_session below stops it. Keeps the same dict shape as the other engine.
        return {"playwright": cam, "context": context, "page": page}

    @staticmethod
    def _stop_camoufox(cam: Any) -> None:
        # Camoufox subclasses playwright's sync PlaywrightContextManager: .start() is
        # __enter__ (starts the sync-playwright driver + its asyncio loop and launches the
        # browser); the ONLY teardown that also stops that driver is __exit__. Using
        # anything else (there is no .stop()) leaves the sync-playwright event loop running
        # in this thread, and the next playwright-sync launch — a second camoufox session
        # OR the cloakbrowser fallback — then aborts with "Playwright Sync API inside the
        # asyncio loop". So always unwind via __exit__.
        if cam is None:
            return
        try:
            cam.__exit__(None, None, None)
        except Exception as e:  # pragma: no cover - best-effort teardown
            LOGGER.debug("camoufox __exit__ during cleanup failed: %s", e)

    @classmethod
    def _close_session(cls, cache: dict[str, Any]) -> None:
        # __exit__ already closes the browser/context, so we do NOT call context.close()
        # first (that could leave the driver half-torn-down). Just unwind the wrapper.
        cls._stop_camoufox(cache.get("playwright"))
