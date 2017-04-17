#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup, Comment
import re
import subprocess
import os
import sys
import urllib.request, urllib.parse, urllib.error
import copy
import signal
import cgi
import feedmakerutil
from feedmakerutil import die, err, warn


# recursion으로 구현된 traverseElement()의 여러 레벨에서 조회하는 변수
footnoteNum = 0
    
def printHeader():
    print("<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'/>")
    print('<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=2.0, minimum-scal#e=0.5, user-scalable=yes" />')
    print("<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; }</style>")


def printTrailer():
    print("<p/>")


def extractContent(args):
    itemUrl = args[0]
    file = ""
    if len(args) > 1:
        file = args[1]

    # configuration
    config = feedmakerutil.readConfig()
    if config == None:
        return -1
    extraction = feedmakerutil.getConfigNode(config, "extraction")

    # read html contents
    html = feedmakerutil.readFile(file)

    if extraction != None:
        elementList = feedmakerutil.getConfigNode(extraction, "element_list")
        if elementList == None:
            die("can't find 'element_list' element from configuration")
        classList = feedmakerutil.getAllConfigValues(elementList, "element_class")
        idList = feedmakerutil.getAllConfigValues(elementList, "element_id")
        pathList = feedmakerutil.getAllConfigValues(elementList, "element_path")

        encoding = feedmakerutil.getConfigValue(elementList, "encoding")

        if encoding == None or encoding == "":
            encoding = "utf8"
        #print("# element_id:", idList)
        #print("# element_class:", classList)
        #print("# element_path:", pathList)
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
    #printHeader()

    # main article sections
    ret = 0
    for parser in [ "html.parser", "html5lib", "lxml" ]:
        soup = BeautifulSoup(html, parser)
        '''
        comments = soup.findAll(text=lambda text: isinstance(text, Comment))
        for comment in comments:
            comment.extract()
        '''

        for aClass in classList:
            divs = soup.find_all(attrs={"class": aClass})
            if divs:
                for div in divs:
                    ret = traverseElement(div, itemUrl, encoding)
        for anId in idList:
            divs = soup.find_all(attrs={"id": anId})
            if divs:
                for div in divs:
                    ret = traverseElement(div, itemUrl, encoding)
        for anPath in pathList:
            divs = feedmakerutil.getNodeWithPath(soup.body, anPath)
            if divs:
                for div in divs:
                    ret = traverseElement(div, itemUrl, encoding)
        if ret > 0:
            break
                
    if (classList == None or classList == []) and (idList == None or idList == []) and (pathList == None or pathList == []):
        ret = traverseElement(soup.body, itemUrl, encoding)

    # trailer
    #printTrailer()

    return True


def checkElementClass(element, elementName, className):
    if element.name == elementName and element.has_attr("class") and className in element["class"]:
        return True
    return False


def traverseElement(element, url, encoding):
    global footnoteNum
    ret = -1
    
    #print("# traverseElement()")
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

        openCloseTag = False
        if element.name == "p":
            print("<p>")
            for e in element.contents:
                ret = traverseElement(e, url, encoding)
            # 하위 노드를 처리하고 return하지 않으면, 텍스트를 직접 
            # 감싸고 있는 <p>의 경우, 중복된 내용이 노출될 수 있음
            print("</p>")
            ret = 1
            return ret
        elif element.name == "img":
            src = ""
            if element.has_attr("data-lazy-src"):
                dataLazySrc = element["data-lazy-src"]
                if not re.search(r'(https?:)?//', dataLazySrc):
                    dataLazySrc = feedmakerutil.concatenateUrl(url, dataLazySrc)
                src = dataLazySrc
            elif element.has_attr("lazysrc"):
                lazySrc = element["lazysrc"]
                if not re.search(r'(https?:)?//', lazySrc):
                    lazySrc = feedmakerutil.concatenateUrl(url, lazySrc)
                src = lazySrc
            elif element.has_attr("data-src"):
                dataSrc = element["data-src"]
                if not re.search(r'(https?:)?//', dataSrc):
                    dataSrc = feedmakerutil.concatenateUrl(url, dataSrc)
                src = dataSrc
            elif element.has_attr("data-original"):
                dataSrc = element["data-original"]
                if not re.search(r'(https?:)?//', dataSrc):
                    dataSrc = feedmakerutil.concatenateUrl(url, dataSrc)
                src = dataSrc
            elif element.has_attr("src"):
                src = element["src"]
                if not re.search(r'(https?:)?//', src):
                    src = feedmakerutil.concatenateUrl(url, src)
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
            if checkElementClass(element, "input", "originSrc"):
                if element.has_attr("value"):
                    value = element["value"]
                    if not re.search(r'(https?:)?//', value):
                        value = feedmakerutil.concatenateUrl(url, value)
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
                    openOrClose = m.group(1)
                    if openOrClose == "open":
                        footnoteNum = m.group(2)
                    return ret
            if element.has_attr("href"):
                # complementing href value
                href = element["href"]
                if not re.search(r'(https?:)?//', href):
                    href = feedmakerutil.concatenateUrl(url, href)
                # A tag는 href와 target attribute를 출력해줘야 함
                sys.stdout.write("<a href='%s'" % href)
                if element.has_attr("target"):
                    sys.stdout.write(" target='%s'>\n" % element["target"])
                else:
                    sys.stdout.write(">")
                ret = 1
                openCloseTag = True
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
                    linkHref = "#"
                    linkTitle = "empty link title"
                    if child.has_attr("href"):
                        linkHref = child["href"]
                    if child.has_attr("alt"):
                        linkTitle = child["alt"]
                    print("<br/><br/><strong><a href='%s'>%s</a></strong><br/><br/>" % (linkHref, linkTitle))
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
            if checkElementClass(element, "div", "paginate_v1"):
                # <div class="paginate_v1">...
                # ajax로 받아오는 페이지들을 미리 요청
                matches = re.findall(r"change_page\('[^']+/literature_module/(\d+)/literature_(\d+)_(\d+)\.html'", str(element))
                for match in matches:
                    leafId = int(match[0])
                    articleNum = int(match[1])
                    pageNum = int(match[2])
                    url = "http://navercast.naver.com/ncc_request.nhn?url=http://data.navercast.naver.com/literature_module/%d/literature_%d_%d.html" % (leafId, articleNum, pageNum)
                    cmd = "wget.sh '%s' | extract_literature.py" % (url)
                    #print(cmd)
                    result = feedmakerutil.execCmd(cmd)
                    if result:
                        print(result)
                    ret = 1
                return ret
            elif checkElementClass(element, "div", "view_option option_top"):
                # "오늘의 문학"에서 폰트크기와 책갈피 이미지 영역 제거
                return ret
            elif checkElementClass(element, "span", "page_prev") or checkElementClass(element, "span", "page_next"):
                # <span class="page_prev">... or <span class="page_next">...
                # 이전/다음 페이지 화살표 링크 영역 제거
                return ret
            elif checkElementClass(element, "dl", "designlist"):
                # <dl class="designlist">...
                # skip this element and sub-elements
                return ret
            elif checkElementClass(element, "div", "na_ly_cmt"):
                # <a onclick="openFootnoteLayer('번호'...)의 번호와 비교
                if hasattr(element, "id"):
                    if element["id"] != "footnoteLayer" + str(footnoteNum):
                        return ret
                    #else:
                        #print str(element)
            else:               
                sys.stdout.write("<%s>\n" % element.name)
                openCloseTag = True
                ret = 1

        if hasattr(element, 'contents'):
            for e in element.contents:
                if e == "\n":
                    continue
                else:
                    ret = traverseElement(e, url, encoding)
        elif isinstance(element, Comment):
            return ret
        else:
            sys.stdout.write(element)
            ret = 1
            return ret

        if openCloseTag == True:
            sys.stdout.write("</%s>\n" % element.name)
            ret = 1

    return ret


def printUsage(programName):
    print("Usage:\t%s\t<file or url> <html file>" % programName)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        printUsage(sys.argv[0])
        sys.exit(-1)
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    extractContent(sys.argv[1:])
