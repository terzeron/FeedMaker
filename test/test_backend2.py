#!/usr/bin/env python

# mypy: disable-error-code="import"

from pathlib import Path
import requests
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for


APP_PORT = 8010
SRC_DIR  = Path(__file__).parent.parent


def _ready(url: str) -> bool:
    try:
        return requests.get(url + "/groups", timeout=1).status_code == 200
    except requests.RequestException:
        return False


class FastAPILocalCodeContainer(DockerContainer):
    def __init__(self) -> None:
        super().__init__("tiangolo/uvicorn-gunicorn-fastapi:python3.11-slim")
        self.with_exposed_ports(APP_PORT)
        self.with_volume_mapping(str(SRC_DIR), "/app", mode="ro")
        self.with_command(
            "pip install -e /app && "
            f"uvicorn app.backend.main --host 0.0.0.0 --port {APP_PORT}"
        )


def test_users_endpoint() -> None:
    with FastAPILocalCodeContainer() as api:
        host = api.get_container_host_ip()
        port = api.get_exposed_port(APP_PORT)
        base = f"http://{host}:{port}"

        wait_for(lambda: _ready(base))

        resp = requests.get(f"{base}/groups", timeout=10)
        assert resp.status_code == 200
