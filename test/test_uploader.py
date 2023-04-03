#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest
from pathlib import Path
from feed_maker_util import Process


class UploaderTest(unittest.TestCase):
    work_dir_path = Path(os.environ["FEED_MAKER_HOME_DIR"]) / "test"
    rss_file_path = work_dir_path / "sportsdonga.webtoon.1.result.xml"
    old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")
    different_rss_file_path = work_dir_path / "sportsdonga.webtoon.2.result.xml"

    www_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
    uploaded_file_path = www_dir_path / rss_file_path.name

    def setUp(self):
        UploaderTest.uploaded_file_path.unlink(missing_ok=True)
        UploaderTest.old_rss_file_path.unlink(missing_ok=True)

    def tearDown(self):
        UploaderTest.uploaded_file_path.unlink(missing_ok=True)
        UploaderTest.old_rss_file_path.unlink(missing_ok=True)

    def test_0_upload_first(self):
        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertTrue("success" in actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())

    def test_1_upload_unchanged(self):
        cmd = f"cp {UploaderTest.rss_file_path} {UploaderTest.old_rss_file_path}"
        Process.exec_cmd(cmd)

        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertTrue("upload failed! no change from old rss file" in actual)
        self.assertFalse(UploaderTest.uploaded_file_path.is_file())

    def test_2_upload_changed(self):
        cmd = f"cp {UploaderTest.different_rss_file_path} {UploaderTest.old_rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)

        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual and actual != "")
        self.assertTrue("success" in actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())


if __name__ == "__main__":
    unittest.main()
