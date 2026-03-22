#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import logging.config
from pathlib import Path
from bs4 import BeautifulSoup, Comment

from bin.extractor import Extractor
from bin.feed_maker_util import Config, header_str
from unittest.mock import patch, MagicMock
from bin.extractor import Extractor, main
import html as html_module

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

dummy_url = "https://test.com"


# mypy: disable-error-code=attr-defined


class ExtractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(feed_dir_path=Path(__file__).parent)
        self.html_content = '''
        <html>
        <body>
        <div id="content">message1</div>
        <div class="content_view">message2</div>
        <div class="content_view">message3</div>
        <div>message4</div>
        <div class="list">
        <span class="link">
        <a href="https://abc.com/test_image1.png">link</a>
        </span>        
        </div>        
        </body>
        </html>'''
        parser = "html.parser"
        self.soup = BeautifulSoup(self.html_content, parser)

    def tearDown(self) -> None:
        del self.soup

    @staticmethod
    def wrap_header(string: str) -> str:
        return header_str + "\n" + string + "\n"

    def test_extract_content(self) -> None:
        extraction_conf = self.config.get_extraction_configs()
        actual = Extractor.extract_content(extraction_conf, dummy_url, input_data=self.html_content)
        expected = ExtractTest.wrap_header(
            '''<div>\nmessage2</div>\n<div>\nmessage3</div>\n<div>\nmessage1</div>'''
        )
        self.assertEqual(expected, actual)

    def test_traverse_element(self) -> None:
        extractor = Extractor()
        element = self.soup.find(id="content")
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = '<div>\nmessage1</div>\n'
        self.assertEqual(expected, actual)

    def test_check_element_class(self) -> None:
        extractor = Extractor()
        element = self.soup.find(class_="list")
        self.assertIsNotNone(element)
        span = getattr(element, "span", None)
        self.assertIsNotNone(span)
        assert span is not None
        actual = extractor._check_element_class(span, "span", "link")
        self.assertTrue(actual)

    def test_paragraph_simple(self) -> None:
        extractor = Extractor()
        html = '<p>Test paragraph</p>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.p
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = '<p>\nTest paragraph</p>\n'
        self.assertEqual(expected, actual)

    def test_image_data_lazy_src(self) -> None:
        extractor = Extractor()
        html = '<img data-lazy-src="/img.png" width="80"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.img
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='https://test.com/img.png' width='80'/>\n"
        self.assertEqual(expected, actual)

    def test_image_src(self) -> None:
        extractor = Extractor()
        html = '<img src="http://other.com/image.jpg"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.img
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='http://other.com/image.jpg'/>\n"
        self.assertEqual(expected, actual)

    def test_input_origin_src(self) -> None:
        extractor = Extractor()
        html = '<input class="origin_src" value="pic.jpg"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.input
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='https://test.com/pic.jpg'/>\n"
        self.assertEqual(expected, actual)

    def test_canvas_data_original(self) -> None:
        extractor = Extractor()
        html = '<canvas data-original="cnv.png" width="60"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.canvas
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='cnv.png' width='60'/>\n"
        self.assertEqual(expected, actual)

    def test_anchor_relative(self) -> None:
        extractor = Extractor()
        html = '<a href="/path" target="_blank">Click</a>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.a
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<a href='https://test.com/path' target='_blank'>Click</a>\n"
        self.assertEqual(expected, actual)

    def test_iframe_flash(self) -> None:
        extractor = Extractor()
        html = '<iframe src="video_player.nhn?id=123"></iframe>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.iframe
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = (
            "<iframe src='video_player.nhn?id=123'></iframe><br/>\n"
            "<a href='video_player.nhn?id=123'>video_player.nhn?id=123</a><br/>\n"
        )
        self.assertEqual(expected, actual)

    def test_iframe_normal(self) -> None:
        extractor = Extractor()
        html = '<iframe src="https://othersite.com/embed"></iframe>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.iframe
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual(str(element), actual)

    def test_script_skip(self) -> None:
        extractor = Extractor()
        html = '<script>alert("x");</script>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.script
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual("", actual)

    def test_pre_preserve(self) -> None:
        extractor = Extractor()
        html = '<pre>  pre\n text  </pre>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.pre
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = str(element) + "\n"
        self.assertEqual(expected, actual)

    def test_default_handler(self) -> None:
        extractor = Extractor()
        html = '<custom>abc</custom>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.custom
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<custom>\nabc</custom>\n"
        self.assertEqual(expected, actual)

    def test_comment_skip(self) -> None:
        extractor = Extractor()
        html = '<!-- comment text --><div>OK</div>'
        soup = BeautifulSoup(html, "html.parser")
        comment = [c for c in soup.contents if isinstance(c, Comment)][0]
        actual = extractor._traverse_element(comment, dummy_url, "utf-8")
        self.assertEqual("", actual)

    def test_embed_flash(self) -> None:
        extractor = Extractor()
        html = '<embed src="movie.swf" />'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.embed
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = (
            "<embed src='movie.swf'></embed><br/>\n"
            "<a href='movie.swf'>movie.swf</a><br/>\n"
        )
        self.assertEqual(expected, actual)

    def test_embed_normal(self) -> None:
        extractor = Extractor()
        html = '<embed src="https://site.com/vid.mp4" />'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.embed
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual(str(element), actual)

    def test_map_area(self) -> None:
        extractor = Extractor()
        html = '<map><area href="link.html" alt="TITLE"></area></map>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.map
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<br/><br/><strong><a href='link.html'>TITLE</a></strong><br/><br/>\n"
        self.assertEqual(expected, actual)

    def test_hidden_style(self) -> None:
        extractor = Extractor()
        html = '<div style="display:none"><span>Hidden</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.div
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual(actual, "")

    def test_param_flash(self) -> None:
        extractor = Extractor()
        html = '<param name="Src" value="movie.swf"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.param
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<video src='movie.swf'></video><br/>\n<a href='movie.swf'>movie.swf</a><br/>\n"
        self.assertEqual(expected, actual)

    def test_object_flash(self) -> None:
        extractor = Extractor()
        html = '<object name="Src" value="movie.swf"></object>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.object
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<video src='movie.swf'></video><br/>\n<a href='movie.swf'>movie.swf</a><br/>\n"
        self.assertEqual(expected, actual)

    def test_style_skip(self) -> None:
        extractor = Extractor()
        html = '<style>h1{color:red;}</style>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.style
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual("", actual)

    def test_map_mixed(self) -> None:
        extractor = Extractor()
        html = '<map>text<area href="a.html" alt="A"></area>more</map>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.map
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<br/><br/><strong><a href='a.html'>A</a></strong><br/><br/>\n"
        self.assertEqual(expected, actual)

    def test_lazysrc_priority(self) -> None:
        extractor = Extractor()
        html = '<img lazysrc="lazy.png"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.img
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='https://test.com/lazy.png'/>\n"
        self.assertEqual(expected, actual)

    def test_protocol_relative_canvas(self) -> None:
        extractor = Extractor()
        html = '<canvas data-src="//cdn.com/img.jpg"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.canvas
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        expected = "<img src='https://cdn.com/img.jpg'/>\n"
        self.assertEqual(expected, actual)

    def test_br_tag(self) -> None:
        extractor = Extractor()
        html = '<br/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.br
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        # default_handler 적용
        expected = '<br>\n</br>\n'
        self.assertEqual(expected, actual)

    def test_input_non_origin(self) -> None:
        extractor = Extractor()
        html = '<input class="other" value="pic.jpg"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.input
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        # origin_src 클래스가 아니면 출력이 없어야 함
        self.assertEqual("", actual)

    def test_lazy_src_priority_combination(self) -> None:
        extractor = Extractor()
        html = '<img data-lazy-src="a.png" lazy-src="b.png" data-original="c.png" src="d.png"/>'
        soup = BeautifulSoup(html, "html.parser")
        element = soup.img
        actual = extractor._traverse_element(element, dummy_url, "utf-8")
        self.assertEqual("<img src='https://test.com/a.png'/>\n", actual)

    def test_complex_mixed_scenario(self) -> None:
        extractor = Extractor()
        html = '''
        <div style="visibility:hidden"><table><tr><td>A</td></tr></table></div>
        <p>Visible<br>Line</p>
        <map>X<area href="/map_link" alt="Map"/></map>
        <img data-lazy-src="/lazy.png" src="//cdn/a.png"/>
        <param name="Src" value="f.swf"/>
        <br/>
        '''
        soup = BeautifulSoup(html, "html.parser")
        # wrap in a container to traverse
        container = soup.new_tag("div")
        for node in soup.find_all(recursive=False):
            container.append(node)
        actual = extractor._traverse_element(container, dummy_url, "utf-8")
        expected = (
            "<div>\n"
            "<p>\nVisible<br>\n</br>\nLine</p>\n"
            "<br/><br/><strong><a href='/map_link'>Map</a></strong><br/><br/>\n"
            "<img src='https://test.com/lazy.png'/>\n"
            "<video src='f.swf'></video><br/>\n"
            "<a href='f.swf'>f.swf</a><br/>\n"
            "<br>\n"
            "</br>\n"
            "</div>\n"
        )
        self.assertEqual(expected, actual)


class TestExtractorExtended(unittest.TestCase):
    """Extended tests for Extractor to improve coverage on uncovered lines."""

    # ── extract_content: no extraction config ──

    def test_extract_content_empty_config(self) -> None:
        """Empty extraction config should return None."""
        result = Extractor.extract_content({}, dummy_url, input_data="<p>hello</p>")
        self.assertIsNone(result)

    def test_extract_content_none_config(self) -> None:
        """None-like config (empty dict) should return None."""
        result = Extractor.extract_content({}, dummy_url)
        self.assertIsNone(result)

    # ── extract_content: parser fallback loop ──

    def test_extract_content_tries_multiple_parsers(self) -> None:
        """When first parser yields no result, should try others."""
        conf = {"element_class_list": ["target"], "element_id_list": [], "element_path_list": [], "encoding": "utf-8"}
        html_input = "<div class='target'>found it</div>"
        result = Extractor.extract_content(conf, dummy_url, input_data=html_input)
        self.assertIsNotNone(result)
        self.assertIn("found it", result)

    def test_extract_content_with_whitespace_only_html(self) -> None:
        """Whitespace-only HTML should produce header but no meaningful content."""
        conf = {"element_class_list": ["x"], "element_id_list": [], "element_path_list": [], "encoding": "utf-8"}
        result = Extractor.extract_content(conf, dummy_url, input_data="   ")
        self.assertIsNotNone(result)

    @patch("sys.stdin")
    def test_extract_content_reads_stdin_when_no_input_data(self, mock_stdin: MagicMock) -> None:
        """When input_data is empty, should read from stdin."""
        mock_stdin.read.return_value = "<div class='x'>from stdin</div>"
        conf = {"element_class_list": ["x"], "element_id_list": [], "element_path_list": [], "encoding": "utf-8"}
        result = Extractor.extract_content(conf, dummy_url, input_data="")
        self.assertIsNotNone(result)
        self.assertIn("from stdin", result)

    # ── extract_content: all three selectors present triggers body traverse ──

    def test_extract_content_all_selectors_traverses_body(self) -> None:
        """When class_list, id_list, and path_list all present, body should be traversed."""
        conf = {"element_class_list": ["cls"], "element_id_list": ["myid"], "element_path_list": ["div"], "encoding": "utf-8"}
        html_input = "<html><body><div class='cls' id='myid'>text</div></body></html>"
        result = Extractor.extract_content(conf, dummy_url, input_data=html_input)
        self.assertIsNotNone(result)
        # The result should contain the text from body traversal
        self.assertIn("text", result)

    # ── extract_content: element_path_list with path selector ──

    def test_extract_content_with_path_list(self) -> None:
        """element_path_list should extract elements by path."""
        conf = {"element_class_list": [], "element_id_list": [], "element_path_list": ["div"], "encoding": "utf-8"}
        html_input = "<html><body><div>path content</div></body></html>"
        result = Extractor.extract_content(conf, dummy_url, input_data=html_input)
        self.assertIsNotNone(result)

    # ── _extract_by_selectors: path_list with no body ──

    def test_extract_by_selectors_no_body(self) -> None:
        """When soup has no body, path_list extraction should not crash."""
        soup = BeautifulSoup("<div>no body tag</div>", "html.parser")
        result = Extractor._extract_by_selectors(soup, class_list=[], id_list=[], path_list=["div"], url=dummy_url, encoding="utf-8")
        # soup.body is None for fragment without <html><body>
        # The method should handle this gracefully
        self.assertIsInstance(result, str)

    # ── _handle_text: empty/whitespace text ──

    def test_handle_text_whitespace(self) -> None:
        result = Extractor._handle_text("   ")
        self.assertEqual("", result)

    def test_handle_text_html_string(self) -> None:
        result = Extractor._handle_text("html")
        self.assertEqual("", result)

    def test_handle_text_normal(self) -> None:
        result = Extractor._handle_text("hello world")
        self.assertEqual("hello world", result)

    def test_handle_text_with_special_chars(self) -> None:
        result = Extractor._handle_text("<script>alert('x')</script>")
        self.assertIn("&lt;", result)
        self.assertIn("&gt;", result)

    # ── _handle_text: UnicodeEncodeError path ──

    def test_handle_text_unicode_encode_error(self) -> None:
        """UnicodeEncodeError during html.escape should be handled."""
        import html as html_module

        original_escape = html_module.escape

        call_count = [0]

        def mock_escape(s, quote=True):
            call_count[0] += 1
            if call_count[0] == 1:
                raise UnicodeEncodeError("utf-8", "x", 0, 1, "error")
            return original_escape(s, quote)

        with patch("bin.extractor.html.escape", side_effect=mock_escape):
            result = Extractor._handle_text("test text")
            # Should attempt word-by-word escape
            self.assertIsInstance(result, str)

    # ── _is_hidden: visibility hidden ──

    def test_is_hidden_visibility(self) -> None:
        soup = BeautifulSoup('<div style="visibility: hidden">x</div>', "html.parser")
        el = soup.div
        self.assertTrue(Extractor._is_hidden(el))

    def test_is_hidden_display_none(self) -> None:
        soup = BeautifulSoup('<div style="display:none">x</div>', "html.parser")
        el = soup.div
        self.assertTrue(Extractor._is_hidden(el))

    def test_is_hidden_no_style(self) -> None:
        soup = BeautifulSoup("<div>visible</div>", "html.parser")
        el = soup.div
        self.assertFalse(Extractor._is_hidden(el))

    # ── _check_element_class edge cases ──

    def test_check_element_class_no_class(self) -> None:
        soup = BeautifulSoup("<div>text</div>", "html.parser")
        el = soup.div
        self.assertFalse(Extractor._check_element_class(el, "div", "myclass"))

    def test_check_element_class_string_class(self) -> None:
        """When class is a string (not list)."""
        soup = BeautifulSoup('<div class="myclass">text</div>', "html.parser")
        el = soup.div
        # In BS4, class is always a list, but we test the logic path
        self.assertTrue(Extractor._check_element_class(el, "div", "myclass"))

    def test_check_element_class_wrong_tag(self) -> None:
        soup = BeautifulSoup('<span class="myclass">text</span>', "html.parser")
        el = soup.span
        self.assertFalse(Extractor._check_element_class(el, "div", "myclass"))

    # ── _traverse_element: NavigableString ──

    def test_traverse_element_navigable_string(self) -> None:
        soup = BeautifulSoup("plain text", "html.parser")
        ns = soup.contents[0]
        result = Extractor._traverse_element(ns, dummy_url, "utf-8")
        self.assertEqual("plain text", result)

    # ── _handle_img: no src at all ──

    def test_handle_img_no_src(self) -> None:
        soup = BeautifulSoup('<img alt="no source"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    def test_handle_img_protocol_relative(self) -> None:
        soup = BeautifulSoup('<img src="//cdn.example.com/img.jpg"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("<img src='https://cdn.example.com/img.jpg'/>\n", result)

    def test_handle_img_data_src(self) -> None:
        soup = BeautifulSoup('<img data-src="pic.png"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("pic.png", result)

    def test_handle_img_data_original(self) -> None:
        soup = BeautifulSoup('<img data-original="/orig.png"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("orig.png", result)

    def test_handle_img_o_src(self) -> None:
        soup = BeautifulSoup('<img o_src="other.png"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("other.png", result)

    def test_handle_img_data_image(self) -> None:
        soup = BeautifulSoup('<img src="data:image/png;base64,abc"/>', "html.parser")
        el = soup.img
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("data:image/png;", result)

    # ── _handle_input: various cases ──

    def test_handle_input_origin_src_absolute_url(self) -> None:
        soup = BeautifulSoup('<input class="origin_src" value="https://img.com/pic.jpg"/>', "html.parser")
        el = soup.input
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("<img src='https://img.com/pic.jpg'/>\n", result)

    def test_handle_input_no_value(self) -> None:
        soup = BeautifulSoup('<input class="origin_src"/>', "html.parser")
        el = soup.input
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    # ── _handle_canvas: various cases ──

    def test_handle_canvas_no_data(self) -> None:
        soup = BeautifulSoup("<canvas></canvas>", "html.parser")
        el = soup.canvas
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    def test_handle_canvas_data_src(self) -> None:
        soup = BeautifulSoup('<canvas data-src="canvas.png" width="100"></canvas>', "html.parser")
        el = soup.canvas
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("canvas.png", result)
        self.assertIn("width='100'", result)

    # ── _handle_anchor: absolute href ──

    def test_handle_anchor_absolute(self) -> None:
        soup = BeautifulSoup('<a href="https://example.com/page">link</a>', "html.parser")
        el = soup.a
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("https://example.com/page", result)

    def test_handle_anchor_no_target(self) -> None:
        soup = BeautifulSoup('<a href="/path">click</a>', "html.parser")
        el = soup.a
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertNotIn("target", result)

    # ── _handle_iframe_embed: various ──

    def test_handle_iframe_swf(self) -> None:
        soup = BeautifulSoup('<iframe src="animation.swf"></iframe>', "html.parser")
        el = soup.iframe
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("animation.swf", result)
        self.assertIn("<a href=", result)

    def test_handle_embed_getCommonPlayer(self) -> None:
        soup = BeautifulSoup('<embed src="getCommonPlayer.nhn?vid=123"/>', "html.parser")
        el = soup.embed
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("getCommonPlayer.nhn", result)

    # ── _handle_param_object: non-flash param ──

    def test_handle_param_non_flash(self) -> None:
        soup = BeautifulSoup('<param name="quality" value="high"/>', "html.parser")
        el = soup.param
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    def test_handle_param_src_no_swf(self) -> None:
        soup = BeautifulSoup('<param name="Src" value="video.mp4"/>', "html.parser")
        el = soup.param
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    # ── _handle_map: area without alt ──

    def test_handle_map_area_no_alt(self) -> None:
        soup = BeautifulSoup('<map><area href="link.html"></area></map>', "html.parser")
        el = soup.map
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("empty link title", result)

    def test_handle_map_empty(self) -> None:
        soup = BeautifulSoup("<map></map>", "html.parser")
        el = soup.map
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertEqual("", result)

    # ── _sanitize ──

    def test_sanitize_br_in_alt(self) -> None:
        html_input = 'alt="line1<br>line2"'
        result = Extractor._sanitize(html_input)
        self.assertIn('alt="line1 line2"', result)

    def test_sanitize_control_chars(self) -> None:
        html_input = "hello\x01world\x08test"
        result = Extractor._sanitize(html_input)
        self.assertEqual("helloworldtest", result)

    def test_sanitize_xml_declaration(self) -> None:
        html_input = '<?xml version="1.0"?><html></html>'
        result = Extractor._sanitize(html_input)
        self.assertNotIn("<?xml", result)
        self.assertIn("<html>", result)

    def test_sanitize_br_replacement(self) -> None:
        html_input = "<p>line1<br>line2</p>"
        result = Extractor._sanitize(html_input)
        self.assertIn("<br/>", result)

    # ── _default_handler: skips bare newlines ──

    def test_default_handler_skips_bare_newlines(self) -> None:
        soup = BeautifulSoup("<section>\n<span>text</span>\n</section>", "html.parser")
        el = soup.section
        result = Extractor._traverse_element(el, dummy_url, "utf-8")
        self.assertIn("<section>", result)
        self.assertIn("text", result)

    # ── main function ──

    @patch("bin.extractor.sys")
    @patch("bin.extractor.Config")
    @patch("bin.extractor.Extractor.extract_content")
    @patch("bin.extractor.signal")
    @patch("bin.extractor.getopt.getopt")
    def test_main_no_args(self, mock_getopt: MagicMock, mock_signal: MagicMock, mock_extract: MagicMock, mock_config: MagicMock, mock_sys: MagicMock) -> None:
        """main() with no args should print usage and return -1."""
        mock_getopt.return_value = ([], [])
        mock_sys.argv = ["extractor.py"]
        result = main()
        self.assertEqual(-1, result)

    @patch("bin.extractor.sys")
    @patch("bin.extractor.Config")
    @patch("bin.extractor.Extractor.extract_content")
    @patch("bin.extractor.signal")
    @patch("bin.extractor.getopt.getopt")
    def test_main_with_url_success(self, mock_getopt: MagicMock, mock_signal: MagicMock, mock_extract: MagicMock, mock_config: MagicMock, mock_sys: MagicMock) -> None:
        """main() with url arg and successful extraction should return 0."""
        mock_getopt.return_value = ([], ["https://example.com/page"])
        mock_sys.argv = ["extractor.py", "https://example.com/page"]
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get_extraction_configs.return_value = {"element_class_list": ["c"]}
        mock_extract.return_value = "extracted content"

        result = main()
        self.assertEqual(0, result)
        mock_extract.assert_called_once()

    @patch("bin.extractor.sys")
    @patch("bin.extractor.Config")
    @patch("bin.extractor.Extractor.extract_content")
    @patch("bin.extractor.signal")
    @patch("bin.extractor.getopt.getopt")
    def test_main_with_url_no_result(self, mock_getopt: MagicMock, mock_signal: MagicMock, mock_extract: MagicMock, mock_config: MagicMock, mock_sys: MagicMock) -> None:
        """main() with url arg but no extraction result should return -1."""
        mock_getopt.return_value = ([], ["https://example.com/page"])
        mock_sys.argv = ["extractor.py", "https://example.com/page"]
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get_extraction_configs.return_value = {"element_class_list": ["c"]}
        mock_extract.return_value = None

        result = main()
        self.assertEqual(-1, result)

    @patch("bin.extractor.sys")
    @patch("bin.extractor.Config")
    @patch("bin.extractor.Extractor.extract_content")
    @patch("bin.extractor.signal")
    @patch("bin.extractor.getopt.getopt")
    def test_main_with_f_option(self, mock_getopt: MagicMock, mock_signal: MagicMock, mock_extract: MagicMock, mock_config: MagicMock, mock_sys: MagicMock) -> None:
        """main() with -f option should use specified feed directory."""
        mock_getopt.return_value = ([("-f", "/custom/path")], ["https://example.com"])
        mock_sys.argv = ["extractor.py", "-f", "/custom/path", "https://example.com"]
        mock_config_instance = MagicMock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.get_extraction_configs.return_value = {"element_class_list": []}
        mock_extract.return_value = "content"

        result = main()
        self.assertEqual(0, result)
        mock_config.assert_called_once_with(feed_dir_path=Path("/custom/path"))

    # ── extract_content: id_list selector ──

    def test_extract_content_by_id(self) -> None:
        conf = {"element_class_list": [], "element_id_list": ["main-content"], "element_path_list": [], "encoding": "utf-8"}
        html_input = '<html><body><div id="main-content">id content</div></body></html>'
        result = Extractor.extract_content(conf, dummy_url, input_data=html_input)
        self.assertIsNotNone(result)
        self.assertIn("id content", result)

    # ── _extract_image_src: priority order ──

    def test_extract_image_src_lazy_src(self) -> None:
        soup = BeautifulSoup('<img lazy-src="lazy.jpg" src="fallback.jpg"/>', "html.parser")
        el = soup.img
        result = Extractor._extract_image_src(el, dummy_url, "utf-8")
        self.assertIn("lazy.jpg", result)

    def test_extract_image_src_none(self) -> None:
        soup = BeautifulSoup('<img alt="nothing"/>', "html.parser")
        el = soup.img
        result = Extractor._extract_image_src(el, dummy_url, "utf-8")
        self.assertIsNone(result)

    # ── _handle_pre ──

    def test_handle_pre_with_code(self) -> None:
        soup = BeautifulSoup("<pre><code>x = 1</code></pre>", "html.parser")
        el = soup.pre
        result = Extractor._handle_pre(el, dummy_url, "utf-8")
        self.assertIn("<pre>", result)
        self.assertIn("x = 1", result)


if __name__ == "__main__":
    unittest.main()
