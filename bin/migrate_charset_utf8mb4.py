#!/usr/bin/env python

"""html_file_info 등 모든 테이블의 charset을 utf8mb3 -> utf8mb4로 변환한다.

기본 charset이 utf8mb3이면 4-byte 문자(이모지 등)에서 'Incorrect string value(1366)'로
INSERT가 실패한다(연결은 utf8mb4). 이 스크립트는 DB 기본값과 모든 테이블을 utf8mb4로 올린다.

멱등(idempotent): 이미 utf8mb4인 테이블은 건너뛰므로 여러 번 실행해도 안전하다.
주의: ALTER는 MySQL에서 auto-commit이라 롤백되지 않는다. utf8mb4는 utf8mb3의 superset이므로
데이터 손실은 없다. 모든 PK/인덱스 컬럼은 <=512자라 utf8mb4(<=2048B)에서도 InnoDB(DYNAMIC,
MySQL 8.0) 인덱스 한계 3072B 이내다.

실행: uv run python -m bin.migrate_charset_utf8mb4
"""

import logging.config
import sys
from pathlib import Path

from sqlalchemy import text

from bin.db import DB
from bin.models import Base

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

TARGET_CHARSET = "utf8mb4"
TARGET_COLLATE = "utf8mb4_general_ci"


def migrate() -> int:
    converted = 0
    with DB.session_ctx() as s:
        db_name = s.execute(text("SELECT DATABASE()")).scalar()

        # DB 기본 charset 변경(이후 명시 charset 없는 CREATE TABLE도 utf8mb4로 생성)
        s.execute(text(f"ALTER DATABASE `{db_name}` CHARACTER SET {TARGET_CHARSET} COLLATE {TARGET_COLLATE}"))
        LOGGER.info("* database '%s' default charset -> %s", db_name, TARGET_CHARSET)

        # 모델에 정의된 테이블만 대상으로 한다.
        for table_name in Base.metadata.tables:
            current = s.execute(text("SELECT ccsa.character_set_name FROM information_schema.TABLES t JOIN information_schema.COLLATION_CHARACTER_SET_APPLICABILITY ccsa   ON ccsa.collation_name = t.TABLE_COLLATION WHERE t.TABLE_SCHEMA = :d AND t.TABLE_NAME = :t"), {"d": db_name, "t": table_name}).scalar()

            if current is None:
                LOGGER.info("- skip '%s' (not found in DB)", table_name)
                continue
            if current == TARGET_CHARSET:
                LOGGER.info("- skip '%s' (already %s)", table_name, TARGET_CHARSET)
                continue

            s.execute(text(f"ALTER TABLE `{table_name}` CONVERT TO CHARACTER SET {TARGET_CHARSET} COLLATE {TARGET_COLLATE}"))
            LOGGER.info("* converted '%s': %s -> %s", table_name, current, TARGET_CHARSET)
            converted += 1

    LOGGER.info("* charset migration done. %d table(s) converted.", converted)
    return converted


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0 if migrate() >= 0 else 1)
