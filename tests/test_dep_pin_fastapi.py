#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `fastapi`.

Purpose
-------
Pin the FastAPI surface backend/main.py and backend/auth.py rely on. A
future FastAPI upgrade that renames middleware decorators, drops a
set_cookie kwarg, or changes the JSONResponse signature will fail here
at CI time before the backend is deployed.

Reference call sites (production code):
    backend/main.py:16-18    FastAPI, Request, Response, HTTPException, Depends, BackgroundTasks
                              + fastapi.responses.{FileResponse, JSONResponse}
                              + fastapi.middleware.cors.CORSMiddleware
    backend/main.py:38-47    @asynccontextmanager lifespan + FastAPI(lifespan=, docs_url=, redoc_url=, openapi_url=)
    backend/main.py:79       @app.middleware("http")
    backend/main.py:97/103   @app.exception_handler(ExceptionClass)
    backend/main.py:135+     @app.get(...) / @app.post(...) + path params + Depends(...)
    backend/auth.py:191-211  response.set_cookie(key, value, max_age, httponly, secure, samesite, path, domain)
                              response.delete_cookie(key, path, domain)
                              request.cookies.get(SESSION_COOKIE_NAME)
                              request.app.state.<attr>
"""

import inspect
import unittest
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.testclient import TestClient


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class FastAPIImportSurfaceTest(unittest.TestCase):
    """Every name production imports from fastapi must remain reachable."""

    def test_top_level_classes(self) -> None:
        for cls in (FastAPI, Request, Response, HTTPException, BackgroundTasks):
            self.assertTrue(isinstance(cls, type), f"{cls!r} is not a class")

    def test_depends_is_callable(self) -> None:
        self.assertTrue(callable(Depends))

    def test_responses_submodule_exposes_json_and_file(self) -> None:
        self.assertTrue(isinstance(JSONResponse, type))
        self.assertTrue(isinstance(FileResponse, type))

    def test_cors_middleware_is_importable(self) -> None:
        # backend/main.py:18 -- from fastapi.middleware.cors import CORSMiddleware
        self.assertTrue(isinstance(CORSMiddleware, type))


# -----------------------------------------------------------------------------
# 2. FastAPI(...) constructor kwargs production passes
# -----------------------------------------------------------------------------


class FastAPIConstructorTest(unittest.TestCase):
    """Pin FastAPI(lifespan=, docs_url=, redoc_url=, openapi_url=)."""

    def test_constructor_accepts_lifespan_and_disabled_docs_kwargs(self) -> None:
        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
            yield

        app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
        self.assertIsInstance(app, FastAPI)

    def test_app_exposes_state_namespace(self) -> None:
        # main.py:63 -- request.app.state.feed_maker_manager
        app = FastAPI()
        app.state.custom_attr = "value"
        self.assertEqual(app.state.custom_attr, "value")


# -----------------------------------------------------------------------------
# 3. Route decorators + path params + Depends
# -----------------------------------------------------------------------------


class RouteDecoratorTest(unittest.TestCase):
    """Pin @app.get / @app.post path-parameter and Depends behavior."""

    def _build_app(self) -> FastAPI:
        app = FastAPI()

        def get_provider() -> str:
            return "injected"

        @app.get("/auth/me")
        async def me() -> dict[str, str]:
            return {"status": "ok"}

        @app.post("/auth/login")
        async def login() -> dict[str, str]:
            return {"status": "logged-in"}

        @app.get("/items/{name}")
        async def item(name: str, dep: str = Depends(get_provider)) -> dict[str, str]:
            return {"name": name, "dep": dep}

        return app

    def test_get_and_post_routes_dispatch(self) -> None:
        app = self._build_app()
        with TestClient(app) as client:
            self.assertEqual(client.get("/auth/me").json(), {"status": "ok"})
            self.assertEqual(client.post("/auth/login").json(), {"status": "logged-in"})

    def test_path_parameters_bind_to_function_arguments(self) -> None:
        app = self._build_app()
        with TestClient(app) as client:
            response = client.get("/items/widget")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["name"], "widget")

    def test_depends_injects_provider_return_value(self) -> None:
        app = self._build_app()
        with TestClient(app) as client:
            self.assertEqual(client.get("/items/x").json()["dep"], "injected")


# -----------------------------------------------------------------------------
# 4. HTTPException(status_code=, detail=)
# -----------------------------------------------------------------------------


class HTTPExceptionTest(unittest.TestCase):
    """Pin HTTPException(...) shape -- both positional and keyword forms used."""

    def test_keyword_form_status_code_and_detail(self) -> None:
        # main.py:150 -- raise HTTPException(status_code=401, detail="...")
        exc = HTTPException(status_code=401, detail="Not authenticated")
        self.assertEqual(exc.status_code, 401)
        self.assertEqual(exc.detail, "Not authenticated")

    def test_positional_form_status_then_detail(self) -> None:
        # main.py:66/249 -- HTTPException(500, detail="...") / HTTPException(404, "...")
        exc = HTTPException(404, "missing")
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.detail, "missing")

    def test_route_handler_raising_http_exception_returns_status(self) -> None:
        app = FastAPI()

        @app.get("/boom")
        async def boom() -> None:
            raise HTTPException(status_code=403, detail="Not authorized")

        with TestClient(app) as client:
            r = client.get("/boom")
            self.assertEqual(r.status_code, 403)
            self.assertEqual(r.json(), {"detail": "Not authorized"})


# -----------------------------------------------------------------------------
# 5. JSONResponse(status_code=, content=)
# -----------------------------------------------------------------------------


class JSONResponseCallShapeTest(unittest.TestCase):
    """Pin JSONResponse shape used in main.py:87/100/106/162/186."""

    def test_json_response_with_content_only(self) -> None:
        # main.py:162 -- JSONResponse(content={"status": "success", "message": ...})
        resp = JSONResponse(content={"status": "success"})
        self.assertEqual(resp.status_code, 200)  # default
        # Body is JSON-encoded bytes.
        self.assertIn(b'"status"', resp.body)

    def test_json_response_with_status_and_content(self) -> None:
        # main.py:87 -- JSONResponse(status_code=401, content={"detail": ...})
        resp = JSONResponse(status_code=401, content={"detail": "Not authenticated"})
        self.assertEqual(resp.status_code, 401)


# -----------------------------------------------------------------------------
# 6. Request object: cookies.get + app.state
# -----------------------------------------------------------------------------


class RequestObjectTest(unittest.TestCase):
    """Pin Request.cookies.get(key) and Request.app.state access."""

    def test_request_cookies_get_returns_cookie_value(self) -> None:
        # main.py:89, auth.py:155 -- request.cookies.get(SESSION_COOKIE_NAME)
        app = FastAPI()

        @app.get("/peek")
        async def peek(request: Request) -> dict[str, str | None]:
            return {"session": request.cookies.get("sid")}

        with TestClient(app) as client:
            r = client.get("/peek", cookies={"sid": "abc"})
            self.assertEqual(r.json(), {"session": "abc"})
            r2 = client.get("/peek")
            self.assertEqual(r2.json(), {"session": None})

    def test_request_app_state_is_reachable_from_handler(self) -> None:
        # main.py:63 -- manager = request.app.state.feed_maker_manager
        app = FastAPI()
        app.state.payload = "hello-state"

        @app.get("/state")
        async def state_route(request: Request) -> dict[str, str]:
            return {"payload": request.app.state.payload}

        with TestClient(app) as client:
            self.assertEqual(client.get("/state").json(), {"payload": "hello-state"})


# -----------------------------------------------------------------------------
# 7. Response.set_cookie / delete_cookie kwargs
# -----------------------------------------------------------------------------


class CookieMutationCallShapeTest(unittest.TestCase):
    """Pin Response.set_cookie / delete_cookie signatures used in auth.py."""

    def test_set_cookie_accepts_all_security_kwargs(self) -> None:
        # auth.py:193-202 passes 8 kwargs.
        sig = inspect.signature(Response.set_cookie)
        for kw in ("key", "value", "max_age", "httponly", "secure", "samesite", "path", "domain"):
            self.assertIn(kw, sig.parameters, f"Response.set_cookie missing kwarg '{kw}'")

    def test_delete_cookie_accepts_path_and_domain(self) -> None:
        # auth.py:207-211 -- response.delete_cookie(key=, path=, domain=)
        sig = inspect.signature(Response.delete_cookie)
        for kw in ("key", "path", "domain"):
            self.assertIn(kw, sig.parameters, f"Response.delete_cookie missing kwarg '{kw}'")

    def test_set_cookie_appears_in_response_headers_end_to_end(self) -> None:
        app = FastAPI()

        @app.post("/login")
        async def login() -> JSONResponse:
            resp = JSONResponse(content={"ok": True})
            resp.set_cookie(key="sid", value="abc", max_age=3600, httponly=True, secure=True, samesite="lax", path="/")
            return resp

        with TestClient(app) as client:
            r = client.post("/login")
            # set-cookie header must carry the directives we set.
            sc = r.headers.get("set-cookie", "")
            self.assertIn("sid=abc", sc)
            self.assertIn("HttpOnly", sc)
            self.assertIn("Secure", sc)
            self.assertIn("samesite=lax", sc.lower())


# -----------------------------------------------------------------------------
# 8. Middleware + exception handler decorators
# -----------------------------------------------------------------------------


class MiddlewareAndExceptionHandlerTest(unittest.TestCase):
    """Pin @app.middleware("http") and @app.exception_handler(Exc)."""

    def test_http_middleware_decorator_wraps_handler(self) -> None:
        # main.py:79 -- @app.middleware("http")
        app = FastAPI()

        @app.middleware("http")
        async def add_header(request: Request, call_next):  # noqa: ANN001
            response = await call_next(request)
            response.headers["X-Test"] = "yes"
            return response

        @app.get("/")
        async def root() -> dict[str, str]:
            return {"ok": "1"}

        with TestClient(app) as client:
            r = client.get("/")
            self.assertEqual(r.headers.get("X-Test"), "yes")

    def test_exception_handler_decorator_intercepts_raised_exception(self) -> None:
        # main.py:97 -- @app.exception_handler(ValueError)
        app = FastAPI()

        @app.exception_handler(ValueError)
        async def handle_value_error(_request: Request, _exc: ValueError) -> JSONResponse:
            return JSONResponse(status_code=400, content={"message": "Invalid input"})

        @app.get("/boom")
        async def boom() -> None:
            raise ValueError("bad")

        with TestClient(app) as client:
            r = client.get("/boom")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json(), {"message": "Invalid input"})


# -----------------------------------------------------------------------------
# 9. Lifespan async-generator contract
# -----------------------------------------------------------------------------


class LifespanCallShapeTest(unittest.TestCase):
    """Pin the lifespan async-context-manager pattern used in main.py:38-47."""

    def test_lifespan_runs_startup_then_shutdown(self) -> None:
        events: list[str] = []

        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
            events.append("startup")
            yield
            events.append("shutdown")

        app = FastAPI(lifespan=lifespan)

        @app.get("/ping")
        async def ping() -> dict[str, str]:
            return {"pong": "1"}

        with TestClient(app) as client:
            client.get("/ping")  # any request inside the with-block

        self.assertEqual(events, ["startup", "shutdown"])


if __name__ == "__main__":
    unittest.main()
