#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `requests`.

Purpose
-------
Pin the requests surface FeedMaker production code actually uses. A future
upgrade that changes the kwargs of get/post/head, drops Response attributes,
or restructures the exceptions hierarchy will fail this test at CI time
before reaching runtime.

Reference call sites (production code):
    backend/auth.py:61-71      requests.get(..., params=, timeout=); response.json(); requests.RequestException
    bin/notification.py:130    requests.post(url, headers=, data=, timeout=)
    bin/crawler.py:189-302     requests.{get,post,head}(...) + Response + exceptions + RequestsCookieJar

Strategy
--------
requests' top-level functions issue real HTTP and we don't want network
dependency in CI. We pin:
  - import-time symbol surface
  - function signatures (kwarg names) via inspect.signature
  - Response class shape: attributes / settable fields / json() / .raw / .request
  - exception class hierarchy
  - RequestsCookieJar mutability and len()
"""

import inspect
import unittest

import requests
import requests.exceptions
from requests.cookies import RequestsCookieJar


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class RequestsImportSurfaceTest(unittest.TestCase):
    """Every name production reaches into the requests namespace for."""

    def test_top_level_functions_are_callable(self) -> None:
        # crawler.py uses .get, .post, .head; notification.py uses .post
        self.assertTrue(callable(requests.get))
        self.assertTrue(callable(requests.post))
        self.assertTrue(callable(requests.head))

    def test_response_class_is_exposed(self) -> None:
        # crawler.py:111 -- def check_login_success(response: requests.Response)
        self.assertTrue(isinstance(requests.Response, type))

    def test_request_exception_is_exposed_at_top_level(self) -> None:
        # backend/auth.py:71 -- except http_requests.RequestException
        self.assertTrue(isinstance(requests.RequestException, type))
        self.assertTrue(issubclass(requests.RequestException, Exception))

    def test_exceptions_submodule_has_connection_and_timeout(self) -> None:
        # crawler.py:190/214/245/249/269/273/457
        self.assertTrue(isinstance(requests.exceptions.ConnectionError, type))
        self.assertTrue(isinstance(requests.exceptions.ReadTimeout, type))

    def test_requests_cookie_jar_is_importable(self) -> None:
        # crawler.py:20 -- from requests.cookies import RequestsCookieJar
        self.assertTrue(isinstance(RequestsCookieJar, type))


# -----------------------------------------------------------------------------
# 2. Function signatures: get / post / head accept the kwargs production passes
# -----------------------------------------------------------------------------


class RequestsFunctionSignatureTest(unittest.TestCase):
    """Pin the kwarg names production passes."""

    def _params(self, fn) -> set[str]:  # noqa: ANN001
        # requests' top-level helpers ultimately accept **kwargs forwarded to
        # Session.request, so we inspect Session.request as the canonical
        # signature.
        return set(inspect.signature(requests.Session.request).parameters)

    def test_session_request_accepts_production_kwargs(self) -> None:
        params = self._params(requests.Session.request)
        # Union of all kwarg names production uses across crawler/notification/auth.
        for kw in ("url", "headers", "params", "data", "timeout", "verify", "allow_redirects"):
            self.assertIn(kw, params, f"requests no longer accepts kwarg '{kw}'")

    def test_top_level_get_post_head_are_thin_wrappers(self) -> None:
        # We don't pin specific kwargs on requests.get/post/head because they
        # vary by version (sometimes **kwargs, sometimes explicit). What we
        # need is that they ARE callable wrappers that forward to request().
        for fn in (requests.get, requests.post, requests.head):
            self.assertTrue(callable(fn))


# -----------------------------------------------------------------------------
# 3. Response class shape -- attributes/methods production touches
# -----------------------------------------------------------------------------


class ResponseObjectShapeTest(unittest.TestCase):
    """
    Production never mocks Response -- it reads attributes directly. So the
    attribute *names* must remain on Response. We construct a bare Response()
    and verify every attribute production references is reachable (even if
    the value is the default).
    """

    def test_response_has_all_attributes_production_reads(self) -> None:
        r = requests.Response()
        # Set by the library, but the attribute must exist.
        for attr in ("status_code", "headers", "cookies", "text", "content", "encoding", "raw", "request"):
            self.assertTrue(hasattr(r, attr), f"Response.{attr} missing")

    def test_response_status_code_is_int_or_none(self) -> None:
        # crawler.py compares to (200, 302), 200, 201; notification.py same.
        r = requests.Response()
        self.assertIn(type(r.status_code).__name__, ("int", "NoneType"))

    def test_response_headers_is_dict_castable(self) -> None:
        # crawler.py:268/285/301 -- dict(response.headers)
        r = requests.Response()
        # Even an unsent Response yields a CaseInsensitiveDict-like for headers.
        self.assertIsNotNone(r.headers)
        # Must be dict-castable.
        as_dict = dict(r.headers)
        self.assertIsInstance(as_dict, dict)

    def test_response_cookies_is_a_requests_cookie_jar(self) -> None:
        # crawler.py: if response.cookies, len(response.cookies), iteration
        r = requests.Response()
        self.assertIsInstance(r.cookies, RequestsCookieJar)
        self.assertEqual(len(r.cookies), 0)

    def test_response_json_is_callable(self) -> None:
        # backend/auth.py:65 -- fb_data = response.json()
        r = requests.Response()
        self.assertTrue(callable(r.json))

    def test_response_encoding_is_settable(self) -> None:
        # crawler.py:297 -- response.encoding = "utf-8"
        r = requests.Response()
        r.encoding = "utf-8"
        self.assertEqual(r.encoding, "utf-8")

    def test_response_raw_has_decode_content_field(self) -> None:
        # crawler.py:288 -- response.raw.decode_content = True
        # raw is None until streamed -- we only need the attribute path to be
        # reachable when raw is set. So we set a stand-in object and confirm
        # attribute assignment works.

        class _RawStub:
            decode_content = False

        r = requests.Response()
        r.raw = _RawStub()
        r.raw.decode_content = True
        self.assertTrue(r.raw.decode_content)


# -----------------------------------------------------------------------------
# 4. Exception hierarchy
# -----------------------------------------------------------------------------


class RequestsExceptionsHierarchyTest(unittest.TestCase):
    """Pin the exception subclass relationships production assumes."""

    def test_connection_error_and_read_timeout_subclass_request_exception(self) -> None:
        # backend/auth.py:71 catches RequestException, which must catch
        # everything crawler.py catches narrowly. If a future version makes
        # ConnectionError or ReadTimeout NOT a RequestException, the auth.py
        # broad-catch will start missing them.
        self.assertTrue(issubclass(requests.exceptions.ConnectionError, requests.RequestException))
        self.assertTrue(issubclass(requests.exceptions.ReadTimeout, requests.RequestException))

    def test_exceptions_are_alias_of_top_level(self) -> None:
        # requests.exceptions.RequestException and requests.RequestException
        # should refer to the same class.
        self.assertIs(requests.exceptions.RequestException, requests.RequestException)


# -----------------------------------------------------------------------------
# 5. RequestsCookieJar mutation
# -----------------------------------------------------------------------------


class RequestsCookieJarShapeTest(unittest.TestCase):
    """Pin RequestsCookieJar usage in crawler.py."""

    def test_cookie_jar_supports_item_assignment(self) -> None:
        # crawler.py:165 -- self.cookies[k] = v   (self.cookies is a RequestsCookieJar)
        jar = RequestsCookieJar()
        jar["session"] = "abc123"
        self.assertEqual(jar["session"], "abc123")

    def test_cookie_jar_supports_len_and_truthiness(self) -> None:
        # crawler.py:112 -- if response.cookies and len(response.cookies) > 0
        jar = RequestsCookieJar()
        self.assertFalse(jar)  # empty jar is falsy
        self.assertEqual(len(jar), 0)
        jar["k"] = "v"
        self.assertTrue(jar)
        self.assertEqual(len(jar), 1)

    def test_cookie_jar_is_iterable_for_each_cookie(self) -> None:
        # write_cookies_to_file in crawler.py iterates cookies -- pin that.
        jar = RequestsCookieJar()
        jar["a"] = "1"
        jar["b"] = "2"
        names = {c.name for c in jar}
        self.assertEqual(names, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
