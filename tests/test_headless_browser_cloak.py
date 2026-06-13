#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from bin.headless_browser_cloak import HeadlessBrowser, PlaywrightError, PlaywrightTimeoutError


def _wait_for_proc_cmdline(pid: int, needle: str, timeout: float = 5.0) -> None:
    """Block until a freshly spawned child's argv is visible in procfs.

    subprocess.Popen returns the moment the child is forked, but /proc/<pid>/cmdline
    stays empty until the child finishes execve and commits its new argv. A test that
    reads cmdline inside that fork→exec window sees an empty buffer (~94% of the time
    on a cold process under load), so the SingletonLock owner check misreads a live,
    profile-owning process as "not the owner" and deletes its lock. Wait for the argv
    to actually appear before exercising the lock logic so the test is deterministic.
    """
    deadline = time.monotonic() + timeout
    needle_b = needle.encode()
    while time.monotonic() < deadline:
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if needle_b in f.read():
                    return
        except OSError:
            pass
        time.sleep(0.005)


class TestHeadlessBrowserCloak(unittest.TestCase):
    def setUp(self):
        HeadlessBrowser.cleanup_all_sessions()

    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser_cloak.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            defaults = dict(dir_path=Path(tempfile.gettempdir()), timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowser(**defaults)

    def _build_session_mocks(self):
        """cloakbrowser.launch_persistent_context returns a Playwright BrowserContext
        directly (it owns the Playwright instance internally and stops it on
        context.close()). So unlike the playwright wrapper there is no
        sync_playwright().start() → chromium.launch_persistent_context() chain
        to mock — we patch the launch function and return the context."""
        mock_page = MagicMock()
        mock_page.url = "about:blank"
        mock_page.content.return_value = "<html>ok</html>"
        mock_page.locator.return_value.first = MagicMock()

        mock_context = MagicMock()
        mock_context.pages = [mock_page]
        mock_context.cookies.return_value = []

        return mock_context, mock_page

    # -------------------------- cloak-specific invariants --------------------------

    def test_cookie_file_is_cloak_specific(self):
        # 분리된 파일명을 써야 playwright 백엔드와 cross-contamination이 없다.
        self.assertEqual(HeadlessBrowser.COOKIE_FILE, "cookies.cloakbrowser.json")

    def test_profile_dir_uses_cloakbrowser_namespace(self):
        # Chromium 버전이 다른 두 백엔드가 같은 user_data_dir를 공유하면 profile schema가 깨진다.
        browser = self._make_browser(dir_path=Path("/tmp/some_feed_dir"))
        self.assertIn("cloakbrowser-profiles", browser._profile_dir)
        self.assertNotIn("playwright-profiles", browser._profile_dir)

    def test_no_navigator_override_script_constants(self):
        # CloakBrowser는 navigator.plugins / navigator.languages를 C++ 바이너리에서 처리한다.
        # JS-level override (Object.defineProperty)는 오히려 detection signature가 되므로
        # 이 클래스에는 SETTING_PLUGINS_SCRIPT / SETTING_LANGUAGES_SCRIPT가 존재하면 안 된다.
        self.assertFalse(hasattr(HeadlessBrowser, "SETTING_PLUGINS_SCRIPT"))
        self.assertFalse(hasattr(HeadlessBrowser, "SETTING_LANGUAGES_SCRIPT"))

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_passes_stealth_kwargs(self, mock_launch):
        browser = self._make_browser()
        mock_context, _mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        browser._launch_session()

        mock_launch.assert_called_once()
        kwargs = mock_launch.call_args.kwargs
        self.assertEqual(kwargs.get("locale"), "ko-KR")
        self.assertEqual(kwargs.get("timezone"), "Asia/Seoul")
        self.assertTrue(kwargs.get("humanize"))
        self.assertTrue(kwargs.get("ignore_https_errors"))
        self.assertEqual(kwargs.get("viewport"), {"width": 1920, "height": 1080})
        self.assertIn("user_data_dir", kwargs)
        # 이전 헤드리스 args가 들어가면 stealth가 깨진다 (--disable-plugins, --disable-gpu 등).
        self.assertNotIn("args", kwargs)

    @staticmethod
    def _dead_pid():
        # A pid that is guaranteed dead: spawn a trivial process and reap it.
        p = subprocess.Popen(["true"])
        p.wait()
        return p.pid

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_clears_stale_singleton_lock(self, mock_launch):
        # 비정상 종료로 남은 SingletonLock(소유 프로세스 죽음)은 launch 전에 제거되어야 한다.
        base = Path(tempfile.mkdtemp())
        browser = self._make_browser(dir_path=base / "feed")
        mock_context, _ = self._build_session_mocks()
        mock_launch.return_value = mock_context

        profile_dir = Path(browser._profile_dir)
        lock_path = profile_dir / "SingletonLock"
        lock_path.symlink_to(f"{socket.gethostname()}-{self._dead_pid()}")
        (profile_dir / "SingletonCookie").symlink_to("12345/678")
        (profile_dir / "SingletonSocket").symlink_to("/tmp/ws-sock")
        self.assertTrue(lock_path.is_symlink())

        browser._launch_session()

        self.assertFalse(lock_path.is_symlink(), "stale SingletonLock must be removed before launch")
        self.assertFalse((profile_dir / "SingletonCookie").is_symlink())
        self.assertFalse((profile_dir / "SingletonSocket").is_symlink())
        shutil.rmtree(base, ignore_errors=True)

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_preserves_live_singleton_lock(self, mock_launch):
        # 이 profile dir를 실제로 점유한 살아있는 Chromium(= argv에 user-data-dir
        # 포함)이 소유한 lock은 제거하면 안 된다 (정상 동시 사용 보호).
        base = Path(tempfile.mkdtemp())
        browser = self._make_browser(dir_path=base / "feed")
        mock_context, _ = self._build_session_mocks()
        mock_launch.return_value = mock_context

        profile_dir = Path(browser._profile_dir)
        # argv에 profile dir가 들어간 살아있는 프로세스 = 진짜 소유자처럼 보인다.
        proc = subprocess.Popen([sys.executable, "-c", "import sys, time; time.sleep(60)", str(profile_dir)])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        # The owner check reads /proc/<pid>/cmdline; wait until execve has committed
        # the argv (incl. profile_dir) so we test the live-owner steady state, not the
        # fork→exec window where cmdline is still empty.
        _wait_for_proc_cmdline(proc.pid, str(profile_dir))

        lock_path = profile_dir / "SingletonLock"
        lock_path.symlink_to(f"{socket.gethostname()}-{proc.pid}")

        browser._launch_session()

        self.assertTrue(lock_path.is_symlink(), "live SingletonLock owned by this profile must NOT be removed")
        shutil.rmtree(base, ignore_errors=True)

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_clears_lock_when_pid_reused(self, mock_launch):
        # PID 재사용: unclean exit로 남은 lock이 가리키는 pid를 OS가 이 profile과
        # 무관한 다른 살아있는 프로세스에 재할당한 경우. 단순 liveness 검사만으로는
        # stale lock을 영원히 보존해 다음 launch가 EEXIST(ProcessSingleton)로 실패한다.
        base = Path(tempfile.mkdtemp())
        browser = self._make_browser(dir_path=base / "feed")
        mock_context, _ = self._build_session_mocks()
        mock_launch.return_value = mock_context

        # 이 profile dir와 전혀 무관한 살아있는 프로세스 (argv에 profile dir 없음).
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)

        profile_dir = Path(browser._profile_dir)
        lock_path = profile_dir / "SingletonLock"
        lock_path.symlink_to(f"{socket.gethostname()}-{proc.pid}")
        self.assertTrue(lock_path.is_symlink())

        browser._launch_session()

        self.assertFalse(lock_path.is_symlink(), "lock owned by a reused (unrelated) pid must be treated as stale")
        shutil.rmtree(base, ignore_errors=True)

    @patch("bin.headless_browser_cloak.time.sleep")
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_retries_on_process_singleton_contention(self, mock_launch, mock_sleep):
        # 같은 그룹의 다른 프로세스가 공유 프로파일을 점유 중이면 launch가 ProcessSingleton으로
        # 실패한다. 즉시 죽지 말고 소유자가 끝날 때까지 대기 후 재시도해 성공해야 한다.
        browser = self._make_browser()
        mock_context, _ = self._build_session_mocks()
        mock_launch.side_effect = [PlaywrightError("BrowserType.launch_persistent_context: Failed to create a ProcessSingleton for your profile directory."), mock_context]
        with patch.object(HeadlessBrowser, "_clear_stale_singleton_lock") as mock_clear:
            session = browser._launch_session()

        self.assertIs(session["context"], mock_context)
        self.assertEqual(mock_launch.call_count, 2)
        # 매 시도 전 stale lock 정리를 호출한다(대기 중 소유자가 죽으면 lock을 깨기 위해).
        self.assertEqual(mock_clear.call_count, 2)
        mock_sleep.assert_called()  # 재시도 사이에 대기했다

    @patch("bin.headless_browser_cloak.Env.get")
    @patch("bin.headless_browser_cloak.time.sleep")
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_gives_up_on_persistent_contention(self, mock_launch, mock_sleep, mock_env_get):
        # 대기 한도(0초)를 넘기면 재시도하지 않고 에러를 전파한다 → 상위 Layer B가 ""로 흡수.
        mock_env_get.side_effect = lambda k, d="": "0" if k == "FM_CRAWLER_PROFILE_LAUNCH_WAIT" else d
        browser = self._make_browser()
        mock_launch.side_effect = PlaywrightError("Failed to create a ProcessSingleton for your profile directory.")
        with patch.object(HeadlessBrowser, "_clear_stale_singleton_lock"):
            with self.assertRaises(PlaywrightError):
                browser._launch_session()
        mock_sleep.assert_not_called()  # deadline이 이미 지나 대기 없이 즉시 포기

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context", None)
    def test_launch_session_import_error_when_cloak_unavailable(self):
        browser = self._make_browser()
        with self.assertRaises(ImportError):
            browser._launch_session()

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_does_not_inject_navigator_overrides(self, mock_launch, _mock_check):
        # make_request 본문이 navigator.plugins / navigator.languages를 JS로 덮어쓰면 안 된다.
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        def evaluate_side_effect(script, *_a, **_kw):
            s = str(script)
            if "outerHTML" in s:
                return "<html>ok</html>"
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        browser.make_request("https://example.com")

        for call in mock_page.evaluate.call_args_list:
            if not call.args:
                continue
            script = str(call.args[0])
            self.assertNotIn("navigator, 'plugins'", script)
            self.assertNotIn("navigator, 'languages'", script)
            self.assertNotIn("navigator.plugins =", script)
            self.assertNotIn("navigator.languages =", script)

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_returns_empty_on_renderer_crash_in_metadata_eval(self, mock_launch, _mock_check):
        # 렌더러가 page.goto() 이후 page.evaluate() 도중 크래시하면 ("Target crashed")
        # 예외가 전파되어 프로세스 전체를 죽이면 안 된다. goto 크래시와 동일하게 ""를 돌려줘
        # 상위 num_retries 재시도가 동작하게 해야 한다.
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_page.evaluate.side_effect = PlaywrightError("Page.evaluate: Target crashed")

        result = browser.make_request("https://example.com")

        self.assertEqual(result, "")

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_returns_empty_on_renderer_crash_in_cloudflare_wait(self, mock_launch, _mock_check):
        # _wait_for_cloudflare()의 wait_for_function이 렌더러 크래시로 TargetClosedError를
        # 던지면 (PlaywrightTimeoutError가 아님) 역시 ""를 돌려줘야 한다.
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_page.wait_for_function.side_effect = PlaywrightError("Target page, context or browser has been closed")

        result = browser.make_request("https://example.com")

        self.assertEqual(result, "")

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_invalidates_dead_session_to_release_profile_lock(self, mock_launch, _mock_check):
        # 렌더러 크래시로 세션이 죽으면, 같은 (공유) 프로파일 dir의 SingletonLock이 잡힌 채
        # 남아 다음 launch가 ProcessSingleton 에러로 실패한다. make_request는 finally에서
        # 죽은 세션을 감지해 _cleanup_cached_session()으로 context를 닫아 lock을 풀어야 한다.
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        # 본문 evaluate(metadata)와 finally의 storage clear 모두 크래시로 실패시킨다.
        mock_page.evaluate.side_effect = PlaywrightError("Page.evaluate: Target crashed")

        # about:blank 리셋(=liveness probe)도 죽은 타깃이라 실패한다.
        def goto_side_effect(target, **_kw):
            if "about:blank" in str(target):
                raise PlaywrightError("Target page, context or browser has been closed")
            return None

        mock_page.goto.side_effect = goto_side_effect

        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "")
        mock_cleanup.assert_called()

    def test_cleanup_cached_session_does_not_require_playwright_stop(self):
        # cloakbrowser는 context.close() 안에서 자기가 만든 Playwright instance를 stop한다.
        # 따라서 cache["playwright"]가 None이어도 cleanup이 깨지면 안 된다.
        session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"

        HeadlessBrowser._cleanup_cached_session()

        session["context"].close.assert_called_once()
        self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_session_cache", None))

    # -------------------------- parity with playwright wrapper --------------------------

    def test_get_cookie_dir_non_writable(self):
        browser = self._make_browser(dir_path=Path("/nonexistent/readonly"))
        with patch("os.access", return_value=False):
            result = browser._get_cookie_dir()
        self.assertIn("fm_cookies", str(result))
        self.assertTrue(result.exists())

    def test_options_hash_and_cached_session_paths(self):
        options = {"headless": True, "profile_dir": "/tmp/p1"}
        session = {"page": MagicMock(url="about:blank"), "context": MagicMock(), "playwright": None}
        HeadlessBrowser._set_cached_session(session, options)
        self.assertIs(HeadlessBrowser._get_cached_session(options), session)

        other = {"headless": False, "profile_dir": "/tmp/p1"}
        self.assertIsNone(HeadlessBrowser._get_cached_session(other))

        HeadlessBrowser._set_cached_session(session, options)
        type(session["page"]).url = PropertyMock(side_effect=RuntimeError("dead"))
        self.assertIsNone(HeadlessBrowser._get_cached_session(options))

    def test_cleanup_cached_session_tolerates_close_errors(self):
        session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        session["context"].close.side_effect = RuntimeError("close failed")
        session["context"].browser = None
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"

        HeadlessBrowser._cleanup_cached_session()

        self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_session_cache", None))

    def test_cleanup_aliases_and_all_sessions(self):
        profile_dir = tempfile.mkdtemp()
        HeadlessBrowser._all_profile_dirs.add(profile_dir)
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            HeadlessBrowser._cleanup_cached_driver()
            HeadlessBrowser.cleanup_all_drivers()
            self.assertEqual(mock_cleanup.call_count, 2)

        session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"
        HeadlessBrowser.cleanup_all_sessions()
        self.assertFalse(Path(profile_dir).exists())

    def test_del_does_not_touch_cloak(self):
        # __del__이 Playwright/cloak API를 호출하면 GC 타이밍에 따라 sync 루프 안에서
        # context.close()가 호출되어 deadlock된다. 명시적 cleanup만 사용해야 한다.
        browser = self._make_browser()
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            browser.__del__()
            mock_cleanup.assert_not_called()

    def test_recycle_session_preserves_profile_dirs(self):
        profile_dir = tempfile.mkdtemp()
        HeadlessBrowser._all_profile_dirs.add(profile_dir)
        session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        HeadlessBrowser._thread_local._session_cache = session
        HeadlessBrowser._thread_local._session_options_hash = "hash"
        try:
            HeadlessBrowser.recycle_session()
            self.assertIsNone(getattr(HeadlessBrowser._thread_local, "_session_cache", None))
            self.assertTrue(Path(profile_dir).exists(), "profile dir must survive recycle_session for cookie persistence")
            self.assertIn(profile_dir, HeadlessBrowser._all_profile_dirs)
        finally:
            HeadlessBrowser._all_profile_dirs.discard(profile_dir)
            shutil.rmtree(profile_dir, ignore_errors=True)

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_login_success(self, mock_launch):
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_context.cookies.return_value = [{"name": "sid", "value": "abc"}]

        id_locator = MagicMock()
        pw_locator = MagicMock()
        submit_locator = MagicMock()

        def locator_side_effect(selector):
            locator = MagicMock()
            if selector == "input[type='text'], input[type='email'], input[type='tel']":
                locator.first = id_locator
            elif selector == "input[type='password']":
                locator.first = pw_locator
            elif selector == "button[type='submit'], input[type='submit']":
                locator.first = submit_locator
            else:
                raise AssertionError(selector)
            return locator

        mock_page.locator.side_effect = locator_side_effect

        with patch.object(browser, "_write_cookies_to_file") as mock_write:
            result = browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"})

        self.assertTrue(result)
        mock_page.goto.assert_called_once()
        id_locator.wait_for.assert_called_once()
        id_locator.fill.assert_called_once_with("tester")
        pw_locator.fill.assert_called_once_with("secret")
        submit_locator.click.assert_called_once()
        mock_write.assert_called_once_with(mock_context)

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_login_success_with_named_fields_and_submit_fallback(self, mock_launch):
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_context.cookies.return_value = [{"name": "sid", "value": "abc"}]

        id_locator = MagicMock()
        pw_locator = MagicMock()
        submit_locator = MagicMock()
        submit_locator.click.side_effect = PlaywrightError("click fail")

        def locator_side_effect(selector):
            locator = MagicMock()
            if selector == '[name="user\\"name"]':
                locator.first = id_locator
            elif selector == '[name="password"]':
                locator.first = pw_locator
            elif selector == "button[type='submit'], input[type='submit']":
                locator.first = submit_locator
            else:
                raise AssertionError(selector)
            return locator

        mock_page.locator.side_effect = locator_side_effect
        mock_page.wait_for_function.side_effect = PlaywrightTimeoutError("stay")

        result = browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret", "id_field": 'user"name', "password_field": "password"})

        self.assertTrue(result)
        pw_locator.press.assert_called_once_with("Enter")

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_login_field_lookup_failure_and_runtime_error(self, mock_launch):
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_page.locator.side_effect = PlaywrightTimeoutError("missing")
        self.assertFalse(browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

        browser2 = self._make_browser()
        with patch.object(browser2, "_get_or_create_session", side_effect=RuntimeError("boom")):
            self.assertFalse(browser2.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_login_no_cookies_after_submit(self, mock_launch):
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_context.cookies.return_value = []

        id_locator = MagicMock()
        pw_locator = MagicMock()
        submit_locator = MagicMock()

        def locator_side_effect(selector):
            locator = MagicMock()
            if selector == "input[type='text'], input[type='email'], input[type='tel']":
                locator.first = id_locator
            elif selector == "input[type='password']":
                locator.first = pw_locator
            elif selector == "button[type='submit'], input[type='submit']":
                locator.first = submit_locator
            else:
                raise AssertionError(selector)
            return locator

        mock_page.locator.side_effect = locator_side_effect
        self.assertFalse(browser.login({"login_url": "https://example.com/login", "id": "tester", "password": "secret"}))

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(False, "blocked"))
    def test_make_request_blocked(self, _mock_check):
        browser = self._make_browser()
        self.assertEqual(browser.make_request("https://blocked.example.com"), "")

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_with_all_options(self, mock_launch, _mock_check):
        browser = self._make_browser(copy_images_from_canvas=True, simulate_scrolling=True, blob_to_dataurl=True, headers={"User-Agent": "test", "Referer": "https://referer.example.com"})
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        def evaluate_side_effect(script, *_args, **_kwargs):
            s = str(script)
            if "scrollHeight" in s:
                return 1000
            if "outerHTML" in s:
                return "<html>ok</html>"
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        result = browser.make_request("https://example.com")

        self.assertEqual(result, "<!DOCTYPE html><html>ok</html>")
        self.assertEqual(mock_page.goto.call_count, 3)  # referer + main URL + about:blank
        # cloak는 plugins/languages 스크립트가 없어야 한다.
        for call in mock_page.evaluate.call_args_list:
            if call.args:
                self.assertNotIn("navigator, 'plugins'", str(call.args[0]))
                self.assertNotIn("navigator, 'languages'", str(call.args[0]))
        # 다른 콘텐츠 스크립트는 그대로 호출돼야 한다.
        self.assertTrue(any(call.args[0] == browser.GETTING_METADATA_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT for call in mock_page.evaluate.call_args_list))
        self.assertTrue(any(call.args[0] == browser.CONVERTING_BLOB_TO_DATAURL_SCRIPT for call in mock_page.evaluate.call_args_list))
        scroll_calls = [c for c in mock_page.evaluate.call_args_list if c.args and "scrollTo" in str(c.args[0])]
        self.assertGreater(len(scroll_calls), 0)
        self.assertTrue(any(browser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING in str(call.args[0]) for call in mock_page.evaluate.call_args_list))
        # _wait_for_cloudflare now polls a single wait_for_function predicate per page
        # (referer + main = 2); wait_for_selector is left to the 3 completion markers.
        self.assertEqual(mock_page.wait_for_function.call_count, 2)
        self.assertEqual(mock_page.wait_for_selector.call_count, 3)
        mock_context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_make_request_returns_empty_when_cloudflare_unresolved(self, mock_launch, _mock_check):
        # If the managed challenge never clears, make_request must return "" (not the
        # interstitial HTML) so crawler.run() retries, discard the persisted clearance so a
        # rejected token isn't replayed, and tear the session down so the retry starts fresh.
        browser = self._make_browser()
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_page.wait_for_function.side_effect = PlaywrightTimeoutError("challenge stuck")

        with patch.object(browser, "_discard_persisted_cookies") as mock_discard:
            result = browser.make_request("https://example.com")

        self.assertEqual(result, "")
        mock_discard.assert_called_once()
        # outerHTML must not be captured from an unresolved challenge page.
        self.assertFalse(any(c.args and "outerHTML" in str(c.args[0]) for c in mock_page.evaluate.call_args_list))
        # The flagged session is torn down (context.close) so the retry relaunches fresh.
        mock_context.close.assert_called_once()

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_launch_session_and_register_handlers(self, mock_launch):
        browser = self._make_browser(blob_to_dataurl=True)
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        session = browser._launch_session()

        self.assertIs(session["page"], mock_page)
        self.assertIsNone(session["playwright"])  # cloak owns the Playwright instance
        mock_launch.assert_called_once()
        mock_context.set_default_timeout.assert_called_once_with(browser.timeout * 1000)
        mock_context.set_default_navigation_timeout.assert_called_once_with(browser.timeout * 1000)
        mock_context.on.assert_called_once()
        mock_context.add_init_script.assert_called_once_with(browser.BLOB_INTERCEPTOR_INIT_SCRIPT)
        mock_page.on.assert_called_once()

    def test_register_dialog_handlers_swallows_errors(self):
        page = MagicMock()
        page.on.side_effect = RuntimeError("no handler")
        HeadlessBrowser._register_dialog_handlers(page)
        page.on.assert_called_once()

    def test_get_or_create_session_reuses_and_relaunches(self):
        browser = self._make_browser()
        mock_page = MagicMock()
        session = {"page": mock_page, "context": MagicMock(), "playwright": None}
        with patch.object(browser, "_build_session_options", return_value={"x": 1}), patch.object(HeadlessBrowser, "_get_cached_session", return_value=session):
            reused, created = browser._get_or_create_session()
        self.assertIs(reused, session)
        self.assertFalse(created)

        browser2 = self._make_browser()
        bad_session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        bad_session["page"].set_default_timeout.side_effect = RuntimeError("dead")
        new_session = {"page": MagicMock(), "context": MagicMock(), "playwright": None}
        with patch.object(browser2, "_build_session_options", return_value={"x": 2}), patch.object(HeadlessBrowser, "_get_cached_session", return_value=bad_session), patch.object(browser2, "_launch_session", return_value=new_session) as mock_launch, patch.object(HeadlessBrowser, "_set_cached_session") as mock_set:
            reused, created = browser2._get_or_create_session()
        self.assertIs(reused, new_session)
        self.assertTrue(created)
        mock_launch.assert_called_once()
        mock_set.assert_called_once()

    def test_read_cookies_from_file_normalizes_expiry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text(json.dumps([{"name": "sid", "value": "abc", "domain": ".example.com", "expiry": 1234}]), encoding="utf-8")
            mock_context = MagicMock()

            browser._read_cookies_from_file(mock_context)

            cookies = mock_context.add_cookies.call_args.args[0]
            self.assertEqual(cookies[0]["expires"], 1234)
            self.assertNotIn("expiry", cookies[0])
            self.assertEqual(cookies[0]["path"], "/")

    def test_read_cookies_from_file_removes_empty_expires(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text(json.dumps([{"name": "sid", "value": "abc", "domain": ".example.com", "expires": ""}]), encoding="utf-8")
            mock_context = MagicMock()

            browser._read_cookies_from_file(mock_context)

            cookies = mock_context.add_cookies.call_args.args[0]
            self.assertNotIn("expires", cookies[0])

    def test_read_cookies_missing_and_corrupt_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            mock_context = MagicMock()
            browser._read_cookies_from_file(mock_context)
            mock_context.add_cookies.assert_not_called()

            cookie_file = Path(tmpdir) / browser.COOKIE_FILE
            cookie_file.write_text("{bad json", encoding="utf-8")
            browser._read_cookies_from_file(mock_context)
            self.assertFalse(cookie_file.exists())

    def test_quote_attr_and_wait_helpers(self):
        browser = self._make_browser()
        self.assertEqual(browser._quote_attr('a"b\\c'), 'a\\"b\\\\c')

        page = MagicMock()
        # _wait_for_cloudflare polls wait_for_function; _wait_for_marker uses
        # wait_for_selector. Both must swallow a timeout without raising.
        page.wait_for_function.side_effect = PlaywrightTimeoutError("cf timeout")
        page.wait_for_selector.side_effect = PlaywrightTimeoutError("marker timeout")
        self.assertFalse(browser._wait_for_cloudflare(page))
        browser._wait_for_marker(page, "marker")
        page.wait_for_function.assert_called_once_with(browser._CLOUDFLARE_CLEARED_PREDICATE, timeout=browser._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC * 1000)

    def test_wait_for_cloudflare_predicate_detects_modern_challenge(self):
        # The cleared-predicate must recognise the modern managed-challenge / Turnstile
        # signals, not just the legacy selectors — otherwise it returns instantly and
        # the interstitial HTML leaks through.
        browser = self._make_browser()
        predicate = browser._CLOUDFLARE_CLEARED_PREDICATE
        self.assertIn("_cf_chl_opt", predicate)
        self.assertIn("challenges.cloudflare.com", predicate)
        self.assertIn("잠시만", predicate)
        # Must also require a populated body, so the post-challenge reload finishes
        # before capture instead of yielding head-only HTML (interactive Turnstile).
        self.assertIn("document.body", predicate)
        self.assertIn("children.length", predicate)

        page = MagicMock()
        self.assertTrue(browser._wait_for_cloudflare(page))
        page.wait_for_function.assert_called_once_with(predicate, timeout=browser._CLOUDFLARE_CHALLENGE_TIMEOUT_SEC * 1000)

    def test_write_cookies_persists_clearance_drops_transient_cookies(self):
        # cf_clearance is the multi-hour clearance token and is persisted so a later run can
        # skip the managed challenge. __cf_bm / __cf_chl* are short-lived, challenge-bound
        # cookies and must never be written (replaying them only re-triggers a challenge).
        with tempfile.TemporaryDirectory() as tmpdir:
            browser = self._make_browser(dir_path=Path(tmpdir))
            mock_context = MagicMock()
            mock_context.cookies.return_value = [{"name": "sid", "value": "keep", "domain": ".example.com"}, {"name": "cf_clearance", "value": "keep", "domain": ".example.com"}, {"name": "__cf_bm", "value": "drop", "domain": ".example.com"}, {"name": "__cf_chl_tk", "value": "drop", "domain": ".example.com"}]
            browser._write_cookies_to_file(mock_context)
            saved = json.loads((Path(tmpdir) / browser.COOKIE_FILE).read_text(encoding="utf-8"))
            self.assertEqual({c["name"] for c in saved}, {"sid", "cf_clearance"})

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    @patch("bin.headless_browser_cloak.URLSafety.check_url")
    def test_make_request_referer_blocked_and_navigation_errors(self, mock_check, mock_launch):
        browser = self._make_browser(headers={"User-Agent": "test", "Referer": "https://referer.example.com"})
        mock_context, _mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_check.side_effect = [(True, ""), (False, "blocked referer")]
        self.assertEqual(browser.make_request("https://example.com"), "")

        browser2 = self._make_browser()
        mock_context2, page2 = self._build_session_mocks()
        mock_launch.return_value = mock_context2
        mock_check.side_effect = [(True, "")]
        page2.goto.side_effect = PlaywrightTimeoutError("timeout")
        self.assertEqual(browser2.make_request("https://example.com"), "")

        browser3 = self._make_browser()
        mock_context3, page3 = self._build_session_mocks()
        mock_launch.return_value = mock_context3
        mock_check.side_effect = [(True, "")]
        page3.goto.side_effect = PlaywrightError("network")
        self.assertEqual(browser3.make_request("https://example.com"), "")

    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    def test_make_request_scrolling_timeout_outer_error_and_finally_invalidation(self, _mock_check, mock_launch):
        browser = self._make_browser(simulate_scrolling=True)
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context
        mock_page.evaluate.return_value = "<html>ok</html>"
        with patch.object(browser, "_run_scrolling_script", side_effect=PlaywrightTimeoutError("scroll timeout")):
            self.assertEqual(browser.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")

        browser2 = self._make_browser()
        with patch.object(browser2, "_get_or_create_session", side_effect=RuntimeError("boom")):
            self.assertEqual(browser2.make_request("https://example.com"), "")

        browser3 = self._make_browser()
        mock_context3, page3 = self._build_session_mocks()
        mock_launch.return_value = mock_context3
        # cloak는 plugins/languages 호출이 없으니 evaluate 시퀀스가 짧다:
        # GETTING_METADATA_SCRIPT(None) + outerHTML + localStorage.clear(raises)
        page3.evaluate.side_effect = [None, "<html>ok</html>", RuntimeError("dead storage")]
        with patch.object(HeadlessBrowser, "_cleanup_cached_session") as mock_cleanup:
            self.assertEqual(browser3.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")
        self.assertGreaterEqual(mock_cleanup.call_count, 1)
        HeadlessBrowser._cleanup_cached_session()

        browser4 = self._make_browser()
        mock_context4, page4 = self._build_session_mocks()
        mock_launch.return_value = mock_context4
        page4.goto.side_effect = RuntimeError("weird failure")
        self.assertEqual(browser4.make_request("https://example.com"), "")
        HeadlessBrowser._cleanup_cached_session()

        browser5 = self._make_browser()
        mock_context5, page5 = self._build_session_mocks()
        mock_launch.return_value = mock_context5
        # cloak: GETTING_METADATA_SCRIPT(None) + outerHTML + two clear() calls raise PlaywrightError
        page5.evaluate.side_effect = [None, "<html>ok</html>", PlaywrightError("clear failed"), PlaywrightError("clear failed")]
        self.assertEqual(browser5.make_request("https://example.com"), "<!DOCTYPE html><html>ok</html>")

    def test_wait_until_default_is_domcontentloaded(self):
        browser = self._make_browser()
        self.assertEqual(browser.wait_until, "domcontentloaded")

    def test_wait_until_custom_value_stored(self):
        browser = self._make_browser(wait_until="load")
        self.assertEqual(browser.wait_until, "load")

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_wait_until_passed_to_goto(self, mock_launch, _mock_check):
        browser = self._make_browser(wait_until="domcontentloaded")
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        browser.make_request("https://example.com")

        goto_calls = mock_page.goto.call_args_list
        url_goto_calls = [c for c in goto_calls if c.args and c.args[0] != "about:blank"]
        self.assertTrue(all(c.kwargs.get("wait_until") == "domcontentloaded" for c in url_goto_calls))

    @patch("bin.headless_browser_cloak.URLSafety.check_url", return_value=(True, ""))
    @patch("bin.headless_browser_cloak._cloak_launch_persistent_context")
    def test_wait_until_load_passed_to_goto(self, mock_launch, _mock_check):
        browser = self._make_browser(wait_until="load")
        mock_context, mock_page = self._build_session_mocks()
        mock_launch.return_value = mock_context

        browser.make_request("https://example.com")

        goto_calls = mock_page.goto.call_args_list
        url_goto_calls = [c for c in goto_calls if c.args and c.args[0] != "about:blank"]
        self.assertTrue(all(c.kwargs.get("wait_until") == "load" for c in url_goto_calls))

    @patch("bin.headless_browser_cloak.HeadlessBrowser.cleanup_all_sessions")
    def test_cleanup_all_drivers_alias(self, mock_cleanup):
        HeadlessBrowser.cleanup_all_drivers()
        mock_cleanup.assert_called_once()

    @patch("bin.headless_browser_cloak.sys.exit", side_effect=SystemExit(0))
    @patch("bin.headless_browser_cloak.HeadlessBrowser.cleanup_all_drivers")
    def test_handle_sigterm_cleans_up_and_exits(self, mock_cleanup, mock_exit):
        from bin.headless_browser_cloak import _handle_sigterm

        with self.assertRaises(SystemExit):
            _handle_sigterm(signal.SIGTERM, object())

        mock_cleanup.assert_called_once()
        mock_exit.assert_called_once_with(0)


class TestRunScrollingScript(unittest.TestCase):
    """_run_scrolling_script: Python-controlled scroll loop. cloak 백엔드에서도 동일하게 동작해야 한다."""

    def setUp(self):
        HeadlessBrowser.cleanup_all_sessions()

    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser_cloak.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            defaults = dict(dir_path=Path(tempfile.gettempdir()), simulate_scrolling=True, timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowser(**defaults)

    def _make_page(self, scroll_height=0):
        mock_page = MagicMock()

        def evaluate_side_effect(script, *args, **kwargs):
            if "scrollHeight" in script:
                return scroll_height
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect
        mock_page.wait_for_timeout.return_value = None
        return mock_page

    def _marker_was_created(self, mock_page):
        marker_id = HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING
        return any(marker_id in str(call.args[0]) for call in mock_page.evaluate.call_args_list if call.args)

    def test_zero_height_skips_scroll_creates_marker(self):
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=0)

        browser._run_scrolling_script(mock_page)

        scroll_calls = [c for c in mock_page.evaluate.call_args_list if "scrollTo" in str(c.args[0])]
        self.assertEqual(len(scroll_calls), 0)
        self.assertTrue(self._marker_was_created(mock_page))

    def test_finite_height_scrolls_down_and_up(self):
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=700)

        browser._run_scrolling_script(mock_page)

        all_evaluate_scripts = [str(c.args[0]) for c in mock_page.evaluate.call_args_list if c.args]
        self.assertTrue(any("scrollTo" in s for s in all_evaluate_scripts))
        self.assertTrue(self._marker_was_created(mock_page))

    def test_playwright_error_during_scroll_still_creates_marker(self):
        browser = self._make_browser()
        mock_page = MagicMock()

        def evaluate_side_effect(script, *args, **kwargs):
            if "scrollHeight" in script:
                return 1000
            if "scrollTo" in script:
                raise PlaywrightError("page closed")
            return None

        mock_page.evaluate.side_effect = evaluate_side_effect

        browser._run_scrolling_script(mock_page)

        self.assertTrue(self._marker_was_created(mock_page))

    def test_scroll_payload_explicitly_returns_null(self):
        # xtoon처럼 window.scrollTo가 async 함수로 오버라이드된 사이트에서
        # page.evaluate가 Promise를 받아 무한 대기하지 않도록.
        browser = self._make_browser()
        mock_page = self._make_page(scroll_height=700)

        browser._run_scrolling_script(mock_page)

        scroll_payloads = [str(c.args[0]) for c in mock_page.evaluate.call_args_list if c.args and "scrollTo" in str(c.args[0]) and "scrollHeight" not in str(c.args[0])]
        self.assertGreater(len(scroll_payloads), 0)
        for payload in scroll_payloads:
            self.assertIn("return null", payload)

    def test_scroll_loop_bounded_by_max_scroll_secs(self):
        self.assertLessEqual(HeadlessBrowser._MAX_SCROLL_SECS, 10)


class TestCloudflareClearedPredicate(unittest.TestCase):
    """Evaluate _CLOUDFLARE_CLEARED_PREDICATE in a real browser against DOM
    fixtures. The predicate decides whether a captured page is real content, a
    Cloudflare interstitial, or the empty body that briefly exists while an
    interactive Turnstile challenge reloads to the origin. That branching is JS,
    so string inspection can't prove it — drive it through actual evaluation.
    The DOM is built locally on about:blank via evaluate (no network, and no
    set_content — cloakbrowser's patched Chromium stalls set_content's lifecycle
    wait); only the cloakbrowser binary is required, so the suite is skipped where
    it can't launch."""

    @classmethod
    def setUpClass(cls):
        from bin import headless_browser_cloak as hb

        if hb._cloak_launch_persistent_context is None:
            raise unittest.SkipTest("cloakbrowser is not installed")
        cls._tmp = tempfile.mkdtemp(prefix="cb-pred-test-")
        try:
            cls.ctx = hb._cloak_launch_persistent_context(user_data_dir=cls._tmp, headless=True, ignore_https_errors=True)
            cls.page = cls.ctx.pages[0] if cls.ctx.pages else cls.ctx.new_page()
            cls.page.goto("about:blank", wait_until="commit", timeout=10000)
        except Exception as e:  # binary missing / sandbox refuses to launch
            shutil.rmtree(cls._tmp, ignore_errors=True)
            raise unittest.SkipTest(f"cannot launch cloakbrowser: {e}")
        cls.predicate = HeadlessBrowser._CLOUDFLARE_CLEARED_PREDICATE

    @classmethod
    def tearDownClass(cls):
        try:
            cls.ctx.close()
        except Exception:
            pass
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def _eval(self, body_html, *, title, challenge_opt=False):
        self.page.evaluate(
            """({body, title, chl}) => {
                document.title = title;
                document.body.innerHTML = body;
                if (chl) { window._cf_chl_opt = {cType: 'managed'}; }
                else { try { delete window._cf_chl_opt; } catch (e) { window._cf_chl_opt = undefined; } }
            }""",
            {"body": body_html, "title": title, "chl": challenge_opt},
        )
        return self.page.evaluate(self.predicate)

    def test_real_page_with_body_passes(self):
        self.assertTrue(self._eval("<div>real content</div>", title="픽 미 업!"))

    def test_window_cf_chl_opt_blocks(self):
        # The defining signal of a modern managed/Turnstile challenge.
        self.assertFalse(self._eval("<div>real content</div>", title="픽 미 업!", challenge_opt=True))

    def test_interstitial_title_blocks(self):
        self.assertFalse(self._eval("<div>x</div>", title="잠시만 기다리십시오…"))
        self.assertFalse(self._eval("<div>x</div>", title="Just a moment..."))

    def test_challenge_iframe_blocks(self):
        self.assertFalse(self._eval('<iframe src="https://challenges.cloudflare.com/cdn-cgi/challenge"></iframe>', title="픽 미 업!"))

    def test_legacy_cf_content_blocks(self):
        self.assertFalse(self._eval('<div id="cf-content">checking</div>', title="픽 미 업!"))

    def test_empty_body_transient_blocks(self):
        # The bug this guards against: post-challenge reload moment — challenge
        # markers already gone and the real title set, but the body has no children
        # yet. Capturing here yields head-only HTML, so the predicate must wait.
        self.assertFalse(self._eval("", title="픽 미 업!"))


if __name__ == "__main__":
    unittest.main()
