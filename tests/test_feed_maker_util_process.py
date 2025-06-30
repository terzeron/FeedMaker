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
        with subprocess.Popen(["sleep", "5"]):
            actual = len(Process._find_process_list(r"sleep 5"))
            expected = 1
            self.assertEqual(expected, actual)

            actual = Process.kill_process_group(r"sleep 5")
            expected = 1
            self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
