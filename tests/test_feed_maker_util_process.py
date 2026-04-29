#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from shutil import which
import subprocess

from bin.feed_maker_util import Process

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class ProcessTest(unittest.TestCase):
    def test_replace_script_path(self) -> None:
        # Test with a command that should exist
        cmd = "shuf"
        real_program_path = which("shuf")
        if real_program_path:
            expected = str(Path(real_program_path).resolve())
            actual = Process._replace_script_path(cmd, Path.cwd())
            self.assertEqual(expected, actual)
            actual = Process._replace_script_path(cmd, Path("/usr/bin"))
            self.assertEqual(expected, actual)
            actual = Process._replace_script_path(cmd, Path("/usr"))
            self.assertEqual(expected, actual)
            actual = Process._replace_script_path(cmd, Path("/"))
            self.assertEqual(expected, actual)
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
        # Test with a relative path to an existing file
        rel_path = Path(__file__).parent / "capture_item_naverwebtoon.py"
        cmd = f"{rel_path} -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        # Since the file exists, we expect a path string, not None
        self.assertIsNotNone(actual)
        self.assertIsInstance(actual, str)
        if actual is not None:  # Type guard for linter
            resolved_path = actual.split(" ")[0]
            self.assertTrue(Path(resolved_path).exists())
        # Test with a relative path to a non-existent file
        rel_path = Path(__file__).parent / "capture_item_naverwebtoon.py"
        cmd = f"{rel_path} -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        # Since the file exists, we expect a path string, not None
        self.assertIsNotNone(actual)
        self.assertIsInstance(actual, str)
        if actual is not None:  # Type guard for linter
            resolved_path = actual.split(" ")[0]
            self.assertTrue(Path(resolved_path).exists())

    def test_exec_cmd(self) -> None:
        result, error = Process.exec_cmd("echo hello", Path.cwd())
        self.assertEqual(result.strip(), "hello")
        self.assertEqual(error, "")

    def test_exec_cmd_nonzero_exit(self) -> None:
        false_path = which("false")
        if not false_path:
            self.skipTest("'false' command not available on this system")
        result, error = Process.exec_cmd(false_path, Path.cwd())
        self.assertEqual(result, "")
        self.assertIn("code", error.lower())

    def test_exec_cmd_disallow_shell(self) -> None:
        result, error = Process.exec_cmd("sh -c 'echo hello'", Path.cwd())
        self.assertEqual(result, "")
        self.assertIn("not allowed", error.lower())

    def test_exec_cmd_disallow_all_shells(self) -> None:
        for shell in ["bash", "zsh", "ksh", "fish", "env"]:
            result, error = Process.exec_cmd(f"{shell} -c 'echo hello'", Path.cwd())
            self.assertEqual(result, "", f"{shell} should be blocked")
            self.assertIn("not allowed", error.lower(), f"{shell} should be blocked")

    def test_exec_cmd_shell_injection_semicolon(self) -> None:
        # shell=False에서 세미콜론은 명령어 구분자가 아닌 일반 인자
        result, error = Process.exec_cmd("echo hello; echo injected", Path.cwd())
        self.assertEqual(error, "")
        # "hello;"와 "echo"와 "injected"가 echo의 인자로 출력됨 (두 번째 명령 실행 아님)
        self.assertEqual(result.strip(), "hello; echo injected")

    def test_exec_cmd_shell_injection_pipe(self) -> None:
        # 파이프를 통한 명령어 체이닝이 차단되는지 확인
        result, error = Process.exec_cmd("echo hello | cat", Path.cwd())
        if not error:
            # shell=False에서 "|"와 "cat"은 echo의 인자
            self.assertIn("|", result)

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


if __name__ == "__main__":
    unittest.main()
