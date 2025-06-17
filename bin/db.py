#!/usr/bin/env python


from __future__ import annotations
from threading import RLock
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import URL

from bin.feed_maker_util import Env


class _DataSource:
    def __init__(self, url: str, **engine_opts):
        self._backend = create_engine(url, pool_pre_ping=True, future=True, **engine_opts)

        # 접속 시 UTC 고정 같은 공통 세팅
        @event.listens_for(self._backend, "connect")
        def _set_utc(dbapi_conn, _):
            with dbapi_conn.cursor() as cur:
                cur.execute("SET time_zone = '+00:00'")

        self._Session = sessionmaker(bind=self._backend, autoflush=False, expire_on_commit=False, future=True)

    @contextmanager
    def session(self) -> Iterator[Session]:
        sess: Session = self._Session()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()


class DataSourceRegistry:
    _cache: dict[str, _DataSource] = {}
    _lock = RLock()

    @staticmethod
    def _url_from_env() -> str:
        return str(
            URL.create(
                "mysql+pymysql",
                username=Env.get("MYSQL_USER"),
                password=Env.get("MYSQL_PASSWORD"),
                host=Env.get("FM_DB_HOST"),
                port=int(Env.get("FM_DB_PORT")),
                database=Env.get("MYSQL_DATABASE"),
                query={"charset": "utf8mb4"},
            )
        )

    @classmethod
    def _get_source(cls, url: str, **opts) -> _DataSource:
        key = f"{url}|{hash(frozenset(opts.items()))}"
        if key in cls._cache:  # fast-path
            return cls._cache[key]

        with cls._lock:  # slow-path
            if key not in cls._cache:  # double-check
                cls._cache[key] = _DataSource(url, **opts)
            return cls._cache[key]

    @classmethod
    @contextmanager
    def session_ctx(cls, url: str | None = None, **engine_opts, ) -> Iterator[Session]:
        ds = cls._get_source(url or cls._url_from_env(), **engine_opts)
        with ds.session() as sess:
            yield sess
