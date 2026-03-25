#!/usr/bin/env python

import unittest
from unittest.mock import patch, MagicMock

from bin.db import DB
from bin.models import SampleTable
from sqlalchemy import event
from sqlalchemy.engine import URL
from bin.db import _DataSource


class TestDBWithMySQL(unittest.TestCase):
    """testcontainers MySQL을 사용한 실제 insert/select/upsert 테스트"""

    @classmethod
    def setUpClass(cls) -> None:
        from tests.common_test_util import start_mysql_container

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

    def test_insert_and_select(self) -> None:
        with DB.session_ctx(db_config=self.db_config) as s:
            s.add(SampleTable(name="Alice", age=10))

        with DB.session_ctx(db_config=self.db_config) as s:
            rows = s.query(SampleTable).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].name, "Alice")
            self.assertEqual(rows[0].age, 10)

        with DB.session_ctx(db_config=self.db_config) as s:
            rows = s.query(SampleTable).where(SampleTable.name == "Alice").all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].name, "Alice")
            self.assertEqual(rows[0].age, 10)

    def test_merge_upsert(self) -> None:
        with DB.session_ctx(db_config=self.db_config) as s:
            s.merge(SampleTable(name="Alice", age=20))

        with DB.session_ctx(db_config=self.db_config) as s:
            s.merge(SampleTable(name="Alice", age=30))

        with DB.session_ctx(db_config=self.db_config) as s:
            rows = s.query(SampleTable).where(SampleTable.name == "Alice").all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].age, 30)


class TestDataSourceInit(unittest.TestCase):
    """_DataSource.__init__ _set_utc event: MySQL cursor (52-54), SQLite fallback (57-60), SQLite failure (61-63)"""

    def _make_ds_and_capture_set_utc(self):
        """Create a _DataSource and capture the _set_utc function via event patching."""
        captured = []
        original = event.listens_for

        def patched_listens_for(target, identifier, *args, **kwargs):
            decorator = original(target, identifier, *args, **kwargs)

            def capturing_decorator(fn):
                if identifier == "connect":
                    captured.append(fn)
                return decorator(fn)

            return capturing_decorator

        with patch("bin.db.event.listens_for", side_effect=patched_listens_for):
            url = URL.create("sqlite", database=":memory:")
            ds = _DataSource(url)

        return ds, captured[0] if captured else None

    def test_set_utc_mysql_cursor_context_manager(self) -> None:
        """MySQL path: conn.cursor() as context manager works -> line 52-54"""
        ds, set_utc = self._make_ds_and_capture_set_utc()
        self.assertIsNotNone(set_utc)

        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        set_utc(conn, None)
        cur.execute.assert_called_with("SET time_zone = '+00:00'")
        ds.dispose()

    def test_set_utc_sqlite_fallback(self) -> None:
        """SQLite path: context manager fails, falls back to direct cursor -> line 57-60"""
        ds = _DataSource(URL.create("sqlite", database=":memory:"))
        # Actually connect to the SQLite engine to trigger the event with a real connection
        # SQLite raw connection does not support cursor() as context manager -> hits TypeError path
        with ds._engine.connect() as conn:
            pass  # _set_utc fired on connect, hitting lines 56-60
        ds.dispose()

    def test_set_utc_sqlite_failure(self) -> None:
        """SQLite path also fails -> line 61-63 (silent pass)"""
        ds, set_utc = self._make_ds_and_capture_set_utc()
        self.assertIsNotNone(set_utc)

        conn = MagicMock()
        # First call: context manager raises TypeError
        cm = MagicMock()
        cm.__enter__ = MagicMock(side_effect=TypeError("no context manager"))
        cm.__exit__ = MagicMock(return_value=False)
        # Second call: direct cursor raises OSError
        conn.cursor.side_effect = [cm, OSError("connection failed")]

        set_utc(conn, None)
        # Should not raise
        ds.dispose()


class TestDataSourceSession(unittest.TestCase):
    """_DataSource.session: autoflush (77), isolation_level (79), rollback (83-85)"""

    def _make_ds(self) -> _DataSource:
        url = URL.create("sqlite", database=":memory:")
        return _DataSource(url)

    def test_session_autoflush(self) -> None:
        """autoflush parameter -> line 77"""
        ds = self._make_ds()
        with ds.session(autoflush=True) as sess:
            self.assertTrue(sess.autoflush)
        ds.dispose()

    def test_session_isolation_level(self) -> None:
        """isolation_level parameter -> line 79"""
        ds = self._make_ds()
        with ds.session(isolation_level="SERIALIZABLE") as sess:
            # If we got here without error, isolation_level was set (line 79 executed)
            pass
        ds.dispose()

    def test_session_rollback_on_exception(self) -> None:
        """Exception in session -> rollback -> line 83-85"""
        ds = self._make_ds()
        with self.assertRaises(ValueError):
            with ds.session() as sess:
                raise ValueError("test error")
        ds.dispose()


class TestDBEnvUrl(unittest.TestCase):
    """DB._env_url: without db_config -> line 109"""

    @patch("bin.db.Env.get")
    def test_env_url_without_config(self, mock_env_get) -> None:
        mock_env_get.side_effect = lambda key: {"MYSQL_USER": "user", "MYSQL_PASSWORD": "pass", "FM_DB_HOST": "localhost", "FM_DB_PORT": "3306", "MYSQL_DATABASE": "testdb"}[key]

        url = DB._env_url(None)
        self.assertIn("mysql", str(url))
        self.assertIn("testdb", str(url))


class TestDBMakeKey(unittest.TestCase):
    """DB._make_key: unhashable opts -> line 124-125"""

    def test_unhashable_opts(self) -> None:
        url = URL.create("sqlite", database=":memory:")
        opts = {"nested": {"key": "value"}}
        key = DB._make_key(url, opts)
        self.assertIsInstance(key, str)
        self.assertIn("|", key)


class TestDBSource(unittest.TestCase):
    """DB._source: cache hit (132-133), new creation (136-138)"""

    def setUp(self) -> None:
        self._original_sources = DB._sources.copy()

    def tearDown(self) -> None:
        for key, ds in DB._sources.items():
            if key not in self._original_sources:
                ds.dispose()
        DB._sources = self._original_sources

    def test_cache_hit_fast_path(self) -> None:
        """Cache hit -> line 132-133"""
        url = URL.create("sqlite", database=":memory:")
        ds1 = DB._source(url)
        ds2 = DB._source(url)
        self.assertIs(ds1, ds2)

    def test_new_creation(self) -> None:
        """New source creation -> line 136-138"""
        url = URL.create("sqlite", database=":memory:")
        DB._sources.clear()
        ds = DB._source(url)
        self.assertIsInstance(ds, _DataSource)
        ds.dispose()


if __name__ == "__main__":
    unittest.main()
