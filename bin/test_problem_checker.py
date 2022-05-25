#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from datetime import datetime
from problem_checker import ProblemChecker


class TestProblemChecker(unittest.TestCase):
    def setUp(self) -> None:
        self.checker = ProblemChecker()

    def test_load_htaccess_file(self):
        self.fail()

    def test_load_all_config_rss_files(self):
        self.fail()

    def test_load_all_public_feed_files(self):
        self.fail()

    def test_get_html_file_name(self):
        self.fail()

    def test_load_all_html_files(self):
        self.fail()

    def test_load_all_progress_info_from_files(self):
        self.fail()

    def test_load_all_httpd_access_files(self):
        self.fail()

    def test_convert_datetime_to_str(self):
        d = "2022-01-01"
        self.assertEqual("2022-01-01", self.checker.convert_datetime_to_str(d))

        d = "2022-12-30 12:12:12"
        self.assertEqual("2022-12-30 12:12:12", self.checker.convert_datetime_to_str(d))

        d = "2018-01-31"
        self.assertEqual("2018-01-31", self.checker.convert_datetime_to_str(d))

        d = "01-31"
        self.assertEqual("01-31", self.checker.convert_datetime_to_str(d))

        d = datetime.strptime("2018-01-13", "%Y-%m-%d")
        self.assertEqual("01-13", self.checker.convert_datetime_to_str(d))

        d = datetime.strptime("2018-01-31 17:04:11", "%Y-%m-%d %H:%M:%S")
        self.assertEqual("01-31", self.checker.convert_datetime_to_str(d))

    def test_get_status_info_with_default(self):
        self.fail()

    def test_merge_all_feeds_status(self):
        self.fail()

    def test_load(self):
        self.fail()


if __name__ == "__main__":
    unittest.main()
