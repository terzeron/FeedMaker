#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from pathlib import Path

from bin.feed_maker_util import Process, Env


class UploaderTest(unittest.TestCase):
    work_dir_path = Path(__file__).parent
    rss_file_path = work_dir_path / "sportsdonga.webtoon.1.result.xml"
    old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")
    different_rss_file_path = work_dir_path / "sportsdonga.webtoon.2.result.xml"

    public_feed_dir_path = Path(Env.get("WEB_SERVICE_ROOT_DIR"))
    uploaded_file_path = public_feed_dir_path / rss_file_path.name

    def setUp(self) -> None:
        UploaderTest.uploaded_file_path.unlink(missing_ok=True)
        UploaderTest.old_rss_file_path.unlink(missing_ok=True)

    def tearDown(self) -> None:
        self.setUp()

    def test_0_upload_first(self) -> None:
        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertIn("success", actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())

    def test_1_upload_unchanged(self) -> None:
        cmd = f"cp {UploaderTest.rss_file_path} {UploaderTest.old_rss_file_path}"
        Process.exec_cmd(cmd)

        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual)
        self.assertIn("upload failed! no change from old rss file", actual)
        self.assertFalse(UploaderTest.uploaded_file_path.is_file())

    def test_2_upload_changed(self) -> None:
        cmd = f"cp {UploaderTest.different_rss_file_path} {UploaderTest.old_rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)

        cmd = f"uploader.py {UploaderTest.rss_file_path}"
        actual, _ = Process.exec_cmd(cmd)
        self.assertTrue(actual and actual != "")
        self.assertIn("success", actual)
        self.assertTrue(UploaderTest.uploaded_file_path.is_file())


if __name__ == "__main__":
    unittest.main()
