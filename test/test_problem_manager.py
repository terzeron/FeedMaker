#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import shutil
import logging.config
from pathlib import Path
from bin.db_manager import DBManager
from bin.problem_manager import ProblemManager
from bin.feed_manager import FeedManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    def setUp(self) -> None:
        db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])
        self.sm = ProblemManager(db)
        self.fm = FeedManager(db)

        self.test_feed_dir_path = self.fm.work_dir / "my_test_group" / "my_test_feed2"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        del self.sm
        shutil.rmtree(self.test_feed_dir_path.parent)

    def test_get_feed_name_status_info_map(self):
        result = self.sm.get_feed_name_status_info_map()
        for _, status_info in result.items():
            self.assertIn("feed_name", status_info)
            self.assertIn("feed_title", status_info)
            self.assertIn("group_name", status_info)
            self.assertIn("http_request", status_info)
            self.assertIn("public_html", status_info)
            self.assertIn("feedmaker", status_info)
            self.assertIn("access_date", status_info)
            self.assertIn("view_date", status_info)
            self.assertIn("upload_date", status_info)
            self.assertIn("update_date", status_info)
            self.assertIn("access_date", status_info)
            self.assertIn("file_path", status_info)

    def test_update_feed_info(self):
        pass

    def test_load_all(self):
        self.sm.load_all(max_num_feeds=20, max_num_public_feeds=40, max_num_days=14)

        row = self.sm.db.query("SELECT * FROM feed_info")
        self.assertGreaterEqual(len(row[0]), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["feed_name"])

        row = self.sm.db.query("SELECT * FROM feed_info WHERE NOT ( http_request IS NULL AND public_html IS NULL AND feedmaker IS NULL ) AND NOT ( http_request IS NOT NULL AND public_html IS NULL AND feedmaker IS NULL AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s ) AND NOT ( http_request IS NOT NULL AND public_html IS NOT NULL AND feedmaker IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )", ProblemManager.num_days, ProblemManager.num_days, ProblemManager.num_days)
        self.assertGreaterEqual(len(row), 0)


if __name__ == "__main__":
    unittest.main()
