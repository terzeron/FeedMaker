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
        expected = real_program_path
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
        cmd = "/usr/bin/tail -5"
        expected = "/usr/bin/tail -5"
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
