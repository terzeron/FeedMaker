#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import logging.config
from pathlib import Path
from bs4 import BeautifulSoup, Comment

from bin.extractor import Extractor
from bin.feed_maker_util import Config, header_str

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


if __name__ == "__main__":
    unittest.main()
