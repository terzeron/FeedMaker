#!/usr/bin/env python

import atexit
import hashlib
import json
import logging.config
import os
import shutil
import signal
import socket
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
    from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright
except ImportError:  # pragma: no cover - exercised via mocks when playwright is unavailable.
    PlaywrightError = Exception
    PlaywrightTimeoutError = TimeoutError
    BrowserContext = Any
    Page = Any
    Playwright = Any
    sync_playwright = None


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class HeadlessBrowser:
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS = "rendering_completed_in_converting_canvas"
    ID_OF_RENDERING_COMPLETION_IN_SCROLLING = "rendering_completed_in_scrolling"
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB = "rendering_completed_in_converting_blob"
    COOKIE_FILE = "cookies.headlessbrowser.json"
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

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
    _SCROLL_DOWN_STEP = 349  # px per scroll-down step
    _SCROLL_UP_STEP = 683  # px per scroll-up step
    _SCROLL_STEP_MS = 200  # ms between steps
    _MAX_SCROLL_SECS = 5  # max seconds per direction; keeps DOM small on infinite-scroll pages
    SETTING_PLUGINS_SCRIPT = "Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});"
    SETTING_LANGUAGES_SCRIPT = "Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})"
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
            "# HeadlessBrowserPlaywright(dir_path=%s, headers=%r, copy_images_from_canvas=%s, simulate_scrolling=%s, disable_headless=%s, blob_to_dataurl=%s, timeout=%d, wait_until=%s)",
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
            self.headers["User-Agent"] = HeadlessBrowser.DEFAULT_USER_AGENT
        self.copy_images_from_canvas: bool = copy_images_from_canvas
        self.simulate_scrolling: bool = simulate_scrolling
        self.disable_headless: bool = disable_headless
        self.blob_to_dataurl: bool = blob_to_dataurl
        self.timeout: int = timeout
        self.wait_until: str = wait_until
        self._cookie_dir: Optional[Path] = None
        self.allow_private_ips = Env.get("FM_CRAWLER_ALLOW_PRIVATE_IPS", "false").strip().lower() in ("1", "true", "yes", "on")
        self.allowed_hosts_raw = Env.get("FM_CRAWLER_ALLOWED_HOSTS", "")
        group_hash = hashlib.sha256(str(dir_path.parent).encode(), usedforsecurity=False).hexdigest()[:16]
        self._profile_dir: str = os.path.join(tempfile.gettempdir(), "playwright-profiles", group_hash)
        os.makedirs(self._profile_dir, exist_ok=True)
        HeadlessBrowser._all_profile_dirs.add(self._profile_dir)

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
            try:
                cache["context"].close()
            except Exception:
                try:
                    browser = cache["context"].browser
                    if browser:
                        browser.close()
                except Exception:
                    pass
            try:
                cache["playwright"].stop()
            except Exception:
                pass
            cls._thread_local._session_cache = None
            cls._thread_local._session_options_hash = None

    @classmethod
    def _cleanup_cached_driver(cls) -> None:
        cls._cleanup_cached_session()

    @classmethod
    def recycle_session(cls) -> None:
        # Chromium 인스턴스만 종료한다. user_data_dir(쿠키, localStorage)은 보존되어
        # 다음 launch_persistent_context 호출 시 로그인 상태가 유지된다.
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

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Process exists but is owned by another user.
            return True
        except OSError:
            return False
        return True

    @classmethod
    def _clear_stale_singleton_lock(cls, profile_dir: str) -> None:
        # Chromium guards a persistent profile with a `SingletonLock` symlink named
        # `<hostname>-<pid>`, removing it only on a clean exit. After an unclean exit
        # (SIGKILL / OOM-kill / crash — our atexit + SIGTERM cleanup never runs) the
        # lock survives, and the next launch on this deterministic profile dir fails
        # with `Failed to create a ProcessSingleton` (symlink → EEXIST). Break the
        # lock only when its owning process is gone, so a genuinely running instance
        # on this host is left untouched (a real concurrent conflict still surfaces).
        lock_path = os.path.join(profile_dir, "SingletonLock")
        try:
            target = os.readlink(lock_path)
        except FileNotFoundError:
            return
        except OSError:
            # Exists but is not a symlink — abnormal; treat it as stale.
            target = None

        if target is not None:
            host, _, pid_str = target.rpartition("-")
            try:
                pid = int(pid_str)
            except ValueError:
                pid = -1
            if host == socket.gethostname() and cls._pid_alive(pid):
                return

        for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                os.unlink(os.path.join(profile_dir, name))
            except FileNotFoundError:
                pass
            except OSError as e:
                LOGGER.warning("Could not remove stale singleton artifact '%s': %s", name, e)

    def _launch_session(self) -> dict[str, Any]:
        if sync_playwright is None:
            raise ImportError("playwright is not installed")

        # A previous run for this group may have died uncleanly and left a stale
        # SingletonLock in the (deterministic) profile dir; clear it before launch.
        self._clear_stale_singleton_lock(self._profile_dir)

        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=self._profile_dir,
            headless=not self.disable_headless,
            viewport={"width": 1920, "height": 1080},
            user_agent=self.headers["User-Agent"],
            locale="ko-KR",
            ignore_https_errors=True,
            args=["--disable-web-security", "--allow-running-insecure-content", "--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions", "--disable-plugins"],
        )
        context.set_default_timeout(self.timeout * 1000)
        context.set_default_navigation_timeout(self.timeout * 1000)
        self._read_cookies_from_file(context)
        context.on("page", self._register_dialog_handlers)
        if self.blob_to_dataurl:
            context.add_init_script(self.BLOB_INTERCEPTOR_INIT_SCRIPT)
        page = context.pages[0] if context.pages else context.new_page()
        self._register_dialog_handlers(page)
        return {"playwright": playwright, "context": context, "page": page}

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

    def _write_cookies_to_file(self, context: BrowserContext) -> None:
        cookies = context.cookies()
        cookie_file = self._get_cookie_dir() / HeadlessBrowser.COOKIE_FILE
        with cookie_file.open("w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

    def _read_cookies_from_file(self, context: BrowserContext) -> None:
        cookie_file = self._get_cookie_dir() / HeadlessBrowser.COOKIE_FILE
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

    _CLOUDFLARE_CHALLENGE_SELECTORS: tuple[str, ...] = ("#cf-content", 'iframe[src*="challenges.cloudflare.com"]', '[data-translate="checking_browser"]')

    def _wait_for_cloudflare(self, page: Page) -> None:
        for selector in self._CLOUDFLARE_CHALLENGE_SELECTORS:
            try:
                page.wait_for_selector(selector, state="hidden", timeout=self.timeout * 1000)
            except PlaywrightTimeoutError:
                pass

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
        LOGGER.debug("# HeadlessBrowserPlaywright.login(login_url=%s)", config["login_url"])
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
                LOGGER.info("HeadlessBrowserPlaywright login successful for '%s'", login_url)
                return True

            LOGGER.warning("HeadlessBrowserPlaywright login failed for '%s' (no cookies after submit)", login_url)
            return False

        except (OSError, TypeError, ValueError, AttributeError, ImportError, RuntimeError) as e:
            LOGGER.warning("HeadlessBrowserPlaywright login error: %s", e)
            return False

    def make_request(self, url: str, download_file: Optional[Path] = None) -> str:
        LOGGER.debug("# HeadlessBrowserPlaywright.make_request(url=%s, download_file=%s)", url, download_file)
        is_ok, reason = URLSafety.check_url(url, allow_private=self.allow_private_ips, allowed_hosts_raw=self.allowed_hosts_raw)
        if not is_ok:
            LOGGER.warning("Blocked URL: %s (%s)", url, reason)
            return ""

        session: Optional[dict[str, Any]] = None

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

            self._wait_for_cloudflare(page)

            LOGGER.debug("executing some scripts")
            page.evaluate(self.SETTING_PLUGINS_SCRIPT)
            page.evaluate(self.SETTING_LANGUAGES_SCRIPT)
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
            # page.content() has no timeout; use evaluate() which respects set_default_timeout
            html = page.evaluate("document.documentElement.outerHTML")
            return f"<!DOCTYPE html>{html}" if html else ""

        except (OSError, TypeError, ValueError, AttributeError, ImportError, RuntimeError) as e:
            LOGGER.error("Unexpected error in make_request: %s", e)
            return ""
        finally:
            if session is not None:
                session_valid = True
                try:
                    session["page"].evaluate("window.localStorage.clear();")
                    session["page"].evaluate("window.sessionStorage.clear();")
                except PlaywrightError:
                    pass
                except Exception:
                    LOGGER.warning("Cached Playwright session is no longer responsive, invalidating cache")
                    self._cleanup_cached_session()
                    session_valid = False
                if session_valid:
                    try:
                        session["page"].goto("about:blank", wait_until="commit", timeout=5000)
                    except Exception:
                        pass


def _handle_sigterm(signum: int, frame: object) -> None:
    HeadlessBrowser.cleanup_all_drivers()
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)
atexit.register(HeadlessBrowser.cleanup_all_drivers)
