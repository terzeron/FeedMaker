#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import signal
import html
import logging
import logging.config
from bs4 import BeautifulSoup, Comment
from feed_maker_util import Config, URL, IO, HTMLExtractor, header_str


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
# recursion으로 구현된 traverse_element()의 여러 레벨에서 조회하는 변수
footnote_num = 0


def print_header() -> None:
    print(header_str)


def print_trailer() -> None:
    pass


def extract_content(args) -> bool:
    LOGGER.debug("# extract_content(args=%r)", args)
    item_url = args[0]
    file = ""
    if len(args) > 1:
        file = args[1]

    # configuration
    config = Config()
    if not config:
        LOGGER.error("can't read configuration")
        sys.exit(-1)
    extraction_conf = config.get_extraction_configs()

    # read html contents
    html_content = IO.read_file(file)

    if extraction_conf:
        class_list = extraction_conf["element_class_list"]
        id_list = extraction_conf["element_id_list"]
        path_list = extraction_conf["element_path_list"]
        encoding = extraction_conf["encoding"]
        LOGGER.debug("# element_id: %s", id_list)
        LOGGER.debug("# element_class: %s", class_list)
        LOGGER.debug("# element_path: %s", path_list)
        LOGGER.debug("# encoding: %s", encoding)
    else:
        print(html_content, end='')
        return True

    # sanitize
    html_content = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html_content)
    html_content = re.sub(r'<br>', '<br/>', html_content)
    html_content = re.sub(r'[\x01\x08]', '', html_content, re.LOCALE)
    html_content = re.sub(r'<\?xml[^>]+>', r'', html_content)
    # html = re.sub(r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/', r'', html)

    # header
    if html_content:
        print_header()

    # main article sections
    ret = True
    for parser in ["html.parser", "html5lib", "lxml"]:
        soup = BeautifulSoup(html_content, parser)

        for class_str in class_list:
            divs = soup.find_all(attrs={"class": class_str})
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)
        for id_str in id_list:
            divs = soup.find_all(attrs={"id": id_str})
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)
        for path_str in path_list:
            divs = HTMLExtractor.get_node_with_path(soup.body, path_str)
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)

        # if any, exit this loop
        if ret:
            break

    if class_list and id_list and path_list:
        ret = traverse_element(soup.body, item_url, encoding)

    if html_content:
        print_trailer()

    return ret


def check_element_class(element, element_name, class_name) -> bool:
    if element.name == element_name and element.has_attr("class") and class_name in element["class"]:
        return True
    return False


def traverse_element(element, url, encoding) -> bool:
    global footnote_num
    ret = False

    if isinstance(element, Comment):
        # if comments, skip sub-elements
        return ret
    if not hasattr(element, 'name') or not element.name:
        # text or self-close element (<br/>)
        p = re.compile(r"^\s*$")
        if not p.match(str(element)):
            # non-blank text
            try:
                sys.stdout.write("%s" % html.escape(str(element)))
            except UnicodeEncodeError:
                # try to print word-by-word
                for word in str(element).split(' '):
                    try:
                        sys.stdout.write(" %s" % html.escape(word))
                    except UnicodeEncodeError:
                        sys.stdout.write(" ****")
        ret = True
        return ret

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
            return ret
    if element.name == "p":
        print("<p%s>" % attribute_str)
        for e in element.contents:
            traverse_element(e, url, encoding)
        # 하위 노드를 처리하고 return하지 않으면, 텍스트를 직접
        # 감싸고 있는 <p>의 경우, 중복된 내용이 노출될 수 있음
        print("</p>")
        return True
    elif element.name == "img":
        src = ""
        if element.has_attr("data-lazy-src"):
            data_lazy_src = element["data-lazy-src"]
            if data_lazy_src:
                if not re.search(r'((https?:)?//|data:image/png;)', data_lazy_src):
                    data_lazy_src = URL.concatenate_url(url, data_lazy_src)
                src = data_lazy_src
        elif element.has_attr("lazy-src"):
            lazy_src = element["lazy-src"]
            if lazy_src:
                if not re.search(r'((https?:)?//|data:image/png;)', lazy_src):
                    lazy_src = URL.concatenate_url(url, lazy_src)
                src = lazy_src
        elif element.has_attr("lazysrc"):
            lazy_src = element["lazysrc"]
            if lazy_src:
                if not re.search(r'((https?:)?//|data:image/png;)', lazy_src):
                    lazy_src = URL.concatenate_url(url, lazy_src)
                src = lazy_src
        elif element.has_attr("data-src"):
            data_src = element["data-src"]
            if data_src:
                if not re.search(r'((https?:)?//|data:image/png;)', data_src):
                    data_src = URL.concatenate_url(url, data_src)
                src = data_src
        elif element.has_attr("data-original"):
            data_src = element["data-original"]
            if data_src:
                if not re.search(r'((https?:)?//|data:image/png;)', data_src):
                    data_src = URL.concatenate_url(url, data_src)
                src = data_src

        # src 속성이 data-lazy-src보다 나중에 결정되어야 함
        if not src:
            if element.has_attr("src"):
                src = element["src"]
                if src:
                    if not re.search(r'((https?:)?//|data:image/png;)', src):
                        src = URL.concatenate_url(url, src)

        if src:
            if re.search(r'^//', src):
                src = re.sub(r'^//', 'http://', src)
            if element.has_attr("width"):
                attribute_str += " width='%s'" % element["width"]
            print("<img src='%s'%s/>" % (src, attribute_str))
        ret = True
    elif element.name in ["input"]:
        if check_element_class(element, "input", "origin_src"):
            if element.has_attr("value"):
                value = element["value"]
                if not re.search(r'(https?:)?//', value):
                    value = URL.concatenate_url(url, value)
                print("<img src='%s'%s/>" % (value, attribute_str))
                ret = True
    elif element.name == "canvas":
        src = ""
        if element.has_attr("data-original"):
            src = element["data-original"]
        elif element.has_attr("data-src"):
            src = element["data-src"]
        if src:
            if element.has_attr("width"):
                attribute_str += " width='%s'" % element["width"]
            print("<img src='%s'%s/>" % (src, attribute_str))
            ret = True
    elif element.name == "a":
        if element.has_attr("onclick"):
            # 주석레이어 제거
            m = re.search(r"(open|close)FootnoteLayer\('(\d+)'", element["onclick"])
            if m:
                open_or_close = m.group(1)
                if open_or_close == "open":
                    footnote_num = m.group(2)
                return ret
        if element.has_attr("href"):
            # complementing href value
            href = element["href"]
            if not re.search(r'(https?:)?//', href):
                href = URL.concatenate_url(url, href)
            # A tag는 href와 target attribute를 출력해줘야 함
            if element.has_attr("target"):
                attribute_str += " target='%s'" % element["target"]
            print("<a href='%s'%s>" % (href, attribute_str), end='')
            ret = True
            open_close_tag = True
    elif element.name in ["iframe", "embed"]:
        if element.has_attr("src"):
            src = element["src"]
            if "video_player.nhn" in src or ".swf" in src or "getCommonPlayer.nhn" in src:
                # flash 파일은 [IFRAME with Flash]라고 표시
                print("<%s src='%s'></%s><br/>" % (element.name, src, element.name))
                print("<a href='%s'>%s</a><br/>" % (src, src))
            else:
                print(str(element))
            ret = True
    elif element.name in ["param", "object"]:
        if element.has_attr("name") and element["name"] == "Src" and element.has_attr("value") and ".swf" in \
                element["value"]:
            src = element["value"]
            print("<video src='%s'></video><br/>" % src)
            print("<a href='%s'>%s</a><br/>" % (src, src))
        ret = True
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
                print("<br/><br/><strong><a href='%s'>%s</a></strong><br/><br/>" % (link_href, link_title))
                ret = True
            elif element.name in ["o:p", "st1:time"]:
                # skip unknown element
                return ret
    elif element.name in ["script"]:
        # skip sub-elements
        return ret
    elif element.name in ["v:shapetype", "qksdmssnfl", "qksdmssnfl<span"]:
        # skip malformed element
        return ret
    elif element.name in ["style", "st1:personname", "script"]:
        # skip sub-elements
        return ret
    elif element.name in ["xmp", "form"]:
        ret = True
    elif element.name in ["pre"]:
        # preserve all white spaces as they are
        print(str(element))
        # skip sub-elementss
        return True
    else:
        print("<%s%s>" % (element.name, attribute_str))
        open_close_tag = True
        ret = True

    if hasattr(element, 'contents'):
        for e in element.contents:
            if e != "\n":
                ret = traverse_element(e, url, encoding)
    elif isinstance(element, Comment):
        return ret
    else:
        sys.stdout.write(element)
        ret = True
        return ret

    if open_close_tag:
        print("</%s>" % element.name)
        ret = True

    return ret


def print_usage() -> None:
    print("_usage:\t%s\t[ <option> ] <file or url> <html file>" % sys.argv[0])
    print()


if __name__ == "__main__":
    if len(sys.argv) < 1:
        print_usage()
        sys.exit(-1)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if extract_content(sys.argv[1:]):
        sys.exit(0)
    sys.exit(-1)
