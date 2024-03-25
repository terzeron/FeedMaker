#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import shutil
import json
import logging.config
from pathlib import Path
from bin.feed_maker_util import Datetime
from bin.feed_manager import FeedManager
from bin.db_manager import DBManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestFeedManager(unittest.TestCase):
    def setUp(self) -> None:
        db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])
        self.fm = FeedManager(db)

        self.test_feed_dir_path = self.fm.work_dir / "my_test_group" / "my_test_feed1"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

        with self.fm.db.get_connection_and_cursor() as (connection, cursor):
            self.fm.db.execute(cursor, "DELETE FROM feed_info WHERE feed_name LIKE 'my_test_feed%'")
            self.fm.db.commit(connection)

    def tearDown(self) -> None:
        with self.fm.db.get_connection_and_cursor() as (connection, cursor):
            self.fm.db.execute(cursor, "DELETE FROM feed_info WHERE feed_name LIKE 'my_test_feed%'")
            self.fm.db.commit(connection)
        del self.fm
        shutil.rmtree(self.test_feed_dir_path.parent)

    def test_get_feed_name_list_url_count_map(self):
        result = self.fm.get_feed_name_list_url_count_map()
        for _, list_url_count in result.items():
            self.assertIn("feed_name", list_url_count)
            self.assertIn("feed_title", list_url_count)
            self.assertIn("group_name", list_url_count)
            self.assertIn("count", list_url_count)

    def test_get_element_name_count_map(self):
        result = self.fm.get_element_name_count_map()
        for _, count in result.items():
            self.assertIn("element_name", count)
            self.assertIn("count", count)

    def test_add_and_remove_config_info(self):
        example_conf_file_path = Path(__file__).parent / "conf.json"
        conf_file_path = self.test_feed_dir_path / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)

        row11 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND config IS NOT NULL AND config_modify_date IS NOT NULL", self.test_feed_dir_path.name)
        self.fm.add_config_info(self.test_feed_dir_path)

        row12 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND config IS NOT NULL AND config_modify_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row11) + 1, len(row12))

        self.fm.remove_config_info(self.test_feed_dir_path)

        row13 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND config IS NOT NULL AND config_modify_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row11), len(row13))

    def test_load_all_config_files(self):
        self.fm.load_all_config_files(max_num_feeds=20)

        row = self.fm.db.query("SELECT * FROM feed_info WHERE config IS NOT NULL")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["feed_title"])
        self.assertIsNotNone(row[0]["group_name"])
        self.assertIsNotNone(row[0]["config"])
        self.assertEqual(type(json.loads(row[0]["config"])), type({}))
        self.assertIsNotNone(row[0]["config_modify_date"])

    def test_add_and_remove_rss_info(self):
        rss_file_path = self.test_feed_dir_path / "my_test_feed1.xml"
        example_rss_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        shutil.copy(example_rss_file_path, rss_file_path)

        row11 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND feedmaker IS NOT NULL AND rss_update_date IS NOT NULL", self.test_feed_dir_path.name)

        self.fm.add_rss_info(self.test_feed_dir_path)

        row12 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND feedmaker IS NOT NULL AND rss_update_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row11) + 1, len(row12))

        self.fm.remove_rss_info(self.test_feed_dir_path)

        row13 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND feedmaker IS NOT NULL AND rss_update_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row11), len(row13))

    def test_load_all_rss_files(self):
        self.fm.load_all_rss_files(max_num_feeds=20)

        row = self.fm.db.query("SELECT * FROM feed_info WHERE feedmaker IS TRUE")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["feedmaker"])
        self.assertIsNotNone(row[0]["rss_update_date"])

    def test_get_feed_name_public_feed_info_map(self):
        result = self.fm.get_feed_name_public_feed_info_map()
        for _, public_feed_info in result.items():
            self.assertIn("feed_name", public_feed_info)
            self.assertIn("feed_title", public_feed_info)
            self.assertIn("group_name", public_feed_info)
            self.assertIn("file_size", public_feed_info)
            self.assertIn("num_items", public_feed_info)
            self.assertIn("upload_date", public_feed_info)

    def test_add_and_remove_public_feed_file(self):
        feed_name = "my_test_feed5"
        public_feed_file_path = self.fm.public_feed_dir / (feed_name + ".xml")
        example_rss_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        shutil.copy(example_rss_file_path, public_feed_file_path)

        row11 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND public_feed_file_path IS NOT NULL AND upload_date IS NOT NULL", feed_name)
        self.fm.add_public_feed(public_feed_file_path)

        row12 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND public_feed_file_path IS NOT NULL AND upload_date IS NOT NULL", feed_name)
        self.assertEqual(len(row11) + 1, len(row12))

        self.fm.remove_public_feed(public_feed_file_path)

        row13 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND public_feed_file_path IS NOT NULL AND upload_date IS NOT NULL", feed_name)
        self.assertEqual(len(row11), len(row13))

    def test_load_all_public_feed_files(self):
        self.fm.load_all_public_feed_files(max_num_public_feeds=40)

        rows = self.fm.db.query("SELECT * FROM feed_info WHERE public_feed_file_path IS NOT NULL")
        self.assertGreater(len(rows), 0)
        row = rows[0]
        self.assertIsNotNone(row["feed_name"])
        self.assertIsNotNone(row["public_feed_file_path"])
        self.assertGreater(row["file_size"], 0)
        self.assertGreater(row["num_items"], 0)
        self.assertIsNotNone(row["upload_date"])

    def test_get_feed_name_progress_info_map(self):
        result = self.fm.get_feed_name_progress_info_map()
        for _, progress_info in result.items():
            self.assertIn("feed_name", progress_info)
            self.assertIn("feed_title", progress_info)
            self.assertIn("group_name", progress_info)
            self.assertIn("current_index", progress_info)
            self.assertIn("total_item_count", progress_info)
            self.assertIn("unit_size_per_day", progress_info)
            self.assertIn("progress_ratio", progress_info)
            self.assertIn("due_date", progress_info)

    def test_add_and_remove_progress_from_info(self):
        example_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.completed.json"
        conf_file_path = self.test_feed_dir_path / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)

        self.fm.add_config_info(self.test_feed_dir_path)

        progress_file_path = self.test_feed_dir_path / "start_idx.txt"
        date_str = Datetime.get_current_time_str()
        with progress_file_path.open("w", encoding="utf-8") as f:
            f.write(f"157\t{date_str}\n")

        row1 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND is_completed IS TRUE AND due_date IS NOT NULL", self.test_feed_dir_path.name)

        self.fm.add_progress_info(self.test_feed_dir_path)

        row2 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND is_completed IS TRUE AND due_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row1) + 1, len(row2))

        self.fm.remove_progress_info(self.test_feed_dir_path)

        row3 = self.fm.db.query("SELECT * FROM feed_info WHERE feed_name = %s AND is_completed IS TRUE AND due_date IS NOT NULL", self.test_feed_dir_path.name)
        self.assertEqual(len(row1), len(row3))

    def test_load_all_progress_info_from_files(self):
        self.fm.load_all_config_files(max_num_feeds=30)
        self.fm.load_all_progress_info_from_files(max_num_feeds=30)

        rows = self.fm.db.query("SELECT * FROM feed_info WHERE is_completed = True")
        self.assertGreater(len(rows), 0)
        row = rows[0]
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row["feed_name"])
        self.assertTrue(row["is_completed"])
        self.assertGreaterEqual(int(row["current_index"]), 0)
        self.assertGreaterEqual(int(row["total_item_count"]), 0)
        self.assertGreaterEqual(float(row["unit_size_per_day"]), 0.0)
        self.assertGreaterEqual(float(row["progress_ratio"]), 0.0)
        self.assertIsNotNone(row["due_date"])


if __name__ == "__main__":
    unittest.main()
