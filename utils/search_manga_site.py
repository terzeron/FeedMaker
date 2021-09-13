#!/usr/bin/env python

import os
import sys
import json
import re
import getopt
import urllib
import logging
import logging.config
from typing import Dict, Tuple, List
from pathlib import Path
from bs4 import BeautifulSoup
from crawler import Crawler, Method
from feed_maker_util import URL, HTMLExtractor


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()

work_dir_path = Path(os.environ["FEED_MAKER_WORK_DIR"])
marumaru_site_config_file_path = work_dir_path / "marumaru" / "site_config.json"


def print_content(site_name: str, result_list: List[Tuple[str, str]]) -> None:
    print("--------------------- %s -------------------------" % site_name)
    for title, link in result_list:
        print("%s\t%s" % (title, link))
    print("-------------------------------------------------------")


def get_data_from_site(config, url_postfix, method=Method.GET, headers={}, data={}) -> str:
    LOGGER.debug("# get_data_from_site(config=%r, url_postfix=%s, method=%s, headers=%r, data=%r)", config, url_postfix, method, headers, data)
    url_prefix: str = URL.get_url_scheme(config["url"]) + "://" + URL.get_url_domain(config["url"])
    encoding: str = config["encoding"] if "encoding" in config else None
    render_js: bool = config["render_js"] if "render_js" in config else False
    c: Crawler = Crawler(render_js=render_js, method=method, headers=headers, encoding=encoding, timeout=240)
    url: str = url_prefix + url_postfix
    response, _ = c.run(url=url, data=data)
    del c
    return response


def extract_sub_content_from_agit(site_url_prefix: str, content: str, keyword: str):
    LOGGER.debug("# extract_sub_content_from_agit(site_url_prefix=%s)", site_url_prefix)
    result_list = []

    content = re.sub(r'^var\s+\w+\s+=\s+', '', content)
    if re.search(r';$', content):
        content = re.sub(r';$', '', content)
    else:
        return None

    data = json.loads(content)
    for item in data:
        if "t" in item:
            if keyword in item["t"]:
                link = URL.concatenate_url(site_url_prefix, item["x"] + ".html")
                result_list.append((item["t"], link))
    return result_list


def extract_sub_content_by_attrs(site_url_prefix: str, content: str, attrs: Dict[str, str]) -> List[Tuple[str, str]]:
    LOGGER.debug("# extract_sub_content_by_attrs(site_url_prefix=%s, attrs=%r)", site_url_prefix, attrs)
    soup = BeautifulSoup(content, "html.parser")
    result_list = []
    for key in attrs.keys():
        if key in ("id", "class"):
            content = soup.find_all(attrs={key: attrs[key]})
        elif key == "path":
            content = HTMLExtractor.get_node_with_path(soup.body, attrs[key])
        LOGGER.debug(content)

        title = ""
        link = ""
        for e in content:
            m = re.search(r'<a[^>]*href="(?P<link>[^"]+)"[^>]*>', str(e))
            if m:
                if m.group("link").startswith("http"):
                    link = m.group("link")
                else:
                    link = URL.concatenate_url(site_url_prefix, m.group("link"))
                link = re.sub(r'&amp;', '&', link)
                link = re.sub(r'&?cpa=\d+', '', link)
                link = re.sub(r'&?stx=\d+', '', link)

            # 주석 제거
            e = re.sub(r'<!--.*-->', '', str(e))
            # 단순(텍스트만 포함한) p 태그 제거
            e = re.sub(r'<p[^>]*>[^<]*</p>', '', e)
            prev_e = e
            while True:
                # 만화사이트에서 자주 보이는 불필요한 텍스트 제거
                e = re.compile(r'''
                    <\w+[^>]*>
                    \s*
                    (
                    \s*
                    [/+\-★]?
                    \s*
                    (
                    만화제목|작가이름|(발행|초성|장르)검색|정렬|검색 결과|공지사항|북마크(업데이트)?|주간랭킹 TOP30|나의 댓?글 반응
                    |
                    주간|격주|격월|월간|단행본|단편|완결|연재|정기|비정기|월요일?|화요일?|수요일?|목요일?|금요일?|토요일?|일요일?
                    |
                    액\b|액션|판타지|성인|무협|무장|드라마|라노벨|개그|학원|BL|스토리?|순정|로맨스|로매스|이세계|전생|일상|치유|애니|백합|미분류|시대극|투믹스|게임|카카오페|느와르|15금|18금|19금|가정부|BL|Bl|GL|일반|러브코미디|화
                    |
                    오늘|어제|그제|(하루|이틀|사흘|(한|두|세|네)\s?(주|달)|(\d+|일|이|삼|사|오|육|칠)\s?(일|월|년))\s?전
                    |
                    (webtoon|cartoon|movie|drama)\d+
                    )
                    )+
                    \s*
                    </\w+>
                ''', re.VERBOSE).sub('', e)
                # 연속된 공백을 공백 1개로 교체
                e = re.sub(r'\s+', ' ', e)
                # #[] 제거
                e = re.sub(r'\#\[\]', '', e)
                if prev_e == e:
                    break
                prev_e = e

            if "jmana" not in site_url_prefix and "flix" not in site_url_prefix:
                e = re.sub(r'.*\b\d+(화|권|부|편).*', '', e)

            # 모든 html 태그 제거            
            e = re.sub(r'</?\w+(\s*[\w\-_]+="[^"]*")*/?>', '', e)
            # #태그 제거
            e = re.sub(r'\s*\#\S+', '', e)
            # 행 처음에 연속하는 공백 제거
            e = re.sub(r'^\s+', '', e)
            # 행 마지막에 연속하는 공백 제거
            e = re.sub(r'(\s|\n)+$', '', e)
            if not re.search(r'^\s*$', e):
                title = e

            if title and link:
                result_list.append((title, urllib.parse.unquote(link)))
                link = ""
                title = ""

    return result_list


def search_site(site_name: str, url_postfix: str, attrs: Dict[str, str], method=Method.GET, headers={}, data={}):
    LOGGER.debug("# search_site(site_name=%s, url_postfix=%s, attrs=%r, method=%s, headers=%r, data=%r)", site_name, url_postfix, attrs, method, headers, data)
    os.chdir(work_dir_path / site_name)
    with open("site_config.json", 'r', encoding='utf-8') as infile:
        config = json.load(infile)
        if site_name == "agit":
            version = ""
            content = get_data_from_site(config, "")
            m = re.search(r'src=\'/data/azi_webtoon_\d.js(?P<version>\?v=[^\']+)\'', content)
            if m:
                version = m.group("version")
            result_list = []
            for i in range(config["num_retries"]):
                content0 = get_data_from_site(config, "/data/azi_webtoon_0.js" + version, method=method, headers=headers, data=data)
                result0 = extract_sub_content_from_agit(config["url"], content0, attrs["keyword"])
                content1 = get_data_from_site(config, "/data/azi_webtoon_1.js" + version, method=method, headers=headers, data=data)
                result1 = extract_sub_content_from_agit(config["url"], content1, attrs["keyword"])
                if result0:
                    result_list.extend(result0)
                    break
                if result1:
                    result_list.extend(result1)
                    break
        else:
            content = get_data_from_site(config, url_postfix, method=method, headers=headers, data=data)
            result_list = extract_sub_content_by_attrs(config["url"], content, attrs)
    print_content(site_name, result_list)


def get_marumaru_site_domain():
    with open(marumaru_site_config_file_path, 'r', encoding='utf-8') as infile:
        marumaru_site_config = json.load(infile)
        return URL.get_url_domain(marumaru_site_config["url"])
    return ""

    
def main():
    LOGGER.debug("# main()")

    site_name: str = None
    optlist, args = getopt.getopt(sys.argv[1:], "s:")
    for o, a in optlist:
        if o == '-s':
            site_name = a

    original_keyword = args[0]
    keyword = urllib.parse.quote(original_keyword)
    keyword_cp949 = original_keyword.encode("cp949")

    site_args_map = { 
        "jmana": ["/comic_list?keyword=" + keyword, {"class": "tit"}],
        "ornson": ["/search?skeyword=" + keyword, {"class": "tag_box"}],
        "manatoki": ["/comic?stx=" + keyword, {"class": "list-item"}],
        "newtoki": ["/webtoon?stx=" + keyword, {"class": "list-item"}],
        "copytoon": ["/bbs/search_webtoon.php?stx=" + keyword, {"class": "section-item-title"}],
        "wfwf": ["/search.html?q=" + urllib.parse.quote(keyword_cp949), {"class": "searchLink"}],
        "wtwt": ["/sh", {"path": '/html/body/section/div/div[2]/div/div[3]/ul/li'}, Method.POST, {"Content-Type": "application/x-www-form-urlencoded"}, {"search_txt": keyword_cp949}],
        "marumaru": ["/bbs/search.php?stx=" + keyword, {"class": "media"}],
        "funbe": ["/bbs/search.php?stx=" + keyword, {"class": "section-item-title"}],
        "tkor": ["/bbs/search.php?stx=" + keyword, {"class": "section-item-title"}],
        "flix": ["/bbs/search.php?stx=" + keyword, {"class": "post-list"}, Method.POST, {"Content-Type": "application/x-www-form-urlencoded"}, {"keyword": original_keyword}],
        "buzztoon": ["/bbs/search.php?stx=" + keyword, {"class": "list_info_title"}],
        #"sektoon": ["/?post_type=post&s=" + keyword, {"class": "entry-title"}],
        "agit":["", {"keyword": original_keyword}],
    }
    for site, args_map in site_args_map.items():
        if (site_name and site_name == site) or not site_name:
            # -s 옵션을 지정하지 않았거나, 지정한 사이트에 대해서만 검색
            search_site(site, *site_args_map[site])
            
    return 0


if __name__ == "__main__":
    sys.exit(main())
