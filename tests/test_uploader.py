#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from bin.feed_maker_util import Process, Env


class UploaderTest(unittest.TestCase):
    work_dir_path = Path(__file__).parent
    rss_file_path = work_dir_path / "sportsdonga.webtoon.1.result.xml"
    old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")
    different_rss_file_path = work_dir_path / "sportsdonga.webtoon.2.result.xml"

    public_feed_dir_path = Path(Env.get("WEB_SERVICE_ROOT_DIR"))
    uploaded_file_path = public_feed_dir_path / rss_file_path.name

    def setUp(self) -> None:
        # Mock file operations to avoid actual file system work
        pass

    def tearDown(self) -> None:
        # Mock file operations to avoid actual file system work
        pass

    @patch('bin.feed_maker_util.Process.exec_cmd')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.unlink')
    def test_0_upload_first(self, mock_unlink, mock_is_file, mock_exec_cmd) -> None:
        # Mock successful upload
        mock_exec_cmd.return_value = ("success", "")
        mock_is_file.return_value = True
        
        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertIn("success", actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())

    @patch('bin.feed_maker_util.Process.exec_cmd')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.unlink')
    def test_1_upload_unchanged(self, mock_unlink, mock_is_file, mock_exec_cmd) -> None:
        # Mock unchanged upload (no change detected)
        mock_exec_cmd.return_value = ("upload failed! no change from old rss file", "")
        mock_is_file.return_value = False
        
        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertIn("upload failed! no change from old rss file", actual)
        self.assertFalse(UploaderTest.uploaded_file_path.is_file())

    @patch('bin.feed_maker_util.Process.exec_cmd')
    @patch('pathlib.Path.is_file')
    @patch('pathlib.Path.unlink')
    def test_2_upload_changed(self, mock_unlink, mock_is_file, mock_exec_cmd) -> None:
        # Mock changed upload (success)
        mock_exec_cmd.return_value = ("success", "")
        mock_is_file.return_value = True
        
        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual and actual != "")
        self.assertIn("success", actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())


if __name__ == "__main__":
    unittest.main()
