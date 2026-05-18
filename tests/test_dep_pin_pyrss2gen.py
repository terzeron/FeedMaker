#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `PyRSS2Gen`.

Purpose
-------
Pin down the *call shape* that `bin/feed_maker.py` relies on, independent of
the PyRSS2Gen version. If a future upgrade of PyRSS2Gen changes any of the
constructor keyword arguments, the `write_xml` signature, or the produced XML
structure that FeedMaker depends on, these tests will fail at CI time --
*before* the change reaches runtime.

This file deliberately does NOT mock PyRSS2Gen. It imports the real library
and exercises only the surface that `bin/feed_maker.py` actually uses:

    1. PyRSS2Gen.RSSItem(title=, link=, guid=, pubDate=, description=)
    2. PyRSS2Gen.RSS2(title=, description=, link=, lastBuildDate=, items=)
    3. rss.write_xml(text_file, encoding="utf-8")

Reference call sites in production code:
    bin/feed_maker.py:494  RSSItem(...)
    bin/feed_maker.py:502  RSS2(...)
    bin/feed_maker.py:504  rss.write_xml(outfile, encoding="utf-8")
"""

import io
import re
import unittest
from xml.etree import ElementTree as ET

import PyRSS2Gen


# A representative pubDate string produced by Datetime.get_rss_date_str()
# (RFC 822 format -- see bin/feed_maker_util.py:222).
SAMPLE_PUB_DATE = "Mon, 18 May 2026 12:34:56 +0000"


class PyRSS2GenRSSItemCallShapeTest(unittest.TestCase):
    """Pin the RSSItem constructor surface used by FeedMaker."""

    def test_rssitem_accepts_five_keyword_args(self) -> None:
        item = PyRSS2Gen.RSSItem(title="sample title", link="https://example.com/article/1", guid="https://example.com/article/1", pubDate=SAMPLE_PUB_DATE, description="<p>body</p>")
        self.assertEqual(item.title, "sample title")
        self.assertEqual(item.link, "https://example.com/article/1")
        self.assertEqual(item.description, "<p>body</p>")

    def test_rssitem_accepts_string_pubdate(self) -> None:
        # FeedMaker passes an RFC822 *string* (not a datetime) into pubDate.
        # If a future PyRSS2Gen requires a datetime here, this will break.
        item = PyRSS2Gen.RSSItem(title="t", link="l", guid="g", pubDate=SAMPLE_PUB_DATE, description="d")
        self.assertEqual(item.pubDate, SAMPLE_PUB_DATE)

    def test_rssitem_guid_can_be_plain_string(self) -> None:
        # FeedMaker passes a plain str (URL or hash), not a PyRSS2Gen.Guid object.
        item = PyRSS2Gen.RSSItem(title="t", link="l", guid="some-guid-value", pubDate=SAMPLE_PUB_DATE, description="d")
        # The library may wrap the string into a Guid object; we only care
        # that the call accepts a plain string without raising.
        self.assertIsNotNone(item.guid)


class PyRSS2GenRSS2CallShapeTest(unittest.TestCase):
    """Pin the RSS2 constructor surface used by FeedMaker."""

    def _make_item(self) -> "PyRSS2Gen.RSSItem":
        return PyRSS2Gen.RSSItem(title="t", link="l", guid="g", pubDate=SAMPLE_PUB_DATE, description="d")

    def test_rss2_accepts_five_keyword_args(self) -> None:
        rss = PyRSS2Gen.RSS2(
            title="Feed Title",
            description="Feed Title",  # FeedMaker reuses title as description
            link="https://example.com/feed",
            lastBuildDate=SAMPLE_PUB_DATE,
            items=[self._make_item()],
        )
        self.assertEqual(rss.title, "Feed Title")
        self.assertEqual(rss.link, "https://example.com/feed")
        self.assertEqual(len(rss.items), 1)

    def test_rss2_accepts_string_last_build_date(self) -> None:
        # FeedMaker passes an RFC822 *string* into lastBuildDate.
        rss = PyRSS2Gen.RSS2(title="t", description="t", link="https://example.com/feed", lastBuildDate=SAMPLE_PUB_DATE, items=[])
        self.assertEqual(rss.lastBuildDate, SAMPLE_PUB_DATE)

    def test_rss2_accepts_empty_item_list(self) -> None:
        # Defensive: FeedMaker may build an empty list if no entries.
        rss = PyRSS2Gen.RSS2(title="t", description="t", link="https://example.com/feed", lastBuildDate=SAMPLE_PUB_DATE, items=[])
        self.assertEqual(rss.items, [])


class PyRSS2GenWriteXmlCallShapeTest(unittest.TestCase):
    """Pin the write_xml(...) surface and output structure used by FeedMaker."""

    def _build_rss(self) -> "PyRSS2Gen.RSS2":
        item = PyRSS2Gen.RSSItem(title="제목 한글", link="https://example.com/a/1", guid="https://example.com/a/1", pubDate=SAMPLE_PUB_DATE, description="<p>본문 & 특수문자</p>")
        return PyRSS2Gen.RSS2(title="My Feed", description="My Feed", link="https://example.com/feed", lastBuildDate=SAMPLE_PUB_DATE, items=[item])

    def test_write_xml_writes_to_text_stream_with_encoding_kwarg(self) -> None:
        # FeedMaker opens the file with open("w", encoding="utf-8") and passes
        # the text-mode handle plus encoding="utf-8" as a keyword arg.
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        output = buf.getvalue()
        self.assertTrue(output.startswith("<?xml"))
        self.assertIn("utf-8", output[:60].lower())

    def test_output_contains_rss_channel_and_item(self) -> None:
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        output = buf.getvalue()

        # Structural guarantees FeedMaker (and downstream feed readers) rely on.
        self.assertIn("<rss", output)
        self.assertIn("<channel>", output)
        self.assertIn("<item>", output)
        self.assertIn("<title>My Feed</title>", output)
        self.assertIn("<link>https://example.com/feed</link>", output)
        self.assertIn("<pubDate>" + SAMPLE_PUB_DATE + "</pubDate>", output)

    def test_output_is_well_formed_xml(self) -> None:
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        # Must parse cleanly; if PyRSS2Gen ever emits invalid XML, downstream
        # `Data.compare_two_rss_files` and feed readers will break.
        root = ET.fromstring(buf.getvalue())
        self.assertEqual(root.tag, "rss")
        channel = root.find("channel")
        self.assertIsNotNone(channel)
        items = channel.findall("item") if channel is not None else []
        self.assertEqual(len(items), 1)

    def test_html_in_description_is_xml_escaped_and_round_trips(self) -> None:
        # FeedMaker stores rendered HTML inside <description>. PyRSS2Gen's
        # contract (as of this learning test): it applies XML text escaping
        # (NOT CDATA wrapping) to the description string. So raw "<" / "&"
        # appear as "&lt;" / "&amp;" in the serialized output, and an XML
        # parser recovers the original characters on read.
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        raw = buf.getvalue()

        # 1. Confirms the escaping strategy: entity escaping, not CDATA.
        self.assertNotIn("<![CDATA[", raw)
        self.assertIn("&lt;p&gt;", raw)
        self.assertIn("&amp;", raw)

        # 2. Confirms round-trip: original characters recoverable on parse.
        root = ET.fromstring(raw)
        desc = root.find("./channel/item/description")
        self.assertIsNotNone(desc)
        assert desc is not None  # for type checkers
        self.assertEqual(desc.text, "<p>본문 & 특수문자</p>")

    def test_korean_text_survives_round_trip(self) -> None:
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        root = ET.fromstring(buf.getvalue())
        title = root.find("./channel/item/title")
        self.assertIsNotNone(title)
        assert title is not None
        self.assertEqual(title.text, "제목 한글")

    def test_output_declares_rss_version_2(self) -> None:
        # Many feed readers branch on the rss version attribute.
        rss = self._build_rss()
        buf = io.StringIO()
        rss.write_xml(buf, encoding="utf-8")
        match = re.search(r'<rss[^>]*version="([^"]+)"', buf.getvalue())
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1), "2.0")


class PyRSS2GenProductionAlignmentTest(unittest.TestCase):
    """
    Pin additional contracts that bin/feed_maker.py depends on beyond
    the bare constructor / write_xml call shape.

    These derive from re-reading the call sites:
      L463  rss_items: list[PyRSS2Gen.RSSItem] = []
            -> RSSItem must be a *class symbol*, usable in type annotations.
      L494  rss_items.append(PyRSS2Gen.RSSItem(...)) inside `for ... reversed(...)`
            -> input order of items must be preserved in the serialized XML.
      L503  with temp_rss_file_path.open("w", encoding="utf-8") as outfile:
      L504      rss.write_xml(outfile, encoding="utf-8")
            -> write_xml must work on a real on-disk text file, not just StringIO.
      L508-509 Data.compare_two_rss_files(self.rss_file_path, temp_rss_file_path)
            -> for byte-by-byte (or canonical) comparison to be meaningful,
               write_xml output must be deterministic for the same input.
    """

    def _make_item(self, n: int) -> "PyRSS2Gen.RSSItem":
        return PyRSS2Gen.RSSItem(title=f"title-{n}", link=f"https://example.com/a/{n}", guid=f"https://example.com/a/{n}", pubDate=SAMPLE_PUB_DATE, description=f"<p>body-{n}</p>")

    def _build_rss(self, items: "list[PyRSS2Gen.RSSItem]") -> "PyRSS2Gen.RSS2":
        return PyRSS2Gen.RSS2(title="Feed", description="Feed", link="https://example.com/feed", lastBuildDate=SAMPLE_PUB_DATE, items=items)

    def test_rssitem_is_a_class_symbol_usable_for_typing_and_isinstance(self) -> None:
        # feed_maker.py L463 annotates `list[PyRSS2Gen.RSSItem]`. That requires
        # RSSItem to be a real class exposed on the package.
        self.assertTrue(isinstance(PyRSS2Gen.RSSItem, type))
        item = self._make_item(1)
        self.assertIsInstance(item, PyRSS2Gen.RSSItem)

    def test_write_xml_works_on_real_on_disk_text_file(self) -> None:
        # Production opens a Path via .open("w", encoding="utf-8") and passes
        # *that* file object to write_xml. StringIO is not enough -- a real
        # file's text-mode handle has subtly different semantics (e.g. newline
        # translation, flush, buffering).
        import tempfile
        from pathlib import Path

        rss = self._build_rss([self._make_item(1)])
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "out.xml"
            with target.open("w", encoding="utf-8") as outfile:
                rss.write_xml(outfile, encoding="utf-8")
            content = target.read_text(encoding="utf-8")

        # Parseable, contains the item we wrote.
        root = ET.fromstring(content)
        self.assertEqual(root.tag, "rss")
        titles = [t.text for t in root.findall("./channel/item/title")]
        self.assertEqual(titles, ["title-1"])

    def test_write_xml_output_is_deterministic_for_identical_input(self) -> None:
        # bin/feed_maker.py:508-509 calls Data.compare_two_rss_files to decide
        # whether to overwrite the previous feed. That comparison only makes
        # sense if write_xml is deterministic. If PyRSS2Gen ever introduces a
        # nondeterministic generator id, randomized attribute order, or a
        # serialization timestamp, this test will catch it.
        items = [self._make_item(i) for i in range(3)]

        buf_a = io.StringIO()
        self._build_rss(items).write_xml(buf_a, encoding="utf-8")

        buf_b = io.StringIO()
        self._build_rss(items).write_xml(buf_b, encoding="utf-8")

        self.assertEqual(buf_a.getvalue(), buf_b.getvalue())

    def test_items_order_is_preserved_in_serialized_output(self) -> None:
        # feed_maker.py decides the displayed order via `reversed(merged_feed_list)`
        # before appending to rss_items. So the list ordering -> XML ordering
        # contract is load-bearing.
        items = [self._make_item(i) for i in range(5)]
        buf = io.StringIO()
        self._build_rss(items).write_xml(buf, encoding="utf-8")
        root = ET.fromstring(buf.getvalue())
        titles = [t.text for t in root.findall("./channel/item/title")]
        self.assertEqual(titles, ["title-0", "title-1", "title-2", "title-3", "title-4"])


if __name__ == "__main__":
    unittest.main()
