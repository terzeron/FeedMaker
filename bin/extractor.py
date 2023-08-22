#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import sys
import signal
import html
import getopt
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from bs4.element import Comment
from bin.feed_maker_util import Config, URL, HTMLExtractor, header_str

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Extractor:
    def extract_content(self, extraction_conf: Dict[str, Any], item_url: str, input_data: str = "") -> Optional[str]:
        LOGGER.debug(f"# extract_content(extraction_conf={extraction_conf}, item_url={item_url})")

        # configuration
        if not extraction_conf:
            LOGGER.error("Error: Can't get extraction configuration")
            return None

        # read html contents
        if input_data:
            html_content = input_data
        else:
            html_content = sys.stdin.read()

        if extraction_conf:
            class_list = extraction_conf["element_class_list"]
            id_list = extraction_conf["element_id_list"]
            path_list = extraction_conf["element_path_list"]
            encoding = extraction_conf["encoding"]
            LOGGER.debug(f"# element_id: {id_list}")
            LOGGER.debug(f"# element_class: {class_list}")
            LOGGER.debug(f"# element_path: {path_list}")
            LOGGER.debug(f"# encoding: {encoding}")
        else:
            return html_content

        # sanitize
        html_content = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html_content)
        html_content = re.sub(r'<br>', '<br/>', html_content)
        html_content = re.sub(r'[\x01\x08]', '', html_content, re.LOCALE)
        html_content = re.sub(r'<\?xml[^>]+>', r'', html_content)

        result: str = ""
        # header
        if html_content:
            result += header_str + "\n"

        # main article sections
        for parser in ("html.parser", "html5lib", "lxml"):
            soup = BeautifulSoup(html_content, parser)

            for class_str in class_list:
                divs = soup.find_all(attrs={"class": class_str})
                if divs:
                    for div in divs:
                        result += self._traverse_element(div, item_url, encoding)
            for id_str in id_list:
                divs = soup.find_all(attrs={"id": id_str})
                if divs:
                    for div in divs:
                        result += self._traverse_element(div, item_url, encoding)
            for path_str in path_list:
                divs = HTMLExtractor.get_node_with_path(soup.body, path_str)
                if divs:
                    for div in divs:
                        result += self._traverse_element(div, item_url, encoding)

            # if any, exit this loop
            if result:
                break

        if class_list and id_list and path_list:
            result += self._traverse_element(soup.body, item_url, encoding)

        return result

    @staticmethod
    def _check_element_class(element, element_name, class_name) -> bool:
        if element.name == element_name and element.has_attr("class") and class_name in element["class"]:
            return True
        return False

    def _traverse_element(self, element, url: str, encoding: str) -> str:
        result: str = ""

        if isinstance(element, Comment):
            # if comments, skip sub-elements
            return result
        if not hasattr(element, 'name') or not element.name:
            # text or self-close element (<br/>)
            if not re.compile(r'^(\s*|html)$').match(str(element)):
                # neither blank text nor <!DOCTYPE html>
                try:
                    result += html.escape(str(element))
                except UnicodeEncodeError:
                    # try to print word-by-word
                    for word in str(element).split(' '):
                        try:
                            result += " " + html.escape(word)
                        except UnicodeEncodeError:
                            return ""
            return result

        # element

        # 원칙
        # 모든 element는 그 안에 다른 element나 text를 포함한다.
        # 그러므로 open tag를 써주고 그 다음에 recursive call로 처리하고
        # close tag를 써주면 된다.
        #
        # 예외 처리
        # 이미지는 src attribute를 써줘야 함, 뒤에 <br/>을 덧붙여야 함
        # naver.net을 포함하고 /17.jpg로 끝나는 이미지 경로는 제거해야 함
        # 테이블 관련 태그는 모두 무시?
        # 자바스크립트?
        # flash?

        open_close_tag = False
        attribute_str = ""
        if element.has_attr("style"):
            # 스타일 속성을 이용하여 요소를 보이지 않게 처리한 경우에는 하위 요소를 삭제함
            m = re.search(r'(?P<style>display\s*:\s*none|visibility\s*:\s*hidden)', element["style"])
            if m:
                # skip sub-elements
                return result

        if element.name == "p":
            result += f"<p{attribute_str}>\n"
            for e in element.contents:
                result += self._traverse_element(e, url, encoding)
            # 하위 노드를 처리하고 return하지 않으면, 텍스트를 직접
            # 감싸고 있는 <p>의 경우, 중복된 내용이 노출될 수 있음
            result += "</p>\n"
            return result

        if element.name == "img":
            src = ""
            extra_attributes = ["data-lazy-src", "lazy-src", "lazysrc", "data-src", "data-original", "o_src"]
            for extra_attribute in extra_attributes:
                if element.has_attr(extra_attribute):
                    extra_src = element[extra_attribute]
                    if extra_src:
                        if not re.search(r'((https?:)?//|data:image/png;)', extra_src):
                            extra_src = URL.concatenate_url(url, extra_src)
                        src = extra_src

            # src 속성이 data-lazy-src보다 나중에 결정되어야 함
            if not src and element.has_attr("src"):
                src = element["src"]
                if src and not re.search(r'((https?:)?//|data:image/png;)', src):
                    src = URL.concatenate_url(url, src)

            if src:
                if re.search(r'^//', src):
                    src = re.sub(r'^//', 'https://', src)
                if element.has_attr("width"):
                    width = element["width"]
                    attribute_str += f" width='{width}'"
                result += f"<img src='{src}'{attribute_str}/>\n"
        elif element.name == "input":
            if self._check_element_class(element, "input", "origin_src") and element.has_attr("value"):
                value = element["value"]
                if not re.search(r'(https?:)?//', value):
                    value = URL.concatenate_url(url, value)
                result += f"<img src='{value}'{attribute_str}/>\n"
        elif element.name == "canvas":
            src = ""
            if element.has_attr("data-original"):
                src = element["data-original"]
            elif element.has_attr("data-src"):
                src = element["data-src"]
            if src:
                if element.has_attr("width"):
                    width = element["width"]
                    attribute_str += f" width='{width}'"
                result += f"<img src='{src}'{attribute_str}/>\n"
        elif element.name == "a":
            if element.has_attr("href"):
                # complementing href value
                href = element["href"]
                if not re.search(r'(https?:)?//', href):
                    href = URL.concatenate_url(url, href)
                # A tag는 href와 target attribute를 출력해줘야 함
                if element.has_attr("target"):
                    target = element["target"]
                    attribute_str += f" target='{target}'"
                result += f"<a href='{href}'{attribute_str}>"
                open_close_tag = True
        elif element.name in ("iframe", "embed"):
            if element.has_attr("src"):
                src = element["src"]
                if "video_player.nhn" in src or ".swf" in src or "getCommonPlayer.nhn" in src:
                    # flash 파일은 [IFRAME with Flash]라고 표시
                    result += f"<{element.name} src='{src}'></{element.name}><br/>\n"
                    result += f"<a href='{src}'>{src}</a><br/>\n"
                else:
                    result += str(element)
            elif element.name in ("param", "object"):
                if element.has_attr("name") and element["name"] == "Src" and element.has_attr("value") and ".swf" in \
                        element["value"]:
                    src = element["value"]
                    result += f"<video src='{src}'></video><br/>\n"
                    result += f"<a href='{src}'>{src}</a><br/>\n"
            elif element.name == "map":
                # image map
                # extract only link information from area element
                for child in element.contents:
                    if hasattr(child, "name") and child.name == "area":
                        link_href = "#"
                        link_title = "empty link title"
                        if child.has_attr("href"):
                            link_href = child["href"]
                        if child.has_attr("alt"):
                            link_title = child["alt"]
                        result += f"<br/><br/><strong><a href='{link_href}'>{link_title}</a></strong><br/><br/>\n"
                    elif element.name in ("o:p", "st1:time"):
                        # skip unknown element
                        return result
        elif element.name in ("v:shapetype", "qksdmssnfl", "qksdmssnfl<span"):
            # skip malformed element
            return result
        elif element.name in ("script", "style", "st1:personname"):
            # skip sub-elements
            return result
        elif element.name == "pre":
            # preserve all white spaces as they are
            result += str(element) + "\n"
            # skip sub-elementss
            return result
        else:
            result += f"<{element.name}{attribute_str}>\n"
            open_close_tag = True

        if hasattr(element, 'contents'):
            for e in element.contents:
                if e != "\n":
                    result += self._traverse_element(e, url, encoding)
        elif isinstance(element, Comment):
            return result
        else:
            result += element
            return result

        if open_close_tag:
            result += f"</{element.name}>\n"

        return result


def print_usage() -> None:
    print(f"_usage:\t{sys.argv[0]}\t[ <option> ] <file or url>")
    print()


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path: Path = Path.cwd()

    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if len(args) < 1:
        print_usage()
        return -1

    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    config = Config(feed_dir_path=feed_dir_path)
    if not config:
        LOGGER.error("Error: Can't get configuration")
        return -1
    extraction_conf = config.get_extraction_configs()

    extractor = Extractor()
    result = extractor.extract_content(extraction_conf, args[0])
    del extractor
    if result:
        print(result)
        return 0
    return -1


if __name__ == "__main__":
    sys.exit(main())
