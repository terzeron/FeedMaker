#!/usr/bin/env python


import json
import logging.config
from pathlib import Path
from contextlib import contextmanager
from threading import RLock
from typing import Iterator, Any, Optional, Literal, TypedDict, Union
from collections.abc import Hashable
from sqlalchemy import create_engine, event, func as _func, and_ as _and_, or_ as _or_, not_ as _not_
from sqlalchemy.engine import Engine, URL, Connection
from sqlalchemy.orm import Session as _Session, sessionmaker as _sessionmaker

from bin.feed_maker_util import Env
from bin.models import Base


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger(__name__)

func = _func
and_ = _and_
or_ = _or_
not_ = _not_

class Session(_Session):
    __slots__ = ()


class EngineOptions(TypedDict, total=False):
    pool_pre_ping: bool
    future: bool
    echo: bool
    isolation_level: Literal['SERIALIZABLE', 'REPEATABLE READ', 'READ COMMITTED', 'READ UNCOMMITTED', 'AUTOCOMMIT']


class _DataSource:
    def __init__(self, url: URL, **engine_opts: Any) -> None:
        self._engine: Engine = create_engine(
            url,
            pool_pre_ping=True,
            future=True,
            echo=False,
            **engine_opts,
        )

        # 커넥션마다 UTC 고정
        @event.listens_for(self._engine, "connect")
        def _set_utc(conn: Any, _: Any) -> None:  # type: ignore
            try:
                # MySQL의 경우 context manager 지원
                with conn.cursor() as cur:
                    cur.execute("SET time_zone = '+00:00'")
            except (TypeError, AttributeError):
                # SQLite의 경우 context manager 미지원
                try:
                    cur = conn.cursor()
                    cur.execute("PRAGMA timezone = '+00:00'")
                    cur.close()
                except RuntimeError:
                    # SQLite에서 timezone 설정이 실패해도 무시
                    pass

        self._Session: Any = _sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

    # 컨텍스트 매니저: 자동 commit / rollback
    @contextmanager
    def session(self, *, autoflush: Optional[bool] = None, isolation_level: Optional[Literal['SERIALIZABLE', 'REPEATABLE READ', 'READ COMMITTED', 'READ UNCOMMITTED', 'AUTOCOMMIT']] = None) -> Iterator[Session]:
        sess: Session = self._Session()
        if autoflush is not None:  # 필요 시 동적으로 변경
            sess.autoflush = autoflush
        if isolation_level:  # 필요 시 동적으로 변경
            sess.connection(execution_options={"isolation_level": isolation_level})
        try:
            yield sess
            sess.commit()
        except RuntimeError:
            sess.rollback()
            raise
        finally:
            sess.close()

    def dispose(self) -> None:
        self._engine.dispose()

    @property
    def engine(self) -> Union[Engine, Connection]:
        return self._engine


class DB:
    _sources: dict[str, _DataSource] = {}
    _lock = RLock()
    _db_config: dict[str, Any] = {}

    @classmethod
    def init(cls, db_config: Optional[dict[str, Any]] = None) -> None:
        cls._db_config = db_config or {}

    @staticmethod
    def _env_url(db_config: Optional[dict[str, Any]]) -> URL:
        if not db_config:
            db_config = {}
        return URL.create(
            drivername="mysql+pymysql",
            username=db_config.get("user", Env.get("MYSQL_USER")),
            password=db_config.get("password", Env.get("MYSQL_PASSWORD")),
            host=db_config.get("host", Env.get("FM_DB_HOST")),
            port=int(db_config.get("port", Env.get("FM_DB_PORT"))),
            database=db_config.get("database", Env.get("MYSQL_DATABASE")),
            query={"charset": "utf8mb4"}
        )

    @staticmethod
    def _make_key(url: URL, opts: dict[str, Any]) -> str:
        try:
            opts_key: Hashable = frozenset(opts.items())
        except TypeError:
            opts_key = json.dumps(opts, sort_keys=True)
        return f"{url}|{hash(opts_key)}"

    @classmethod
    def _source(cls, url: URL, **engine_opts: Any) -> _DataSource:
        key = cls._make_key(url, engine_opts)

        if key in cls._sources:  # fast-path
            return cls._sources[key]

        with cls._lock:  # slow-path (최초 생성)
            if key not in cls._sources:  # double-check
                cls._sources[key] = _DataSource(url, **engine_opts)
            return cls._sources[key]

    @classmethod
    @contextmanager
    def session_ctx(cls, *, db_config: Optional[dict[str, Any]] = None, autoflush: Optional[bool] = None, isolation_level: Optional[Literal['SERIALIZABLE', 'REPEATABLE READ', 'READ COMMITTED', 'READ UNCOMMITTED', 'AUTOCOMMIT']] = None, **engine_opts: EngineOptions) -> Iterator[Session]:
        actual_config: dict[str, Any] = db_config or cls._db_config
        ds = cls._source(cls._env_url(actual_config), **engine_opts)
        with ds.session(autoflush=autoflush, isolation_level=isolation_level) as sess:
            yield sess

    @classmethod
    def create_all_tables(cls, db_config: Optional[dict[str, Any]] = None, **engine_opts: Any) -> None:
        LOGGER.debug("# create_all_tables()")
        actual_config: dict[str, Any] = db_config or cls._db_config
        ds = cls._source(cls._env_url(actual_config), **engine_opts)
        Base.metadata.create_all(ds.engine, checkfirst=True)

    @classmethod
    def drop_all_tables(cls, db_config: Optional[dict[str, Any]] = None, **engine_opts: Any) -> None:
        LOGGER.debug("# drop_all_tables()")
        actual_config: dict[str, Any] = db_config or cls._db_config
        ds = cls._source(cls._env_url(actual_config), **engine_opts)
        Base.metadata.drop_all(ds.engine, checkfirst=True)

    @classmethod
    def dispose_all(cls) -> None:
        LOGGER.debug("# dispose_all()")
        with cls._lock:
            for ds in cls._sources.values():
                ds.dispose()
            cls._sources.clear()
