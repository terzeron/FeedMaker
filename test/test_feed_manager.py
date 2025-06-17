#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from pathlib import Path

from test.test_common import TestCommon
from bin.feed_maker_util import Datetime
from bin.feed_manager import FeedManager
from bin.db import DB
from bin.models import FeedInfo

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestFeedManager(unittest.TestCase):
    mysql_container = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mysql_container = TestCommon.prepare_mysql_container()
        DB.init(TestCommon.get_db_config(cls.mysql_container))

    @classmethod
    def tearDownClass(cls) -> None:
        TestCommon.dispose_mysql_container(cls.mysql_container)

    def setUp(self) -> None:
        self.db_config = TestCommon.get_db_config(self.__class__.mysql_container)
        DB.create_all_tables(self.db_config)

        self.fm = FeedManager()

        self.test_feed_dir_path = self.fm.work_dir_path / "my_test_group" / "my_test_feed1"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)

        del self.fm

        DB.drop_all_tables(self.db_config)
        del self.db_config

    def test_get_feed_name_list_url_count_map(self) -> None:
        result = FeedManager.get_feed_name_list_url_count_map()
        for _, list_url_count in result.items():
            self.assertIn("feed_name", list_url_count)
            self.assertIn("feed_title", list_url_count)
            self.assertIn("group_name", list_url_count)
            self.assertIn("count", list_url_count)

    def test_get_element_name_count_map(self) -> None:
        result = FeedManager.get_element_name_count_map()
        for _, count in result.items():
            self.assertIn("element_name", count)
            self.assertIn("count", count)

    def test_add_and_remove_config_info(self) -> None:
        example_conf_file_path = Path(__file__).parent / "conf.json"
        conf_file_path = self.test_feed_dir_path / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)

        with DB.session_ctx() as s:
            rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.config.is_not(None), 
                                             FeedInfo.config_modify_date.is_not(None)).all()
            assert rows11 is not None

        FeedManager.add_config_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.config.is_not(None), 
                                             FeedInfo.config_modify_date.is_not(None)).all()
            assert rows12 is not None
            self.assertEqual(len(rows11) + 1, len(rows12))

        FeedManager.remove_config_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.config.is_not(None), 
                                             FeedInfo.config_modify_date.is_not(None)).all()
            assert rows13 is not None
            self.assertEqual(len(rows11), len(rows13))

    def test_load_all_config_files(self) -> None:
        self.fm.load_all_config_files(max_num_feeds=20)

        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.config.is_not(None)).first()
            assert row is not None
            self.assertIsNotNone(row.feed_name)
            self.assertIsNotNone(row.feed_title)
            self.assertIsNotNone(row.group_name)
            self.assertIsNotNone(row.config)
            if row.is_active:
                self.assertIsNotNone(row.config_modify_date)

    def test_add_and_remove_rss_info(self) -> None:
        rss_file_path = self.test_feed_dir_path / "my_test_feed1.xml"
        example_rss_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        shutil.copy(example_rss_file_path, rss_file_path)

        with DB.session_ctx() as s:
            rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.feedmaker.is_not(None), 
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows11 is not None

        FeedManager.add_rss_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.feedmaker.is_not(None), 
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows12 is not None
            self.assertEqual(len(rows11) + 1, len(rows12))

        FeedManager.remove_rss_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.feedmaker.is_not(None), 
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows13 is not None
            self.assertEqual(len(rows11), len(rows13))

    def test_load_all_rss_files(self) -> None:
        self.fm.load_all_rss_files(max_num_feeds=20)

        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.feedmaker.is_(True)).first()
            assert row is not None
            self.assertIsNotNone(row.feed_name)
            self.assertIsNotNone(row.feedmaker)
            self.assertIsNotNone(row.rss_update_date)

    def test_get_feed_name_public_feed_info_map(self) -> None:
        result = FeedManager.get_feed_name_public_feed_info_map()
        for _, public_feed_info in result.items():
            self.assertIn("feed_name", public_feed_info)
            self.assertIn("feed_title", public_feed_info)
            self.assertIn("group_name", public_feed_info)
            self.assertIn("file_size", public_feed_info)
            self.assertIn("num_items", public_feed_info)
            self.assertIn("upload_date", public_feed_info)

    def test_add_and_remove_public_feed_file(self) -> None:
        feed_name = "my_test_feed5"
        public_feed_file_path = self.fm.public_feed_dir_path / (feed_name + ".xml")
        example_rss_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        shutil.copy(example_rss_file_path, public_feed_file_path)

        with DB.session_ctx() as s:
            rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name, 
                                             FeedInfo.public_html.is_(True), 
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows11 is not None
            
        FeedManager.add_public_feed(public_feed_file_path)

        with DB.session_ctx() as s:
            rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name, 
                                             FeedInfo.public_html.is_(True), 
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows12 is not None
            self.assertEqual(len(rows11) + 1, len(rows12))

        FeedManager.remove_public_feed(public_feed_file_path)

        with DB.session_ctx() as s:
            rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name, 
                                             FeedInfo.public_html.is_(True), 
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows13 is not None
            self.assertEqual(len(rows11), len(rows13))

    def test_load_all_public_feed_files(self) -> None:
        self.fm.load_all_public_feed_files(max_num_public_feeds=40)

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).where(FeedInfo.public_feed_file_path.is_not(None)).all()
            assert rows is not None
            self.assertGreater(len(rows), 0)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.feed_name)
                self.assertIsNotNone(row.public_feed_file_path)
                self.assertGreater(row.file_size, 0)
                self.assertGreaterEqual(row.num_items, 0)
                self.assertIsNotNone(row.upload_date)

    def test_get_feed_name_progress_info_map(self) -> None:
        result = FeedManager.get_feed_name_progress_info_map()
        for _, progress_info in result.items():
            self.assertIn("feed_name", progress_info)
            self.assertIn("feed_title", progress_info)
            self.assertIn("group_name", progress_info)
            self.assertIn("current_index", progress_info)
            self.assertIn("total_item_count", progress_info)
            self.assertIn("unit_size_per_day", progress_info)
            self.assertIn("progress_ratio", progress_info)
            self.assertIn("due_date", progress_info)

    def test_add_and_remove_progress_from_info(self) -> None:
        example_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.completed.json"
        conf_file_path = self.test_feed_dir_path / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)

        FeedManager.add_config_info(self.test_feed_dir_path)

        progress_file_path = self.test_feed_dir_path / "start_idx.txt"
        date_str = Datetime.get_current_time_str()
        with progress_file_path.open("w", encoding="utf-8") as f:
            f.write(f"157\t{date_str}\n")

        with DB.session_ctx() as s:
            rows1 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.is_completed.is_(True), 
                                             FeedInfo.due_date.is_not(None)).all()
            assert rows1 is not None

        FeedManager.add_progress_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows2 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.is_completed.is_(True), 
                                             FeedInfo.due_date.is_not(None)).all()
            assert rows2 is not None
            self.assertEqual(len(rows1) + 1, len(rows2))

        FeedManager.remove_progress_info(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows3 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name, 
                                             FeedInfo.is_completed.is_(True), 
                                             FeedInfo.due_date.is_not(None)).all()
            assert rows3 is not None
            self.assertEqual(len(rows1), len(rows3))

    def test_load_all_progress_info_from_files(self) -> None:
        self.fm.load_all_config_files(max_num_feeds=100)
        self.fm.load_all_progress_info_from_files(max_num_feeds=300)

        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.is_completed.is_(True)).first()
            assert row is not None
            self.assertIsNotNone(row.feed_name)
            self.assertTrue(row.is_completed)
            self.assertGreaterEqual(row.current_index, 0)
            self.assertGreaterEqual(row.total_item_count, 0)
            self.assertGreaterEqual(row.unit_size_per_day, 0.0)
            self.assertGreaterEqual(row.progress_ratio, 0.0)
            self.assertIsNotNone(row.due_date)


if __name__ == "__main__":
    unittest.main()
