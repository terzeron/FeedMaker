#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `urllib3`.

Purpose
-------
Pin the small urllib3 surface bin/crawler.py imports directly (separately
from `requests`, which vendors its own urllib3). crawler.py silences the
InsecureRequestWarning emitted when verify_ssl is disabled. A urllib3
upgrade that renames `disable_warnings` or moves `InsecureRequestWarning`
out of `urllib3.exceptions` would raise at import/call time in the
crawler, so it must fail here at CI time first.

Reference call sites (production code):
    bin/crawler.py:18    import urllib3
    bin/crawler.py:141   urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
"""

import unittest

import urllib3


class Urllib3SurfaceTest(unittest.TestCase):
    def test_disable_warnings_is_callable(self) -> None:
        # bin/crawler.py:141 -- urllib3.disable_warnings(...)
        self.assertTrue(callable(urllib3.disable_warnings))

    def test_insecure_request_warning_lives_under_exceptions(self) -> None:
        # bin/crawler.py:141 -- urllib3.exceptions.InsecureRequestWarning
        self.assertTrue(hasattr(urllib3, "exceptions"))
        self.assertTrue(hasattr(urllib3.exceptions, "InsecureRequestWarning"))

    def test_insecure_request_warning_is_a_warning_subclass(self) -> None:
        self.assertTrue(issubclass(urllib3.exceptions.InsecureRequestWarning, Warning))

    def test_disable_warnings_accepts_the_warning_category(self) -> None:
        # The exact call crawler.py makes must not raise.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


if __name__ == "__main__":
    unittest.main()
