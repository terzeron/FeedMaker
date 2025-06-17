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
        cmd = "shuf"
        # OS마다 shuf가 설치된 경로가 다를 수 있음
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
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "/usr/bin/tail -5"
        # 어떤 디렉토리에서 실행하든 /usr/bin/tail이 실행되어야 함
        expected = "/usr/bin/tail -5"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "non_existent_program arg1"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "uploader.py test.xml"
        real_program_path = which("uploader.py")
        expected = f"{real_program_path} test.xml"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "../capture_item_naverwebtoon.py -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "./capture_item_naverwebtoon.py -n 500"
        actual = Process._replace_script_path(cmd, Path.cwd())
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

        cmd = "./capture_item_link_title.py"
        actual = Process._replace_script_path(cmd, Path.cwd())
        expected = str(Path.cwd() / "capture_item_link_title.py")
        self.assertEqual(expected, actual)
        actual = Process._replace_script_path(cmd, Path("/usr/bin"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/usr"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("../backend"))
        self.assertIsNone(actual)
        actual = Process._replace_script_path(cmd, Path("/no_such_a_dir/workspace/fma/naver/naverwebtoon"))
        self.assertIsNone(actual)

    def test_exec_cmd(self) -> None:
        valid_cmd = "ls test_feed_maker_util_datetime.py"
        actual, error = Process.exec_cmd(valid_cmd)
        self.assertTrue(actual)
        self.assertEqual(error, "")
        self.assertIn("test_feed_maker_util_datetime.py", actual)

        invalid_cmd = "ls non_existent_file"
        actual, error = Process.exec_cmd(invalid_cmd)
        self.assertFalse(actual)
        self.assertIn("No such file or directory", error)

        invalid_cmd = "lslslsls non_existent_file"
        actual, error = Process.exec_cmd(invalid_cmd)
        self.assertFalse(actual)
        self.assertIn("Error in getting path of executable", error)

        bidirectional_cmd = "cat"
        input_str = "hello world"
        actual, error = Process.exec_cmd(bidirectional_cmd, input_data=input_str)
        self.assertTrue(actual)
        self.assertEqual(error, "")
        self.assertIn("hello world", actual)

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
