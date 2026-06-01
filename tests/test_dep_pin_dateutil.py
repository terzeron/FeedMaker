#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `python-dateutil`.

Purpose
-------
Pin dateutil's parse() and isoparser() surface used by bin/feed_maker.py.
A future dateutil upgrade that changes the parser callable name,
stops accepting timezone-bearing strings, or raises a different exception
type will break feed_maker's index-file reading and the failed-URL cache.

Reference call sites (production code):
    bin/feed_maker.py:13    import dateutil.parser
    bin/feed_maker.py:14    from dateutil.parser import isoparser
    bin/feed_maker.py:65    self.isoparser = isoparser()
    bin/feed_maker.py:332   mtime = dateutil.parser.parse(mtime_str)
    bin/feed_maker.py:605   expiry_dt = self.isoparser.isoparse(expiry_str)
                            ... except ValueError: ...
"""

import unittest
from datetime import datetime

import dateutil.parser
from dateutil.parser import isoparser


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class DateutilImportSurfaceTest(unittest.TestCase):
    """Pin the imports feed_maker.py:13-14 relies on."""

    def test_dateutil_parser_module_exposes_parse(self) -> None:
        # feed_maker.py:332 -- dateutil.parser.parse(mtime_str)
        self.assertTrue(callable(dateutil.parser.parse))

    def test_isoparser_is_a_callable_class(self) -> None:
        # feed_maker.py:65 -- self.isoparser = isoparser()
        self.assertTrue(callable(isoparser))
        instance = isoparser()
        self.assertTrue(callable(instance.isoparse))


# -----------------------------------------------------------------------------
# 2. dateutil.parser.parse(mtime_str)
# -----------------------------------------------------------------------------


class DateutilParserParseTest(unittest.TestCase):
    """Pin parse(...) used in feed_maker.py:332 for mtime strings."""

    def test_parse_returns_datetime_for_iso_like_string(self) -> None:
        # `mtime_str` comes from index files; format can vary so parse() is used
        # for tolerance (vs the strict isoparse).
        dt = dateutil.parser.parse("2026-05-18 12:34:56+00:00")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 5)
        self.assertEqual(dt.day, 18)

    def test_parse_returns_datetime_for_rfc822_like_string(self) -> None:
        # FeedMaker also serializes RFC822-style strings -- they must parse.
        dt = dateutil.parser.parse("Mon, 18 May 2026 12:34:56 +0000")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)

    def test_parse_preserves_timezone_when_present(self) -> None:
        dt = dateutil.parser.parse("2026-05-18T00:00:00+09:00")
        self.assertIsNotNone(dt.tzinfo)


# -----------------------------------------------------------------------------
# 3. isoparser().isoparse(expiry_str) -- strict ISO 8601 parser
# -----------------------------------------------------------------------------


class IsoparserCallShapeTest(unittest.TestCase):
    """Pin isoparser().isoparse(...) used in feed_maker.py:605/633."""

    def setUp(self) -> None:
        self.iso = isoparser()

    def test_isoparse_returns_datetime_for_iso8601_with_offset(self) -> None:
        dt = self.iso.isoparse("2026-05-18T12:34:56+00:00")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.hour, 12)

    def test_isoparse_raises_value_error_on_malformed_input(self) -> None:
        # feed_maker.py:608 catches ValueError specifically.
        with self.assertRaises(ValueError):
            self.iso.isoparse("not-a-timestamp")

    def test_isoparse_raises_value_error_on_rfc822_style_input(self) -> None:
        # isoparse is strict; it does NOT accept RFC822, which is why
        # production uses parse() for index files but isoparser for the
        # failed-urls cache (which writes ISO 8601 deliberately).
        with self.assertRaises(ValueError):
            self.iso.isoparse("Mon, 18 May 2026 12:34:56 +0000")


if __name__ == "__main__":
    unittest.main()
