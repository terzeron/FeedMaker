#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import unittest
import subprocess
import feedmakerutil


class CrawlerTest(unittest.TestCase):
    work_dir = os.environ["HOME"] + "/public_html/xml"
    downloaded_file_path = work_dir + "/" + rss_file_name

    def setUp(self):
        feedmakerutil.remove_file(self.downloaded_file_path)

    def test_uploadFirst(self):
        cmd = "upload.py %s" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)

        self.assertTrue(result and result != "")
        self.assertTrue("success" in result)
        self.assertTrue(os.path.isfile(self.downloaded_file_path))

    def test_uploadUnchanged(self):
        cmd = "cp %s %s" % (self.rss_file_name, self.old_rss_file_name)
        result, error = feedmakerutil.exec_cmd(cmd)
        # print(cmd)

        cmd = "upload.py %s 2>&1" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)
        # print(cmd)
        # print(result)

        self.assertTrue(result)
        self.assertTrue("failed" in result)
        self.assertTrue("No change" in result)
        self.assertFalse(os.path.isfile(self.downloaded_file_path))

    def test_uploadChanged(self):
        cmd = "cp %s %s" % (self.different_rss_file_name, self.old_rss_file_name)
        (result, error) = feedmakerutil.exec_cmd(cmd)

        cmd = "upload.py %s" % self.rss_file_name
        (result, error) = feedmakerutil.exec_cmd(cmd)

        self.assertTrue(result and result != "")
        self.assertTrue("success" in result)
        self.assertTrue(os.path.isfile(self.downloaded_file_path))

    def tearDown(self):
        feedmakerutil.remove_file(self.downloaded_file_path)


if __name__ == "__main__":
    unittest.main()
