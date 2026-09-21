#!/usr/bin/env python

import threading
from pathlib import Path
from typing import Any, Optional

from bin.headless_browser import ENGINE_COOKIE_FILES, LOGGER, HeadlessBrowserBase

try:
    from patchright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised when patchright is unavailable.
    sync_playwright = None


class HeadlessBrowserPatchright(HeadlessBrowserBase):
    """Playwright-compatible Chromium engine using Patchright's patched driver."""

    COOKIE_FILE = ENGINE_COOKIE_FILES["patchright"]
    _thread_local = threading.local()
    _all_profile_dirs: set[str] = set()

    def make_request(self, url: str, download_file: Optional[Path] = None) -> str:
        try:
            return super().make_request(url, download_file=download_file)
        except Exception as e:
            LOGGER.error("patchright request failed for '%s': %s", url, e)
            return ""

    def login(self, config: dict[str, str]) -> bool:
        try:
            return super().login(config)
        except Exception as e:
            LOGGER.error("patchright login failed: %s", e)
            return False

    def _launch_session(self) -> dict[str, Any]:
        if sync_playwright is None:
            raise ImportError("patchright is not installed; run `pip install patchright` and `patchright install chromium`")

        manager = sync_playwright().start()
        browser = None
        context = None
        try:
            browser = manager.chromium.launch(headless=not self.disable_headless)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="ko-KR",
                timezone_id="Asia/Seoul",
                ignore_https_errors=True,
            )
            context.set_default_timeout(self.timeout * 1000)
            context.set_default_navigation_timeout(self.timeout * 1000)
            playwright_context: Any = context
            self._read_cookies_from_file(playwright_context)
            playwright_context.on("page", self._register_dialog_handlers)
            if self.blob_to_dataurl:
                context.add_init_script(self.BLOB_INTERCEPTOR_INIT_SCRIPT)
            page = context.new_page()
            playwright_page: Any = page
            self._register_dialog_handlers(playwright_page)
            return {
                "playwright": manager,
                "browser": browser,
                "context": context,
                "page": page,
            }
        except Exception:
            self._close_parts(manager, browser, context)
            raise

    @staticmethod
    def _close_parts(manager: Any, browser: Any, context: Any) -> None:
        for resource in (context, browser):
            if resource is not None:
                try:
                    resource.close()
                except Exception as e:  # pragma: no cover - browser process dependent.
                    LOGGER.debug("patchright cleanup failed: %s", e)
        if manager is not None:
            try:
                manager.stop()
            except Exception as e:  # pragma: no cover - driver process dependent.
                LOGGER.debug("patchright manager cleanup failed: %s", e)

    @classmethod
    def _close_session(cls, cache: dict[str, Any]) -> None:
        cls._close_parts(cache.get("playwright"), cache.get("browser"), cache.get("context"))
