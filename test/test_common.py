#!/usr/bin/env python

# mypy: disable-error-code="import"

import time
import json
from pathlib import Path
from typing import Any, TypedDict, List, Dict
import requests
from testcontainers.core.container import DockerContainer # mypy: disable-error-code="import"
from testcontainers.mysql import MySqlContainer # mypy: disable-error-code="import"

from bin.feed_maker_util import Env
from bin.db import DB


class StreamEntry(TypedDict):
    stream: Dict[str, Any]
    values: List[List[str]]

class TestCommon:
    @staticmethod
    def _wait_for_loki(port: int) -> None:
        loki_url = f"http://localhost:{port}/ready"
        max_retries = 30
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.get(loki_url, timeout=10)
                if response.status_code == 200:
                    return
            except requests.RequestException:
                pass

            retry_count += 1
            time.sleep(1)

        raise RuntimeError("Loki container did not become ready in time")

    @staticmethod
    def prepare_loki_container() -> DockerContainer:
        loki_container = DockerContainer("grafana/loki:3.4.3")
        loki_container.with_exposed_ports(3100)
        loki_container.start()

        port = loki_container.get_exposed_port(3100)
        TestCommon._wait_for_loki(port)

        # initial data loading from file to loki
        with Path(Env.get("HOME") + "/exported_logs.json").open("r", encoding="utf-8") as infile:
            original = json.load(infile)

        streams: List[Dict[str, Any]] = []
        for result in original.get("streams", {}):
            streams.append({
                "stream": result.get("stream", {}),
                "values": result.get("values", [])
            })
        push_payload: Dict[str, List[Dict[str, Any]]] = {"streams": streams}

        loki_url = TestCommon.get_loki_url(loki_container)
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{loki_url}/push", json=push_payload, headers=headers, timeout=10)
        if response.status_code not in (200, 204):
            raise RuntimeError(f"Failed to push logs to Loki: {response.status_code} - {response.text}")

        return loki_container

    @staticmethod
    def get_loki_url(loki_container: DockerContainer) -> str:
        port = loki_container.get_exposed_port(3100)
        return f"http://localhost:{port}/loki/api/v1"

    @staticmethod
    def dispose_loki_container(loki_container: DockerContainer) -> None:
        if loki_container:
            loki_container.stop()

    @staticmethod
    def prepare_mysql_container() -> MySqlContainer:
        mysql_container = MySqlContainer("mysql:8.0")
        mysql_container.start()
        DB.dispose_all()
        return mysql_container

    @staticmethod
    def get_db_config(mysql_container: MySqlContainer) -> dict[str, Any]:
        return {
            "host": "localhost",
            "port": int(mysql_container.get_exposed_port(3306)),
            "database": mysql_container.dbname,
            "user": mysql_container.username,
            "password": mysql_container.password,
        }

    @staticmethod
    def dispose_mysql_container(mysql_container: MySqlContainer) -> None:
        DB.dispose_all()
        if mysql_container:
            mysql_container.stop()
