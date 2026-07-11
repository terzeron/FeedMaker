#!/usr/bin/env python

import hashlib
import os
import socket
import tempfile
import threading
import time
from typing import Any, Optional

from bin.feed_maker_util import Env
from bin.headless_browser import ENGINE_COOKIE_FILES, LOGGER, HeadlessBrowserBase, PlaywrightError

try:
    from cloakbrowser import launch_persistent_context as _cloak_launch_persistent_context
except ImportError:  # pragma: no cover - exercised when cloakbrowser is unavailable.
    _cloak_launch_persistent_context = None


class HeadlessBrowserCloakbrowser(HeadlessBrowserBase):
    """Stealth engine backed by cloakbrowser's patched Chromium. Uses a persistent
    per-group user_data_dir, so it carries the SingletonLock contention handling that
    a shared Chromium profile requires."""

    COOKIE_FILE = ENGINE_COOKIE_FILES["cloakbrowser"]

    # Each engine keeps its OWN cache/profile registry so a cached cloakbrowser session
    # never collides with a cached camoufox session in the shared classmethod cache.
    _thread_local = threading.local()
    _all_profile_dirs: set[str] = set()

    # The profile dir is shared per feed group (group_hash = hash of the parent dir),
    # but Chromium permits only one live instance per user_data_dir. Concurrent feed
    # processes of the same group therefore contend for it; the loser must wait for the
    # owner to exit rather than crash. These bound that wait. Override the total wait
    # with FM_CRAWLER_PROFILE_LAUNCH_WAIT (seconds).
    PROFILE_LAUNCH_WAIT_SEC = 180
    PROFILE_LAUNCH_RETRY_INTERVAL_SEC = 3

    def _setup_profile(self) -> None:
        group_hash = hashlib.sha256(str(self.dir_path.parent).encode(), usedforsecurity=False).hexdigest()[:16]
        # cloakbrowser uses a patched Chromium 146.x binary — keep user_data_dir
        # separate from playwright's bundled Chromium to avoid profile schema clashes.
        self._profile_dir = os.path.join(tempfile.gettempdir(), "cloakbrowser-profiles", group_hash)
        os.makedirs(self._profile_dir, exist_ok=True)
        type(self)._all_profile_dirs.add(self._profile_dir)

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

    @staticmethod
    def _pid_owns_profile(pid: int, profile_dir: str) -> Optional[bool]:
        # Confirm a live pid is really the Chromium that holds THIS profile: its
        # argv carries `--user-data-dir=<profile_dir>`. After an unclean exit the
        # kernel can recycle the dead browser's pid onto an unrelated process, and
        # a bare liveness check then mistakes that for a live owner — keeping a
        # stale SingletonLock forever so the next launch fails with EEXIST. Returns
        # True (genuine owner), False (pid reused by an unrelated process), or None
        # when ownership can't be determined (no procfs), so the caller can fall
        # back to a conservative liveness-only decision off Linux.
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmdline = f.read()
        except FileNotFoundError:
            # procfs present but pid gone → not a live owner; no procfs at all → unknown.
            return False if os.path.isdir("/proc") else None
        except OSError:
            return None
        return profile_dir.encode() in cmdline

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
                # Liveness alone isn't enough: a recycled pid (the owning Chromium
                # died uncleanly and the kernel reassigned its pid) looks alive but
                # isn't the owner. Preserve the lock only for the genuine owner, or
                # when ownership can't be determined (off Linux) — never for a pid
                # confirmed to belong to an unrelated process.
                if cls._pid_owns_profile(pid, profile_dir) is not False:
                    return

        for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                os.unlink(os.path.join(profile_dir, name))
            except FileNotFoundError:
                pass
            except OSError as e:
                LOGGER.warning("Could not remove stale singleton artifact '%s': %s", name, e)

    def _launch_session(self) -> dict[str, Any]:
        if _cloak_launch_persistent_context is None:
            raise ImportError("cloakbrowser is not installed; run `pip install cloakbrowser`")

        # cloakbrowser bundles a patched Chromium binary with source-level stealth
        # patches (canvas, WebGL, audio, TLS, navigator.webdriver, etc.). No JS
        # injection of navigator.plugins / navigator.languages — those are handled
        # at the binary level and any user-space override becomes a detection signal.
        #
        # The profile dir is shared across a group's feeds, so a concurrent process
        # may already hold this Chromium instance. Each iteration first clears any
        # *stale* SingletonLock (owner died uncleanly), then attempts the launch; a
        # ProcessSingleton failure means a *live* owner still holds it, so wait and
        # retry until it exits or the bounded deadline passes. _clear_stale_singleton_lock
        # never breaks a live owner's lock, so this can't corrupt a running profile.
        wait_sec = int(Env.get("FM_CRAWLER_PROFILE_LAUNCH_WAIT", str(self.PROFILE_LAUNCH_WAIT_SEC)) or self.PROFILE_LAUNCH_WAIT_SEC)
        # Per-process jitter (no random import) so concurrent waiters don't retry in lockstep.
        interval = self.PROFILE_LAUNCH_RETRY_INTERVAL_SEC + (os.getpid() % 1000) / 1000.0
        deadline = time.monotonic() + wait_sec
        context = None
        while True:
            self._clear_stale_singleton_lock(self._profile_dir)
            try:
                # Do NOT override the user agent. cloakbrowser's patched Chromium sets the
                # UA string AND the matching Sec-CH-UA client hints from the bundled binary
                # version at the C++ level. Forcing a stale UA (e.g. an old Chrome/12x) here
                # leaves the client hints reporting the real binary version — a UA/client-hint
                # mismatch that Cloudflare flags as a bot, yielding a managed challenge that
                # never auto-solves. Let cloakbrowser present its native, self-consistent UA.
                context = _cloak_launch_persistent_context(user_data_dir=self._profile_dir, headless=not self.disable_headless, viewport={"width": 1920, "height": 1080}, locale="ko-KR", timezone="Asia/Seoul", humanize=True, ignore_https_errors=True)
                break
            except PlaywrightError as e:
                msg = str(e)
                is_singleton_contention = "ProcessSingleton" in msg or "already in use" in msg or "SingletonLock" in msg
                if is_singleton_contention and time.monotonic() < deadline:
                    LOGGER.warning("profile '%s' is in use by another process; waiting %.1fs to retry launch (%.0fs left)", self._profile_dir, interval, deadline - time.monotonic())
                    time.sleep(interval)
                    continue
                raise
        context.set_default_timeout(self.timeout * 1000)
        context.set_default_navigation_timeout(self.timeout * 1000)
        self._read_cookies_from_file(context)
        context.on("page", self._register_dialog_handlers)
        if self.blob_to_dataurl:
            context.add_init_script(self.BLOB_INTERCEPTOR_INIT_SCRIPT)
        page = context.pages[0] if context.pages else context.new_page()
        self._register_dialog_handlers(page)
        # cloakbrowser owns the Playwright instance and stops it on context.close().
        # We keep the key for shape compatibility with the other engine.
        return {"playwright": None, "context": context, "page": page}
