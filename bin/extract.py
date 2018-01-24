#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup, Comment
import re
import os
import sys
import signal
import cgi
import getopt
import feedmakerutil
from feedmakerutil import die, err, warn


# recursion으로 구현된 traverse_element()의 여러 레벨에서 조회하는 변수
footnote_num = 0
    
def print_header():
    print("<meta http-equiv='_content-Type' content='text/html; charset=UTF-8'/>")
    print('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=2.0, minimum-scal#e=0.5, user-scalable=yes" />')
    print("<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; }</style>")
    print("")


def print_trailer():
    None


def extract_content(args):
    item_url = args[0]
    file = ""
    if len(args) > 1:
        file = args[1]
        
    # configuration
    config = feedmakerutil.read_config()
    if config == None:
        return -1
    extraction_conf = feedmakerutil.get_config_node(config, "extraction")

    # read html contents
    html = feedmakerutil.read_file(file)

    if extraction_conf:
        element_list = feedmakerutil.get_config_node(extraction_conf, "element_list")
        if not element_list:
            die("can't find 'element_list' element from configuration")
        class_list = feedmakerutil.get_all_config_values(element_list, "element_class")
        id_list = feedmakerutil.get_all_config_values(element_list, "element_id")
        path_list = feedmakerutil.get_all_config_values(element_list, "element_path")

        encoding = feedmakerutil.get_config_value(element_list, "encoding")

        if not encoding:
            encoding = "utf8"
        #print("# element_id:", id_list)
        #print("# element_class:", class_list)
        #print("# element_path:", path_list)
        #print("# encoding:", encoding)
    else:
        print(html, end='')
        return True
    
    # sanitize
    html = re.sub(r'alt="(.*)<br>(.*)"', r'alt="\1 \2"', html)
    html = re.sub(r'<br>', '<br/>', html)
    html = re.sub(r'[\x01\x08]', '', html, re.LOCALE)
    html = re.sub(r'<\?xml[^>]+>', r'', html)
    #html = re.sub(r'/\*([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*\*+/', r'', html)

    # header
    if html:
        print_header()
    
    # main article sections
    ret = 0
    for parser in [ "html.parser", "html5lib", "lxml" ]:
        soup = BeautifulSoup(html, parser)
        '''
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        '''

        for a_class in class_list:
            divs = soup.find_all(attrs={"class": a_class})
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)
        for id in id_list:
            divs = soup.find_all(attrs={"id": id})
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)
        for path in path_list:
            divs = feedmakerutil.get_node_with_path(soup.body, path)
            if divs:
                for div in divs:
                    ret = traverse_element(div, item_url, encoding)
        if ret > 0:
            break
                
    if (class_list == None or class_list == []) and (id_list == None or id_list == []) and (path_list == None or path_list == []):
        ret = traverse_element(soup.body, item_url, encoding)

    if html:
        print_trailer()
        
    return True


def check_element_class(element, element_name, class_name):
    if element.name == element_name and element.has_attr("class") and class_name in element["class"]:
        return True
    return False


def traverse_element(element, url, encoding):
    global footnote_num
    ret = -1
    
    #print("# traverse_element()")
    if isinstance(element, Comment):
        # skip sub-elements
        return ret
    elif not hasattr(element, 'name') or element.name == None:
        # text or self-close element (<br/>)
        p = re.compile("^\s*$")
        if not p.match(str(element)):
            sys.stdout.write("%s" % cgi.escape(str(element)))
        ret = 1
        return ret
    else: 
        # element
        #print("#%s#" % element.name)

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
        if element.name == "p":
            print("<p>")
            for e in element.contents:
                ret = traverse_element(e, url, encoding)
            # 하위 노드를 처리하고 return하지 않으면, 텍스트를 직접 
            # 감싸고 있는 <p>의 경우, 중복된 내용이 노출될 수 있음
            print("</p>")
            ret = 1
            return ret
        elif element.name == "img":
            src = ""
            if element.has_attr("data-lazy-src"):
                data_lazy_src = element["data-lazy-src"]
                if not re.search(r'(https?:)?//', data_lazy_src):
                    data_lazy_src = feedmakerutil.concatenate_url(url, data_lazy_src)
                src = data_lazy_src
            elif element.has_attr("lazysrc"):
                lazy_src = element["lazysrc"]
                if not re.search(r'(https?:)?//', lazy_src):
                    lazy_src = feedmakerutil.concatenate_url(url, lazy_src)
                src = lazy_src
            elif element.has_attr("data-src"):
                data_src = element["data-src"]
                if not re.search(r'(https?:)?//', data_src):
                    data_src = feedmakerutil.concatenate_url(url, data_src)
                src = data_src
            elif element.has_attr("data-original"):
                data_src = element["data-original"]
                if not re.search(r'(https?:)?//', data_src):
                    data_src = feedmakerutil.concatenate_url(url, data_src)
                src = data_src
            elif element.has_attr("src"):
                src = element["src"]
                if not re.search(r'(https?:)?//', src):
                    src = feedmakerutil.concatenate_url(url, src)
                if "ncc.phinf.naver.net" in src and ("/17.jpg" in src or "/8_17px.jpg" in src or "/7px.jpg" in src or "/20px.jpg" in src):
                    # 외부에서 접근 불가능한 이미지 제거
                    return ret
            if src and src != "":
                if re.search(r'^//', src):
                    src = re.sub(r'^//', 'http://', src)
                sys.stdout.write("<img src='%s'" % src)
            if element.has_attr("width"):
                sys.stdout.write(" width='%s'" % element["width"])
            sys.stdout.write("/>\n")
            ret = 1
        elif element.name in ("input"):
            if check_element_class(element, "input", "origin_src"):
                if element.has_attr("value"):
                    value = element["value"]
                    if not re.search(r'(https?:)?//', value):
                        value = feedmakerutil.concatenate_url(url, value)
                    sys.stdout.write("<img src='%s'/>\n" % value)
                    ret = 1
        elif element.name == "canvas":
            src = ""
            if element.has_attr("data-original"):
                src = element["data-original"]
            elif element.has_attr("data-src"):
                src = element["data-src"]
            if src and src != "":
                sys.stdout.write("<img src='%s'" % src)
                if element.has_attr("width"):
                    sys.stdout.write(" width='%s'" % element["width"])
                sys.stdout.write("/>\n")
                ret = 1
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
                    href = feedmakerutil.concatenate_url(url, href)
                # A tag는 href와 target attribute를 출력해줘야 함
                sys.stdout.write("<a href='%s'" % href)
                if element.has_attr("target"):
                    sys.stdout.write(" target='%s'>\n" % element["target"])
                else:
                    sys.stdout.write(">")
                ret = 1
                open_close_tag = True
        elif element.name in ("iframe", "embed"):
            if element.has_attr("src"):
                src = element["src"]
                if "video_player.nhn" in src or ".swf" in src or "getCommonPlayer.nhn" in src:
                    # flash 파일은 [IFRAME with Flash]라고 표시
                    print("[Flash Player]<br/>")
                    print("<%s src='%s'></%s><br/>" % (element.name, src, element.name))
                    print("<a href='%s'>%s</a><br/>" % (src, src))
                else:
                    sys.stdout.write("%s\n" % str(element))
                ret = 1
        elif element.name in ("param", "object"):
            if element.has_attr("name") and element["name"] == "Src" and element.has_attr("value") and ".swf" in element["value"]:
                src = element["value"]
                print("[Flash Player]<br/>")
                print("<video src='%s'></video><br/>" % (src))
                print("<a href='%s'>%s</a><br/>" % (src, src))
            ret = 1
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
                    ret = 1
                elif element.name in ("o:p", "st1:time"):
                    # skip unknown element 
                    return ret
        elif element.name in ("script"):
            # skip sub-element
            return ret
        elif element.name in ("v:shapetype", "qksdmssnfl", "qksdmssnfl<span"):
            # skip malformed element
            return ret
        elif element.name in ("style", "st1:personname", "script"):
            # skip sub-elements
            return ret
        elif element.name in ("xmp", "form"):
            ret = 1
        else:
            if check_element_class(element, "div", "paginate_v1"):
                # <div class="paginate_v1">...
                # ajax로 받아오는 페이지들을 미리 요청
                matches = re.findall(r"change_page\('[^']+/literature_module/(\d+)/literature_(\d+)_(\d+)\.html'", str(element))
                for match in matches:
                    leaf_id = int(match[0])
                    article_num = int(match[1])
                    page_num = int(match[2])
                    url = "http://navercast.naver.com/ncc_request.nhn?url=http://data.navercast.naver.com/literature_module/%d/literature_%d_%d.html" % (leaf_id, article_num, page_num)
                    cmd = "crawler.sh '%s' | extract_literature.py" % (url)
                    #print(cmd)
                    result = feedmakerutil.exec_cmd(cmd)
                    if result:
                        print(result)
                    ret = 1
                return ret
            elif check_element_class(element, "div", "view_option option_top"):
                # "오늘의 문학"에서 폰트크기와 책갈피 이미지 영역 제거
                return ret
            elif check_element_class(element, "span", "page_prev") or check_element_class(element, "span", "page_next"):
                # <span class="page_prev">... or <span class="page_next">...
                # 이전/다음 페이지 화살표 링크 영역 제거
                return ret
            elif check_element_class(element, "dl", "designlist"):
                # <dl class="designlist">...
                # skip this element and sub-elements
                return ret
            elif check_element_class(element, "div", "na_ly_cmt"):
                # <a onclick="openFootnoteLayer('번호'...)의 번호와 비교
                if hasattr(element, "id"):
                    if element["id"] != "footnoteLayer" + str(footnote_num):
                        return ret
                    #else:
                        #print str(element)
            else:               
                sys.stdout.write("<%s>\n" % element.name)
                open_close_tag = True
                ret = 1

        if hasattr(element, 'contents'):
            for e in element.contents:
                if e == "\n":
                    continue
                else:
                    ret = traverse_element(e, url, encoding)
        elif isinstance(element, Comment):
            return ret
        else:
            sys.stdout.write(element)
            ret = 1
            return ret

        if open_close_tag == True:
            sys.stdout.write("</%s>\n" % element.name)
            ret = 1

    return ret


def print_usage(program_name):
    print("_usage:\t%s\t[ <option> ] <file or url> <html file>" % program_name)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 1:
        print_usage()
        sys.exit(-1)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    extract_content(sys.argv[1:])

