#!/usr/bin/env python

# mypy: disable-error-code="import"

import os
import logging
import logging.config
from pathlib import Path
from typing import Any
from contextlib import contextmanager

# Disable Ryuk for Colima/Docker Desktop compatibility
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

from testcontainers.mysql import MySqlContainer


# Configure logging for tests
logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class CommonTestUtil:
    """Common test utilities for feed maker tests"""

    @staticmethod
    def get_test_config() -> dict[str, Any]:
        """Get test configuration"""
        return {"host": "localhost", "port": 3306, "user": "test", "password": "test", "database": "test"}


@contextmanager
def start_mysql_container():
    """Start MySQL container for testing

    Usage:
        with start_mysql_container() as mysql:
            mysql_url = mysql.get_connection_url()
            # Test code...
    """
    LOGGER.info("Starting MySQL container...")
    mysql = MySqlContainer(image="mysql:8.0", username="test", password="test", dbname="test")

    try:
        mysql.start()
        LOGGER.info(f"MySQL container started at port {mysql.get_exposed_port(3306)}")
        yield mysql
    finally:
        LOGGER.info("Stopping MySQL container...")
        mysql.stop()
