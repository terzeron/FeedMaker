#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import logging.config
import tempfile
from pathlib import Path
from shutil import which
from unittest.mock import patch
import subprocess

from bin.feed_maker_util import Process

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class ProcessTest(unittest.TestCase):
    def test_replace_script_path(self) -> None:
        # 시스템 유틸리티는 allowlist에 등재된 절대경로로 지정해야 한다.
        # (bare name "shuf"는 PATH 조회로 해석되지만 프로젝트 디렉터리 밖이라 거부된다)
        cmd = "/usr/bin/shuf"
        if Path("/usr/bin/shuf").exists():
            expected = str(Path("/usr/bin/shuf").resolve())
            actual = Process._replace_script_path(cmd, Path.cwd())
            self.assertEqual(expected, actual)
            # 절대경로이므로 dir_path와 무관하게 같은 결과여야 한다
            actual = Process._replace_script_path(cmd, Path("/usr/bin"))
            self.assertEqual(expected, actual)
            actual = Process._replace_script_path(cmd, Path("/usr"))
            self.assertEqual(expected, actual)
            actual = Process._replace_script_path(cmd, Path("/"))
            self.assertEqual(expected, actual)
        # allowlist에 없는 시스템 명령은 PATH에 있어도 거부된다
        self.assertIsNone(Process._replace_script_path("shuf", Path.cwd()))
        # Test with a non-existent command, should return None
        cmd = "no_such_command_abcdefg"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        # Test with an absolute path and arguments
        # resolve() follows symlinks, so expected must match the real path on this system
        cmd = "/usr/bin/tail -5"
        expected = str(Path("/usr/bin/tail").resolve())
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        # 프로젝트 소유 디렉터리(FM_WORK_DIR) 안의 스크립트는 허용된다
        script_path = Path(__file__).parent / "capture_item_naverwebtoon.py"
        cmd = f"{script_path} -n 500"
        with patch.dict(os.environ, {"FM_WORK_DIR": str(Path(__file__).parent), "FM_HOME_DIR": ""}):
            actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNotNone(actual)
        self.assertIsInstance(actual, str)
        if actual is not None:  # Type guard for linter
            self.assertTrue(Path(actual).exists())

    def test_exec_cmd(self) -> None:
        # allowlist에 등재된 시스템 유틸리티로 stdout 캡처를 확인한다
        result, error = Process.exec_cmd("/usr/bin/grep hello", Path.cwd(), input_data="hello\nworld\n")
        self.assertEqual(result.strip(), "hello")
        self.assertEqual(error, "")

    def test_exec_cmd_nonzero_exit(self) -> None:
        # grep은 매칭이 없으면 exit code 1로 종료한다
        result, error = Process.exec_cmd("/usr/bin/grep no_such_pattern_xyz", Path.cwd(), input_data="hello\n")
        self.assertEqual(result, "")
        self.assertIn("code", error.lower())

    def test_exec_cmd_script_without_shebang(self) -> None:
        # shebang이 없는 실행 스크립트는 shell=False에서 ENOEXEC(OSError: Exec format error)를 일으킨다.
        # exec_cmd가 이 OSError를 잡아 예외를 전파하지 않고 ("", error)로 반환해야,
        # 호출부가 정상 에러 경로로 실패를 인지할 수 있다.
        with tempfile.TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "no_shebang.sh"
            script_path.write_text("cat - | grep -v DROP\n", encoding="utf-8")
            script_path.chmod(0o755)
            # 스크립트가 allowlist 안(FM_WORK_DIR 하위)에 있어야 실행 단계까지 도달한다
            try:
                with patch.dict(os.environ, {"FM_WORK_DIR": tmp}):
                    result, error = Process.exec_cmd(str(script_path), Path(tmp), input_data="keep\nDROP\n")
            except OSError as e:
                self.fail(f"exec_cmd should not raise OSError for a shebang-less script, but raised: {e!r}")
        self.assertEqual(result, "")
        self.assertNotEqual(error, "")
        self.assertIn("error", error.lower())

    def test_exec_cmd_disallow_shell(self) -> None:
        result, error = Process.exec_cmd("sh -c 'echo hello'", Path.cwd())
        self.assertEqual(result, "")
        self.assertIn("not allowed", error.lower())

    def test_exec_cmd_disallow_all_shells(self) -> None:
        for shell in ["bash", "zsh", "ksh", "fish", "env"]:
            result, error = Process.exec_cmd(f"{shell} -c 'echo hello'", Path.cwd())
            self.assertEqual(result, "", f"{shell} should be blocked")
            self.assertNotEqual(error, "", f"{shell} should be blocked")
            # 설치되어 있는 셸은 allowlist 밖이라 'not allowed'로 거부된다.
            # 설치되지 않은 셸은 경로 해석 단계에서 먼저 실패하므로 메시지가 다르다(둘 다 실행 거부).
            if which(shell):
                self.assertIn("not allowed", error.lower(), f"{shell} should be blocked by allowlist")

    def test_exec_cmd_shell_injection_semicolon(self) -> None:
        # shell=False에서 세미콜론은 명령어 구분자가 아닌 grep 패턴의 일부다
        result, error = Process.exec_cmd("/usr/bin/grep 'hello; echo injected'", Path.cwd(), input_data="hello; echo injected\nother\n")
        self.assertEqual(error, "")
        self.assertEqual(result.strip(), "hello; echo injected")

    def test_exec_cmd_shell_injection_pipe(self) -> None:
        # shell=False에서 파이프도 명령어 체이닝이 아닌 패턴의 일부다
        result, error = Process.exec_cmd("/usr/bin/grep 'hello | cat'", Path.cwd(), input_data="hello | cat\nother\n")
        self.assertEqual(error, "")
        self.assertEqual(result.strip(), "hello | cat")

    def test_build_argv_invalid_command(self) -> None:
        argv, error = Process._build_argv("", Path.cwd())
        self.assertEqual(argv, [])
        self.assertIn("empty", error.lower())

    def test_build_argv_unclosed_quote(self) -> None:
        argv, error = Process._build_argv("echo 'unclosed", Path.cwd())
        self.assertEqual(argv, [])
        self.assertIn("invalid", error.lower())

    def test_find_process_group_and_kill_process_group(self) -> None:
        import time

        # Use a unique sleep duration to avoid conflicts with other sleep processes
        unique_sleep_duration = "987654321"

        # Count existing processes before starting our test process
        initial_count = len(Process._find_process_list(f"sleep {unique_sleep_duration}"))

        # Start a long-running process with unique duration
        proc = subprocess.Popen(["sleep", unique_sleep_duration])
        try:
            # Give it a moment to start
            time.sleep(0.2)

            # Find the process - should be initial_count + 1
            actual = len(Process._find_process_list(f"sleep {unique_sleep_duration}"))
            expected = initial_count + 1
            self.assertEqual(expected, actual)

            actual = Process.kill_process_group(f"sleep {unique_sleep_duration}")
            expected = 1
            self.assertEqual(expected, actual)

            # Give it a moment to be killed
            time.sleep(0.2)

            # Verify process is gone - should be back to initial count
            actual = len(Process._find_process_list(f"sleep {unique_sleep_duration}"))
            expected = initial_count
            self.assertEqual(expected, actual)
        finally:
            # Clean up: make sure process is terminated
            if proc.poll() is None:  # Process is still running
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)


class ProcessExecutableAllowlistTest(unittest.TestCase):
    """실행 대상 allowlist: 프로젝트 소유 디렉터리 + 등재된 시스템 유틸리티만 허용한다."""

    @staticmethod
    def _make_script(path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("#!/usr/bin/env python3\nprint('ok')\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_group_and_feed_dir_scripts_are_allowed(self) -> None:
        """그룹 디렉터리('../x.py')와 피드 디렉터리('./x.py')의 임의 스크립트를 허용한다."""
        with tempfile.TemporaryDirectory() as tmp:
            work_dir = Path(tmp)
            feed_dir = work_dir / "mygroup" / "myfeed"
            self._make_script(feed_dir / "post_process.py")
            self._make_script(work_dir / "mygroup" / "capture_item_mysite.py")
            with patch.dict(os.environ, {"FM_WORK_DIR": str(work_dir), "FM_HOME_DIR": ""}):
                argv, error = Process._build_argv("./post_process.py -n 5", feed_dir)
                self.assertEqual(error, "")
                self.assertTrue(argv[0].endswith("post_process.py"))
                argv, error = Process._build_argv("../capture_item_mysite.py -n 5", feed_dir)
                self.assertEqual(error, "")
                self.assertTrue(argv[0].endswith("capture_item_mysite.py"))

    def test_interpreter_is_denied(self) -> None:
        """인터프리터를 argv[0]에 두는 우회는 거부된다(이름 denylist가 못 막던 경로)."""
        for program in ("python3", "perl", "awk", "/usr/bin/python3", "/usr/bin/env"):
            _, error = Process._build_argv(f"{program} --version", Path.cwd())
            self.assertIn("not allowed", error.lower(), f"{program} should be blocked")

    def test_venv_interpreter_is_denied(self) -> None:
        """FM_HOME_DIR 하위라도 .venv/bin은 허용 대상이 아니다(bin/, utils/만 허용)."""
        venv_python = Path(__file__).parent.parent / ".venv" / "bin" / "python3"
        if not venv_python.exists():
            self.skipTest(".venv/bin/python3 not present")
        with patch.dict(os.environ, {"FM_HOME_DIR": str(Path(__file__).parent.parent), "FM_WORK_DIR": ""}):
            _, error = Process._build_argv(f"{venv_python} --version", Path.cwd())
        self.assertIn("not allowed", error.lower())

    def test_script_outside_allowed_roots_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = self._make_script(Path(tmp) / "outside.py")
            with patch.dict(os.environ, {"FM_WORK_DIR": "/nonexistent_work_dir_xyz", "FM_HOME_DIR": ""}):
                _, error = Process._build_argv(str(script), Path(tmp))
        self.assertIn("not allowed", error.lower())

    def test_allowed_system_executables(self) -> None:
        """등재된 시스템 유틸리티는 심볼릭 링크 환경과 무관하게 절대경로로 허용된다."""
        for program in ("/usr/bin/grep", "/usr/bin/shuf", "/usr/bin/tail"):
            if not Path(program).exists():
                continue
            _, error = Process._build_argv(f"{program} -5", Path.cwd())
            self.assertEqual(error, "", f"{program} should be allowed")


if __name__ == "__main__":
    unittest.main()
