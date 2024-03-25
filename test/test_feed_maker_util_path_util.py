#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import logging.config
from pathlib import Path
from bin.feed_maker_util import PathUtil

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class PathUtilTest(unittest.TestCase):
    def test_short_path1(self):
        work_dir = Path(os.environ["FM_WORK_DIR"])
        public_feed_dir = Path(os.environ["WEB_SERVICE_FEEDS_DIR"])
        httpd_access_log_dir = Path(os.environ["FM_LOG_DIR"])
        self.assertEqual(PathUtil.short_path(work_dir), ".")
        self.assertEqual(PathUtil.short_path(public_feed_dir), ".")
        self.assertEqual(PathUtil.short_path(httpd_access_log_dir), "logs")

    def test_short_path2(self):
        self.assertEqual(PathUtil.short_path(None), "")


if __name__ == "__main__":
    unittest.main()
