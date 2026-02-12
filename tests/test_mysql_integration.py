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
from datetime import datetime, timezone

from tests.common_test_util import start_mysql_container
from bin.db import DB
from bin.models import SampleTable, FeedInfo, GroupInfo, UserSession


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
            LOGGER.info(f"Testing CRUD operations with MySQL")

            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

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
            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

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
            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

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
            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Create initial FeedInfo records
                with DB.session_ctx(db_config=db_config) as session:
                    feed1 = FeedInfo(
                        feed_name="comic/naver/test_feed1",
                        feed_title="Test Feed 1",
                        group_name="comic",
                        is_active=True,
                        http_request=False,
                        access_date=None,
                        view_date=None
                    )
                    feed2 = FeedInfo(
                        feed_name="comic/daum/test_feed2",
                        feed_title="Test Feed 2",
                        group_name="comic",
                        is_active=True,
                        http_request=False,
                        access_date=None,
                        view_date=None
                    )
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
                    accessed_feeds = session.query(FeedInfo).filter(
                        FeedInfo.http_request == True,
                        FeedInfo.access_date.isnot(None)
                    ).all()
                    self.assertEqual(len(accessed_feeds), 1)
                    self.assertEqual(accessed_feeds[0].feed_name, "comic/naver/test_feed1")
                    LOGGER.info("Verified query for accessed feeds")

                # Query feeds with view_date
                with DB.session_ctx(db_config=db_config) as session:
                    viewed_feeds = session.query(FeedInfo).filter(
                        FeedInfo.http_request == True,
                        FeedInfo.view_date.isnot(None)
                    ).all()
                    self.assertEqual(len(viewed_feeds), 1)
                    self.assertEqual(viewed_feeds[0].feed_name, "comic/daum/test_feed2")
                    LOGGER.info("Verified query for viewed feeds")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()

    def test_group_info_feed_info_relationship(self) -> None:
        """Test GroupInfo and FeedInfo relationship"""
        with start_mysql_container() as mysql:
            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                # Create GroupInfo
                with DB.session_ctx(db_config=db_config) as session:
                    group = GroupInfo(
                        group_name="comic",
                        feed_name="comic/naver/test_feed"
                    )
                    session.add(group)
                    session.commit()
                    LOGGER.info("Created GroupInfo: comic")

                # Create FeedInfo with same group_name
                with DB.session_ctx(db_config=db_config) as session:
                    feed = FeedInfo(
                        feed_name="comic/naver/test_feed",
                        feed_title="Test Comic Feed",
                        group_name="comic",
                        is_active=True
                    )
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
            db_config = {
                "drivername": "mysql+pymysql",
                "user": mysql.username,
                "password": mysql.password,
                "host": "localhost",
                "port": int(mysql.get_exposed_port(3306)),
                "database": mysql.dbname
            }

            DB.init(db_config)
            DB.create_all_tables(db_config)

            try:
                from datetime import timedelta

                # Create a valid session
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    valid_session = UserSession(
                        session_id="test_session_123",
                        user_email="test@example.com",
                        user_name="Test User",
                        facebook_access_token="test_token_123",
                        created_at=now,
                        expires_at=now + timedelta(hours=24),
                        last_accessed_at=now
                    )
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
                        facebook_access_token="expired_token_456",
                        created_at=now - timedelta(days=2),
                        expires_at=now - timedelta(hours=1),  # Expired 1 hour ago
                        last_accessed_at=now - timedelta(days=1)
                    )
                    session.add(expired_session)
                    session.commit()
                    LOGGER.info("Created expired UserSession")

                # Query valid sessions
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    valid_sessions = session.query(UserSession).filter(
                        UserSession.expires_at > now
                    ).all()
                    self.assertEqual(len(valid_sessions), 1)
                    self.assertEqual(valid_sessions[0].session_id, "test_session_123")
                    LOGGER.info("Verified valid session query")

                # Query expired sessions
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    expired_sessions = session.query(UserSession).filter(
                        UserSession.expires_at <= now
                    ).all()
                    self.assertEqual(len(expired_sessions), 1)
                    self.assertEqual(expired_sessions[0].session_id, "expired_session_456")
                    LOGGER.info("Verified expired session query")

                # Update last_accessed_at
                with DB.session_ctx(db_config=db_config) as session:
                    now = datetime.now(timezone.utc)
                    user_session = session.query(UserSession).filter_by(
                        session_id="test_session_123"
                    ).first()
                    user_session.last_accessed_at = now
                    session.commit()
                    LOGGER.info("Updated last_accessed_at")

                # Verify update
                with DB.session_ctx(db_config=db_config) as session:
                    user_session = session.query(UserSession).filter_by(
                        session_id="test_session_123"
                    ).first()
                    # MySQL may return timezone-naive datetime, so ensure both are UTC-aware for comparison
                    last_accessed_aware = user_session.last_accessed_at.replace(tzinfo=timezone.utc) if user_session.last_accessed_at.tzinfo is None else user_session.last_accessed_at
                    now_aware = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now
                    time_diff = abs((last_accessed_aware - now_aware).total_seconds())
                    self.assertLess(time_diff, 1.0)
                    LOGGER.info("Verified last_accessed_at update")

            finally:
                DB.drop_all_tables(db_config)
                DB.dispose_all()


if __name__ == "__main__":
    unittest.main()
