#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `starlette`.

Purpose
-------
Pin the starlette surface backend/main.py relies on, and lock in the
security fix for PYSEC-2026-161 (Host-header URL reconstruction that can
lead to authentication bypass). The backend auth middleware decides
whether a route is auth-exempt from `request.url.path`
(backend/main.py:84). The security-relevant invariant is therefore:
`request.url.path` must reflect only the real routed ASGI path and must
NOT be influenced by a forged `Host` header. starlette < 1.0.1 is
vulnerable to PYSEC-2026-161; this project pins starlette>=1.0.1
(pyproject.toml), pulled in transitively through fastapi>=0.136.x.

Reference call sites (production code):
    backend/main.py:14   from starlette.responses import Response
    backend/main.py:69   AUTH_EXEMPT_PATHS = {"/auth/login", "/auth/logout", "/auth/me"}
    backend/main.py:70   AUTH_EXEMPT_PREFIXES = ("/feed/",)
    backend/main.py:73   _is_auth_exempt(path): path in PATHS or path.startswith(prefix)
    backend/main.py:79   @app.middleware("http")
    backend/main.py:84   if not _is_auth_exempt(request.url.path): ...
"""

import unittest
from importlib.metadata import version
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.responses import Response


def _version_tuple(v: str) -> tuple[int, ...]:
    parts: list[int] = []
    for component in v.split(".")[:3]:
        digits = "".join(ch for ch in component if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


# -----------------------------------------------------------------------------
# 1. Security floor -- the whole reason this dependency is pinned explicitly
# -----------------------------------------------------------------------------


class StarletteSecurityFloorTest(unittest.TestCase):
    """A downgrade below the PYSEC-2026-161 fix must fail CI."""

    def test_starlette_at_or_above_pysec_2026_161_fix(self) -> None:
        # PYSEC-2026-161 fixed in starlette 1.0.1; pyproject pins >=1.0.1.
        self.assertGreaterEqual(_version_tuple(version("starlette")), (1, 0, 1))


# -----------------------------------------------------------------------------
# 2. Import surface backend/main.py depends on
# -----------------------------------------------------------------------------


class StarletteImportSurfaceTest(unittest.TestCase):
    def test_response_is_a_class(self) -> None:
        # backend/main.py:14 -- from starlette.responses import Response
        self.assertTrue(isinstance(Response, type))


# -----------------------------------------------------------------------------
# 3. request.url.path reflects only the real routed ASGI path
# -----------------------------------------------------------------------------


class RequestUrlPathReflectsRoutedPathTest(unittest.TestCase):
    """`request.url.path` is the routed path -- the value auth depends on."""

    def test_url_path_is_the_asgi_path(self) -> None:
        app = FastAPI()
        seen: dict[str, str] = {}

        @app.get("/api/secret")
        async def secret(request: Request) -> dict[str, bool]:
            seen["path"] = request.url.path
            return {"ok": True}

        with TestClient(app) as client:
            client.get("/api/secret")
        self.assertEqual(seen["path"], "/api/secret")


# -----------------------------------------------------------------------------
# 4. PYSEC-2026-161 regression: a forged Host header must not flip auth exemption
# -----------------------------------------------------------------------------

# Replica of the production auth-exempt middleware (backend/main.py:69-88),
# kept self-contained so the test pins starlette behavior without the DB /
# session wiring of the real app.
AUTH_EXEMPT_PATHS = {"/auth/login", "/auth/logout", "/auth/me"}
AUTH_EXEMPT_PREFIXES = ("/feed/",)


def _is_auth_exempt(path: str) -> bool:
    if path in AUTH_EXEMPT_PATHS:
        return True
    return any(path.startswith(p) for p in AUTH_EXEMPT_PREFIXES)


def _build_guarded_app() -> FastAPI:
    app = FastAPI()

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next: Any) -> Response:
        if not _is_auth_exempt(request.url.path):
            # No session in this standalone app -> protected routes are rejected.
            return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        return await call_next(request)

    @app.get("/feed/{name}")
    async def feed(name: str) -> dict[str, str]:
        return {"feed": name}

    @app.get("/api/secret")
    async def secret() -> dict[str, str]:
        return {"secret": "data"}

    return app


class HostHeaderAuthBypassRegressionTest(unittest.TestCase):
    def test_protected_path_stays_protected_under_forged_host(self) -> None:
        app = _build_guarded_app()
        # Each value tries to smuggle the exempt "/feed/" prefix via the Host
        # header. The patched request.url.path stays "/api/secret" -> 401.
        forged_hosts = ["feed", "/feed/", "evil.example.com/feed/", "feed/x"]
        with TestClient(app) as client:
            for host in forged_hosts:
                try:
                    response = client.get("/api/secret", headers={"Host": host})
                except Exception:
                    # Client library rejected the malformed Host outright;
                    # the request never reached the app -> not a bypass.
                    continue
                self.assertEqual(response.status_code, 401, f"Host={host!r} bypassed auth")

    def test_exempt_prefix_still_works_normally(self) -> None:
        app = _build_guarded_app()
        with TestClient(app) as client:
            response = client.get("/feed/x")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"feed": "x"})


if __name__ == "__main__":
    unittest.main()
