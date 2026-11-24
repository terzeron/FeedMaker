#!/usr/bin/env python

"""테스트가 환경 변수 기반 기본 DB(production)에 접속하지 못하게 막는다.

셸에 export된 MYSQL_*/FM_DB_* 값을 pytest가 그대로 물려받으므로, DB를 mock하지
않은 테스트는 production DB에 쓴다. 테스트 데이터는 testcontainers MySQL이나
fake session에서만 다룬다. 이 fixture는 세션 시작 시점의 환경 변수로 production
접속 대상을 정하고, 그 대상에 대한 연결을 차단한 뒤 해당 테스트를 실패시킨다.
코드가 DB 예외를 경고로 삼켜도 놓치지 않도록 접근 기록으로 판정한다.
"""

import os
from typing import Any, Iterator, Optional

import pytest

from bin.db import DB


def _production_target() -> Optional[tuple[str, str, str]]:
    host = os.environ.get("FM_DB_HOST", "")
    port = os.environ.get("FM_DB_PORT", "")
    database = os.environ.get("MYSQL_DATABASE", "")
    if not (host and database):
        return None
    return host, port, database


_PRODUCTION_TARGET = _production_target()


@pytest.fixture(autouse=True)
def _block_production_db(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if _PRODUCTION_TARGET is None:
        yield
        return

    original_source = DB._source.__func__  # type: ignore[attr-defined]
    hits: list[str] = []

    def guarded_source(cls: Any, url: Any, **engine_opts: Any) -> Any:
        target = (str(url.host or ""), str(url.port or ""), str(url.database or ""))
        if target == _PRODUCTION_TARGET:
            hits.append(f"{url.host}:{url.port}/{url.database}")
            raise RuntimeError("production DB access is blocked in tests; use testcontainers or mock DB")
        return original_source(cls, url, **engine_opts)

    monkeypatch.setattr(DB, "_source", classmethod(guarded_source))
    yield
    if hits:
        pytest.fail(f"test tried to access production DB {hits[0]} ({len(hits)} times)")
