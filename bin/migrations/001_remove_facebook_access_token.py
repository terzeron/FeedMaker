#!/usr/bin/env python
"""Migration 001: remove facebook_access_token column from user_session table.

Run once on existing databases after deploying the code that removes this column
from the UserSession model. Idempotent — safe to re-run.

Usage:
    uv run python -m bin.migrations.001_remove_facebook_access_token
"""

import logging
from sqlalchemy import inspect, text

from bin.db import DB

LOGGER = logging.getLogger(__name__)

TABLE = "user_session"
COLUMN = "facebook_access_token"


def run() -> None:
    with DB.session_ctx() as session:
        conn = session.connection()
        inspector = inspect(conn)
        columns = {col["name"] for col in inspector.get_columns(TABLE)}
        if COLUMN not in columns:
            LOGGER.info("Migration 001: column '%s.%s' does not exist — skipping", TABLE, COLUMN)
            return
        session.execute(text(f"ALTER TABLE {TABLE} DROP COLUMN {COLUMN}"))
        LOGGER.info("Migration 001: dropped column '%s.%s'", TABLE, COLUMN)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
