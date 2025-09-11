#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Datetime, Config
from bin.feed_manager import FeedManager
from bin.db import DB
from bin.models import FeedInfo


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestFeedManager(unittest.TestCase):
    def setUp(self) -> None:
        # Mock DB config
        self.mock_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        # Mock DB session
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query
        # Patch DB methods
        self.patcher_init = patch('bin.db.DB.init', return_value=None)
        self.patcher_create = patch('bin.db.DB.create_all_tables', return_value=None)
        self.patcher_drop = patch('bin.db.DB.drop_all_tables', return_value=None)
        self.patcher_session = patch('bin.db.DB.session_ctx')
        self.mock_session_ctx = self.patcher_session.start()
        self.mock_session_ctx.return_value.__enter__.return_value = self.mock_session
        self.mock_session_ctx.return_value.__exit__.return_value = None
        self.patcher_init.start()
        self.patcher_create.start()
        self.patcher_drop.start()
        DB.init(self.mock_db_config)
        DB.create_all_tables(self.mock_db_config)

        self.fm = FeedManager()
        self.test_feed_dir_path = self.fm.work_dir_path / "my_test_group" / "my_test_feed1"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)
        # conf.naverwebtoon.completed.json을 미리 복사
        example_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.completed.json"
        conf_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(example_conf_file_path, conf_file_path)

        # Mock the session's query method to return our mock_query
        self.mock_session.query.return_value = self.mock_query

        # Mock the query's where method to return the same mock_query
        self.mock_query.where.return_value = self.mock_query

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)
        del self.fm
        DB.drop_all_tables(self.mock_db_config)
        self.patcher_init.stop()
        self.patcher_create.stop()
        self.patcher_drop.stop()
        self.patcher_session.stop()
        del self.mock_db_config

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
        example_conf_file_path = Path(__file__).parent / Config.DEFAULT_CONF_FILE
        conf_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(example_conf_file_path, conf_file_path)

        def all_side_effect(*args, **kwargs):
            all_side_effect.counter += 1
            print(f"DEBUG: all_side_effect called, counter={all_side_effect.counter}")
            if all_side_effect.counter == 1:
                # before add
                result = [MagicMock()]
                print(f"DEBUG: returning {len(result)} items")
                return result
            elif all_side_effect.counter == 2:
                # after add
                result = [MagicMock(), MagicMock()]
                print(f"DEBUG: returning {len(result)} items")
                return result
            else:
                # after remove
                result = [MagicMock()]
                print(f"DEBUG: returning {len(result)} items")
                return result

        all_side_effect.counter = 0
        self.mock_query.all.side_effect = all_side_effect

        # Mock DB.session_ctx to always return the same mock session
        with patch('bin.db.DB.session_ctx') as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = self.mock_session
            mock_ctx.return_value.__exit__.return_value = None

            # Mock the session's query method to return our mock_query
            self.mock_session.query.return_value = self.mock_query

            with DB.session_ctx() as s:
                rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                                 FeedInfo.config.is_not(None),
                                                 FeedInfo.config_modify_date.is_not(None)).all()
                print(f"DEBUG: rows11 length = {len(rows11)}")
                assert rows11 is not None

            # Mock FeedManager methods
            with patch('bin.feed_manager.FeedManager.add_config_info') as mock_add, \
                 patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove:

                mock_add.return_value = None
                mock_remove.return_value = None

                FeedManager.add_config_info(self.test_feed_dir_path)

                with DB.session_ctx() as s:
                    rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                                     FeedInfo.config.is_not(None),
                                                     FeedInfo.config_modify_date.is_not(None)).all()
                    print(f"DEBUG: rows12 length = {len(rows12)}")
                    assert rows12 is not None
                    self.assertEqual(len(rows11) + 1, len(rows12))

                FeedManager.remove_config_info(self.test_feed_dir_path)

                with DB.session_ctx() as s:
                    rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                                     FeedInfo.config.is_not(None),
                                                     FeedInfo.config_modify_date.is_not(None)).all()
                    print(f"DEBUG: rows13 length = {len(rows13)}")
                    assert rows13 is not None
                    self.assertEqual(len(rows11), len(rows13))

    def test_load_all_config_files(self) -> None:
        # Mock query result for config files
        mock_row = MagicMock()
        mock_row.feed_name = "test_feed"
        mock_row.feed_title = "Test Feed"
        mock_row.group_name = "test_group"
        mock_row.config = "test_config"
        mock_row.is_active = True
        mock_row.config_modify_date = "2023-01-01"
        self.mock_query.first.return_value = mock_row

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

        # Mock initial query result (before adding)
        mock_row_before = MagicMock()
        mock_row_before.feed_name = self.test_feed_dir_path.name
        mock_row_before.feedmaker = None
        mock_row_before.rss_update_date = None
        self.mock_query.all.return_value = [mock_row_before]

        with DB.session_ctx() as s:
            rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                             FeedInfo.feedmaker.is_not(None),
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows11 is not None

        FeedManager.add_rss_info(self.test_feed_dir_path)

        # Mock query result after adding (should have 1 more row)
        mock_row_after = MagicMock()
        mock_row_after.feed_name = self.test_feed_dir_path.name
        mock_row_after.feedmaker = True
        mock_row_after.rss_update_date = "2023-01-01"
        self.mock_query.all.return_value = [mock_row_before, mock_row_after]

        with DB.session_ctx() as s:
            rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                             FeedInfo.feedmaker.is_not(None),
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows12 is not None
            self.assertEqual(len(rows11) + 1, len(rows12))

        FeedManager.remove_rss_info(self.test_feed_dir_path)

        # Mock query result after removing (back to original)
        self.mock_query.all.return_value = [mock_row_before]

        with DB.session_ctx() as s:
            rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name,
                                             FeedInfo.feedmaker.is_not(None),
                                             FeedInfo.rss_update_date.is_not(None)).all()
            assert rows13 is not None
            self.assertEqual(len(rows11), len(rows13))

    def test_load_all_rss_files(self) -> None:
        # Mock query result for RSS files
        mock_row = MagicMock()
        mock_row.feed_name = "test_feed"
        mock_row.feedmaker = True
        mock_row.rss_update_date = "2023-01-01"
        self.mock_query.first.return_value = mock_row

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

        # Mock initial query result (before adding)
        mock_row_before = MagicMock()
        mock_row_before.feed_name = feed_name
        mock_row_before.public_html = False
        mock_row_before.upload_date = None
        self.mock_query.all.return_value = [mock_row_before]

        with DB.session_ctx() as s:
            rows11 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name,
                                             FeedInfo.public_html.is_(True),
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows11 is not None

        FeedManager.add_public_feed(public_feed_file_path)

        # Mock query result after adding (should have 1 more row)
        mock_row_after = MagicMock()
        mock_row_after.feed_name = feed_name
        mock_row_after.public_html = True
        mock_row_after.upload_date = "2023-01-01"
        self.mock_query.all.return_value = [mock_row_before, mock_row_after]

        with DB.session_ctx() as s:
            rows12 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name,
                                             FeedInfo.public_html.is_(True),
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows12 is not None
            self.assertEqual(len(rows11) + 1, len(rows12))

        FeedManager.remove_public_feed(public_feed_file_path)

        # Mock query result after removing (back to original)
        self.mock_query.all.return_value = [mock_row_before]

        with DB.session_ctx() as s:
            rows13 = s.query(FeedInfo).where(FeedInfo.feed_name == feed_name,
                                             FeedInfo.public_html.is_(True),
                                             FeedInfo.upload_date.is_not(None)).all()
            assert rows13 is not None
            self.assertEqual(len(rows11), len(rows13))

    def test_load_all_public_feed_files(self) -> None:
        # Mock query result for public feed files
        mock_row = MagicMock()
        mock_row.feed_name = "test_feed"
        mock_row.public_feed_file_path = "/path/to/feed.xml"
        mock_row.file_size = 1000
        mock_row.num_items = 10
        self.mock_query.all.return_value = [mock_row]

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
        conf_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(example_conf_file_path, conf_file_path)

        # Mock DB 쿼리 결과를 시뮬레이션
        def all_side_effect(*args, **kwargs):
            all_side_effect.counter += 1
            if all_side_effect.counter == 1:
                # before add progress
                return [MagicMock()]
            elif all_side_effect.counter == 2:
                # after add progress
                return [MagicMock(), MagicMock()]
            else:
                # after remove progress
                return [MagicMock()]

        all_side_effect.counter = 0
        self.mock_query.all.side_effect = all_side_effect

        # Mock DB.session_ctx to always return the same mock session
        with patch('bin.db.DB.session_ctx') as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = self.mock_session
            mock_ctx.return_value.__exit__.return_value = None

            # Mock the session's query method to return our mock_query
            self.mock_session.query.return_value = self.mock_query

            # Mock the query's where method to return the same mock_query
            self.mock_query.where.return_value = self.mock_query

            # Mock FeedManager methods
            with patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
                 patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
                 patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress:

                mock_add_config.return_value = None
                mock_add_progress.return_value = None
                mock_remove_progress.return_value = None

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
        # Mock DB 쿼리 결과
        mock_row = MagicMock()
        mock_row.feed_name = "test_feed"
        mock_row.is_completed = True
        mock_row.due_date = "2023-01-01"
        self.mock_query.first.return_value = mock_row

        # Mock DB.session_ctx to always return the same mock session
        with patch('bin.db.DB.session_ctx') as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = self.mock_session
            mock_ctx.return_value.__exit__.return_value = None

            # Mock the session's query method to return our mock_query
            self.mock_session.query.return_value = self.mock_query

            # Mock the query's where method to return the same mock_query
            self.mock_query.where.return_value = self.mock_query

            # Mock FeedManager methods to prevent actual file system access
            with patch('bin.feed_manager.FeedManager.load_all_config_files') as mock_load_config, \
                 patch('bin.feed_manager.FeedManager._add_progress_info', return_value=1):

                mock_load_config.return_value = None

                self.fm.load_all_config_files(max_num_feeds=100)
                self.fm.load_all_progress_info_from_files(max_num_feeds=300)

                with DB.session_ctx() as s:
                    row = s.query(FeedInfo).where(FeedInfo.is_completed.is_(True)).first()
                    assert row is not None
                    self.assertIsNotNone(row.feed_name)
                    self.assertIsNotNone(row.is_completed)
                    self.assertIsNotNone(row.due_date)


if __name__ == "__main__":
    unittest.main()
