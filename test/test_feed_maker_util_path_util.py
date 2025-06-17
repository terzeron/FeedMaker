#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from bin.feed_maker_util import PathUtil, Env

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class PathUtilTest(unittest.TestCase):
    def test_short_path1(self) -> None:
        work_dir_path = Path(Env.get("FM_WORK_DIR"))
        public_feed_dir_path = Path(Env.get("WEB_SERVICE_FEED_DIR_PREFIX"))
        httpd_access_log_dir_path = Path(Env.get("FM_LOG_DIR"))
        self.assertEqual(PathUtil.short_path(work_dir_path), ".")
        self.assertEqual(PathUtil.short_path(public_feed_dir_path), ".")
        self.assertEqual(PathUtil.short_path(httpd_access_log_dir_path), "logs")

    def test_short_path2(self) -> None:
        self.assertEqual(PathUtil.short_path(None), "")


if __name__ == "__main__":
    unittest.main()
