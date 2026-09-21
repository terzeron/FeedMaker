#!/usr/bin/env python

import threading
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from bin.feed_maker_util import Env, URLSafety
from bin.headless_browser import ENGINE_COOKIE_FILES, LOGGER, HeadlessBrowserBase


class HeadlessBrowserFlaresolverr(HeadlessBrowserBase):
    """Adapter for a separately operated FlareSolverr HTTP service."""

    COOKIE_FILE = ENGINE_COOKIE_FILES["flaresolverr"]
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

    @staticmethod
    def _service_url() -> str:
        base_url = Env.get(
            "FM_FLARESOLVERR_URL",
            "http://127.0.0.1:8191",
        ).rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("FM_FLARESOLVERR_URL must be an absolute HTTP(S) URL")
        return f"{base_url}/v1"

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

        payload: dict[str, Any] = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": max(self.timeout * 1000, 1000),
        }
        session = Env.get("FM_FLARESOLVERR_SESSION", "").strip()
        if session:
            payload["session"] = session

        try:
            response = requests.post(
                self._service_url(),
                json=payload,
                timeout=(10, self.timeout + 10),
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError, TypeError) as e:
            LOGGER.error("FlareSolverr request failed for '%s': %s", url, e)
            return ""

        if data.get("status") != "ok":
            LOGGER.warning(
                "FlareSolverr did not solve '%s': %s",
                url,
                data.get("message", "unknown error"),
            )
            return ""
        solution = data.get("solution")
        if not isinstance(solution, dict):
            return ""
        html = solution.get("response", "")
        if not isinstance(html, str) or self._contains_cloudflare_challenge(html):
            LOGGER.warning("FlareSolverr returned an unresolved challenge for '%s'", url)
            return ""
        if not html:
            return ""
        return html if html.lstrip().lower().startswith("<!doctype") else f"<!DOCTYPE html>{html}"

    def login(self, config: dict[str, str]) -> bool:
        del config
        LOGGER.warning("FlareSolverr backend does not support automated login")
        return False
