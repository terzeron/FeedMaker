#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `bs4` (BeautifulSoup4).

Purpose
-------
Pin the bs4 surface FeedMaker production code actually uses, independent of
the bs4 version. A future bs4 upgrade that renames `decompose`, changes
`find_all`'s kwargs, returns a non-mutable `.attrs`, or breaks the
`isinstance(node, NavigableString)` invariant will fail this test at CI time
rather than at runtime.

Reference call sites (production code):
    bin/feed_maker_util.py:23           from bs4 import Tag
    bin/extractor.py                    BeautifulSoup, Comment, NavigableString, Tag
    utils/translation.py                BeautifulSoup, NavigableString
    utils/search_manga_site.py          BeautifulSoup, Comment + heavy DOM ops
"""

import unittest

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

# A representative document covering every node type / operation production
# touches: tag attribute access, find / find_all permutations, comment nodes,
# attrs dict mutation, decompose / unwrap / extract, get_text(strip=True).
SAMPLE_HTML = """\
<html>
  <body>
    <div class="container" id="root">
      <p>hello <b>world</b></p>
      <!-- a comment -->
      <a href="/x" title="t1" data-track="1" onclick="boom()">link1</a>
      <a href="/y" title="t2">link2</a>
      <font color="red">legacy</font>
      <svg width="10"><circle/></svg>
      <h1>Heading 1</h1>
      <h2>Heading 2</h2>
    </div>
    <pre>code</pre>
  </body>
</html>"""


def _make_soup() -> BeautifulSoup:
    return BeautifulSoup(SAMPLE_HTML, "html.parser")


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class Bs4ImportSurfaceTest(unittest.TestCase):
    """Every symbol production imports must remain a class."""

    def test_four_top_level_symbols_are_classes(self) -> None:
        # extractor.py imports all four; feed_maker_util.py imports Tag;
        # search_manga_site.py imports BeautifulSoup + Comment; translation.py
        # imports BeautifulSoup + NavigableString.
        self.assertTrue(isinstance(BeautifulSoup, type))
        self.assertTrue(isinstance(Comment, type))
        self.assertTrue(isinstance(NavigableString, type))
        self.assertTrue(isinstance(Tag, type))


# -----------------------------------------------------------------------------
# 2. Constructor call shape: BeautifulSoup(html_str, parser_str)
# -----------------------------------------------------------------------------


class BeautifulSoupConstructorTest(unittest.TestCase):
    """Pin BeautifulSoup(html_content, parser) positional-arg shape."""

    def test_constructor_with_html_parser(self) -> None:
        # search_manga_site.py:103, translation.py:423 -- BeautifulSoup(html, "html.parser")
        soup = BeautifulSoup("<p>x</p>", "html.parser")
        self.assertIsInstance(soup, BeautifulSoup)

    def test_constructor_accepts_parser_as_variable(self) -> None:
        # extractor.py:37 -- BeautifulSoup(html_content, parser)  (parser is a variable)
        parser = "html.parser"
        soup = BeautifulSoup("<p>x</p>", parser)
        self.assertIsInstance(soup, BeautifulSoup)


# -----------------------------------------------------------------------------
# 3. Tag access by attribute name: soup.body / soup.div
# -----------------------------------------------------------------------------


class TagAttributeAccessTest(unittest.TestCase):
    """Pin `soup.<tagname>` attribute access used in extractor + search_manga_site."""

    def test_soup_body_returns_first_body_tag(self) -> None:
        # extractor.py:44 -- soup.body
        # extractor.py:66 -- if soup.body is not None and isinstance(soup.body, Tag)
        soup = _make_soup()
        self.assertIsNotNone(soup.body)
        self.assertIsInstance(soup.body, Tag)

    def test_soup_div_returns_first_div_tag(self) -> None:
        # search_manga_site.py:104 -- if soup.div:
        soup = _make_soup()
        self.assertIsNotNone(soup.div)
        self.assertIsInstance(soup.div, Tag)

    def test_soup_body_is_none_when_missing(self) -> None:
        # The truthiness check (search_manga_site.py:104) and is-not-None check
        # (extractor.py:66) both assume missing tag -> falsy/None.
        soup = BeautifulSoup("<p>no body here</p>", "html.parser")
        # html.parser does NOT auto-insert <body>, so this is None.
        self.assertIsNone(soup.body)


# -----------------------------------------------------------------------------
# 4. find_all permutations
# -----------------------------------------------------------------------------


class FindAllCallShapeTest(unittest.TestCase):
    """Pin every find_all signature used in production."""

    def test_find_all_with_attrs_dict_for_class(self) -> None:
        # extractor.py:60 -- soup.find_all(attrs={"class": cls})
        soup = _make_soup()
        els = soup.find_all(attrs={"class": "container"})
        self.assertEqual(len(els), 1)
        assert isinstance(els[0], Tag)
        self.assertEqual(els[0].name, "div")

    def test_find_all_with_attrs_dict_for_id(self) -> None:
        # extractor.py:63 -- soup.find_all(attrs={"id": _id})
        soup = _make_soup()
        els = soup.find_all(attrs={"id": "root"})
        self.assertEqual(len(els), 1)

    def test_find_all_with_tag_name(self) -> None:
        # search_manga_site.py:175 -- soup_fragment.find_all("svg")
        soup = _make_soup()
        self.assertEqual(len(soup.find_all("a")), 2)
        self.assertEqual(len(soup.find_all("svg")), 1)

    def test_find_all_with_no_args_returns_every_tag(self) -> None:
        # search_manga_site.py:188 -- soup_fragment.find_all()
        soup = _make_soup()
        all_tags = soup.find_all()
        self.assertGreater(len(all_tags), 5)
        for t in all_tags:
            self.assertIsInstance(t, Tag)

    def test_find_all_with_tag_name_and_attr_filter(self) -> None:
        # search_manga_site.py:206 -- soup_fragment.find_all("a", title=True)
        soup = _make_soup()
        anchors = soup.find_all("a", title=True)
        self.assertEqual(len(anchors), 2)  # both <a> tags carry title

    def test_find_all_with_list_of_tag_names(self) -> None:
        # search_manga_site.py:210 -- a_tag.find_all(["h1", "h2", ..., "h6"])
        soup = _make_soup()
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        self.assertEqual(len(headings), 2)


# -----------------------------------------------------------------------------
# 5. find() shape
# -----------------------------------------------------------------------------


class FindCallShapeTest(unittest.TestCase):
    """Pin `find()` shape used in search_manga_site.py:498."""

    def test_find_returns_first_match(self) -> None:
        soup = _make_soup()
        pre = soup.find("pre")
        self.assertIsNotNone(pre)
        assert isinstance(pre, Tag)
        self.assertEqual(pre.name, "pre")

    def test_find_returns_none_when_missing(self) -> None:
        soup = _make_soup()
        self.assertIsNone(soup.find("article"))


# -----------------------------------------------------------------------------
# 6. Calling a tag as a function = find_all-by-string filter
# -----------------------------------------------------------------------------


class TagCallableShapeTest(unittest.TestCase):
    """Pin `soup.div(string=lambda ...)` -- search_manga_site.py:105."""

    def test_tag_callable_with_string_lambda_finds_matching_nodes(self) -> None:
        # search_manga_site.py uses this exact pattern to locate Comment nodes:
        #   for element in soup.div(string=lambda text: isinstance(text, Comment)):
        #       element.extract()
        soup = _make_soup()
        div = soup.div
        self.assertIsInstance(div, Tag)
        assert isinstance(div, Tag)
        found = div(string=lambda t: isinstance(t, Comment))
        self.assertEqual(len(found), 1)
        self.assertIsInstance(found[0], Comment)


# -----------------------------------------------------------------------------
# 7. tag.attrs dict semantics
# -----------------------------------------------------------------------------


class TagAttrsCallShapeTest(unittest.TestCase):
    """Pin `tag.attrs` as a mutable dict -- search_manga_site.py:192-203."""

    def test_attrs_is_a_dict_with_keys_method(self) -> None:
        soup = _make_soup()
        a = soup.find("a")
        assert isinstance(a, Tag)
        # search_manga_site.py:192 -- if attr in tag.attrs
        # search_manga_site.py:196 -- tag.attrs.keys()
        self.assertIn("href", a.attrs)
        self.assertIn("title", a.attrs)
        self.assertIn("href", list(a.attrs.keys()))

    def test_attrs_supports_del_for_attribute_removal(self) -> None:
        # search_manga_site.py:193 -- del tag.attrs[attr]
        # search_manga_site.py:198 -- del tag.attrs[attr]  (for on* handlers)
        soup = _make_soup()
        a = soup.find("a")
        assert isinstance(a, Tag)
        self.assertIn("onclick", a.attrs)
        del a.attrs["onclick"]
        self.assertNotIn("onclick", a.attrs)

    def test_keys_can_be_iterated_for_startswith_filter(self) -> None:
        # search_manga_site.py:196 / 201 -- [attr for attr in tag.attrs.keys() if attr.startswith("on")]
        soup = _make_soup()
        a = soup.find("a")
        assert isinstance(a, Tag)
        data_keys = [k for k in a.attrs.keys() if k.startswith("data-")]
        self.assertEqual(data_keys, ["data-track"])


# -----------------------------------------------------------------------------
# 8. Tag mutation methods: extract / decompose / unwrap
# -----------------------------------------------------------------------------


class TagMutationCallShapeTest(unittest.TestCase):
    """Pin extract/decompose/unwrap methods used in production."""

    def test_extract_removes_node_from_tree(self) -> None:
        # search_manga_site.py:106 -- element.extract()
        soup = _make_soup()
        div = soup.div
        assert isinstance(div, Tag)
        comments = div(string=lambda t: isinstance(t, Comment))
        for c in comments:
            c.extract()
        # After extract, no Comment remains under div.
        remaining = div(string=lambda t: isinstance(t, Comment))
        self.assertEqual(remaining, [])

    def test_decompose_destroys_element(self) -> None:
        # search_manga_site.py:176 -- svg_element.decompose()
        soup = _make_soup()
        for svg in soup.find_all("svg"):
            svg.decompose()
        self.assertEqual(soup.find_all("svg"), [])

    def test_unwrap_replaces_tag_with_its_contents(self) -> None:
        # search_manga_site.py:178 -- font_element.unwrap()
        soup = BeautifulSoup("<div><font>keep me</font></div>", "html.parser")
        for f in soup.find_all("font"):
            f.unwrap()
        self.assertEqual(soup.find_all("font"), [])
        div = soup.find("div")
        assert isinstance(div, Tag)
        self.assertEqual(div.get_text(strip=True), "keep me")


# -----------------------------------------------------------------------------
# 9. tag.name / tag.contents / get_text(strip=True)
# -----------------------------------------------------------------------------


class TagContentsAndTextTest(unittest.TestCase):
    """Pin .name, .contents and .get_text(strip=True)."""

    def test_tag_name_attribute(self) -> None:
        # extractor.py:87 -- getattr(element, "name", None)
        # extractor.py:210 -- child.name == "area"
        soup = _make_soup()
        a = soup.find("a")
        assert isinstance(a, Tag)
        self.assertEqual(a.name, "a")

    def test_tag_contents_is_iterable_list(self) -> None:
        # extractor.py:223 -- for c in el.contents
        soup = BeautifulSoup("<p>hi <b>there</b></p>", "html.parser")
        p = soup.find("p")
        assert isinstance(p, Tag)
        self.assertGreater(len(p.contents), 1)

    def test_get_text_with_strip_true_returns_trimmed_text(self) -> None:
        # search_manga_site.py:211 -- heading.get_text(strip=True)
        # search_manga_site.py:250 -- BeautifulSoup(...).get_text(strip=True)
        soup = BeautifulSoup("<p>  hello  <b> world </b>  </p>", "html.parser")
        p = soup.find("p")
        assert isinstance(p, Tag)
        self.assertEqual(p.get_text(strip=True), "helloworld")


# -----------------------------------------------------------------------------
# 10. isinstance checks against bs4 node classes
# -----------------------------------------------------------------------------


class IsinstanceCheckShapeTest(unittest.TestCase):
    """Pin isinstance(node, Comment/NavigableString/Tag) contracts."""

    def test_comment_node_is_instance_of_comment(self) -> None:
        # extractor.py:85 -- if isinstance(element, Comment)
        soup = _make_soup()
        comments = [c for c in soup.descendants if isinstance(c, Comment)]
        self.assertEqual(len(comments), 1)

    def test_text_node_is_instance_of_navigable_string(self) -> None:
        # extractor.py:87 -- isinstance(element, NavigableString)
        # extractor.py:223 -- isinstance(c, NavigableString) and str(c) == "\n"
        soup = BeautifulSoup("<p>plain text</p>", "html.parser")
        p = soup.find("p")
        assert isinstance(p, Tag)
        self.assertTrue(any(isinstance(c, NavigableString) for c in p.contents))

    def test_comment_is_subclass_of_navigable_string(self) -> None:
        # Production relies on isinstance(comment, Comment) being more specific
        # than NavigableString -- the order of isinstance checks matters in
        # extractor.py:85-87.
        self.assertTrue(issubclass(Comment, NavigableString))


if __name__ == "__main__":
    unittest.main()
