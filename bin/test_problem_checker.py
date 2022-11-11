#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from problem_checker import ProblemChecker


class TestProblemChecker(unittest.TestCase):
    def setUp(self) -> None:
        self.checker = ProblemChecker()
        self.test_feed_path = Path(os.environ["FEED_MAKER_WORK_DIR"]) / "my_test_group" / "my_test_feed"
        self.test_feed_html_file_path = self.test_feed_path / "html" / "31d4598.html"

    def _first_item(self, d: Dict[str, Any]):
        first_key = list(d.keys())[0]
        return d[first_key]

    def test_load_htaccess_file(self):
        self.checker.load_htaccess_file()
        self.assertGreater(len(self.checker.feed_alias_name_map), 0)
        self.assertGreater(len(self.checker.feed_name_aliases_map), 0)

    def test_load_all_config_rss_files(self):
        self.checker.load_all_config_rss_files()
        self.assertGreater(len(self.checker.feed_name_list_url_count_map), 0)
        self.assertGreater(len(self.checker.feed_name_rss_info_map), 0)
        self.assertGreater(len(self.checker.element_name_count_map), 0)

    def test_load_all_public_feed_files(self):
        self.checker.load_all_public_feed_files()
        self.assertGreater(len(self.checker.public_feed_info_map), 0)

    def test_get_html_file_name(self):
        self.checker.load_all_public_feed_files()
        expected = "my_test_feed/html/31d4598.html"
        actual = self.checker.get_html_file_name(self.test_feed_html_file_path)
        self.assertEqual(expected, actual)

    def test_add_and_remove_html_file_info_in_path(self):
        self.checker.add_html_files_in_path_to_info(self.test_feed_html_file_path)
        self.assertGreaterEqual(len(self.checker.html_file_with_many_image_tag_map), 0)
        if len(self.checker.html_file_with_many_image_tag_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("count", self._first_item(self.checker.html_file_with_many_image_tag_map))
        self.assertGreaterEqual(len(self.checker.html_file_without_image_tag_map), 0)
        if len(self.checker.html_file_without_image_tag_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("count", self._first_item(self.checker.html_file_without_image_tag_map))
        self.assertGreaterEqual(len(self.checker.html_file_image_not_found_map), 0)
        if len(self.checker.html_file_image_not_found_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("count", self._first_item(self.checker.html_file_image_not_found_map))

        self.checker.remove_html_file_in_path_from_info("file_path", self.test_feed_html_file_path)
        self.assertEqual(len(self.checker.html_file_with_many_image_tag_map), 0)
        self.assertEqual(len(self.checker.html_file_without_image_tag_map), 0)
        self.assertEqual(len(self.checker.html_file_image_not_found_map), 0)

    def test_load_all_html_files(self):
        self.checker.load_all_html_files()
        self.assertGreaterEqual(len(self.checker.html_file_size_map), 0)
        if len(self.checker.html_file_size_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_size_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_size_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_size_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_size_map))
            self.assertIn("size", self._first_item(self.checker.html_file_size_map))
            self.assertIn("update_date", self._first_item(self.checker.html_file_size_map))
        self.assertGreaterEqual(len(self.checker.html_file_with_many_image_tag_map), 0)
        if len(self.checker.html_file_with_many_image_tag_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_with_many_image_tag_map))
            self.assertIn("count", self._first_item(self.checker.html_file_with_many_image_tag_map))
        self.assertGreaterEqual(len(self.checker.html_file_without_image_tag_map), 0)
        if len(self.checker.html_file_without_image_tag_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_without_image_tag_map))
            self.assertIn("count", self._first_item(self.checker.html_file_without_image_tag_map))
        self.assertGreaterEqual(len(self.checker.html_file_image_not_found_map), 0)
        if len(self.checker.html_file_image_not_found_map) > 0:
            self.assertIn("file_name", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("file_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("feed_dir_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("group_dir_path", self._first_item(self.checker.html_file_image_not_found_map))
            self.assertIn("count", self._first_item(self.checker.html_file_image_not_found_map))

    def test_load_all_progress_info_from_files(self):
        self.checker.load_all_progress_info_from_files()
        self.assertGreaterEqual(len(self.checker.feed_name_progress_info_map), 0)
        if len(self.checker.feed_name_progress_info_map) > 0:
            self.assertIn("feed_name", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("feed_title", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("group_name", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("index", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("ratio", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("unit_size", self._first_item(self.checker.feed_name_progress_info_map))
            self.assertIn("due_date", self._first_item(self.checker.feed_name_progress_info_map))

    def test_load_all_httpd_access_files(self):
        self.checker.load_all_httpd_access_files()
        self.assertGreaterEqual(len(self.checker.feed_alias_access_info_map), 0)
        if len(self.checker.feed_alias_access_info_map) > 0:
            self.assertIn("feed_alias", self._first_item(self.checker.feed_alias_access_info_map))
            self.assertIn("feed_name", self._first_item(self.checker.feed_alias_access_info_map))
            self.assertIn("access_date", self._first_item(self.checker.feed_alias_access_info_map))
            self.assertIn("access_status", self._first_item(self.checker.feed_alias_access_info_map))
            self.assertIn("is_in_xml_dir", self._first_item(self.checker.feed_alias_access_info_map))

    def test_convert_datetime_to_str(self):
        d = "2022-01-01"
        self.assertEqual("2022-01-01", self.checker.convert_datetime_to_str(d))

        d = "2022-12-30 12:12:12"
        self.assertEqual("2022-12-30 12:12:12", self.checker.convert_datetime_to_str(d))

        d = "2018-01-31"
        self.assertEqual("2018-01-31", self.checker.convert_datetime_to_str(d))

        d = "01-31"
        self.assertEqual("01-31", self.checker.convert_datetime_to_str(d))

        dt = datetime.strptime("2018-01-13", "%Y-%m-%d")
        self.assertEqual("18-01-13", self.checker.convert_datetime_to_str(dt))

        dt = datetime.strptime("2018-01-31 17:04:11", "%Y-%m-%d %H:%M:%S")
        self.assertEqual("18-01-31", self.checker.convert_datetime_to_str(dt))

    def test_get_status_info_with_default(self):
        self.checker.merge_all_feeds_status()
        self.checker.get_status_info_with_default("my_test_feed")
        self.assertGreaterEqual(len(self.checker.feed_alias_status_info_map), 0)
        if len(self.checker.feed_alias_status_info_map) > 0:
            self.assertIn("http_request", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("htaccess", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("feedmaker", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("access_date", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("view_date", self._first_item(self.checker.feed_alias_status_info_map))

    def test_merge_all_feeds_status(self):
        self.checker.merge_all_feeds_status()
        self.assertGreaterEqual(len(self.checker.feed_alias_status_info_map), 0)
        if len(self.checker.feed_alias_status_info_map) > 0:
            self.assertIn("http_request", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("htaccess", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("feedmaker", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("access_date", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("view_date", self._first_item(self.checker.feed_alias_status_info_map))

    def test_load_all(self):
        self.checker.load_all()
        self.assertGreater(len(self.checker.feed_alias_status_info_map), 0)
        if len(self.checker.feed_alias_status_info_map) > 0:
            self.assertIn("http_request", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("htaccess", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("feedmaker", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("access_date", self._first_item(self.checker.feed_alias_status_info_map))
            self.assertIn("view_date", self._first_item(self.checker.feed_alias_status_info_map))


if __name__ == "__main__":
    unittest.main()
