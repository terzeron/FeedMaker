#!/usr/bin/env python

# mypy: disable-error-code="import"

import os
import logging
import logging.config
from pathlib import Path
from typing import Dict, Any
from contextlib import contextmanager
import threading

# Disable Ryuk for Colima/Docker Desktop compatibility
# Ryuk is a resource reaper that cleans up containers, but it has issues
# with Docker socket mounting in some environments
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

from testcontainers.mysql import MySqlContainer
from testcontainers.core.container import DockerContainer


# Configure logging for tests
logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class CommonTestUtil:
    """Common test utilities for feed maker tests"""

    @staticmethod
    def get_test_config() -> Dict[str, Any]:
        """Get test configuration"""
        return {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }

    @staticmethod
    def get_test_loki_url() -> str:
        """Get test Loki URL"""
        return "http://localhost:3100"


@contextmanager
def start_loki_container():
    """Start Loki container for testing

    Usage:
        with start_loki_container() as loki:
            loki_url = loki.get_url()
            # Test code...
    """
    LOGGER.info("Starting Loki container...")
    loki = DockerContainer("grafana/loki:3.0.0")
    loki.with_exposed_ports(3100)
    loki.with_command(["-config.file=/etc/loki/local-config.yaml"])

    try:
        loki.start()
        LOGGER.info(f"Loki container started at port {loki.get_exposed_port(3100)}")

        # Add helper method to get URL
        def get_url():
            return f"http://localhost:{loki.get_exposed_port(3100)}"

        loki.get_url = get_url
        yield loki
    finally:
        LOGGER.info("Stopping Loki container...")
        loki.stop()


@contextmanager
def start_mysql_container():
    """Start MySQL container for testing

    Usage:
        with start_mysql_container() as mysql:
            mysql_url = mysql.get_connection_url()
            # Test code...
    """
    LOGGER.info("Starting MySQL container...")
    mysql = MySqlContainer(
        image="mysql:8.0",
        username="test",
        password="test",
        dbname="test"
    )

    try:
        mysql.start()
        LOGGER.info(f"MySQL container started at port {mysql.get_exposed_port(3306)}")
        yield mysql
    finally:
        LOGGER.info("Stopping MySQL container...")
        mysql.stop()


@contextmanager
def start_containers_parallel():
    """Start Loki and MySQL containers in parallel for better performance

    Usage:
        with start_containers_parallel() as (loki, mysql):
            loki_url = loki.get_url()
            mysql_url = mysql.get_connection_url()
            # Test code...
    """
    LOGGER.info("Starting containers in parallel...")

    # Initialize containers
    loki = DockerContainer("grafana/loki:3.0.0")
    loki.with_exposed_ports(3100)
    loki.with_command(["-config.file=/etc/loki/local-config.yaml"])

    mysql = MySqlContainer(
        image="mysql:8.0",
        username="test",
        password="test",
        dbname="test"
    )

    # Start containers in parallel
    errors = []

    def start_loki():
        try:
            loki.start()
            LOGGER.info(f"Loki container started at port {loki.get_exposed_port(3100)}")
        except Exception as e:
            errors.append(("loki", e))

    def start_mysql():
        try:
            mysql.start()
            LOGGER.info(f"MySQL container started at port {mysql.get_exposed_port(3306)}")
        except Exception as e:
            errors.append(("mysql", e))

    threads = [
        threading.Thread(target=start_loki),
        threading.Thread(target=start_mysql)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    if errors:
        # Cleanup any started containers
        try:
            loki.stop()
        except:
            pass
        try:
            mysql.stop()
        except:
            pass
        raise Exception(f"Failed to start containers: {errors}")

    # Add helper method to get Loki URL
    def get_url():
        return f"http://localhost:{loki.get_exposed_port(3100)}"

    loki.get_url = get_url

    try:
        yield loki, mysql
    finally:
        LOGGER.info("Stopping containers...")

        # Stop containers in parallel
        def stop_loki():
            try:
                loki.stop()
            except Exception as e:
                LOGGER.error(f"Error stopping Loki: {e}")

        def stop_mysql():
            try:
                mysql.stop()
            except Exception as e:
                LOGGER.error(f"Error stopping MySQL: {e}")

        threads = [
            threading.Thread(target=stop_loki),
            threading.Thread(target=stop_mysql)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()
