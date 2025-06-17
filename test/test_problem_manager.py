#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
from datetime import date
import logging.config
from pathlib import Path

from test.test_common import TestCommon
from bin.problem_manager import ProblemManager
from bin.db import DB, func, and_, or_, not_
from bin.models import FeedInfo

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    loki_container = None
    mysql_container = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.loki_container = TestCommon.prepare_loki_container()
        cls.mysql_container = TestCommon.prepare_mysql_container()
        DB.init(TestCommon.get_db_config(cls.mysql_container))

    @classmethod
    def tearDownClass(cls) -> None:
        TestCommon.dispose_mysql_container(cls.mysql_container)
        TestCommon.dispose_loki_container(cls.loki_container)

    def setUp(self) -> None:
        self.loki_url = TestCommon.get_loki_url(self.__class__.loki_container)
        self.db_config = TestCommon.get_db_config(self.__class__.mysql_container)
        DB.create_all_tables(self.db_config)

        self.pm = ProblemManager(self.loki_url)

        self.test_feed_dir_path = self.pm.feed_manager.work_dir_path / "my_test_group" / "my_test_feed2"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)

        del self.pm

        DB.drop_all_tables(self.db_config)
        del self.db_config
        del self.loki_url

    def test_get_feed_name_status_info_map(self) -> None:
        result = ProblemManager.get_feed_name_status_info_map()
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

    def test_update_feed_info(self) -> None:
        self.pm.update_feed_info(self.test_feed_dir_path)
        with DB.session_ctx() as s:
            row = s.query(FeedInfo).where(FeedInfo.feed_name == self.test_feed_dir_path.name).first()
            assert row is not None
            self.assertIsNotNone(row.feed_name)
            self.assertIsNotNone(row.feed_title)
            self.assertIsNotNone(row.group_name)

    def test_load_all(self) -> None:
        self.pm.load_all(max_num_feeds=20, max_num_public_feeds=40, max_num_days=1)

        with DB.session_ctx() as s:
            rows = s.query(FeedInfo).all()
            for row in rows:
                self.assertIsNotNone(row.feed_name)

            today = date.today()
            # 조건 1: 비어 있지 않은 피드
            has_some_data = or_(
                FeedInfo.http_request.isnot(None),
                FeedInfo.public_html.isnot(None),
                FeedInfo.feedmaker.isnot(None),
            )

            # 조건 2: 오래된 접근만 존재하는 미완성 피드 제외
            old_partial_feed = and_(
                FeedInfo.http_request.isnot(None),
                FeedInfo.public_html.is_(None),
                FeedInfo.feedmaker.is_(None),
                FeedInfo.access_date.isnot(None),
                func.datediff(FeedInfo.access_date, today) > self.pm.num_days
            )

            # 조건 3: 최근에 접근 또는 조회한 완성된 피드 제외
            recent_complete_feed = and_(
                FeedInfo.http_request.isnot(None),
                FeedInfo.public_html.isnot(None),
                FeedInfo.feedmaker.isnot(None),
                or_(
                    and_(
                        FeedInfo.access_date.isnot(None),
                        func.datediff(today, FeedInfo.access_date) < self.pm.num_days
                    ),
                    and_(
                        FeedInfo.view_date.isnot(None),
                        func.datediff(today, FeedInfo.view_date) < self.pm.num_days
                    )
                )
            )

            rows = s.query(FeedInfo).where(
                and_(has_some_data,
                     not_(old_partial_feed),
                     not_(recent_complete_feed))).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 0)


if __name__ == "__main__":
    unittest.main()
