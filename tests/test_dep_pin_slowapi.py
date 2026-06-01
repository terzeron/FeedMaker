#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `slowapi`.

Purpose
-------
Pin the slowapi surface used by backend/main.py for rate limiting. A
slowapi upgrade that renames the rate-string format, drops
_rate_limit_exceeded_handler, or restructures key_func will silently
disable login rate limiting (which would matter for credential stuffing).

Reference call sites (production code):
    backend/main.py:21   from slowapi import Limiter, _rate_limit_exceeded_handler
    backend/main.py:22   from slowapi.errors import RateLimitExceeded
    backend/main.py:23   from slowapi.util import get_remote_address
    backend/main.py:34   limiter = Limiter(key_func=get_remote_address)
    backend/main.py:48   app.state.limiter = limiter
    backend/main.py:49   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    backend/main.py:136  @limiter.limit("10/minute")
"""

import unittest

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


# -----------------------------------------------------------------------------
# 1. Import surface
# -----------------------------------------------------------------------------


class SlowapiImportSurfaceTest(unittest.TestCase):
    def test_limiter_is_a_class(self) -> None:
        self.assertTrue(isinstance(Limiter, type))

    def test_rate_limit_exceeded_handler_is_callable(self) -> None:
        self.assertTrue(callable(_rate_limit_exceeded_handler))

    def test_rate_limit_exceeded_is_an_exception(self) -> None:
        self.assertTrue(isinstance(RateLimitExceeded, type))
        self.assertTrue(issubclass(RateLimitExceeded, Exception))

    def test_get_remote_address_is_callable(self) -> None:
        self.assertTrue(callable(get_remote_address))


# -----------------------------------------------------------------------------
# 2. Limiter(key_func=...) constructor + .limit(rate_str) decorator
# -----------------------------------------------------------------------------


class LimiterCallShapeTest(unittest.TestCase):
    """Pin Limiter(key_func=) and limiter.limit("N/period") used in main.py."""

    def test_limiter_accepts_key_func_kwarg(self) -> None:
        limiter = Limiter(key_func=get_remote_address)
        self.assertTrue(hasattr(limiter, "limit"))

    def test_limit_returns_a_decorator(self) -> None:
        # main.py:136 -- @limiter.limit("10/minute")
        limiter = Limiter(key_func=get_remote_address)
        deco = limiter.limit("10/minute")
        self.assertTrue(callable(deco))


# -----------------------------------------------------------------------------
# 3. End-to-end: wire limiter into FastAPI exactly like main.py
# -----------------------------------------------------------------------------


class SlowapiFastAPIIntegrationTest(unittest.TestCase):
    """Pin the wiring: app.state.limiter + add_exception_handler + @limit."""

    def test_rate_limit_exceeded_returns_429_after_threshold(self) -> None:
        # Mirror of backend/main.py:34-49 + a rate-limited route.
        limiter = Limiter(key_func=get_remote_address)
        app = FastAPI()
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

        @app.get("/ping")
        @limiter.limit("2/minute")
        async def ping(request: Request) -> JSONResponse:
            return JSONResponse(content={"ok": True})

        with TestClient(app) as client:
            r1 = client.get("/ping")
            r2 = client.get("/ping")
            r3 = client.get("/ping")

        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r3.status_code, 429)  # third request exceeds 2/minute


if __name__ == "__main__":
    unittest.main()
