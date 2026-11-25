#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MySQL Integration Tests using testcontainers

This module tests MySQL database operations with a real MySQL container.
These tests verify CRUD operations and DB class functionality.

Note: These tests require Docker to be running.
"""

import json
import shutil
import tempfile
import unittest
import logging.config
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tests.common_test_util import start_mysql_container
from bin.db import DB
from bin.feed_manager import FeedManager
from bin.models import SampleTable, FeedInfo, GroupInfo, UserSession
from backend import auth


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestMySQLIntegration(unittest.TestCase):
    """Integration tests for MySQL using real container"""

    mysql_container = None
    db_config = None

    @classmethod
    def setUpClass(cls) -> None:
        """Start MySQL container once for all tests"""
        cls._ctx = start_mysql_container()
        cls.mysql_container = cls._ctx.__enter__()
        cls.db_config = {"drivername": "mysql+pymysql", "user": cls.mysql_container.username, "password": cls.mysql_container.password, "host": "localhost", "port": int(cls.mysql_container.get_exposed_port(3306)), "database": cls.mysql_container.dbname}
        DB.init(cls.db_config)
        LOGGER.info(f"MySQL container started at port {cls.db_config['port']}")

    @classmethod
    def tearDownClass(cls) -> None:
        """Stop MySQL container after all tests"""
        DB.dispose_all()
        cls._ctx.__exit__(None, None, None)

    def setUp(self) -> None:
        """Create tables before each test"""
        DB.create_all_tables(self.db_config)

    def tearDown(self) -> None:
        """Drop tables after each test for isolation"""
        DB.drop_all_tables(self.db_config)

    def test_mysql_container_startup(self) -> None:
        """Test that MySQL container starts successfully"""
        connection_url = self.mysql_container.get_connection_url()
        LOGGER.info(f"MySQL connection URL: {connection_url}")
        self.assertIsNotNone(connection_url)
        self.assertIn("mysql", connection_url)

    def test_mysql_basic_crud(self) -> None:
        """Test basic CRUD operations with MySQL container"""
        LOGGER.info("Testing CRUD operations with MySQL")

        # Test CREATE
        with DB.session_ctx(db_config=self.db_config) as session:
            sample = SampleTable(name="Alice", age=25)
            session.add(sample)
            session.commit()
            LOGGER.info("Created record: Alice, age 25")

        # Test READ
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).all()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].name, "Alice")
            self.assertEqual(results[0].age, 25)
            LOGGER.info("Read record successfully")

        # Test UPDATE
        with DB.session_ctx(db_config=self.db_config) as session:
            record = session.query(SampleTable).filter_by(name="Alice").first()
            self.assertIsNotNone(record)
            record.age = 30
            session.commit()
            LOGGER.info("Updated Alice's age to 30")

        # Verify UPDATE
        with DB.session_ctx(db_config=self.db_config) as session:
            record = session.query(SampleTable).filter_by(name="Alice").first()
            self.assertEqual(record.age, 30)
            LOGGER.info("Verified update")

        # Test DELETE
        with DB.session_ctx(db_config=self.db_config) as session:
            record = session.query(SampleTable).filter_by(name="Alice").first()
            session.delete(record)
            session.commit()
            LOGGER.info("Deleted record: Alice")

        # Verify DELETE
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).all()
            self.assertEqual(len(results), 0)
            LOGGER.info("Verified deletion")

    def test_mysql_multiple_records(self) -> None:
        """Test operations with multiple records"""
        # Insert multiple records
        with DB.session_ctx(db_config=self.db_config) as session:
            session.add(SampleTable(name="Alice", age=25))
            session.add(SampleTable(name="Bob", age=30))
            session.add(SampleTable(name="Charlie", age=35))
            session.commit()
            LOGGER.info("Created 3 records")

        # Query all
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).all()
            self.assertEqual(len(results), 3)
            LOGGER.info("Verified 3 records exist")

        # Query with filter
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).filter(SampleTable.age >= 30).all()
            self.assertEqual(len(results), 2)
            names = [r.name for r in results]
            self.assertIn("Bob", names)
            self.assertIn("Charlie", names)
            LOGGER.info("Verified filter query")

        # Query with order by
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).order_by(SampleTable.age.desc()).all()
            self.assertEqual(results[0].name, "Charlie")
            self.assertEqual(results[1].name, "Bob")
            self.assertEqual(results[2].name, "Alice")
            LOGGER.info("Verified order by query")

    def test_mysql_merge_upsert(self) -> None:
        """Test merge (upsert) operations"""
        # First merge (insert)
        with DB.session_ctx(db_config=self.db_config) as session:
            session.merge(SampleTable(name="Alice", age=25))
            session.commit()
            LOGGER.info("First merge (insert): Alice, age 25")

        # Second merge (update)
        with DB.session_ctx(db_config=self.db_config) as session:
            session.merge(SampleTable(name="Alice", age=30))
            session.commit()
            LOGGER.info("Second merge (update): Alice, age 30")

        # Verify final state
        with DB.session_ctx(db_config=self.db_config) as session:
            results = session.query(SampleTable).filter_by(name="Alice").all()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].age, 30)
            LOGGER.info("Verified merge result: only one Alice with age 30")

    def test_feed_info_access_date_update(self) -> None:
        """Test FeedInfo access_date update - core business logic"""
        # Create initial FeedInfo records
        with DB.session_ctx(db_config=self.db_config) as session:
            feed1 = FeedInfo(feed_name="comic/naver/test_feed1", feed_title="Test Feed 1", group_name="comic", is_active=True, http_request=False, access_date=None, view_date=None)
            feed2 = FeedInfo(feed_name="comic/daum/test_feed2", feed_title="Test Feed 2", group_name="comic", is_active=True, http_request=False, access_date=None, view_date=None)
            session.add(feed1)
            session.add(feed2)
            session.commit()
            LOGGER.info("Created 2 FeedInfo records")

        # Simulate access log processing - update access_date
        access_time = datetime.now(timezone.utc)
        with DB.session_ctx(db_config=self.db_config) as session:
            feed = session.query(FeedInfo).filter_by(feed_name="comic/naver/test_feed1").first()
            self.assertIsNotNone(feed)
            feed.http_request = True
            feed.access_date = access_time
            session.commit()
            LOGGER.info(f"Updated access_date for test_feed1: {access_time}")

        # Verify access_date was updated
        with DB.session_ctx(db_config=self.db_config) as session:
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
        with DB.session_ctx(db_config=self.db_config) as session:
            feed = session.query(FeedInfo).filter_by(feed_name="comic/daum/test_feed2").first()
            self.assertIsNotNone(feed)
            feed.http_request = True
            feed.view_date = view_time
            session.commit()
            LOGGER.info(f"Updated view_date for test_feed2: {view_time}")

        # Verify view_date was updated
        with DB.session_ctx(db_config=self.db_config) as session:
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
        with DB.session_ctx(db_config=self.db_config) as session:
            accessed_feeds = session.query(FeedInfo).filter(FeedInfo.http_request.is_(True), FeedInfo.access_date.isnot(None)).all()
            self.assertEqual(len(accessed_feeds), 1)
            self.assertEqual(accessed_feeds[0].feed_name, "comic/naver/test_feed1")
            LOGGER.info("Verified query for accessed feeds")

        # Query feeds with view_date
        with DB.session_ctx(db_config=self.db_config) as session:
            viewed_feeds = session.query(FeedInfo).filter(FeedInfo.http_request.is_(True), FeedInfo.view_date.isnot(None)).all()
            self.assertEqual(len(viewed_feeds), 1)
            self.assertEqual(viewed_feeds[0].feed_name, "comic/daum/test_feed2")
            LOGGER.info("Verified query for viewed feeds")

    def test_group_info_feed_info_relationship(self) -> None:
        """Test GroupInfo and FeedInfo relationship"""
        # Create GroupInfo
        with DB.session_ctx(db_config=self.db_config) as session:
            group = GroupInfo(group_name="comic", feed_name="comic/naver/test_feed")
            session.add(group)
            session.commit()
            LOGGER.info("Created GroupInfo: comic")

        # Create FeedInfo with same group_name
        with DB.session_ctx(db_config=self.db_config) as session:
            feed = FeedInfo(feed_name="comic/naver/test_feed", feed_title="Test Comic Feed", group_name="comic", is_active=True)
            session.add(feed)
            session.commit()
            LOGGER.info("Created FeedInfo with group_name: comic")

        # Query feeds by group_name
        with DB.session_ctx(db_config=self.db_config) as session:
            feeds = session.query(FeedInfo).filter_by(group_name="comic").all()
            self.assertEqual(len(feeds), 1)
            self.assertEqual(feeds[0].feed_name, "comic/naver/test_feed")
            self.assertEqual(feeds[0].group_name, "comic")
            LOGGER.info("Verified feed-group relationship")

    def test_user_session_creation_and_expiry(self) -> None:
        """Test UserSession creation and expiry checking"""
        # Create a valid session
        with DB.session_ctx(db_config=self.db_config) as session:
            now = datetime.now(timezone.utc)
            valid_session = UserSession(session_id="test_session_123", user_email="test@example.com", user_name="Test User", created_at=now, expires_at=now + timedelta(hours=24), last_accessed_at=now)
            session.add(valid_session)
            session.commit()
            LOGGER.info("Created valid UserSession")

        # Create an expired session
        with DB.session_ctx(db_config=self.db_config) as session:
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
        with DB.session_ctx(db_config=self.db_config) as session:
            now = datetime.now(timezone.utc)
            valid_sessions = session.query(UserSession).filter(UserSession.expires_at > now).all()
            self.assertEqual(len(valid_sessions), 1)
            self.assertEqual(valid_sessions[0].session_id, "test_session_123")
            LOGGER.info("Verified valid session query")

        # Query expired sessions
        with DB.session_ctx(db_config=self.db_config) as session:
            now = datetime.now(timezone.utc)
            expired_sessions = session.query(UserSession).filter(UserSession.expires_at <= now).all()
            self.assertEqual(len(expired_sessions), 1)
            self.assertEqual(expired_sessions[0].session_id, "expired_session_456")
            LOGGER.info("Verified expired session query")

        # Update last_accessed_at
        with DB.session_ctx(db_config=self.db_config) as session:
            now = datetime.now(timezone.utc)
            user_session = session.query(UserSession).filter_by(session_id="test_session_123").first()
            user_session.last_accessed_at = now
            session.commit()
            LOGGER.info("Updated last_accessed_at")

        # Verify update
        with DB.session_ctx(db_config=self.db_config) as session:
            user_session = session.query(UserSession).filter_by(session_id="test_session_123").first()
            # MySQL may return timezone-naive datetime, so ensure both are UTC-aware for comparison
            last_accessed_aware = user_session.last_accessed_at.replace(tzinfo=timezone.utc) if user_session.last_accessed_at.tzinfo is None else user_session.last_accessed_at
            now_aware = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now
            time_diff = abs((last_accessed_aware - now_aware).total_seconds())
            self.assertLess(time_diff, 1.0)
            LOGGER.info("Verified last_accessed_at update")


class TestStatusInfoDuplicateFeedFiltering(unittest.TestCase):
    """get_feed_name_status_info_map의 중복 feed_name 필터링을 실제 MySQL로 검증"""

    mysql_container = None
    db_config = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = start_mysql_container()
        cls.mysql_container = cls._ctx.__enter__()
        cls.db_config = {"drivername": "mysql+pymysql", "user": cls.mysql_container.username, "password": cls.mysql_container.password, "host": "localhost", "port": int(cls.mysql_container.get_exposed_port(3306)), "database": cls.mysql_container.dbname}
        DB.init(cls.db_config)

    @classmethod
    def tearDownClass(cls) -> None:
        DB.dispose_all()
        cls._ctx.__exit__(None, None, None)

    def setUp(self) -> None:
        DB.create_all_tables(self.db_config)

    def tearDown(self) -> None:
        DB.drop_all_tables(self.db_config)

    def test_feedmaker_false_excluded_when_true_sibling_exists(self) -> None:
        """
        같은 feed_name에 feedmaker=True(정상)와 feedmaker=False(비정상)가 공존할 때,
        feedmaker=True가 SQL 조건 3번으로 제외되어도
        feedmaker=False가 status_info 결과에 나타나지 않아야 한다.
        (mzgtoon/story_of_sword_of_student 케이스 재현)
        """
        from bin.problem_manager import ProblemManager

        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            # feedmaker=True, 최근 접근, config 있음 → SQL 3번 조건으로 rows에서 제외됨
            s.add(FeedInfo(feed_name="dup_feed", group_name="good_group", is_active=True, feedmaker=True, public_html=True, http_request=True, config='{"configuration": {}}', access_date=recent))
            # feedmaker=False, config 없음 → 제외 조건에 안 걸림 → rows에 포함됨
            s.add(FeedInfo(feed_name="dup_feed", group_name="bad_group", is_active=True, feedmaker=False, public_html=True, http_request=True, access_date=recent))

        result = ProblemManager.get_feed_name_status_info_map()

        # feedmaker=False인 bad_group이 결과에 없어야 함
        self.assertNotIn("dup_feed", result)

    def test_feedmaker_false_kept_when_no_true_sibling(self) -> None:
        """feedmaker=True 레코드가 없으면 feedmaker=False 레코드가 결과에 포함되어야 한다."""
        from bin.problem_manager import ProblemManager

        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name="solo_feed", group_name="only_group", is_active=True, feedmaker=False, public_html=True, http_request=True, access_date=recent))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("solo_feed", result)
        self.assertEqual(result["solo_feed"]["group_name"], "only_group")
        self.assertFalse(result["solo_feed"]["feedmaker"])

    def test_normal_feed_excluded_by_condition3(self) -> None:
        """feedmaker=True + 최근 접근 + config 있음 → 정상 피드로 결과에서 제외"""
        from bin.problem_manager import ProblemManager

        now = datetime.now(timezone.utc)
        recent = now - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name="normal_feed", group_name="normal_group", is_active=True, feedmaker=True, public_html=True, http_request=True, config='{"configuration": {}}', access_date=recent))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertNotIn("normal_feed", result)

    def test_record_feed_access_updates_all_duplicates(self) -> None:
        """record_feed_access가 같은 feed_name의 모든 레코드를 업데이트하는지 검증"""
        from bin.access_log_manager import AccessLogManager

        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name="shared_feed", group_name="group_a", is_active=True))
            s.add(FeedInfo(feed_name="shared_feed", group_name="group_b", is_active=True))

        AccessLogManager.record_feed_access("shared_feed")

        with DB.session_ctx(db_config=self.db_config) as s:
            feeds = s.query(FeedInfo).filter_by(feed_name="shared_feed").all()
            self.assertEqual(len(feeds), 2)
            for feed in feeds:
                self.assertTrue(feed.http_request)
                self.assertIsNotNone(feed.access_date)


class TestStatusInfoQueryAllFieldCombinations(unittest.TestCase):
    """
    status_info 쿼리에 관여하는 6개 필드의 모든 2^6=64 조합을 실제 MySQL로 검증.

    필드 (MSB→LSB):
      bit5: http_request (H)
      bit4: public_html (P)
      bit3: feedmaker (F)
      bit2: access_date (A) — recent(1일전) / None
      bit1: view_date (V) — recent(1일전) / None
      bit0: config (C) — non-empty / empty("")

    쿼리 제외 조건:
      C1: H=0 AND P=0 AND F=0
      C2: H=1 AND P=0 AND F=0 AND A!=NULL AND DATEDIFF>60 — recent이면 미적용
      C3: H=1 AND P=1 AND F=1 AND config!="" AND (A recent OR V recent)
    """

    mysql_container = None
    db_config = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = start_mysql_container()
        cls.mysql_container = cls._ctx.__enter__()
        cls.db_config = {"drivername": "mysql+pymysql", "user": cls.mysql_container.username, "password": cls.mysql_container.password, "host": "localhost", "port": int(cls.mysql_container.get_exposed_port(3306)), "database": cls.mysql_container.dbname}
        DB.init(cls.db_config)

    @classmethod
    def tearDownClass(cls) -> None:
        DB.dispose_all()
        cls._ctx.__exit__(None, None, None)

    def setUp(self) -> None:
        DB.create_all_tables(self.db_config)

    def tearDown(self) -> None:
        DB.drop_all_tables(self.db_config)

    @staticmethod
    def _should_be_excluded(h: bool, p: bool, f: bool, a: bool, v: bool, c: bool) -> str:
        """제외 조건에 해당하면 조건명 반환, 포함이면 빈 문자열.
        collect_date, rss_update_date, upload_date는 WHERE에 미사용이므로
        필터링 결과에 영향을 주지 않는다."""
        # C1: http_request=0 AND public_html=0 AND feedmaker=0 AND config=""
        #     (설정이 있는 미운영 피드는 문제로 표시)
        if not h and not p and not f and not c:
            return "C1"
        # C2: H=1, P=0, F=0, A=recent → DATEDIFF=1 < 60 → 미적용
        # C3: H=1 AND P=1 AND F=1 AND config!="" AND (A recent OR V recent)
        if h and p and f and c and (a or v):
            return "C3"
        return ""

    def test_all_512_combinations(self) -> None:
        """9개 필드의 모든 2^9=512 조합에 대해 쿼리 결과 검증.

        WHERE 필터 필드 (6개):
          bit8: http_request (H)
          bit7: public_html (P)
          bit6: feedmaker (F)
          bit5: access_date (A)
          bit4: view_date (V)
          bit3: config (C)

        ORDER BY 전용 필드 (3개) — WHERE에 미사용, 필터링 결과에 영향 없어야 함:
          bit2: collect_date (CD)
          bit1: rss_update_date (RU)
          bit0: upload_date (UD)
        """
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)
        older = datetime.now(timezone.utc) - timedelta(days=30)

        with DB.session_ctx(db_config=self.db_config) as s:
            for i in range(512):
                h = bool(i & 256)
                p = bool(i & 128)
                f = bool(i & 64)
                a = recent if (i & 32) else None
                v = recent if (i & 16) else None
                c_val = '{"configuration": {}}' if (i & 8) else ""
                cd = older if (i & 4) else None
                ru = older if (i & 2) else None
                ud = older if (i & 1) else None

                s.add(FeedInfo(feed_name=f"feed_{i:09b}", group_name=f"group_{i:09b}", is_active=True, http_request=h, public_html=p, feedmaker=f, access_date=a, view_date=v, config=c_val, collect_date=cd, rss_update_date=ru, upload_date=ud))

        result = ProblemManager.get_feed_name_status_info_map()

        excluded_count = 0
        included_count = 0
        for i in range(512):
            h = bool(i & 256)
            p = bool(i & 128)
            f = bool(i & 64)
            a = bool(i & 32)
            v = bool(i & 16)
            c = bool(i & 8)
            cd = bool(i & 4)
            ru = bool(i & 2)
            ud = bool(i & 1)
            feed_name = f"feed_{i:09b}"
            bits = f"H={int(h)} P={int(p)} F={int(f)} A={int(a)} V={int(v)} C={int(c)} CD={int(cd)} RU={int(ru)} UD={int(ud)}"

            reason = self._should_be_excluded(h, p, f, a, v, c)
            if reason:
                self.assertNotIn(feed_name, result, f"{feed_name} ({bits}) should be excluded by {reason}")
                excluded_count += 1
            else:
                self.assertIn(feed_name, result, f"{feed_name} ({bits}) should be included")
                included_count += 1

        # C1: H=0,P=0,F=0,C=0 → 32조합(A,V,CD,RU,UD) = 32개 제외
        # C3: H=1,P=1,F=1,C=1,(A=1 OR V=1) → 3×8조합(CD,RU,UD) = 24개 제외
        # 합계: 56개 제외, 456개 포함
        self.assertEqual(excluded_count, 56, "Expected 56 excluded (C1=32, C3=24)")
        self.assertEqual(included_count, 456, "Expected 456 included")
        self.assertEqual(len(result), 456)

    def test_config_empty_vs_nonempty(self) -> None:
        """config="" vs config=non-empty가 C3 조건에 미치는 영향 검증.
        config!=""일 때만 C3가 적용되어 정상 피드로 제외되어야 한다."""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            # config="" → C3 미적용 → 포함 (설정 없는 피드는 문제 피드)
            s.add(FeedInfo(feed_name="feed_empty_config", group_name="group_empty", is_active=True, http_request=True, public_html=True, feedmaker=True, access_date=recent, view_date=recent, config=""))
            # config=non-empty → C3 적용 → 제외 (완전한 정상 피드)
            s.add(FeedInfo(feed_name="feed_valid_config", group_name="group_valid", is_active=True, http_request=True, public_html=True, feedmaker=True, access_date=recent, view_date=recent, config='{"configuration": {}}'))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("feed_empty_config", result, "config='' → C3 should NOT apply → included as problem feed")
        self.assertNotIn("feed_valid_config", result, "config=non-empty → C3 applies → excluded as healthy")

    def test_condition2_old_access_date(self) -> None:
        """C2: H=1, P=0, F=0, access_date > 60일 전 → 제외"""
        from bin.problem_manager import ProblemManager

        old = datetime.now(timezone.utc) - timedelta(days=90)
        recent = datetime.now(timezone.utc) - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            # 오래된 접근 → C2로 제외
            s.add(FeedInfo(feed_name="feed_old_access", group_name="group_old", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=old))
            # 최근 접근 → C2 미적용 → 포함
            s.add(FeedInfo(feed_name="feed_recent_access", group_name="group_recent", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=recent))
            # 접근 없음 → C2 미적용(access_date IS NULL) → 포함
            s.add(FeedInfo(feed_name="feed_no_access", group_name="group_no", is_active=True, http_request=True, public_html=False, feedmaker=False))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertNotIn("feed_old_access", result, "Old access should be excluded by C2")
        self.assertIn("feed_recent_access", result, "Recent access should not be excluded by C2")
        self.assertIn("feed_no_access", result, "No access_date should not be excluded by C2")

    def test_condition2_boundary_60_days(self) -> None:
        """C2 경계값: DATEDIFF 정확히 60일 vs 61일"""
        from bin.problem_manager import ProblemManager

        exactly_60 = datetime.now(timezone.utc) - timedelta(days=60)
        exactly_61 = datetime.now(timezone.utc) - timedelta(days=61)

        with DB.session_ctx(db_config=self.db_config) as s:
            # 60일 → DATEDIFF=60, NOT > 60 → 포함
            s.add(FeedInfo(feed_name="feed_60d", group_name="group_60d", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=exactly_60))
            # 61일 → DATEDIFF=61, > 60 → C2로 제외
            s.add(FeedInfo(feed_name="feed_61d", group_name="group_61d", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=exactly_61))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("feed_60d", result, "60 days is NOT > 60 → should be included")
        self.assertNotIn("feed_61d", result, "61 days > 60 → should be excluded by C2")

    def test_inactive_feed_always_excluded(self) -> None:
        """is_active=False인 피드는 모든 조건과 무관하게 제외"""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name="feed_inactive", group_name="group_inactive", is_active=False, http_request=True, public_html=True, feedmaker=False, access_date=recent))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertNotIn("feed_inactive", result)

    def test_result_contains_correct_fields(self) -> None:
        """결과 dict의 value에 모든 필수 필드가 올바른 값으로 포함되는지 검증"""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name="feed_fields", group_name="group_fields", feed_title="Test Title", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=recent, view_date=recent, rss_update_date=recent, upload_date=recent, public_feed_file_path="/xml/feed_fields.xml"))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("feed_fields", result)
        entry = result["feed_fields"]
        self.assertEqual(entry["feed_name"], "feed_fields")
        self.assertEqual(entry["feed_title"], "Test Title")
        self.assertEqual(entry["group_name"], "group_fields")
        self.assertTrue(entry["http_request"])
        self.assertTrue(entry["public_html"])
        self.assertFalse(entry["feedmaker"])
        self.assertIsNotNone(entry["access_date"])
        self.assertIsNotNone(entry["view_date"])
        self.assertIsNotNone(entry["update_date"])  # rss_update_date
        self.assertIsNotNone(entry["upload_date"])
        self.assertEqual(entry["file_path"], "/xml/feed_fields.xml")

    def test_duplicate_feed_name_order_by_affects_result(self) -> None:
        """같은 feed_name 중복 시 ORDER BY에 의해 나중 row가 dict를 덮어쓰는지 검증"""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)
        older = datetime.now(timezone.utc) - timedelta(days=30)

        with DB.session_ctx(db_config=self.db_config) as s:
            # feedmaker=False → ORDER BY feedmaker에서 먼저 나옴 (0)
            s.add(FeedInfo(feed_name="dup_feed", group_name="group_first", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=recent, upload_date=older))
            # feedmaker=True → ORDER BY feedmaker에서 나중 (1) → dict 덮어씀
            s.add(
                FeedInfo(
                    feed_name="dup_feed",
                    group_name="group_second",
                    is_active=True,
                    http_request=True,
                    public_html=True,
                    feedmaker=True,
                    access_date=recent,
                    upload_date=recent,
                    config="",  # config="" → C3 미적용 → rows에 포함
                )
            )

        result = ProblemManager.get_feed_name_status_info_map()

        # feedmaker_true_names 필터로 feedmaker=False(group_first)가 스킵됨
        # feedmaker=True(group_second)가 결과에 남음
        self.assertIn("dup_feed", result)
        self.assertEqual(result["dup_feed"]["group_name"], "group_second")

    def test_order_by_datetime_fields_affect_dict_override(self) -> None:
        """ORDER BY에 포함된 datetime 필드(collect_date, rss_update_date, upload_date)가
        NULL vs 값 있음일 때 중복 feed_name에서 어떤 row가 최종 dict에 남는지 검증.
        ORDER BY: feedmaker, public_html, http_request, collect_date, rss_update_date,
                  upload_date, access_date, view_date (ASC, NULL이 먼저)
        → 나중 row가 dict를 덮어쓰므로, 값이 있는 row가 최종 결과에 남아야 한다."""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)
        older = datetime.now(timezone.utc) - timedelta(days=30)

        with DB.session_ctx(db_config=self.db_config) as s:
            # 같은 feedmaker/public_html/http_request, collect_date=NULL → ORDER BY에서 먼저
            s.add(FeedInfo(feed_name="order_feed", group_name="group_null_dates", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=recent, collect_date=None, rss_update_date=None, upload_date=None))
            # collect_date=값 → ORDER BY에서 나중 → dict 덮어씀
            s.add(FeedInfo(feed_name="order_feed", group_name="group_with_dates", is_active=True, http_request=True, public_html=True, feedmaker=False, access_date=recent, collect_date=older, rss_update_date=older, upload_date=older))

        result = ProblemManager.get_feed_name_status_info_map()

        self.assertIn("order_feed", result)
        # datetime 값이 있는 group_with_dates가 나중에 처리되어 dict에 남아야 함
        self.assertEqual(result["order_feed"]["group_name"], "group_with_dates")
        self.assertIsNotNone(result["order_feed"]["update_date"])  # rss_update_date
        self.assertIsNotNone(result["order_feed"]["upload_date"])

    def test_output_fields_with_various_null_combinations(self) -> None:
        """출력 필드(rss_update_date, upload_date, public_feed_file_path)가
        NULL/값 있음일 때 결과 dict에 올바르게 반영되는지 검증"""
        from bin.problem_manager import ProblemManager

        recent = datetime.now(timezone.utc) - timedelta(days=1)

        with DB.session_ctx(db_config=self.db_config) as s:
            # 모든 출력 필드 NULL
            s.add(FeedInfo(feed_name="feed_all_null", group_name="group_all_null", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=recent))
            # 모든 출력 필드 값 있음
            s.add(FeedInfo(feed_name="feed_all_set", group_name="group_all_set", is_active=True, http_request=True, public_html=False, feedmaker=False, access_date=recent, rss_update_date=recent, upload_date=recent, public_feed_file_path="/xml/test.xml"))

        result = ProblemManager.get_feed_name_status_info_map()

        # NULL 필드
        self.assertIn("feed_all_null", result)
        null_entry = result["feed_all_null"]
        self.assertIsNone(null_entry["update_date"])
        self.assertIsNone(null_entry["upload_date"])
        self.assertEqual(null_entry["file_path"], "")

        # 값 있는 필드
        self.assertIn("feed_all_set", result)
        set_entry = result["feed_all_set"]
        self.assertIsNotNone(set_entry["update_date"])
        self.assertIsNotNone(set_entry["upload_date"])
        self.assertEqual(set_entry["file_path"], "/xml/test.xml")


class TestAuthMySQLIntegration(unittest.TestCase):
    """backend.auth session lifecycle를 실제 MySQL로 검증"""

    mysql_container = None
    db_config = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = start_mysql_container()
        cls.mysql_container = cls._ctx.__enter__()
        cls.db_config = {"drivername": "mysql+pymysql", "user": cls.mysql_container.username, "password": cls.mysql_container.password, "host": "localhost", "port": int(cls.mysql_container.get_exposed_port(3306)), "database": cls.mysql_container.dbname}
        DB.init(cls.db_config)

    @classmethod
    def tearDownClass(cls) -> None:
        DB.dispose_all()
        cls._ctx.__exit__(None, None, None)

    def setUp(self) -> None:
        self.enterContext(patch.dict("os.environ", {"FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST": "user@example.com,expired@example.com"}))
        DB.create_all_tables(self.db_config)
        self._original_session_ctx = DB.session_ctx
        self._db_patch = patch("backend.auth.DB.session_ctx", side_effect=lambda *args, **kwargs: self._original_session_ctx(db_config=self.db_config))
        self._db_patch.start()

    def tearDown(self) -> None:
        self._db_patch.stop()
        DB.drop_all_tables(self.db_config)

    @patch("backend.auth.generate_session_id", return_value="session_integration_123")
    def test_create_session_and_get_session_extend_expiry(self, mock_session_id) -> None:
        session_id = auth.create_session("user@example.com", "Test User", "https://example.com/profile.png")
        self.assertEqual(session_id, "session_integration_123")

        with DB.session_ctx(db_config=self.db_config) as session:
            created = session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(created)
            self.assertEqual(created.user_email, "user@example.com")
            original_expires_at = created.expires_at

        result = auth.get_session(session_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.user_name, "Test User")
        self.assertEqual(result.profile_picture_url, "https://example.com/profile.png")

        with DB.session_ctx(db_config=self.db_config) as session:
            updated = session.query(UserSession).filter_by(session_id=session_id).first()
            self.assertIsNotNone(updated)
            updated_expires_at = updated.expires_at
            original_aware = original_expires_at.replace(tzinfo=timezone.utc) if original_expires_at.tzinfo is None else original_expires_at
            updated_aware = updated_expires_at.replace(tzinfo=timezone.utc) if updated_expires_at.tzinfo is None else updated_expires_at
            self.assertGreaterEqual(updated_aware, original_aware)
            self.assertIsNotNone(updated.last_accessed_at)

    def test_get_session_deletes_expired_session(self) -> None:
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        with DB.session_ctx(db_config=self.db_config) as session:
            session.add(UserSession(session_id="expired_integration_session", user_email="expired@example.com", user_name="Expired User", expires_at=expired_time, last_accessed_at=expired_time))

        result = auth.get_session("expired_integration_session")
        self.assertIsNone(result)

        with DB.session_ctx(db_config=self.db_config) as session:
            deleted = session.query(UserSession).filter_by(session_id="expired_integration_session").first()
            self.assertIsNone(deleted)

    def test_delete_session_and_cleanup_expired_sessions(self) -> None:
        now = datetime.now(timezone.utc)
        with DB.session_ctx(db_config=self.db_config) as session:
            session.add(UserSession(session_id="active_to_delete", user_email="active@example.com", user_name="Active User", expires_at=now + timedelta(days=1), last_accessed_at=now))
            session.add(UserSession(session_id="expired_to_cleanup", user_email="expired@example.com", user_name="Expired User", expires_at=now - timedelta(days=1), last_accessed_at=now - timedelta(days=2)))

        self.assertTrue(auth.delete_session("active_to_delete"))
        self.assertFalse(auth.delete_session("active_to_delete"))

        cleaned = auth.cleanup_expired_sessions()
        self.assertEqual(cleaned, 1)

        with DB.session_ctx(db_config=self.db_config) as session:
            remaining = {row.session_id for row in session.query(UserSession).all()}
            self.assertNotIn("active_to_delete", remaining)
            self.assertNotIn("expired_to_cleanup", remaining)


class TestFeedProgressMySQLIntegration(unittest.TestCase):
    """진행 중(is_completed) 피드의 진행 현황 갱신과 조회를 실제 MySQL + 파일시스템으로 검증한다."""

    mysql_container = None
    db_config = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._ctx = start_mysql_container()
        cls.mysql_container = cls._ctx.__enter__()
        cls.db_config = {"drivername": "mysql+pymysql", "user": cls.mysql_container.username, "password": cls.mysql_container.password, "host": "localhost", "port": int(cls.mysql_container.get_exposed_port(3306)), "database": cls.mysql_container.dbname}
        DB.init(cls.db_config)

    @classmethod
    def tearDownClass(cls) -> None:
        DB.dispose_all()
        cls._ctx.__exit__(None, None, None)

    def setUp(self) -> None:
        DB.create_all_tables(self.db_config)
        self.tmp_root = Path(tempfile.mkdtemp())
        self.group_name = "naver"
        self.feed_name = "progress_feed"
        self.feed_dir_path = self.tmp_root / self.group_name / self.feed_name
        (self.feed_dir_path / "newlist").mkdir(parents=True)
        (self.feed_dir_path / "html").mkdir()
        conf = {"configuration": {"collection": {"is_completed": True, "unit_size_per_day": 2}}}
        (self.feed_dir_path / "conf.json").write_text(json.dumps(conf), encoding="utf-8")
        (self.feed_dir_path / "start_idx.txt").write_text("3\t2026-11-01 00:00:00\n", encoding="utf-8")
        # 두 목록 파일에 걸쳐 중복 URL이 있다 → 고유 URL 10개
        (self.feed_dir_path / "newlist" / "20261101.txt").write_text("".join(f"https://example.com/{i}\tT{i}\n" for i in range(6)), encoding="utf-8")
        (self.feed_dir_path / "newlist" / "20261102.txt").write_text("".join(f"https://example.com/{i}\tT{i}\n" for i in range(4, 10)), encoding="utf-8")
        for i in range(2):
            (self.feed_dir_path / "html" / f"{i}.html").write_text("<html></html>", encoding="utf-8")
        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(FeedInfo(feed_name=self.feed_name, group_name=self.group_name, feed_title="Progress", is_active=True, is_completed=True, config=json.dumps(conf), total_item_count=0))
        self._work_dir_patcher = patch.object(FeedManager, "work_dir_path", self.tmp_root)
        self._work_dir_patcher.start()

    def tearDown(self) -> None:
        self._work_dir_patcher.stop()
        shutil.rmtree(self.tmp_root, ignore_errors=True)
        DB.drop_all_tables(self.db_config)

    def _db_row(self) -> FeedInfo:
        with DB.session_ctx(db_config=self.db_config) as s:
            row = s.query(FeedInfo).filter_by(group_name=self.group_name, feed_name=self.feed_name).one()
            s.expunge(row)
            return row

    def test_refresh_progress_counts_persists_newlist_totals(self) -> None:
        FeedManager.refresh_progress_counts(self.feed_dir_path)

        row = self._db_row()
        self.assertTrue(row.is_completed)
        self.assertEqual(row.current_index, 3)
        self.assertEqual(row.total_item_count, 10)
        self.assertEqual(row.progress_ratio, int((3 + 4) * 100 / (10 + 1)))
        self.assertIsNotNone(row.collect_date)
        # 남은 3개를 하루 2개씩 → 2일 뒤 완료 예정
        due_date = row.due_date
        assert due_date is not None
        due_date = due_date if due_date.tzinfo else due_date.replace(tzinfo=timezone.utc)
        self.assertAlmostEqual((due_date - datetime.now(timezone.utc)).total_seconds(), timedelta(days=2).total_seconds(), delta=60)

    def test_progress_map_counts_newlist_live_before_db_refresh(self) -> None:
        FeedManager.refresh_progress_counts(self.feed_dir_path)
        # run.py 실행 도중 newlist에 새 URL이 추가되었지만 DB는 아직 갱신 전이다
        with (self.feed_dir_path / "newlist" / "20261103.txt").open("w", encoding="utf-8") as f:
            f.write("https://example.com/9\tT9\nhttps://example.com/10\tT10\nhttps://example.com/11\tT11\n")

        info = FeedManager.get_feed_name_progress_info_map()[self.feed_name]

        self.assertEqual(self._db_row().total_item_count, 10)
        self.assertEqual(info["total_item_count"], 12)
        self.assertEqual(info["html_file_count"], 2)
        self.assertEqual(info["current_index"], 3)

    def test_progress_map_finds_inactive_prefixed_directories(self) -> None:
        # 비활성 그룹/피드는 '_' 접두사 디렉터리지만 DB 이름은 canonical이다
        inactive_dir = self.tmp_root / f"_{self.group_name}" / f"_{self.feed_name}"
        inactive_dir.parent.mkdir()
        self.feed_dir_path.rename(inactive_dir)

        info = FeedManager.get_feed_name_progress_info_map()[self.feed_name]

        self.assertEqual(info["total_item_count"], 10)
        self.assertEqual(info["html_file_count"], 2)

    def test_progress_map_falls_back_to_db_without_newlist(self) -> None:
        FeedManager.refresh_progress_counts(self.feed_dir_path)
        shutil.rmtree(self.feed_dir_path / "newlist")

        info = FeedManager.get_feed_name_progress_info_map()[self.feed_name]

        self.assertEqual(info["total_item_count"], 10)

    def test_progress_map_falls_back_to_db_when_newlist_is_empty(self) -> None:
        FeedManager.refresh_progress_counts(self.feed_dir_path)
        for list_file in (self.feed_dir_path / "newlist").glob("*.txt"):
            list_file.unlink()

        info = FeedManager.get_feed_name_progress_info_map()[self.feed_name]

        self.assertEqual(info["total_item_count"], 10)


if __name__ == "__main__":
    unittest.main()
