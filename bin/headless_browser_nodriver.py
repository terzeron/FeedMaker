#!/usr/bin/env python

import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Optional

from bin.feed_maker_util import Env, URLSafety
from bin.headless_browser import ENGINE_COOKIE_FILES, LOGGER, HeadlessBrowserBase

try:
    import nodriver
    from nodriver import ProtocolException

    _CDP_ERRORS: tuple[type[Exception], ...] = (ProtocolException, RuntimeError)
except ImportError:  # pragma: no cover - exercised when nodriver is unavailable.
    nodriver = None
    _CDP_ERRORS = (RuntimeError,)


class HeadlessBrowserNodriver(HeadlessBrowserBase):
    """Synchronous crawler adapter around nodriver's asynchronous Chrome API."""

    COOKIE_FILE = ENGINE_COOKIE_FILES["nodriver"]
    _thread_local = threading.local()
    _all_profile_dirs: set[str] = set()

    @staticmethod
    def _contains_cloudflare_challenge(html: str) -> bool:
        lowered = html.lower()
        return any(
            marker in lowered
            for marker in (
                "window._cf_chl_opt",
                "challenges.cloudflare.com/cdn-cgi/challenge",
                'id="cf-content"',
                "id='cf-content'",
                'data-translate="checking_browser"',
                "data-translate='checking_browser'",
                "<title>just a moment",
                "<title>잠시만",
            )
        )

    async def _wait_for_cloudflare_html(self, tab: Any) -> Optional[str]:
        timeout = int(
            Env.get(
                "FM_NODRIVER_CHALLENGE_TIMEOUT",
                str(self._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC),
            )
            or self._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC
        )
        start = time.monotonic()
        deadline = start + timeout
        # Same policy as the Playwright engines: an interactive Turnstile widget waits
        # for its checkbox, so tick it every click interval, at most _CLOUDFLARE_MAX_CLICKS times.
        next_click = start + self._CLOUDFLARE_CLICK_INTERVAL_SEC
        clicks = 0
        while True:
            html = await tab.get_content()
            if not self._contains_cloudflare_challenge(html):
                return html
            now = time.monotonic()
            if now >= deadline:
                return None
            if clicks < self._CLOUDFLARE_MAX_CLICKS and now >= next_click:
                try:
                    if await self._try_click_cloudflare_checkbox_cdp(tab):
                        clicks += 1
                        LOGGER.info("Clicked Cloudflare checkbox (attempt %d/%d)", clicks, self._CLOUDFLARE_MAX_CLICKS)
                except _CDP_ERRORS as e:
                    clicks += 1
                    LOGGER.debug("Cloudflare checkbox interaction failed: %r", e)
                next_click = time.monotonic() + self._CLOUDFLARE_CLICK_INTERVAL_SEC
            await asyncio.sleep(1)

    async def _try_click_cloudflare_checkbox_cdp(self, tab: Any) -> bool:
        # nodriver has no frame boxes, so walk the pierced DOM (closed shadow roots and
        # nested documents included) for the Turnstile iframe and click it via CDP input.
        cdp = nodriver.cdp
        nodes = [await tab.send(cdp.dom.get_document(depth=-1, pierce=True))]
        while nodes:
            node = nodes.pop()
            if node.node_name == "IFRAME":
                attrs = node.attributes or []
                if self._is_cloudflare_challenge_frame(dict(zip(attrs[::2], attrs[1::2])).get("src", "")):
                    try:
                        q = (await tab.send(cdp.dom.get_box_model(backend_node_id=node.backend_node_id))).content
                    except _CDP_ERRORS:
                        # The frame can detach while the tree is inspected.
                        q = None
                    point = self._cloudflare_checkbox_point(q[0], q[1], q[2] - q[0], q[5] - q[1]) if q and len(q) == 8 else None
                    if point is not None:
                        x, y = point
                        for kind, button, buttons in (("mouseMoved", "none", 0), ("mousePressed", "left", 1), ("mouseReleased", "left", 0)):
                            await tab.send(cdp.input_.dispatch_mouse_event(kind, x=x, y=y, button=cdp.input_.MouseButton(button), buttons=buttons, click_count=1))
                        return True
            nodes.extend(node.children or [])
            nodes.extend(node.shadow_roots or [])
            if node.content_document is not None:
                nodes.append(node.content_document)
        return False

    async def _scroll(self, tab: Any) -> None:
        deadline = time.monotonic() + self._MAX_SCROLL_SECS
        pos = 0
        bottom = await tab.evaluate(
            "document.body ? document.body.scrollHeight : 0",
            return_by_value=True,
        )
        try:
            bottom = int(bottom or 0)
        except (TypeError, ValueError):
            bottom = 0
        while pos < bottom and time.monotonic() < deadline:
            await tab.evaluate(f"window.scrollTo(0, {pos}); null")
            await asyncio.sleep(self._SCROLL_STEP_MS / 1000)
            pos += self._SCROLL_DOWN_STEP
        if pos:
            await tab.evaluate("window.scrollTo(0, 0); null")

    async def _fetch(self, url: str) -> str:
        if nodriver is None:
            raise ImportError("nodriver is not installed; run `pip install nodriver`")

        browser = await nodriver.start(
            headless=not self.disable_headless,
            lang="ko-KR",
        )
        try:
            referer = self.headers.get("Referer", "")
            if referer:
                is_ok, reason = URLSafety.check_url(
                    referer,
                    allow_private=self.allow_private_ips,
                    allowed_hosts_raw=self.allowed_hosts_raw,
                )
                if not is_ok:
                    LOGGER.warning("Blocked referer URL: %s (%s)", referer, reason)
                    return ""
                await browser.get(referer)

            tab = await browser.get(url)
            html = await self._wait_for_cloudflare_html(tab)
            if html is None:
                LOGGER.warning(
                    "Cloudflare challenge unresolved for '%s'; returning empty to trigger retry",
                    url,
                )
                return ""

            await tab.evaluate(self.GETTING_METADATA_SCRIPT)
            if self.copy_images_from_canvas:
                await tab.evaluate(
                    self.CONVERTING_CANVAS_TO_IMAGES_SCRIPT,
                    await_promise=True,
                )
            if self.simulate_scrolling:
                await self._scroll(tab)
            if self.blob_to_dataurl:
                await tab.evaluate(
                    self.CONVERTING_BLOB_TO_DATAURL_SCRIPT,
                    await_promise=True,
                )

            html = await tab.get_content()
            if self._contains_cloudflare_challenge(html):
                return ""
            return f"<!DOCTYPE html>{html}" if html else ""
        finally:
            browser.stop()

    def make_request(
        self,
        url: str,
        download_file: Optional[Path] = None,
    ) -> str:
        del download_file
        is_ok, reason = URLSafety.check_url(
            url,
            allow_private=self.allow_private_ips,
            allowed_hosts_raw=self.allowed_hosts_raw,
        )
        if not is_ok:
            LOGGER.warning("Blocked URL: %s (%s)", url, reason)
            return ""
        try:
            return asyncio.run(self._fetch(url))
        except (OSError, TypeError, ValueError, AttributeError, ImportError, RuntimeError) as e:
            LOGGER.error("nodriver request failed for '%s': %s", url, e)
            return ""

    def login(self, config: dict[str, str]) -> bool:
        del config
        LOGGER.warning("nodriver backend does not support automated login")
        return False
