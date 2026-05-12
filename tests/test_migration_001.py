#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Migration 001 — facebook_access_token 컬럼 제거 마이그레이션 테스트."""

import importlib.util
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

MIGRATION_PATH = Path(__file__).parent.parent / "bin" / "migrations" / "001_remove_facebook_access_token.py"

_OLD_SCHEMA = """
CREATE TABLE user_session (
    session_id       VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_email       VARCHAR(256) NOT NULL,
    user_name        VARCHAR(256) NOT NULL,
    facebook_access_token VARCHAR(512),
    profile_picture_url   VARCHAR(512),
    created_at       DATETIME,
    expires_at       DATETIME    NOT NULL,
    last_accessed_at DATETIME
)
"""

_NEW_SCHEMA = """
CREATE TABLE user_session (
    session_id          VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_email          VARCHAR(256) NOT NULL,
    user_name           VARCHAR(256) NOT NULL,
    profile_picture_url VARCHAR(512),
    created_at          DATETIME,
    expires_at          DATETIME NOT NULL,
    last_accessed_at    DATETIME
)
"""


def _load_migration():
    spec = importlib.util.spec_from_file_location("mig001", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_session_ctx(engine):
    """DB.session_ctx の代替 — SQLite engine を使った contextmanager を返す."""
    Session = sessionmaker(bind=engine, autoflush=False)

    @contextmanager
    def _ctx(**kwargs):
        sess = Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    return _ctx


def _column_names(engine, table):
    inspector = inspect(engine)
    return {col["name"] for col in inspector.get_columns(table)}


class TestMigration001:
    def test_drops_column_when_present(self):
        """facebook_access_token 컬럼이 존재하면 삭제한다."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text(_OLD_SCHEMA))
            conn.commit()

        assert "facebook_access_token" in _column_names(engine, "user_session")

        mod = _load_migration()
        with patch.object(mod, "DB") as mock_db:
            mock_db.session_ctx = _make_session_ctx(engine)
            mod.run()

        assert "facebook_access_token" not in _column_names(engine, "user_session")

    def test_idempotent_when_column_absent(self):
        """컬럼이 이미 없으면 오류 없이 스킵한다."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text(_NEW_SCHEMA))
            conn.commit()

        assert "facebook_access_token" not in _column_names(engine, "user_session")

        mod = _load_migration()
        with patch.object(mod, "DB") as mock_db:
            mock_db.session_ctx = _make_session_ctx(engine)
            mod.run()  # must not raise

        assert "facebook_access_token" not in _column_names(engine, "user_session")

    def test_other_columns_preserved(self):
        """마이그레이션 후 나머지 컬럼이 그대로 남아 있어야 한다."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text(_OLD_SCHEMA))
            conn.commit()

        mod = _load_migration()
        with patch.object(mod, "DB") as mock_db:
            mock_db.session_ctx = _make_session_ctx(engine)
            mod.run()

        remaining = _column_names(engine, "user_session")
        expected = {"session_id", "user_email", "user_name", "profile_picture_url", "created_at", "expires_at", "last_accessed_at"}
        assert expected.issubset(remaining), f"Missing columns after migration: {expected - remaining}"

    def test_double_run_is_safe(self):
        """두 번 실행해도 오류가 없어야 한다 (멱등성)."""
        engine = create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            conn.execute(text(_OLD_SCHEMA))
            conn.commit()

        mod = _load_migration()
        with patch.object(mod, "DB") as mock_db:
            mock_db.session_ctx = _make_session_ctx(engine)
            mod.run()
            mod.run()  # second run — must not raise
