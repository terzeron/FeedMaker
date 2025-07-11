#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import signal
import html
import getopt
import logging.config
from pathlib import Path
from typing import Any, Optional, Callable
from bs4 import BeautifulSoup, Comment, NavigableString, Tag
from bin.feed_maker_util import Config, URL, HTMLExtractor, header_str

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Extractor:
    @staticmethod
    def extract_content(extraction_conf: dict[str, Any], item_url: str, input_data: str = "") -> Optional[str]:
        if not extraction_conf:
            LOGGER.error("Error: Can't get extraction configuration")
            return None

        html_content = input_data or sys.stdin.read()
        class_list = extraction_conf.get("element_class_list", [])
        id_list = extraction_conf.get("element_id_list", [])
        path_list = extraction_conf.get("element_path_list", [])
        encoding = extraction_conf.get("encoding", "utf-8")

        html_content = Extractor._sanitize(html_content)
        result = header_str + "\n" if html_content else ""
        soup = None

        for parser in ("html.parser", "html5lib", "lxml"):
            soup = BeautifulSoup(html_content, parser)
            result += Extractor._extract_by_selectors(soup, class_list=class_list, id_list=id_list, path_list=path_list, url=item_url, encoding=encoding)
            if result.strip():
                break

        # if multiple selectors present, also traverse whole body
        if soup and class_list and id_list and path_list:
            result += Extractor._traverse_element(soup.body, item_url, encoding)

        return result

    @staticmethod
    def _sanitize(html_content: str) -> str:
        html_content = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html_content)
        html_content = html_content.replace('<br>', '<br/>')
        html_content = re.sub(r'[\x01\x08]', '', html_content)
        html_content = re.sub(r'<\?xml[^>]+>', '', html_content)
        return html_content

    @staticmethod
    def _extract_by_selectors(soup: BeautifulSoup, *, class_list: list[str], id_list: list[str], path_list: list[str], url: str, encoding: str) -> str:
        result = ""
        for cls in class_list:
            for el in soup.find_all(attrs={"class": cls}):
                result += Extractor._traverse_element(el, url, encoding)
        for _id in id_list:
            for el in soup.find_all(attrs={"id": _id}):
                result += Extractor._traverse_element(el, url, encoding)
        for path in path_list:
            if soup.body is not None and isinstance(soup.body, Tag):
                nodes: Optional[list[Tag]] = HTMLExtractor.get_node_with_path(soup.body, path)  
                for el in nodes or []:
                    result += Extractor._traverse_element(el, url, encoding)
        return result

    @staticmethod
    def _check_element_class(element: Tag, name: str, class_name: str) -> bool:
        classes = element.get("class", None)
        if classes is None:
            classes = []
        elif isinstance(classes, str):
            classes = [classes]
        return element.name == name and class_name in classes

    @staticmethod
    def _traverse_element(element: Any, url: str, encoding: str) -> str:
        if isinstance(element, Comment):
            return ""
        if isinstance(element, NavigableString) or not getattr(element, 'name', None):
            return Extractor._handle_text(element)

        if Extractor._is_hidden(element):
            return ""

        handler = Extractor._get_handler(element.name)
        return handler(element, url, encoding)

    @staticmethod
    def _handle_text(node: Any) -> str:
        text = str(node)
        if re.match(r'^(\s*|html)$', text):
            return ''
        try:
            return html.escape(text)
        except UnicodeEncodeError:
            escaped = ''
            for word in text.split(' '):
                try:
                    escaped += ' ' + html.escape(word)
                except UnicodeEncodeError:
                    return ''
            return escaped

    @staticmethod
    def _is_hidden(element: Tag) -> bool:
        style = str(element.get('style', ''))
        return bool(re.search(r'display\s*:\s*none|visibility\s*:\s*hidden', style))

    @staticmethod
    def _get_handler(tag: str) -> Callable[[Tag, str, str], str]:
        handlers: dict[str, Callable[[Tag, str, str], str]] = {
            'p': Extractor._handle_paragraph,
            'img': Extractor._handle_img,
            'input': Extractor._handle_input,
            'canvas': Extractor._handle_canvas,
            'a': Extractor._handle_anchor,
            'iframe': Extractor._handle_iframe_embed,
            'embed': Extractor._handle_iframe_embed,
            'param': Extractor._handle_param_object,
            'object': Extractor._handle_param_object,
            'map': Extractor._handle_map,
            'script': lambda _tag, _url, _encoding: '',
            'style': lambda _tag, _url, _encoding: '',
            'pre': Extractor._handle_pre
        }
        return handlers.get(tag, Extractor._default_handler)

    @staticmethod
    def _handle_paragraph(el: Tag, url: str, encoding: str) -> str:
        content = ''.join(Extractor._traverse_element(c, url, encoding) for c in el.contents)
        return f"<p>\n{content}</p>\n"

    @staticmethod
    def _handle_img(el: Tag, url: str, encoding: str) -> str:
        src = Extractor._extract_image_src(el, url, encoding)
        if not src:
            return ''
        width = el.get('width')
        attr = f" width='{width}'" if width else ''
        return f"<img src='{src}'{attr}/>\n"

    @staticmethod
    def _extract_image_src(el: Tag, url: str, _encoding: str) -> Optional[str]:
        for attr in ["data-lazy-src", "lazy-src", "lazysrc", "data-src", "data-original", "o_src"] + ['src']:
            if el.has_attr(attr):
                src = str(el[attr])
                if not re.search(r'(https?:)?//|data:image/png;', src):
                    src = URL.concatenate_url(url, src)
                if src.startswith('//'):
                    src = 'https:' + src
                return src
        return None

    @staticmethod
    def _handle_input(el: Tag, url: str, _encoding: str) -> str:
        if Extractor._check_element_class(el, 'input', 'origin_src') and el.has_attr('value'):
            val = str(el['value'])
            if not re.search(r'(https?:)?//', val):
                val = URL.concatenate_url(url, val)
            return f"<img src='{val}'/>\n"
        return ''

    @staticmethod
    def _handle_canvas(el: Tag, _url: str, _encoding: str) -> str:
        src = str(el.get('data-original') or el.get('data-src', ''))
        if not src:
            return ''
        width = el.get('width')
        attr = f" width='{width}'" if width else ''
        if src.startswith('//'):
            src = 'https:' + src
        return f"<img src='{src}'{attr}/>\n"

    @staticmethod
    def _handle_anchor(el: Tag, url: str, encoding: str) -> str:
        href = str(el.get('href', ''))
        if not re.search(r'(https?:)?//', href):
            href = URL.concatenate_url(url, href)
        target = el.get('target')
        attr = f" target='{target}'" if target else ''
        content = ''.join(Extractor._traverse_element(c, url, encoding) for c in el.contents)
        return f"<a href='{href}'{attr}>{content}</a>\n"

    @staticmethod
    def _handle_iframe_embed(el: Tag, _url: str, _encoding: str) -> str:
        src = str(el.get('src', ''))
        if any(x in src for x in ('video_player.nhn', '.swf', 'getCommonPlayer.nhn')):
            return (
                f"<{el.name} src='{src}'></{el.name}><br/>\n"
                f"<a href='{src}'>{src}</a><br/>\n"
            )
        return str(el)

    @staticmethod
    def _handle_param_object(el: Tag, _url: str, _encoding: str) -> str:
        if el.get('name') == 'Src' and '.swf' in str(el.get('value', '')):
            src = str(el['value'])
            return (
                f"<video src='{src}'></video><br/>\n"
                f"<a href='{src}'>{src}</a><br/>\n"
            )
        return ''

    @staticmethod
    def _handle_map(el: Tag, _url: str, _encoding: str) -> str:
        out = ''
        for child in el.contents:
            if isinstance(child, Tag) and child.name == 'area':
                href = child.get('href', '#')
                alt = child.get('alt', 'empty link title')
                out += f"<br/><br/><strong><a href='{href}'>{alt}</a></strong><br/><br/>\n"
        return out

    @staticmethod
    def _handle_pre(el: Tag, _url: str, _encoding: str) -> str:
        return str(el) + "\n"

    @staticmethod
    def _default_handler(el: Tag, url: str, encoding: str) -> str:
        open_tag = f"<{el.name}>\n"
        inner = ''.join(Extractor._traverse_element(c, url, encoding) for c in el.contents if not (isinstance(c, NavigableString) and str(c) == '\n'))
        close_tag = f"</{el.name}>\n"
        return open_tag + inner + close_tag


def main() -> int:
    LOGGER.debug("# main()")
    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    feed_dir_path = Path.cwd()
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if len(args) < 1:
        print(f"_usage:\t{sys.argv[0]}\t[ <option> ] <file or url>")
        return -1

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    config = Config(feed_dir_path=feed_dir_path)
    result = Extractor.extract_content(config.get_extraction_configs(), args[0])
    if result:
        print(result)
        return 0
    return -1


if __name__ == "__main__":
    sys.exit(main())
