#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""charset utf8mb3 -> utf8mb4 마이그레이션 테스트.

migrate()의 SQL은 MySQL 전용(SELECT DATABASE(), information_schema,
ALTER ... CONVERT TO CHARACTER SET)이라 SQLite로 실행할 수 없다.
따라서 DB.session_ctx를 fake session으로 대체해 분기(변환/스킵)와
실제로 발행된 SQL을 검증한다.
"""

from contextlib import contextmanager
from unittest.mock import patch

from bin import migrate_charset_utf8mb4 as mig
from bin.models import Base

DB_NAME = "feedmaker_test"
ALL_TABLES = list(Base.metadata.tables.keys())


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeSession:
    """migrate()가 호출하는 execute()를 SQL 종류별로 흉내 낸다."""

    def __init__(self, db_name, charset_by_table):
        self.db_name = db_name
        self.charset_by_table = charset_by_table
        self.executed = []  # (sql, params) 누적

    def execute(self, clause, params=None):
        sql = str(clause)
        self.executed.append((sql, params))
        if "SELECT DATABASE()" in sql:
            return _FakeResult(self.db_name)
        if "character_set_name" in sql:
            return _FakeResult(self.charset_by_table.get(params["t"]))
        # ALTER DATABASE / ALTER TABLE — 반환값 미사용
        return _FakeResult(None)

    # 발행된 ALTER TABLE 대상 테이블 추출 헬퍼
    def altered_tables(self):
        result = []
        for sql, _ in self.executed:
            if sql.startswith("ALTER TABLE"):
                # ALTER TABLE `name` CONVERT ...
                result.append(sql.split("`")[1])
        return result

    def has_alter_database(self):
        return any(sql.startswith("ALTER DATABASE") for sql, _ in self.executed)


def _patched_db(session):
    @contextmanager
    def _ctx(**kwargs):
        yield session

    return patch.object(mig.DB, "session_ctx", _ctx)


class TestMigrateCharset:
    def test_converts_all_non_utf8mb4_tables(self):
        """모든 테이블이 utf8mb3이면 전부 변환하고 변환 수를 반환한다."""
        session = _FakeSession(DB_NAME, {t: "utf8mb3" for t in ALL_TABLES})
        with _patched_db(session):
            converted = mig.migrate()

        assert converted == len(ALL_TABLES)
        assert set(session.altered_tables()) == set(ALL_TABLES)
        assert session.has_alter_database()

    def test_skips_tables_already_utf8mb4(self):
        """이미 utf8mb4인 테이블은 건너뛴다 (멱등성)."""
        session = _FakeSession(DB_NAME, {t: "utf8mb4" for t in ALL_TABLES})
        with _patched_db(session):
            converted = mig.migrate()

        assert converted == 0
        assert session.altered_tables() == []
        # ALTER DATABASE 기본값 변경은 멱등하게 항상 수행된다.
        assert session.has_alter_database()

    def test_skips_table_not_present_in_db(self):
        """DB에 없는 테이블(charset None)은 스킵한다."""
        session = _FakeSession(DB_NAME, {t: None for t in ALL_TABLES})
        with _patched_db(session):
            converted = mig.migrate()

        assert converted == 0
        assert session.altered_tables() == []

    def test_mixed_states_converts_only_legacy(self):
        """utf8mb3 / utf8mb4 / 없음이 섞이면 utf8mb3만 변환한다."""
        legacy = ALL_TABLES[:2]
        already = ALL_TABLES[2:4]
        missing = ALL_TABLES[4:]
        charset_map = {}
        charset_map.update({t: "utf8mb3" for t in legacy})
        charset_map.update({t: "utf8mb4" for t in already})
        charset_map.update({t: None for t in missing})

        session = _FakeSession(DB_NAME, charset_map)
        with _patched_db(session):
            converted = mig.migrate()

        assert converted == len(legacy)
        assert set(session.altered_tables()) == set(legacy)

    def test_alter_database_targets_current_db(self):
        """ALTER DATABASE는 SELECT DATABASE()로 얻은 현재 DB명을 대상으로 한다."""
        session = _FakeSession(DB_NAME, {t: "utf8mb4" for t in ALL_TABLES})
        with _patched_db(session):
            mig.migrate()

        alter_db_sql = next(sql for sql, _ in session.executed if sql.startswith("ALTER DATABASE"))
        assert f"`{DB_NAME}`" in alter_db_sql
        assert mig.TARGET_CHARSET in alter_db_sql
        assert mig.TARGET_COLLATE in alter_db_sql

    def test_only_model_tables_are_queried(self):
        """모델에 정의된 테이블만 charset 조회 대상이다."""
        session = _FakeSession(DB_NAME, {t: "utf8mb4" for t in ALL_TABLES})
        with _patched_db(session):
            mig.migrate()

        queried = [params["t"] for sql, params in session.executed if "character_set_name" in sql]
        assert set(queried) == set(ALL_TABLES)
