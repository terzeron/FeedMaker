#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `defusedxml`.

Purpose
-------
Pin defusedxml.ElementTree's surface used by backend/feed_maker_manager.py.
A defusedxml upgrade that removes one of the security exceptions or
changes ET.parse() return shape would silently let unsafe XML through.

Reference call sites (production code):
    backend/feed_maker_manager.py:14   import defusedxml.ElementTree as ET
    backend/feed_maker_manager.py:285  tree = ET.parse(path)
    backend/feed_maker_manager.py:286  root = tree.getroot()
    backend/feed_maker_manager.py:288  for item in root.findall(".//item"):
    backend/feed_maker_manager.py:289  item.findtext("title")
    backend/feed_maker_manager.py:320  except (ET.ParseError, ET.DTDForbidden,
                                              ET.EntitiesForbidden,
                                              ET.ExternalReferenceForbidden) as e:
"""

import tempfile
import unittest
from pathlib import Path

import defusedxml.ElementTree as ET


SAFE_RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Feed</title>
    <item>
      <title>First</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 18 May 2026 12:34:56 +0000</pubDate>
    </item>
    <item>
      <title>Second</title>
      <link>https://example.com/2</link>
      <pubDate>Mon, 18 May 2026 12:35:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""

# A document that defusedxml MUST refuse (entity-expansion / billion laughs).
ENTITIES_XML = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY a "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA">
]>
<foo>&a;</foo>
"""


# -----------------------------------------------------------------------------
# 1. Import surface: ET.parse + 4 exception classes
# -----------------------------------------------------------------------------


class DefusedXmlImportSurfaceTest(unittest.TestCase):
    """Pin every name the production except-clause references."""

    def test_parse_is_callable(self) -> None:
        self.assertTrue(callable(ET.parse))

    def test_all_four_exception_classes_exist(self) -> None:
        # feed_maker_manager.py:320 catches all four. If any is removed, the
        # narrow except will fail at import-time.
        for name in ("ParseError", "DTDForbidden", "EntitiesForbidden", "ExternalReferenceForbidden"):
            self.assertTrue(hasattr(ET, name), f"defusedxml.ElementTree.{name} missing")
            cls = getattr(ET, name)
            self.assertTrue(isinstance(cls, type))
            self.assertTrue(issubclass(cls, Exception), f"{name} must be an Exception subclass")


# -----------------------------------------------------------------------------
# 2. ET.parse() returns a tree with getroot() and findall()
# -----------------------------------------------------------------------------


class ParseSafeRSSTest(unittest.TestCase):
    """Pin the tree.getroot() / root.findall() / item.findtext() chain."""

    def _parse_string(self, xml: str) -> "ET.ElementTree":
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "feed.xml"
            p.write_text(xml, encoding="utf-8")
            return ET.parse(p)

    def test_getroot_returns_element_with_rss_tag(self) -> None:
        tree = self._parse_string(SAFE_RSS)
        root = tree.getroot()
        self.assertEqual(root.tag, "rss")

    def test_findall_returns_list_of_items(self) -> None:
        # feed_maker_manager.py:288 -- root.findall(".//item")
        tree = self._parse_string(SAFE_RSS)
        root = tree.getroot()
        items = root.findall(".//item")
        self.assertEqual(len(items), 2)

    def test_findtext_returns_string_for_child_tag(self) -> None:
        # feed_maker_manager.py:289 -- item.findtext("title")
        tree = self._parse_string(SAFE_RSS)
        root = tree.getroot()
        first = root.findall(".//item")[0]
        self.assertEqual(first.findtext("title"), "First")
        self.assertEqual(first.findtext("link"), "https://example.com/1")
        self.assertEqual(first.findtext("pubDate"), "Mon, 18 May 2026 12:34:56 +0000")

    def test_findtext_returns_none_when_child_missing(self) -> None:
        # feed_maker_manager.py:289-291 -- `if not title: continue`
        tree = self._parse_string("<root><item/></root>")
        root = tree.getroot()
        self.assertIsNone(root.find("item").findtext("title"))


# -----------------------------------------------------------------------------
# 3. Defusing behavior: ET.parse refuses dangerous XML
# -----------------------------------------------------------------------------


class DefuseDangerousXmlTest(unittest.TestCase):
    """Pin: defusedxml raises a security-tagged exception, not a silent parse."""

    def test_doctype_with_entity_raises_entities_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "evil.xml"
            p.write_text(ENTITIES_XML, encoding="utf-8")
            with self.assertRaises(ET.EntitiesForbidden):
                ET.parse(p)

    def test_malformed_xml_raises_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.xml"
            p.write_text("<root><unclosed>", encoding="utf-8")
            with self.assertRaises(ET.ParseError):
                ET.parse(p)


if __name__ == "__main__":
    unittest.main()
