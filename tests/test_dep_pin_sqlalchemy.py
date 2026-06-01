#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `sqlalchemy`.

Purpose
-------
Pin the SQLAlchemy surface that FeedMaker production code actually uses,
independent of the SQLAlchemy minor version. If a future upgrade changes
any of the constructor kwargs, classmethods, declarative API, type
descriptors, inspector shape, or event decorator semantics, these tests
will fail at CI time -- *before* the change reaches runtime.

Reference call sites (production code):
    bin/db.py                                  -- engine + session + URL + events
    bin/models.py                              -- declarative models + column types
    bin/migrations/001_remove_facebook_access_token.py -- inspect + text

Test substrate: SQLite in-memory. The SQLAlchemy *interface* contract is
identical to mysql+pymysql for everything FeedMaker uses; only the dialect
differs. Using sqlite removes the external DB dependency from CI.
"""

import unittest
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text, and_, create_engine, event, func, inspect, not_, or_, text
from sqlalchemy.engine import Connection, Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, declarative_base, mapped_column, sessionmaker


# -----------------------------------------------------------------------------
# 1. Top-level symbol surface (every `from sqlalchemy import X` in production)
# -----------------------------------------------------------------------------


class SQLAlchemyImportSurfaceTest(unittest.TestCase):
    """Every symbol production imports must remain importable as a name."""

    def test_core_type_descriptors_are_classes(self) -> None:
        # models.py imports these as column type descriptors.
        for cls in (String, Integer, Float, Boolean, DateTime, Text):
            self.assertTrue(callable(cls), f"{cls!r} must be callable")

    def test_index_is_constructible(self) -> None:
        # models.py: Index("feed_info_access_date_idx", "access_date")
        idx = Index("test_idx", "col_a", "col_b")
        self.assertEqual(idx.name, "test_idx")

    def test_text_returns_a_clause_element(self) -> None:
        # models.py: text("CURRENT_TIMESTAMP")  -- used as server_default
        # migrations: session.execute(text("ALTER TABLE ..."))
        expr = text("SELECT 1")
        # Must compile to SQL without raising.
        self.assertEqual(str(expr.compile(compile_kwargs={"literal_binds": True})), "SELECT 1")

    def test_sql_helpers_are_exposed_as_callables(self) -> None:
        # db.py: from sqlalchemy import func as _func, and_ as _and_, or_ as _or_, not_ as _not_
        self.assertTrue(callable(func.count))
        self.assertTrue(callable(and_))
        self.assertTrue(callable(or_))
        self.assertTrue(callable(not_))

    def test_engine_types_are_importable(self) -> None:
        # db.py: from sqlalchemy.engine import Engine, URL, Connection
        for cls in (Engine, URL, Connection):
            self.assertTrue(isinstance(cls, type), f"{cls!r} must be a class")

    def test_orm_symbols_are_importable(self) -> None:
        # db.py + models.py
        self.assertTrue(callable(sessionmaker))
        self.assertTrue(isinstance(Session, type))
        self.assertTrue(isinstance(DeclarativeBase, type))
        self.assertTrue(callable(declarative_base))
        self.assertTrue(callable(mapped_column))
        # Mapped is a typing construct -- just confirm it's subscriptable.
        _ = Mapped[int]


# -----------------------------------------------------------------------------
# 2. create_engine kwargs that db.py passes
# -----------------------------------------------------------------------------


class CreateEngineCallShapeTest(unittest.TestCase):
    """Pin create_engine(...) kwargs used in db.py:40-46."""

    def test_create_engine_accepts_pool_pre_ping_future_echo(self) -> None:
        # db.py passes pool_pre_ping=True, future=True, echo=False.
        engine = create_engine("sqlite:///:memory:", pool_pre_ping=True, future=True, echo=False)
        self.assertIsInstance(engine, Engine)
        engine.dispose()

    def test_engine_has_dispose_method(self) -> None:
        # db.py:90 -- self._engine.dispose()
        engine = create_engine("sqlite:///:memory:")
        self.assertTrue(callable(engine.dispose))
        engine.dispose()


# -----------------------------------------------------------------------------
# 3. URL.create kwargs (db.py:_env_url)
# -----------------------------------------------------------------------------


class URLCreateCallShapeTest(unittest.TestCase):
    """Pin URL.create(...) kwargs used in db.py:107-118."""

    def test_url_create_accepts_seven_keyword_args(self) -> None:
        url = URL.create(drivername="mysql+pymysql", username="user", password="pw", host="db.internal", port=3306, database="feedmaker", query={"charset": "utf8mb4"})
        self.assertEqual(url.drivername, "mysql+pymysql")
        self.assertEqual(url.username, "user")
        self.assertEqual(url.password, "pw")
        self.assertEqual(url.host, "db.internal")
        self.assertEqual(url.port, 3306)
        self.assertEqual(url.database, "feedmaker")
        self.assertEqual(dict(url.query), {"charset": "utf8mb4"})

    def test_url_can_be_passed_to_create_engine(self) -> None:
        # db.py builds a URL via URL.create() and passes it directly to create_engine().
        url = URL.create(drivername="sqlite", database=":memory:")
        engine = create_engine(url)
        self.assertIsInstance(engine, Engine)
        engine.dispose()


# -----------------------------------------------------------------------------
# 4. event.listens_for(engine, "connect")
# -----------------------------------------------------------------------------


class EventListensForCallShapeTest(unittest.TestCase):
    """Pin event.listens_for usage in db.py:49-63."""

    def test_listens_for_connect_event_fires_with_two_args(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        captured: list[tuple] = []

        @event.listens_for(engine, "connect")
        def _on_connect(dbapi_conn, connection_record):  # noqa: ANN001
            captured.append((dbapi_conn, connection_record))

        # Trigger a connect.
        with engine.connect() as _conn:
            pass

        self.assertGreaterEqual(len(captured), 1)
        self.assertEqual(len(captured[0]), 2)  # exactly two args -- matches db.py signature
        engine.dispose()


# -----------------------------------------------------------------------------
# 5. sessionmaker(...) kwargs
# -----------------------------------------------------------------------------


class SessionmakerCallShapeTest(unittest.TestCase):
    """Pin sessionmaker kwargs used in db.py:65-70."""

    def test_sessionmaker_accepts_bind_autoflush_expire_on_commit_future(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
        sess = SessionLocal()
        self.assertIsInstance(sess, Session)
        # autoflush / expire_on_commit propagate to the session
        self.assertFalse(sess.autoflush)
        self.assertFalse(sess.expire_on_commit)
        sess.close()
        engine.dispose()


# -----------------------------------------------------------------------------
# 6. Session lifecycle: autoflush attr, connection(execution_options=), commit/rollback/close
# -----------------------------------------------------------------------------


class SessionLifecycleCallShapeTest(unittest.TestCase):
    """Pin Session-instance API used in db.py:74-87."""

    def _new_session(self) -> tuple[Engine, Session]:
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
        return engine, SessionLocal()

    def test_session_autoflush_is_writable_attribute(self) -> None:
        # db.py:77 -- sess.autoflush = autoflush
        engine, sess = self._new_session()
        sess.autoflush = True
        self.assertTrue(sess.autoflush)
        sess.autoflush = False
        self.assertFalse(sess.autoflush)
        sess.close()
        engine.dispose()

    def test_session_connection_accepts_execution_options_kwarg(self) -> None:
        # db.py:79 -- sess.connection(execution_options={"isolation_level": ...})
        engine, sess = self._new_session()
        conn = sess.connection(execution_options={"isolation_level": "SERIALIZABLE"})
        self.assertIsInstance(conn, Connection)
        sess.close()
        engine.dispose()

    def test_session_has_commit_rollback_close(self) -> None:
        # db.py:82-87
        engine, sess = self._new_session()
        for name in ("commit", "rollback", "close"):
            self.assertTrue(callable(getattr(sess, name)), f"Session.{name} missing")
        sess.close()
        engine.dispose()

    def test_session_is_subclassable_with_slots(self) -> None:
        # db.py:27-28 declares  class Session(_Session): __slots__ = ()
        class MySession(Session):
            __slots__ = ()

        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine, class_=MySession)
        sess = SessionLocal()
        self.assertIsInstance(sess, MySession)
        sess.close()
        engine.dispose()


# -----------------------------------------------------------------------------
# 7. Declarative model definition + Base.metadata API
# -----------------------------------------------------------------------------


class DeclarativeBaseLearningBase(DeclarativeBase):
    pass


class _Sample(DeclarativeBaseLearningBase):
    __tablename__ = "lt_sample"
    name: Mapped[str] = mapped_column(String(256), primary_key=True)
    age: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("lt_sample_age_idx", "age"),)


class DeclarativeModelCallShapeTest(unittest.TestCase):
    """Pin the declarative-model surface used in models.py."""

    def test_declarative_base_is_subclassable(self) -> None:
        # models.py uses DeclarativeBase as the canonical 2.x base class.
        self.assertTrue(isinstance(DeclarativeBaseLearningBase, type))
        self.assertTrue(issubclass(_Sample, DeclarativeBaseLearningBase))

    def test_legacy_declarative_base_still_callable(self) -> None:
        # models.py:11-13 falls back to declarative_base() under TYPE_CHECKING=False.
        LegacyBase = declarative_base()
        self.assertTrue(isinstance(LegacyBase, type))

    def test_mapped_column_supports_production_kwargs(self) -> None:
        # Combined kwargs used across models.py:
        #   primary_key=True, default=..., nullable=True/False,
        #   server_default=text("..."), DateTime(timezone=True)
        col = _Sample.__table__.c
        self.assertTrue(col.name.primary_key)
        self.assertTrue(col.updated_at.nullable)
        self.assertFalse(col.created_at.nullable)
        # server_default is set
        self.assertIsNotNone(col.created_at.server_default)
        # DateTime(timezone=True)
        self.assertTrue(isinstance(col.created_at.type, DateTime))
        self.assertTrue(col.created_at.type.timezone)

    def test_index_is_attached_via_table_args(self) -> None:
        # models.py:57 -- __table_args__ = (Index(...),)
        idx_names = {idx.name for idx in _Sample.__table__.indexes}
        self.assertIn("lt_sample_age_idx", idx_names)

    def test_base_metadata_create_all_and_drop_all_accept_checkfirst(self) -> None:
        # db.py:153  -- Base.metadata.create_all(ds.engine, checkfirst=True)
        # db.py:160  -- Base.metadata.drop_all(ds.engine, checkfirst=True)
        engine = create_engine("sqlite:///:memory:")
        DeclarativeBaseLearningBase.metadata.create_all(engine, checkfirst=True)
        DeclarativeBaseLearningBase.metadata.create_all(engine, checkfirst=True)  # idempotent re-call
        DeclarativeBaseLearningBase.metadata.drop_all(engine, checkfirst=True)
        DeclarativeBaseLearningBase.metadata.drop_all(engine, checkfirst=True)  # idempotent re-call
        engine.dispose()


# -----------------------------------------------------------------------------
# 8. inspect(conn).get_columns(table) -- used in migration 001
# -----------------------------------------------------------------------------


class InspectorCallShapeTest(unittest.TestCase):
    """Pin inspect(conn).get_columns(table) surface used in migrations/001."""

    def test_inspect_then_get_columns_returns_list_of_name_dicts(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        DeclarativeBaseLearningBase.metadata.create_all(engine, checkfirst=True)
        with engine.connect() as conn:
            inspector = inspect(conn)
            cols = inspector.get_columns("lt_sample")
        DeclarativeBaseLearningBase.metadata.drop_all(engine, checkfirst=True)
        engine.dispose()

        self.assertIsInstance(cols, list)
        self.assertGreater(len(cols), 0)
        # Migration uses col["name"]. That key must exist.
        names = {col["name"] for col in cols}
        self.assertIn("name", names)
        self.assertIn("age", names)


# -----------------------------------------------------------------------------
# 9. session.execute(text("..."))  -- migration runs raw DDL through here
# -----------------------------------------------------------------------------


class SessionExecuteCallShapeTest(unittest.TestCase):
    """Pin session.execute(text(...)) and session.connection() shape."""

    def test_session_execute_with_text_runs_raw_sql(self) -> None:
        # migrations/001 line 30 -- session.execute(text(f"ALTER TABLE ..."))
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine, future=True)
        with SessionLocal() as sess:
            sess.execute(text("CREATE TABLE lt_x (id INTEGER PRIMARY KEY)"))
            sess.execute(text("INSERT INTO lt_x (id) VALUES (1)"))
            row = sess.execute(text("SELECT id FROM lt_x")).first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row[0], 1)
            sess.commit()
        engine.dispose()

    def test_session_connection_returns_a_connection(self) -> None:
        # migrations/001 line 24 -- conn = session.connection()
        engine = create_engine("sqlite:///:memory:")
        SessionLocal = sessionmaker(bind=engine, future=True)
        with SessionLocal() as sess:
            conn = sess.connection()
            self.assertIsInstance(conn, Connection)
        engine.dispose()


# -----------------------------------------------------------------------------
# 10. Production-alignment smoke: the full db.py pattern works end-to-end
# -----------------------------------------------------------------------------


class ProductionAlignmentTest(unittest.TestCase):
    """End-to-end: replicate db.py's pattern against sqlite and confirm it runs."""

    def test_engine_sessionmaker_create_all_session_execute_pattern(self) -> None:
        engine = create_engine("sqlite:///:memory:", pool_pre_ping=True, future=True, echo=False)
        SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

        DeclarativeBaseLearningBase.metadata.create_all(engine, checkfirst=True)

        # Mimic db.py:session_ctx's try/commit/rollback/close shape.
        sess = SessionLocal()
        try:
            sess.add(_Sample(name="alice", age=30))
            sess.commit()
            found = sess.execute(text("SELECT name, age FROM lt_sample WHERE name = 'alice'")).first()
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found[0], "alice")
            self.assertEqual(found[1], 30)
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

        DeclarativeBaseLearningBase.metadata.drop_all(engine, checkfirst=True)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
