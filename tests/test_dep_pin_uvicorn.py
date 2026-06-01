#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `uvicorn`.

Purpose
-------
Pin the uvicorn surface used by backend/main.py: `uvicorn.run(app, host=, port=)`
and `uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware`. An upgrade
that renames trusted_hosts or moves the middleware module would break the
production entrypoint.

Reference call sites (production code):
    backend/main.py:15   from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
    backend/main.py:20   import uvicorn
    backend/main.py:53   app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_trusted_proxy_ips)
    backend/main.py:594  uvicorn.run(app, host=_host, port=_port)
"""

import inspect
import unittest

import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


# -----------------------------------------------------------------------------
# 1. Import surface
# -----------------------------------------------------------------------------


class UvicornImportSurfaceTest(unittest.TestCase):
    def test_uvicorn_run_is_callable(self) -> None:
        # main.py:594 -- uvicorn.run(app, host=, port=)
        self.assertTrue(callable(uvicorn.run))

    def test_proxy_headers_middleware_is_a_class(self) -> None:
        # main.py:15 -- from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
        self.assertTrue(isinstance(ProxyHeadersMiddleware, type))


# -----------------------------------------------------------------------------
# 2. uvicorn.run signature accepts (app, host=, port=)
# -----------------------------------------------------------------------------


class UvicornRunSignatureTest(unittest.TestCase):
    """Pin the kwargs production passes to uvicorn.run()."""

    def test_run_accepts_app_host_port(self) -> None:
        sig = inspect.signature(uvicorn.run)
        # First positional must be the app; host & port must be keyword-accessible.
        params = sig.parameters
        self.assertIn("host", params)
        self.assertIn("port", params)


# -----------------------------------------------------------------------------
# 3. ProxyHeadersMiddleware accepts trusted_hosts= when added via FastAPI
# -----------------------------------------------------------------------------


class ProxyHeadersMiddlewareCallShapeTest(unittest.TestCase):
    """Pin app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=...) shape."""

    def test_middleware_init_accepts_app_and_trusted_hosts(self) -> None:
        # ASGI middleware init signature must include `trusted_hosts`.
        sig = inspect.signature(ProxyHeadersMiddleware.__init__)
        self.assertIn("trusted_hosts", sig.parameters)

    def test_fastapi_can_add_proxy_headers_middleware_with_trusted_hosts(self) -> None:
        # End-to-end: the wiring main.py:53 uses must keep working.
        app = FastAPI()
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")

        @app.get("/ip")
        async def ip_route() -> dict[str, str]:
            return {"ok": "1"}

        with TestClient(app) as client:
            r = client.get("/ip")
            self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
