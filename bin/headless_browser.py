#!/usr/bin/env python

import atexit
import hashlib
import json
import logging.config
import os
import shutil
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

from bin.feed_maker_util import Env, PathUtil, URLSafety

try:
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import BrowserContext, Page
except ImportError:  # pragma: no cover - exercised via mocks when playwright is unavailable.
    PlaywrightError = Exception
    PlaywrightTimeoutError = TimeoutError
    BrowserContext = Any
    Page = Any

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class HeadlessBrowserBase:
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS = "rendering_completed_in_converting_canvas"
    ID_OF_RENDERING_COMPLETION_IN_SCROLLING = "rendering_completed_in_scrolling"
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB = "rendering_completed_in_converting_blob"
    # Engine subclasses override COOKIE_FILE so the cloakbrowser (Chromium) and
    # camoufox (Firefox) jars never cross-contaminate.
    COOKIE_FILE = "cookies.headlessbrowser.json"
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

    # Each engine subclass declares its OWN _thread_local / _all_profile_dirs so a
    # cached cloakbrowser session and a cached camoufox session never collide in the
    # shared classmethod cache. The base copies exist only so the base class itself is
    # usable in isolation (e.g. tests); real engines shadow them.
    _thread_local = threading.local()
    _all_profile_dirs: set[str] = set()

    GETTING_METADATA_SCRIPT = """
        var metas = document.getElementsByTagName("meta");
        var has_og_url_property = false;
        for (var i = 0; i < metas.length; i++) {
            var meta = metas[i];
            if (meta.getAttribute("property") == "og:url") {
                has_og_url_property = true;
            }
        }
        if (!has_og_url_property) {
            var new_meta = document.createElement("meta");
            new_meta.setAttribute("property", "og:url");
            new_meta.setAttribute("content", window.location.href);
            document.head.appendChild(new_meta);
        }
    """
    CONVERTING_CANVAS_TO_IMAGES_SCRIPT = (
        """
        (async function () {
            div = document.createElement("DIV");
            div.className = "images_from_canvas";
            var canvas_list = document.getElementsByTagName("canvas");
            for (var i = 0; i < canvas_list.length; i++) {
                img_data = canvas_list[i].toDataURL("image/png");
                img = document.createElement("IMG");
                img.src = img_data;
                div.appendChild(img);
            }
            document.body.appendChild(div);
        }());

        var div = document.createElement("DIV");
        document.body.appendChild(div);
        div.id = "%s";
        """
        % ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS
    )
    _SCROLL_DOWN_STEP = 349
    _SCROLL_UP_STEP = 683
    _SCROLL_STEP_MS = 200
    _MAX_SCROLL_SECS = 5
    BLOB_INTERCEPTOR_INIT_SCRIPT = """
        (function() {
            if (window._blobInterceptorInstalled) return;
            window._blobInterceptorInstalled = true;
            window._capturedImageDataURLs = [];
            window._blobURLToDataURL = {};

            const _origCreate = URL.createObjectURL;
            URL.createObjectURL = function(obj) {
                const blobUrl = _origCreate.call(URL, obj);
                if (obj && obj.type && obj.type.startsWith('image/') &&
                    !obj.type.includes('svg') && obj.size > 10240) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        const dataURL = e.target.result;
                        if (!window._capturedImageDataURLs.includes(dataURL)) {
                            window._capturedImageDataURLs.push(dataURL);
                        }
                        window._blobURLToDataURL[blobUrl] = dataURL;
                    };
                    reader.readAsDataURL(obj);
                }
                return blobUrl;
            };
        })();
    """
    CONVERTING_BLOB_TO_DATAURL_SCRIPT = (
        """
        (async function () {
            await new Promise(r => setTimeout(r, 2000));

            var images = document.getElementsByTagName("img");
            for (var i = 0; i < images.length; i++) {
                var src = images[i].src;
                if (src && src.startsWith("blob:")) {
                    if (window._blobURLToDataURL && window._blobURLToDataURL[src]) {
                        images[i].src = window._blobURLToDataURL[src];
                    } else {
                        try {
                            var response = await fetch(src);
                            var data = await response.arrayBuffer();
                            var blob = new Blob([data], {type: 'image/png'});
                            var dataURL = await new Promise(function(resolve) {
                                var reader = new FileReader();
                                reader.onload = function(e) { resolve(e.target.result); };
                                reader.readAsDataURL(blob);
                            });
                            images[i].src = dataURL;
                        } catch(e) {}
                    }
                }
            }

            if (window._capturedImageDataURLs && window._capturedImageDataURLs.length > 0) {
                var existingDataSrcs = new Set();
                var allImgs = document.getElementsByTagName("img");
                for (var j = 0; j < allImgs.length; j++) {
                    if (allImgs[j].src && allImgs[j].src.startsWith("data:image/")) {
                        existingDataSrcs.add(allImgs[j].src);
                    }
                }
                var root = document.getElementById("root") || document.body;
                for (var k = 0; k < window._capturedImageDataURLs.length; k++) {
                    var captured = window._capturedImageDataURLs[k];
                    if (!existingDataSrcs.has(captured)) {
                        var img = document.createElement("img");
                        img.src = captured;
                        root.appendChild(img);
                        existingDataSrcs.add(captured);
                    }
                }
            }

            var div = document.createElement("DIV");
            document.body.appendChild(div);
            div.id = "%s";
        }());
        """
        % ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB
    )

    def __init__(self, *, dir_path: Path = Path.cwd(), headers: Optional[dict[str, str]] = None, copy_images_from_canvas: bool = False, simulate_scrolling: bool = False, disable_headless: bool = False, blob_to_dataurl: bool = False, timeout: int = 60, wait_until: str = "domcontentloaded") -> None:
        LOGGER.debug(
            "# HeadlessBrowserCloak(dir_path=%s, headers=%r, copy_images_from_canvas=%s, simulate_scrolling=%s, disable_headless=%s, blob_to_dataurl=%s, timeout=%d, wait_until=%s)",
            PathUtil.short_path(dir_path),
            headers,
            copy_images_from_canvas,
            simulate_scrolling,
            disable_headless,
            blob_to_dataurl,
            timeout,
            wait_until,
        )
        self.dir_path: Path = dir_path
        self.headers: dict[str, str] = headers if headers is not None else {}
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = self.DEFAULT_USER_AGENT
        self.copy_images_from_canvas: bool = copy_images_from_canvas
        self.simulate_scrolling: bool = simulate_scrolling
        self.disable_headless: bool = disable_headless
        self.blob_to_dataurl: bool = blob_to_dataurl
        self.timeout: int = timeout
        self.wait_until: str = wait_until
        self._cookie_dir: Optional[Path] = None
        self.allow_private_ips = Env.get("FM_CRAWLER_ALLOW_PRIVATE_IPS", "false").strip().lower() in ("1", "true", "yes", "on")
        self.allowed_hosts_raw = Env.get("FM_CRAWLER_ALLOWED_HOSTS", "")
        self._profile_dir: Optional[str] = None
        self._setup_profile()

    def _setup_profile(self) -> None:
        # Default: no persistent on-disk profile (the camoufox engine launches a fresh
        # browser per session and persists only the cookie jar). The cloakbrowser engine
        # overrides this to create a per-group Chromium user_data_dir.
        self._profile_dir = None

    def __del__(self) -> None:
        # GC가 Playwright sync API의 메시지 dispatch 도중에 __del__을 호출하면
        # context.close()가 reentrancy로 deadlock된다 (asyncio 루프 안에서 sync 호출).
        # 명시적 정리는 cleanup_all_sessions() / recycle_session()에 위임한다.
        pass

    def _get_cookie_dir(self) -> Path:
        if self._cookie_dir is not None:
            return self._cookie_dir
        if os.access(self.dir_path, os.W_OK):
            self._cookie_dir = self.dir_path
        else:
            dir_hash = hashlib.md5(str(self.dir_path).encode(), usedforsecurity=False).hexdigest()[:12]
            fallback = Path(tempfile.gettempdir()) / "fm_cookies" / dir_hash
            fallback.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Cookie dir '%s' not writable, using fallback '%s'", self.dir_path, fallback)
            self._cookie_dir = fallback
        return self._cookie_dir

    @classmethod
    def _get_options_hash(cls, options: dict[str, Any]) -> str:
        options_str = json.dumps(options, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(options_str.encode(), usedforsecurity=False).hexdigest()

    def _build_session_options(self) -> dict[str, Any]:
        return {"headless": not self.disable_headless, "user_agent": self.headers["User-Agent"], "blob_to_dataurl": self.blob_to_dataurl, "copy_images_from_canvas": self.copy_images_from_canvas, "simulate_scrolling": self.simulate_scrolling, "group_key": str(self.dir_path.parent)}

    @classmethod
    def _get_cached_session(cls, options: dict[str, Any]) -> Optional[dict[str, Any]]:
        cache: Optional[dict[str, Any]] = getattr(cls._thread_local, "_session_cache", None)
        if cache is None:
            return None

        current_hash = cls._get_options_hash(options)
        cached_hash = getattr(cls._thread_local, "_session_options_hash", None)
        if cached_hash != current_hash:
            cls._cleanup_cached_session()
            return None

        try:
            cache["page"].url
            return cache
        except Exception:
            cls._cleanup_cached_session()
            return None

    @classmethod
    def _set_cached_session(cls, session: dict[str, Any], options: dict[str, Any]) -> None:
        cls._thread_local._session_cache = session
        cls._thread_local._session_options_hash = cls._get_options_hash(options)

    @classmethod
    def _cleanup_cached_session(cls) -> None:
        cache = getattr(cls._thread_local, "_session_cache", None)
        if cache:
            cls._close_session(cache)
            cls._thread_local._session_cache = None
            cls._thread_local._session_options_hash = None

    @classmethod
    def _close_session(cls, cache: dict[str, Any]) -> None:
        # Engine-specific teardown of a launched session. Default closes the browser
        # context; subclasses override when their launcher owns extra state (e.g. the
        # camoufox engine must also stop its Camoufox/Playwright wrapper).
        try:
            cache["context"].close()
        except Exception:
            try:
                browser = cache["context"].browser
                if browser:
                    browser.close()
            except Exception:
                pass

    @classmethod
    def _cleanup_cached_driver(cls) -> None:
        cls._cleanup_cached_session()

    @classmethod
    def recycle_session(cls) -> None:
        cls._cleanup_cached_session()

    @classmethod
    def cleanup_all_sessions(cls) -> None:
        cls._cleanup_cached_session()
        for d in list(cls._all_profile_dirs):
            shutil.rmtree(d, ignore_errors=True)
        cls._all_profile_dirs.clear()

    @classmethod
    def cleanup_all_drivers(cls) -> None:
        cls.cleanup_all_sessions()

    def _launch_session(self) -> dict[str, Any]:
        # Engine-specific: launch the stealth browser and return a session dict of the
        # shape {"playwright": <owner-or-None>, "context": BrowserContext, "page": Page}.
        # Implemented by HeadlessBrowserCloakbrowser and HeadlessBrowserCamoufox.
        raise NotImplementedError

    @staticmethod
    def _register_dialog_handlers(page: Page) -> None:
        try:
            page.on("dialog", lambda dialog: dialog.dismiss())
        except Exception:
            pass

    def _get_or_create_session(self) -> tuple[dict[str, Any], bool]:
        options = self._build_session_options()
        session = self._get_cached_session(options)
        if session is not None:
            try:
                session["page"].set_default_timeout(self.timeout * 1000)
                session["page"].set_default_navigation_timeout(self.timeout * 1000)
            except Exception:
                self._cleanup_cached_session()
                session = None
        if session is not None:
            return session, False

        session = self._launch_session()
        self._set_cached_session(session, options)
        return session, True

    # __cf_bm (bot-management, ~30 min) and the __cf_chl*/cf_chl*/__cfwaitingroom challenge
    # cookies are short-lived and bound to an in-flight challenge, so persisting them only
    # replays junk. cf_clearance is different: it is the actual clearance token with a
    # multi-hour TTL, so reusing a still-valid one lets a later run skip the managed
    # challenge entirely — a big reliability win for back-to-back batch runs. We persist it;
    # if Cloudflare later rejects a stale token the challenge simply re-runs, and
    # make_request() discards the jar and retries on a fresh session when it fails to clear
    # (see _discard_persisted_cookies and the _wait_for_cloudflare handling below).
    _NON_PERSISTENT_COOKIE_PREFIXES: tuple[str, ...] = ("__cf_bm", "__cf_chl", "cf_chl", "__cfwaitingroom")

    @classmethod
    def _is_persistable_cookie(cls, name: str) -> bool:
        return not any(name.startswith(prefix) for prefix in cls._NON_PERSISTENT_COOKIE_PREFIXES)

    def _write_cookies_to_file(self, context: BrowserContext) -> None:
        cookies = [c for c in context.cookies() if self._is_persistable_cookie(c.get("name", ""))]
        cookie_file = self._get_cookie_dir() / self.COOKIE_FILE
        with cookie_file.open("w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

    def _discard_persisted_cookies(self) -> None:
        # Drop the saved cookie jar so a stale/rejected Cloudflare clearance token isn't
        # replayed on the next attempt or run; all cookies are re-minted on a clean pass.
        cookie_file = self._get_cookie_dir() / self.COOKIE_FILE
        cookie_file.unlink(missing_ok=True)

    def _read_cookies_from_file(self, context: BrowserContext) -> None:
        cookie_file = self._get_cookie_dir() / self.COOKIE_FILE
        if not cookie_file.is_file():
            return

        try:
            with cookie_file.open("r", encoding="utf-8") as f:
                cookies = json.load(f)
            normalized_cookies: list[dict[str, Any]] = []
            for cookie in cookies:
                cookie = dict(cookie)
                if "expiry" in cookie:
                    cookie["expires"] = cookie.pop("expiry")
                if "expires" in cookie and cookie["expires"] in (None, ""):
                    cookie.pop("expires")
                cookie.setdefault("path", "/")
                normalized_cookies.append(cookie)
            if normalized_cookies:
                context.add_cookies(normalized_cookies)  # type: ignore[arg-type]
        except Exception:
            cookie_file.unlink(missing_ok=True)
            self._read_cookies_from_file(context)

    @staticmethod
    def _quote_attr(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    # Legacy "checking your browser" interstitial markup. The modern managed
    # challenge / Turnstile instead exposes window._cf_chl_opt and a
    # challenges.cloudflare.com iframe under a "Just a moment…"/"잠시만…" title.
    _CLOUDFLARE_CHALLENGE_SELECTORS: tuple[str, ...] = ("#cf-content", 'iframe[src*="challenges.cloudflare.com"]', '[data-translate="checking_browser"]')
    # How long to let a Cloudflare managed challenge run its JS and reload to the origin
    # before giving up. Kept separate from (and larger than) the per-navigation timeout
    # because an interactive Turnstile solve routinely needs longer than a plain page load.
    _CLOUDFLARE_CHALLENGE_TIMEOUT_SEC: int = 90
    # Predicate is true once no Cloudflare interstitial remains on the page.
    _CLOUDFLARE_CLEARED_PREDICATE = """
        () => {
            if (window._cf_chl_opt) return false;
            if (document.querySelector('iframe[src*="challenges.cloudflare.com"], #cf-content, [data-translate="checking_browser"]')) return false;
            const t = document.title || "";
            if (t.includes("Just a moment") || t.includes("잠시만")) return false;
            // After an interactive Turnstile challenge clears, Cloudflare reloads to the
            // origin; for a moment the challenge markers are gone but the real document
            // has no body yet. Require a populated body so we wait for that reload to
            // finish instead of capturing the empty transitional page (head-only HTML).
            return !!(document.body && document.body.children.length > 0);
        }
    """

    def _wait_for_cloudflare(self, page: Page) -> bool:
        # A Cloudflare challenge auto-solves only if we let its JS run to completion
        # and reload to the real page; grabbing the HTML too early captures the
        # interstitial instead. wait_for_selector(state="hidden") returned instantly
        # when the markup didn't match these selectors, so the challenge HTML leaked
        # through. Poll a predicate that is satisfied immediately when no challenge is
        # present and otherwise blocks until the challenge clears (or times out).
        # Returns True once cleared (or no challenge was present), False if it never
        # cleared within the timeout — the caller uses this to retry instead of
        # capturing the interstitial.
        try:
            page.wait_for_function(self._CLOUDFLARE_CLEARED_PREDICATE, timeout=self._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC * 1000)
            return True
        except PlaywrightTimeoutError:
            LOGGER.warning("Cloudflare challenge did not clear within %ds", self._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC)
            return False

    def _wait_for_marker(self, page: Page, marker_id: str) -> None:
        try:
            page.wait_for_selector(f"#{marker_id}", state="attached", timeout=self.timeout * 1000)
            LOGGER.debug("Found completion marker: %s", marker_id)
        except PlaywrightTimeoutError:
            LOGGER.warning("Timeout waiting for completion marker: %s", marker_id)

    def _run_scrolling_script(self, page: Page) -> None:
        marker_id = self.ID_OF_RENDERING_COMPLETION_IN_SCROLLING
        # Use a wrapper that explicitly returns null so Playwright never waits
        # on a Promise — xtoon and similar sites override window.scrollTo with
        # an async function, which would cause page.evaluate() to hang forever.
        _SCROLL_JS = "(function(y) {{ window.scrollTo(0, y); return null; }})({pos})"
        try:
            time.sleep(1)

            start = time.monotonic()
            pos = 0
            try:
                bottom = int(page.evaluate("document.body.scrollHeight") or 0)
            except (TypeError, ValueError):
                bottom = 0

            while pos < bottom and time.monotonic() - start < self._MAX_SCROLL_SECS:
                page.evaluate(_SCROLL_JS.format(pos=pos))
                time.sleep(self._SCROLL_STEP_MS / 1000)
                pos += self._SCROLL_DOWN_STEP
                try:
                    bottom = int(page.evaluate("document.body.scrollHeight") or 0)
                except (TypeError, ValueError):
                    break

            if pos > 0:
                start = time.monotonic()
                while pos >= 0 and time.monotonic() - start < self._MAX_SCROLL_SECS:
                    page.evaluate(_SCROLL_JS.format(pos=pos))
                    time.sleep(self._SCROLL_STEP_MS / 1000)
                    pos -= self._SCROLL_UP_STEP

            time.sleep(1)
        except (PlaywrightError, PlaywrightTimeoutError) as e:
            LOGGER.warning("Scrolling interrupted: %s", e)
        finally:
            try:
                page.evaluate(f'if (!document.getElementById("{marker_id}")) {{ const d = document.createElement("div"); d.id = "{marker_id}"; document.body.appendChild(d); }}')
            except Exception:
                pass

    def login(self, config: dict[str, str]) -> bool:
        LOGGER.debug("# HeadlessBrowserCloak.login(login_url=%s)", config["login_url"])
        login_url = config["login_url"]

        try:
            session, _ = self._get_or_create_session()
            page: Page = session["page"]
            context: BrowserContext = session["context"]

            page.goto(login_url, wait_until=self.wait_until, timeout=self.timeout * 1000)  # type: ignore[arg-type]

            id_field = config.get("id_field", "")
            password_field = config.get("password_field", "")
            try:
                if id_field:
                    selector = f'[name="{self._quote_attr(id_field)}"]'
                else:
                    selector = "input[type='text'], input[type='email'], input[type='tel']"
                id_element = page.locator(selector).first
                id_element.wait_for(state="visible", timeout=self.timeout * 1000)
                id_element.fill(config["id"])

                if password_field:
                    pw_selector = f'[name="{self._quote_attr(password_field)}"]'
                else:
                    pw_selector = "input[type='password']"
                pw_element = page.locator(pw_selector).first
                pw_element.fill(config["password"])
            except (PlaywrightTimeoutError, PlaywrightError) as e:
                LOGGER.warning("Failed to find login form fields: %s", e)
                return False

            try:
                page.locator("button[type='submit'], input[type='submit']").first.click()
            except PlaywrightError:
                pw_element.press("Enter")

            try:
                page.wait_for_function("(loginUrl) => window.location.href !== loginUrl", login_url, timeout=self.timeout * 1000)
            except PlaywrightTimeoutError:
                pass

            cookies = context.cookies()
            if cookies:
                self._write_cookies_to_file(context)
                LOGGER.info("HeadlessBrowserCloak login successful for '%s'", login_url)
                return True

            LOGGER.warning("HeadlessBrowserCloak login failed for '%s' (no cookies after submit)", login_url)
            return False

        except (OSError, TypeError, ValueError, AttributeError, ImportError, RuntimeError) as e:
            LOGGER.warning("HeadlessBrowserCloak login error: %s", e)
            return False

    def make_request(self, url: str, download_file: Optional[Path] = None) -> str:
        LOGGER.debug("# HeadlessBrowserCloak.make_request(url=%s, download_file=%s)", url, download_file)
        is_ok, reason = URLSafety.check_url(url, allow_private=self.allow_private_ips, allowed_hosts_raw=self.allowed_hosts_raw)
        if not is_ok:
            LOGGER.warning("Blocked URL: %s (%s)", url, reason)
            return ""

        session: Optional[dict[str, Any]] = None
        challenge_cleared: bool = True

        try:
            session, _ = self._get_or_create_session()
            page: Page = session["page"]
            context: BrowserContext = session["context"]

            referer = self.headers.get("Referer", "")
            if referer:
                is_ok, reason = URLSafety.check_url(referer, allow_private=self.allow_private_ips, allowed_hosts_raw=self.allowed_hosts_raw)
                if not is_ok:
                    LOGGER.warning("Blocked referer URL: %s (%s)", referer, reason)
                    return ""
                LOGGER.debug("visiting referer page '%s'", referer)
                page.goto(referer, wait_until=self.wait_until, timeout=self.timeout * 1000)  # type: ignore[arg-type]
                self._wait_for_cloudflare(page)
                self._write_cookies_to_file(context)

            LOGGER.debug("getting the page '%s'", url)
            try:
                page.goto(url, wait_until=self.wait_until, timeout=self.timeout * 1000)  # type: ignore[arg-type]
            except PlaywrightTimeoutError as e:
                LOGGER.warning("<!-- Warning: can't can't read data from '%s' for timeout -->", url)
                LOGGER.warning("<!-- %r -->", e)
                return ""
            except PlaywrightError as e:
                LOGGER.warning("<!-- Warning: can't connect to '%s' for temporary network error -->", url)
                LOGGER.warning("<!-- %r -->", e)
                return ""
            except Exception as e:
                LOGGER.warning("<!-- Warning: can't connect to '%s' for temporary network error -->", url)
                LOGGER.warning("<!-- %r -->", e)
                return ""

            if not self._wait_for_cloudflare(page):
                # The challenge never cleared, so the page still holds Cloudflare's
                # interstitial rather than the real content. Returning that HTML would make
                # the caller treat a block page as a successful fetch and skip its retry —
                # capture then extracts nothing. Discard the persisted clearance (so a
                # rejected/stale token isn't replayed), mark the session for teardown in the
                # finally block, and return "" so crawler.run()'s num_retries re-attempts on
                # a fresh browser session.
                challenge_cleared = False
                self._discard_persisted_cookies()
                LOGGER.warning("Cloudflare challenge unresolved for '%s'; returning empty to trigger retry", url)
                return ""

            # navigator.plugins / navigator.languages spoofing is intentionally removed:
            # cloakbrowser sets these at the C++ binary level. A JS-level override here
            # would replace the natural values with an Object.defineProperty signature
            # that fingerprinting scripts can detect.
            self._write_cookies_to_file(context)

            LOGGER.debug("executing a script for metadata")
            page.evaluate(self.GETTING_METADATA_SCRIPT)

            if self.copy_images_from_canvas:
                LOGGER.debug("converting canvas to images")
                page.evaluate(self.CONVERTING_CANVAS_TO_IMAGES_SCRIPT)

            if self.simulate_scrolling:
                LOGGER.debug("simulating scrolling")
                try:
                    self._run_scrolling_script(page)
                except PlaywrightTimeoutError:
                    LOGGER.warning("Scrolling script timed out, continuing...")

            if self.blob_to_dataurl:
                LOGGER.debug("converting blob to dataurl")
                page.evaluate(self.CONVERTING_BLOB_TO_DATAURL_SCRIPT)

            for option, waiting_div_id in ((self.copy_images_from_canvas, self.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS), (self.simulate_scrolling, self.ID_OF_RENDERING_COMPLETION_IN_SCROLLING), (self.blob_to_dataurl, self.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB)):
                if option:
                    self._wait_for_marker(page, waiting_div_id)

            LOGGER.debug("getting inner html")
            html = page.evaluate("document.documentElement.outerHTML")
            return f"<!DOCTYPE html>{html}" if html else ""

        except (PlaywrightError, PlaywrightTimeoutError) as e:
            # A renderer crash (TargetClosedError, "Target crashed") raised after
            # page.goto() — e.g. in _wait_for_cloudflare or page.evaluate — would
            # otherwise propagate and kill the whole run. Treat it like a goto crash:
            # warn and return "" so the caller's num_retries logic can re-attempt with
            # a fresh session (the cached one is invalidated in the finally block below).
            LOGGER.warning("<!-- Warning: can't get result from web page '%s' for renderer crash or error -->", url)
            LOGGER.warning("<!-- %r -->", e)
            return ""
        except (OSError, TypeError, ValueError, AttributeError, ImportError, RuntimeError) as e:
            LOGGER.error("Unexpected error in make_request: %s", e)
            return ""
        finally:
            if session is not None and not challenge_cleared:
                # An unresolved challenge means this browser is already flagged by
                # Cloudflare; an immediate re-nav on the same session is unlikely to clear.
                # Tear it down so crawler.run()'s retry relaunches a fresh session.
                self._cleanup_cached_session()
            elif session is not None:
                session_valid = True
                try:
                    session["page"].evaluate("window.localStorage.clear();")
                    session["page"].evaluate("window.sessionStorage.clear();")
                except PlaywrightError:
                    pass
                except Exception:
                    LOGGER.warning("Cached headless browser session is no longer responsive, invalidating cache")
                    self._cleanup_cached_session()
                    session_valid = False
                if session_valid:
                    try:
                        session["page"].goto("about:blank", wait_until="commit", timeout=5000)
                    except Exception:
                        # The about:blank reset doubles as a liveness probe: if it fails
                        # the session is dead (renderer crashed / target closed). A dead
                        # cloakbrowser session also keeps its profile's SingletonLock held,
                        # so the next launch for that (shared) profile dir would abort with
                        # "Failed to create a ProcessSingleton". Tear it down here so the
                        # session close releases any such lock before a retry relaunches.
                        LOGGER.warning("Headless browser session is dead, invalidating cache")
                        self._cleanup_cached_session()


# ---------------------------------------------------------------------------
# Engine selection & fallback facade
# ---------------------------------------------------------------------------

# Canonical per-engine cookie jar filenames. Kept here as the single source of
# truth so the engine subclasses and the facade never drift apart. Separate files
# stop the cloakbrowser (Chromium) and camoufox (Firefox) jars cross-contaminating.
ENGINE_COOKIE_FILES: dict[str, str] = {"camoufox": "cookies.camoufox.json", "cloakbrowser": "cookies.cloakbrowser.json"}
_ENGINE_NAMES: tuple[str, ...] = ("camoufox", "cloakbrowser")


def _import_engine_class(name: str) -> Optional[type["HeadlessBrowserBase"]]:
    # Import an engine class by name, tolerating a missing optional dependency
    # (camoufox / cloakbrowser not installed) by returning None. The engine modules
    # import only names defined ABOVE this point in this module, so this is not circular.
    try:
        if name == "camoufox":
            from bin.headless_browser_camoufox import HeadlessBrowserCamoufox

            return HeadlessBrowserCamoufox
        if name == "cloakbrowser":
            from bin.headless_browser_cloakbrowser import HeadlessBrowserCloakbrowser

            return HeadlessBrowserCloakbrowser
    except ImportError as e:  # pragma: no cover - only when an engine dep is absent
        LOGGER.warning("headless engine '%s' is unavailable: %s", name, e)
    return None


# Import the engine modules EAGERLY, once, at module load. run.py / crawler.py import
# this module single-threaded at startup, so the (relatively slow) camoufox import
# finishes before any worker thread runs. A previous lazy per-call import raced under
# the extractor's thread pool: a second thread hit headless_browser_camoufox while the
# first was still initializing it → "cannot import name ... partially initialized module".
_ENGINE_CLASSES: dict[str, type["HeadlessBrowserBase"]] = {}
for _engine_name in _ENGINE_NAMES:
    _engine_cls = _import_engine_class(_engine_name)
    if _engine_cls is not None:
        _ENGINE_CLASSES[_engine_name] = _engine_cls


def _load_engine_class(name: str) -> Optional[type["HeadlessBrowserBase"]]:
    # Accessor over the eagerly-populated registry; safe to call from any thread.
    return _ENGINE_CLASSES.get(name)


def _resolve_engine_order() -> list[str]:
    # FM_HEADLESS_BACKEND: comma-separated engine names in priority order. Default puts
    # camoufox first — its Firefox build clears the Cloudflare managed challenge on
    # tkor*/toonkor mirrors that the cloakbrowser Chromium (v146) no longer solves —
    # with cloakbrowser kept as a fallback for sites where the Firefox engine misbehaves.
    raw = Env.get("FM_HEADLESS_BACKEND", "camoufox,cloakbrowser")
    names = [n.strip().lower() for n in raw.split(",") if n.strip()]
    order = [n for n in names if n in _ENGINE_NAMES]
    return order or list(_ENGINE_NAMES)


class HeadlessBrowser:
    """Stealth-browser facade the crawler instantiates. Routes each request through
    the configured engines in priority order (camoufox by default, cloakbrowser as
    fallback), returning the first non-empty result. Preserves the public interface
    (make_request / login / _get_cookie_dir / COOKIE_FILE / cleanup classmethods)."""

    # Tracks the primary engine's jar so crawler's login-skip check reads the right file.
    COOKIE_FILE: str = ENGINE_COOKIE_FILES[_resolve_engine_order()[0]]

    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = kwargs
        self._engine_order = _resolve_engine_order()
        self._engines: dict[str, HeadlessBrowserBase] = {}

    def __getattr__(self, name: str) -> Any:
        # Only invoked for attributes not found normally. Delegate public attribute reads
        # (e.g. simulate_scrolling, copy_images_from_canvas, timeout, headers, dir_path) to
        # the primary engine so callers that introspect crawler.headless_browser keep working.
        # Guard underscore names to avoid recursion on internal attrs during __init__.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._primary, name)

    def _engine(self, name: str) -> Optional["HeadlessBrowserBase"]:
        if name not in self._engines:
            engine_cls = _load_engine_class(name)
            if engine_cls is None:
                return None
            self._engines[name] = engine_cls(**self._kwargs)
        return self._engines[name]

    @property
    def _primary(self) -> "HeadlessBrowserBase":
        for name in self._engine_order:
            engine = self._engine(name)
            if engine is not None:
                return engine
        raise ImportError("no headless browser engine is available (install camoufox or cloakbrowser)")

    def make_request(self, url: str, download_file: Optional[Path] = None) -> str:
        available = [n for n in self._engine_order if _load_engine_class(n) is not None]
        result = ""
        for i, name in enumerate(available):
            engine = self._engine(name)
            if engine is None:
                continue
            result = engine.make_request(url, download_file=download_file)
            if result:
                return result
            if i < len(available) - 1:
                # Tear down this engine's cached session before trying the next one. Both
                # engines drive playwright-sync, and only ONE sync-playwright instance can
                # be live per thread; a still-cached camoufox session would otherwise make
                # the cloakbrowser fallback abort with "Playwright Sync API inside the
                # asyncio loop". recycle_session() runs the engine's _close_session, which
                # fully stops its driver/event loop and frees the thread for the next launch.
                type(engine).recycle_session()
                LOGGER.warning("headless engine '%s' returned empty for '%s'; falling back to '%s'", name, url, available[i + 1])
        return result

    def login(self, config: dict[str, str]) -> bool:
        return self._primary.login(config)

    def _get_cookie_dir(self) -> Path:
        return self._primary._get_cookie_dir()

    def __del__(self) -> None:
        pass

    @classmethod
    def recycle_session(cls) -> None:
        for name in _ENGINE_NAMES:
            engine_cls = _load_engine_class(name)
            if engine_cls is not None:
                engine_cls.recycle_session()

    @classmethod
    def cleanup_all_sessions(cls) -> None:
        for name in _ENGINE_NAMES:
            engine_cls = _load_engine_class(name)
            if engine_cls is not None:
                engine_cls.cleanup_all_sessions()

    @classmethod
    def cleanup_all_drivers(cls) -> None:
        cls.cleanup_all_sessions()


def _handle_sigterm(signum: int, frame: object) -> None:
    HeadlessBrowser.cleanup_all_drivers()
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)
atexit.register(HeadlessBrowser.cleanup_all_drivers)
