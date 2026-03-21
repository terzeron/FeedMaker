#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MySQL Integration Tests using testcontainers

This module tests MySQL database operations with a real MySQL container.
These tests verify CRUD operations and DB class functionality.

Note: These tests require Docker to be running.
"""

import unittest
import logging.config
from pathlib import Path
from datetime import datetime, timedelta, timezone

from tests.common_test_util import start_mysql_container
from bin.db import DB
from bin.models import SampleTable, FeedInfo, GroupInfo, UserSession
from bin.problem_manager import ProblemManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestMySQLIntegration(unittest.TestCase):
    """Integration tests for MySQL using real container"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        self.mysql_container = None
        self.db_config = None

    def tearDown(self) -> None:
        """Clean up test fixtures"""
        pass

    def test_mysql_container_startup(self) -> None:
        """Test that MySQL container starts successfully"""
        with start_mysql_container() as mysql:
            # Verify connection URL is generated
            connection_url = mysql.get_connection_url()
            LOGGER.info(f"MySQL connection URL: {connection_url}")
            self.assertIsNotNone(connection_url)
            self.assertIn("mysql", connection_url)

    def test_mysql_basic_crud(self) -> None:
        """Test basic CRUD operations with MySQL container"""
        with start_mysql_container() as mysql:
            # Get connection details from container attributes
            LOGGER.info("Testing CRUD operations with MySQL")

            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            # Initialize DB
            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Test CREATE
                with DB.session_ctx(db_config=db_config) as session:
                    sample = SampleTable(name="Alice", age=25)
                    session.add(sample)
                    session.commit()
                    LOGGER.info("Created record: Alice, age 25")

                # Test READ
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).all()
                    self.assertEqual(len(results), 1)
                    self.assertEqual(results[0].name, "Alice")
                    self.assertEqual(results[0].age, 25)
                    LOGGER.info("Read record successfully")

                # Test UPDATE
                with DB.session_ctx(db_config=db_config) as session:
                    record = session.query(SampleTable).filter_by(name="Alice").first()
                    self.assertIsNotNone(record)
                    record.age = 30
                    session.commit()
                    LOGGER.info("Updated Alice's age to 30")

                # Verify UPDATE
                with DB.session_ctx(db_config=db_config) as session:
                    record = session.query(SampleTable).filter_by(name="Alice").first()
                    self.assertEqual(record.age, 30)
                    LOGGER.info("Verified update")

                # Test DELETE
                with DB.session_ctx(db_config=db_config) as session:
                    record = session.query(SampleTable).filter_by(name="Alice").first()
                    session.delete(record)
                    session.commit()
                    LOGGER.info("Deleted record: Alice")

                # Verify DELETE
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).all()
                    self.assertEqual(len(results), 0)
                    LOGGER.info("Verified deletion")

            finally:
                # Cleanup
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_mysql_multiple_records(self) -> None:
        """Test operations with multiple records"""
        with start_mysql_container() as mysql:
            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Insert multiple records
                with DB.session_ctx(db_config=db_config) as session:
                    session.add(SampleTable(name="Alice", age=25))
                    session.add(SampleTable(name="Bob", age=30))
                    session.add(SampleTable(name="Charlie", age=35))
                    session.commit()
                    LOGGER.info("Created 3 records")

                # Query all
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).all()
                    self.assertEqual(len(results), 3)
                    LOGGER.info("Verified 3 records exist")

                # Query with filter
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).filter(SampleTable.age >= 30).all()
                    self.assertEqual(len(results), 2)
                    names = [r.name for r in results]
                    self.assertIn("Bob", names)
                    self.assertIn("Charlie", names)
                    LOGGER.info("Verified filter query")

                # Query with order by
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).order_by(SampleTable.age.desc()).all()
                    self.assertEqual(results[0].name, "Charlie")
                    self.assertEqual(results[1].name, "Bob")
                    self.assertEqual(results[2].name, "Alice")
                    LOGGER.info("Verified order by query")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_mysql_merge_upsert(self) -> None:
        """Test merge (upsert) operations"""
        with start_mysql_container() as mysql:
            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # First merge (insert)
                with DB.session_ctx(db_config=db_config) as session:
                    session.merge(SampleTable(name="Alice", age=25))
                    session.commit()
                    LOGGER.info("First merge (insert): Alice, age 25")

                # Second merge (update)
                with DB.session_ctx(db_config=db_config) as session:
                    session.merge(SampleTable(name="Alice", age=30))
                    session.commit()
                    LOGGER.info("Second merge (update): Alice, age 30")

                # Verify final state
                with DB.session_ctx(db_config=db_config) as session:
                    results = session.query(SampleTable).filter_by(name="Alice").all()
                    self.assertEqual(len(results), 1)
                    self.assertEqual(results[0].age, 30)
                    LOGGER.info("Verified merge result: only one Alice with age 30")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_feed_info_access_date_update(self) -> None:
        """Test FeedInfo access_date update - core business logic"""
        with start_mysql_container() as mysql:
            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Create initial FeedInfo records
                with DB.session_ctx(db_config=db_config) as session:
                    feed1 = FeedInfo(feed_name="comic/naver/test_feed1", feed_title="Test Feed 1", group_name="comic", is_active=True, http_request=False, access_date=None, view_date=None)
                    feed2 = FeedInfo(feed_name="comic/daum/test_feed2", feed_title="Test Feed 2", group_name="comic", is_active=True, http_request=False, access_date=None, view_date=None)
                    session.add(feed1)
                    session.add(feed2)
                    session.commit()
                    LOGGER.info("Created 2 FeedInfo records")

                # Simulate access log processing - update access_date
                access_time = datetime.now(timezone.utc)
                with DB.session_ctx(db_config=db_config) as session:
                    feed = session.query(FeedInfo).filter_by(feed_name="comic/naver/test_feed1").first()
                    self.assertIsNotNone(feed)
                    feed.http_request = True
                    feed.access_date = access_time
                    session.commit()
                    LOGGER.info(f"Updated access_date for test_feed1: {access_time}")

                # Verify access_date was updated
                with DB.session_ctx(db_config=db_config) as session:
                    feed = session.query(FeedInfo).filter_by(feed_name="comic/naver/test_feed1").first()
                    self.assertIsNotNone(feed)
                    self.assertTrue(feed.http_request)
                    self.assertIsNotNone(feed.access_date)
                    # MySQL may return timezone-naive datetime, so ensure both are UTC-aware for comparison
                    access_date_aware = feed.access_date.replace(tzinfo=timezone.utc) if feed.access_date.tzinfo is None else feed.access_date
                    access_time_aware = access_time.replace(tzinfo=timezone.utc) if access_time.tzinfo is None else access_time
                    time_diff = abs((access_date_aware - access_time_aware).total_seconds())
                    self.assertLess(time_diff, 1.0, "Access date should be within 1 second")
                    LOGGER.info("Verified access_date update")

                # Simulate view log processing - update view_date
                view_time = datetime.now(timezone.utc)
                with DB.session_ctx(db_config=db_config) as session:
                    feed = session.query(FeedInfo).filter_by(feed_name="comic/daum/test_feed2").first()
                    self.assertIsNotNone(feed)
                    feed.http_request = True
                    feed.view_date = view_time
                    session.commit()
                    LOGGER.info(f"Updated view_date for test_feed2: {view_time}")

                # Verify view_date was updated
                with DB.session_ctx(db_config=db_config) as session:
                    feed = session.query(FeedInfo).filter_by(feed_name="comic/daum/test_feed2").first()
                    self.assertIsNotNone(feed)
                    self.assertTrue(feed.http_request)
                    self.assertIsNotNone(feed.view_date)
                    # MySQL may return timezone-naive datetime, so ensure both are UTC-aware for comparison
                    view_date_aware = feed.view_date.replace(tzinfo=timezone.utc) if feed.view_date.tzinfo is None else feed.view_date
                    view_time_aware = view_time.replace(tzinfo=timezone.utc) if view_time.tzinfo is None else view_time
                    time_diff = abs((view_date_aware - view_time_aware).total_seconds())
                    self.assertLess(time_diff, 1.0, "View date should be within 1 second")
                    LOGGER.info("Verified view_date update")

                # Query feeds with access_date (simulating AccessLogManager behavior)
                with DB.session_ctx(db_config=db_config) as session:
                    accessed_feeds = session.query(FeedInfo).filter(FeedInfo.http_request == True, FeedInfo.access_date.isnot(None)).all()
                    self.assertEqual(len(accessed_feeds), 1)
                    self.assertEqual(accessed_feeds[0].feed_name, "comic/naver/test_feed1")
                    LOGGER.info("Verified query for accessed feeds")

                # Query feeds with view_date
                with DB.session_ctx(db_config=db_config) as session:
                    viewed_feeds = session.query(FeedInfo).filter(FeedInfo.http_request == True, FeedInfo.view_date.isnot(None)).all()
                    self.assertEqual(len(viewed_feeds), 1)
                    self.assertEqual(viewed_feeds[0].feed_name, "comic/daum/test_feed2")
                    LOGGER.info("Verified query for viewed feeds")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_group_info_feed_info_relationship(self) -> None:
        """Test GroupInfo and FeedInfo relationship"""
        with start_mysql_container() as mysql:
            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Create GroupInfo
                with DB.session_ctx(db_config=db_config) as session:
                    group = GroupInfo(group_name="comic", feed_name="comic/naver/test_feed")
                    session.add(group)
                    session.commit()
                    LOGGER.info("Created GroupInfo: comic")

                # Create FeedInfo with same group_name
                with DB.session_ctx(db_config=db_config) as session:
                    feed = FeedInfo(feed_name="comic/naver/test_feed", feed_title="Test Comic Feed", group_name="comic", is_active=True)
                    session.add(feed)
                    session.commit()
                    LOGGER.info("Created FeedInfo with group_name: comic")

                # Query feeds by group_name
                with DB.session_ctx(db_config=db_config) as session:
                    feeds = session.query(FeedInfo).filter_by(group_name="comic").all()
                    self.assertEqual(len(feeds), 1)
                    self.assertEqual(feeds[0].feed_name, "comic/naver/test_feed")
                    self.assertEqual(feeds[0].group_name, "comic")
                    LOGGER.info("Verified feed-group relationship")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_user_session_creation_and_expiry(self) -> None:
        """Test UserSession creation and expiry checking"""
        with start_mysql_container() as mysql:
            db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                from datetime import timedelta

                # Create a valid session
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    valid_session = UserSession(session_id="test_session_123", user_email="test@example.com", user_name="Test User", created_at=now, expires_at=now + timedelta(hours=24), last_accessed_at=now)
                    session.add(valid_session)
                    session.commit()
                    LOGGER.info("Created valid UserSession")

                # Create an expired session
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    expired_session = UserSession(
                        session_id="expired_session_456",
                        user_email="expired@example.com",
                        user_name="Expired User",
                        created_at=now - timedelta(days=2),
                        expires_at=now - timedelta(hours=1),  # Expired 1 hour ago
                        last_accessed_at=now - timedelta(days=1),
                    )
                    session.add(expired_session)
                    session.commit()
                    LOGGER.info("Created expired UserSession")

                # Query valid sessions
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    valid_sessions = session.query(UserSession).filter(UserSession.expires_at > now).all()
                    self.assertEqual(len(valid_sessions), 1)
                    self.assertEqual(valid_sessions[0].session_id, "test_session_123")
                    LOGGER.info("Verified valid session query")

                # Query expired sessions
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    expired_sessions = session.query(UserSession).filter(UserSession.expires_at <= now).all()
                    self.assertEqual(len(expired_sessions), 1)
                    self.assertEqual(expired_sessions[0].session_id, "expired_session_456")
                    LOGGER.info("Verified expired session query")

                # Update last_accessed_at
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    user_session = session.query(UserSession).filter_by(session_id="test_session_123").first()
                    user_session.last_accessed_at = now
                    session.commit()
                    LOGGER.info("Updated last_accessed_at")

                # Verify update
                with DB.session_ctx(db_config=db_config) as session:
                    user_session = session.query(UserSession).filter_by(session_id="test_session_123").first()
                    # MySQL may return timezone-naive datetime, so ensure both are UTC-aware for comparison
                    last_accessed_aware = user_session.last_accessed_at.replace(tzinfo=timezone.utc) if user_session.last_accessed_at.tzinfo is None else user_session.last_accessed_at
                    now_aware = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now
                    time_diff = abs((last_accessed_aware - now_aware).total_seconds())
                    self.assertLess(time_diff, 1.0)
                    LOGGER.info("Verified last_accessed_at update")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def _setup_status_info_db(self, mysql):
        """get_feed_name_status_info_map 테스트용 DB 초기화 헬퍼"""
        db_config = {"drivername": "mysql+pymysql", "user": mysql.username, "password": mysql.password, "host": "localhost", "port": int(mysql.get_exposed_port(3306)), "database": mysql.dbname}
        DB.dispose_all()
        DB.init(db_config)
        DB.create_all_tables(db_config)
        return db_config

    def test_status_info_excludes_inactive_feeds(self) -> None:
        """비활성화된 피드(is_active=False)가 결과에서 제외되는지 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    session.add(FeedInfo(feed_name="active_feed", group_name="mygroup", feed_title="Active Feed", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.add(FeedInfo(feed_name="inactive_feed", group_name="mygroup", feed_title="", is_active=False, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("active_feed", result)
                self.assertNotIn("inactive_feed", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_excludes_unregistered_feeds(self) -> None:
        """조건1: http_request=0, public_html=0, feedmaker=0인 피드 제외 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    # 완전히 미등록된 피드 (모두 False) → 제외 대상
                    session.add(FeedInfo(feed_name="unregistered", group_name="grp", feed_title="Unregistered", is_active=True, http_request=False, public_html=False, feedmaker=False))
                    # 하나라도 True면 포함
                    session.add(FeedInfo(feed_name="only_requested", group_name="grp", feed_title="Only Requested", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.add(FeedInfo(feed_name="only_public", group_name="grp", feed_title="Only Public", is_active=True, http_request=False, public_html=True, feedmaker=False))
                    session.add(FeedInfo(feed_name="only_feedmaker", group_name="grp", feed_title="Only Feedmaker", is_active=True, http_request=False, public_html=False, feedmaker=True))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertNotIn("unregistered", result)
                self.assertIn("only_requested", result)
                self.assertIn("only_public", result)
                self.assertIn("only_feedmaker", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_same_feed_name_active_vs_inactive_groups(self) -> None:
        """동일 feed_name이 활성/비활성 그룹에 존재할 때 활성 것만 반환 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    session.add(FeedInfo(feed_name="shared_feed", group_name="groupA", feed_title="Shared Active", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.add(FeedInfo(feed_name="shared_feed", group_name="groupB", feed_title="", is_active=False, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("shared_feed", result)
                self.assertEqual(result["shared_feed"]["group_name"], "groupA")
                self.assertEqual(result["shared_feed"]["feed_title"], "Shared Active")
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_empty_table(self) -> None:
        """빈 테이블에서 빈 결과 반환 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                result = ProblemManager.get_feed_name_status_info_map()
                self.assertEqual(result, {})
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_all_inactive_returns_empty(self) -> None:
        """모든 피드가 비활성일 때 빈 결과 반환 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    session.add(FeedInfo(feed_name="feed1", group_name="grp", is_active=False, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.add(FeedInfo(feed_name="feed2", group_name="grp", is_active=False, http_request=True, public_html=False, feedmaker=True))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()
                self.assertEqual(result, {})
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_partial_setup_feeds_included(self) -> None:
        """부분적으로 설정된 피드들(문제 있는 상태)이 결과에 포함되는지 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    # http_request=1, public_html=1, feedmaker=0 → 등록됐지만 feedmaker 미실행
                    session.add(FeedInfo(feed_name="no_feedmaker", group_name="grp", feed_title="No Feedmaker", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    # http_request=0, public_html=1, feedmaker=1 → 요청은 안 됐지만 등록/생성됨
                    session.add(FeedInfo(feed_name="no_request", group_name="grp", feed_title="No Request", is_active=True, http_request=False, public_html=True, feedmaker=True))
                    # http_request=1, public_html=0, feedmaker=1 → 요청/생성은 됐지만 등록 안 됨
                    session.add(FeedInfo(feed_name="no_public", group_name="grp", feed_title="No Public", is_active=True, http_request=True, public_html=False, feedmaker=True, access_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("no_feedmaker", result)
                self.assertIn("no_request", result)
                self.assertIn("no_public", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_result_contains_all_expected_fields(self) -> None:
        """반환된 결과에 필요한 모든 필드가 포함되는지 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                with DB.session_ctx() as session:
                    session.add(FeedInfo(feed_name="test_feed", group_name="test_group", feed_title="Test Title", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now, view_date=now, rss_update_date=now, upload_date=now, public_feed_file_path="/path/to/feed.xml"))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("test_feed", result)
                info = result["test_feed"]
                expected_keys = {"feed_name", "feed_title", "group_name", "http_request", "access_date", "view_date", "feedmaker", "update_date", "public_html", "file_path", "upload_date"}
                self.assertEqual(set(info.keys()), expected_keys)
                self.assertEqual(info["feed_name"], "test_feed")
                self.assertEqual(info["feed_title"], "Test Title")
                self.assertEqual(info["group_name"], "test_group")
                self.assertTrue(info["http_request"])
                self.assertTrue(info["public_html"])
                self.assertFalse(info["feedmaker"])
                self.assertEqual(info["file_path"], "/path/to/feed.xml")
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_excludes_fully_healthy_feeds(self) -> None:
        """조건3: 완전히 정상인 피드(요청+등록+생성+config+최근접근) 제외 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                old = now - timedelta(days=90)

                with DB.session_ctx() as session:
                    # 정상 피드: 모두 갖춰져 있고 최근 접근됨 → 제외 대상
                    session.add(FeedInfo(feed_name="healthy_feed", group_name="grp", feed_title="Healthy", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=now))
                    # 정상이지만 오래된 접근 → 문제 피드로 포함
                    session.add(FeedInfo(feed_name="stale_feed", group_name="grp", feed_title="Stale", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=old))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                # 최근 접근된 정상 피드는 제외
                self.assertNotIn("healthy_feed", result)
                # 오래된 접근의 정상 피드는 포함 (문제 피드)
                self.assertIn("stale_feed", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_excludes_old_requested_only_feeds(self) -> None:
        """조건2: 요청만 되고(http_request=1, public_html=0, feedmaker=0) 오래 전 접근된 피드 제외 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                old = now - timedelta(days=90)

                with DB.session_ctx() as session:
                    # 요청만 되고 오래 전 접근됨 → 제외 대상
                    session.add(FeedInfo(feed_name="old_requested", group_name="grp", feed_title="Old Requested", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=old))
                    # 요청만 되고 최근 접근됨 → 문제 피드로 포함
                    session.add(FeedInfo(feed_name="recent_requested", group_name="grp", feed_title="Recent Requested", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=now))
                    # 요청만 되고 access_date 없음 → 포함
                    session.add(FeedInfo(feed_name="no_access_date", group_name="grp", feed_title="No Access Date", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=None))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                # 오래 전 접근된 요청만 된 피드는 제외
                self.assertNotIn("old_requested", result)
                # 최근 접근된 요청만 된 피드는 포함
                self.assertIn("recent_requested", result)
                # access_date 없는 요청만 된 피드는 포함
                self.assertIn("no_access_date", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_healthy_feed_with_view_date_only(self) -> None:
        """조건3: view_date만 최근인 정상 피드도 제외되는지 검증"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)

                with DB.session_ctx() as session:
                    # access_date 없고 view_date만 최근 → 정상이므로 제외
                    session.add(FeedInfo(feed_name="viewed_only", group_name="grp", feed_title="Viewed Only", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=None, view_date=now))
                    # feedmaker=False면 조건3(http_request=1,public_html=1,feedmaker=1) 패턴에 매칭되지 않음 → 포함
                    session.add(FeedInfo(feed_name="partial_setup", group_name="grp", feed_title="Partial Setup", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now, view_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                # view_date만 최근인 정상 피드는 제외
                self.assertNotIn("viewed_only", result)
                # feedmaker=False인 부분 설정 피드는 조건3에 해당하지 않으므로 포함
                self.assertIn("partial_setup", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_condition2_boundary_at_num_days(self) -> None:
        """조건2 경계값: 정확히 num_days(60일) 전 접근은 제외되지 않고, 61일 전은 제외"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                at_boundary = now - timedelta(days=60)
                past_boundary = now - timedelta(days=61)

                with DB.session_ctx() as session:
                    # 정확히 60일 전 → DATEDIFF=60, 60 > 60 은 False → 포함
                    session.add(FeedInfo(feed_name="at_60days", group_name="grp", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=at_boundary))
                    # 61일 전 → DATEDIFF=61, 61 > 60 은 True → 제외
                    session.add(FeedInfo(feed_name="at_61days", group_name="grp", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=past_boundary))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("at_60days", result)
                self.assertNotIn("at_61days", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_condition3_boundary_at_num_days(self) -> None:
        """조건3 경계값: 정확히 num_days(60일) 전 접근은 제외되지 않고, 59일 전은 제외"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                at_boundary = now - timedelta(days=60)
                within_boundary = now - timedelta(days=59)

                with DB.session_ctx() as session:
                    # 정확히 60일 전 → DATEDIFF=60, 60 < 60 은 False → 포함 (문제 피드)
                    session.add(FeedInfo(feed_name="at_60days", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=at_boundary))
                    # 59일 전 → DATEDIFF=59, 59 < 60 은 True → 제외 (정상 피드)
                    session.add(FeedInfo(feed_name="at_59days", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=within_boundary))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("at_60days", result)
                self.assertNotIn("at_59days", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_condition3_or_logic_access_old_view_recent(self) -> None:
        """조건3 OR 로직: access_date가 오래됐어도 view_date가 최근이면 정상으로 제외"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                old = now - timedelta(days=90)

                with DB.session_ctx() as session:
                    # access_date 오래됨 + view_date 최근 → OR 조건으로 정상 판정 → 제외
                    session.add(FeedInfo(feed_name="old_access_recent_view", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=old, view_date=now))
                    # access_date 최근 + view_date 오래됨 → OR 조건으로 정상 판정 → 제외
                    session.add(FeedInfo(feed_name="recent_access_old_view", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=now, view_date=old))
                    # 둘 다 오래됨 → OR 조건 모두 False → 포함 (문제 피드)
                    session.add(FeedInfo(feed_name="both_old", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=old, view_date=old))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertNotIn("old_access_recent_view", result)
                self.assertNotIn("recent_access_old_view", result)
                self.assertIn("both_old", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_condition2_not_applied_when_public_html_true(self) -> None:
        """조건2는 public_html=0인 경우에만 적용됨. public_html=True면 매칭 안 됨"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                old = now - timedelta(days=90)

                with DB.session_ctx() as session:
                    # http_request=1, public_html=1, feedmaker=0, 오래된 접근
                    # → 조건2 패턴(public_html=0)에 매칭 안 됨 → 제외 안 됨
                    session.add(FeedInfo(feed_name="has_public", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=old))
                    # http_request=1, public_html=0, feedmaker=1, 오래된 접근
                    # → 조건2 패턴(feedmaker=0)에 매칭 안 됨 → 제외 안 됨
                    session.add(FeedInfo(feed_name="has_feedmaker", group_name="grp", is_active=True, http_request=True, public_html=False, feedmaker=True, access_date=old))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                self.assertIn("has_public", result)
                self.assertIn("has_feedmaker", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_condition3_empty_config_not_excluded(self) -> None:
        """조건3: config가 빈 문자열이면 IS NOT NULL이지만 유효하지 않은 설정.
        현재 구현에서는 빈 문자열도 IS NOT NULL로 판정되어 제외됨을 검증."""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)

                with DB.session_ctx() as session:
                    # config 빈 문자열 (모델 기본값) + 나머지 조건 모두 충족
                    # → config IS NOT NULL = True (빈 문자열은 NULL이 아님)
                    # → 조건3에 매칭되어 제외됨
                    session.add(FeedInfo(feed_name="empty_config", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config="", access_date=now))
                    # 유효한 config
                    session.add(FeedInfo(feed_name="valid_config", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                # 둘 다 조건3에 의해 정상 피드로 판정되어 제외됨
                self.assertNotIn("empty_config", result)
                self.assertNotIn("valid_config", result)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_status_info_comprehensive_mixed_scenario(self) -> None:
        """다양한 상태의 피드들이 혼재된 종합 시나리오"""
        with start_mysql_container() as mysql:
            db_config = self._setup_status_info_db(mysql)
            try:
                now = datetime.now(timezone.utc)
                old = now - timedelta(days=90)

                with DB.session_ctx() as session:
                    # 1. 비활성 → 제외
                    session.add(FeedInfo(feed_name="inactive", group_name="grp", is_active=False, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=now))
                    # 2. 미등록 (모두 False) → 조건1에 의해 제외
                    session.add(FeedInfo(feed_name="unregistered", group_name="grp", is_active=True, http_request=False, public_html=False, feedmaker=False))
                    # 3. 요청전용 + 오래 전 접근 → 조건2에 의해 제외
                    session.add(FeedInfo(feed_name="old_request_only", group_name="grp", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=old))
                    # 4. 정상 피드 + 최근 접근 → 조건3에 의해 제외
                    session.add(FeedInfo(feed_name="healthy", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=now))
                    # 5. 요청전용 + 최근 접근 → 문제 피드, 포함
                    session.add(FeedInfo(feed_name="recent_request_only", group_name="grp", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=now))
                    # 6. 정상 구조이지만 오래된 접근 → 문제 피드, 포함
                    session.add(FeedInfo(feed_name="stale_healthy", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=True, config='{"rss":{}}', access_date=old))
                    # 7. 부분 설정 (feedmaker 없음) → 문제 피드, 포함
                    session.add(FeedInfo(feed_name="no_feedmaker", group_name="grp", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=now))
                    session.commit()

                result = ProblemManager.get_feed_name_status_info_map()

                # 제외되어야 하는 피드
                self.assertNotIn("inactive", result)
                self.assertNotIn("unregistered", result)
                self.assertNotIn("old_request_only", result)
                self.assertNotIn("healthy", result)
                # 포함되어야 하는 피드 (문제 피드)
                self.assertIn("recent_request_only", result)
                self.assertIn("stale_healthy", result)
                self.assertIn("no_feedmaker", result)
                self.assertEqual(len(result), 3)
            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()


if __name__ == "__main__":
    unittest.main()
