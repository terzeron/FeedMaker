#!/usr/bin/env python

import sys
import json
import re
import getopt
from threading import Thread
import logging.config
from typing import Optional, Union, Any, Tuple, List
from pathlib import Path
from urllib.parse import urlparse, unquote, quote

import requests

from bs4 import BeautifulSoup, Comment
from bin.crawler import Crawler, Method
from bin.feed_maker_util import URL, HTMLExtractor, NotFoundConfigFileError, Env


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Site:
    site_name: str = ""
    work_dir_path: Optional[Path] = None

    url_prefix: str = ""
    url_postfix: str = ""
    extraction_attrs: dict[str, str] = {}

    encoding: str = ""
    render_js: bool = False
    num_retries: int = 1
    method: Method = Method.GET
    headers: dict[str, str] = {}
    payload: dict[str, Union[str, bytes]] = {}

    @classmethod
    def set_work_dir(cls, work_dir: str) -> None:
        """작업 디렉토리를 설정합니다."""
        cls.work_dir_path = Path(work_dir)

    @classmethod
    def get_work_dir(cls) -> Path:
        """작업 디렉토리를 반환합니다. 설정되지 않은 경우 환경변수에서 가져옵니다."""
        if not cls.work_dir_path:
            cls.work_dir_path = Path(Env.get("FM_WORK_DIR"))
        return cls.work_dir_path

    def __init__(self, site_name: str) -> None:
        #LOGGER.debug("# Site(site_name='%s')", site_name)
        work_dir_path = self.get_work_dir()
        site_conf_file_path = work_dir_path / site_name / "site_config.json"
        if not site_conf_file_path.exists():
            raise NotFoundConfigFileError(f"can't find configuration file '{site_conf_file_path}'")

        self.site_name = site_name
        with site_conf_file_path.open("r", encoding="utf-8") as infile:
            config = json.load(infile)
            self.url_prefix = config.get("url")
            self.encoding = config.get("encoding", "utf-8")
            self.render_js = config.get("render_js", False)
            self.num_retries = config.get("num_retries", 1)
            self.headers = {"Referer": config.get("referer", "")}

    def set_url_prefix(self, url_prefix: str) -> None:
        LOGGER.debug(f"# set_url_prefix(url_prefix={url_prefix})")
        self.url_prefix = url_prefix

    def set_url_postfix(self, url_postfix: str) -> None:
        LOGGER.debug(f"# set_url_postfix(url_postfix={url_postfix})")
        self.url_postfix = url_postfix

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        self.set_url_postfix(keyword)  # 기본 구현

    def set_payload(self, keyword: str = "") -> None:
        LOGGER.debug(f"# set_payload(keyword={keyword})")

    def get_data_from_site(self, url: str = "") -> Optional[str]:
        LOGGER.debug(f"# get_data_from_site(url={url})")
        if self.site_name:
            work_dir_path = self.get_work_dir()
            site_dir_path = work_dir_path / self.site_name
            crawler: Crawler = Crawler(dir_path=site_dir_path, render_js=self.render_js, method=self.method, headers=self.headers, encoding=self.encoding, timeout=240)
            if not url:
                url = URL.get_url_scheme(self.url_prefix) + "://" + URL.get_url_domain(self.url_prefix) + self.url_postfix
                LOGGER.debug(f"url={url}")
            response, _, _ = crawler.run(url=url, data=self.payload)
            del crawler
            return response
        return None

    def extract_sub_content(self, content: str, attrs: dict[str, str]) -> list[tuple[str, str]]:
        LOGGER.debug(f"# extract_sub_content(attrs={attrs})")
        element_list: list[Any] = []
        soup = BeautifulSoup(content, "html.parser")
        if soup.div:
            for element in soup.div(text=lambda text: isinstance(text, Comment)):
                element.extract()

        result_list: list[tuple[str, str]] = []
        for key in attrs.keys():
            if key in ("id", "class"):
                element_list = soup.find_all(attrs={key: attrs[key]})
            elif key == "path":
                if soup.body is not None:
                    path_list = HTMLExtractor.get_node_with_path(soup.body, attrs[key])
                    if path_list:
                        element_list = path_list

            for element_obj in element_list:
                title: str = ""
                link: str = ""
                LOGGER.debug(f"element_obj={element_obj}")
                if not element_obj:
                    continue
                e = re.sub(r"\r?\n", "", str(element_obj))
                e = re.sub(r"\s\s+", " ", e)


                #LOGGER.debug(f"{e=}, {title=}, {link=}")
                # 링크 추출
                m = re.search(r'<a[^>]*href="(?P<link>[^"]+)"[^>]*>', e)
                if m:
                    if m.group("link").startswith("http"):
                        link = m.group("link")
                    else:
                        link = URL.concatenate_url(self.url_prefix, m.group("link"))
                    link = link.replace(r'&amp;', '&')
                    link = re.sub(r'&?cpa=\d+', '', link)
                    link = re.sub(r'&?stx=\d+', '', link)
                    #LOGGER.debug(f"{e=}, {title=}, {link=}")

                # 주석 제거
                e = re.sub(r'<!--[^>]*-->', '', str(e))
                # 단순(텍스트만 포함한) p 태그 제거
                prev_e = e
                while True:
                    # 명시적인 타이틀 텍스트 추출
                    m = re.search(r'<\w+[^>]*class="[^"]*([Tt]it(le)?|[Ss]ubject)"[^>]*>(?P<title>[^<>]+?)</\w+>', e)
                    if m:
                        title = m.group("title")
                        if title == "/ 검색":
                            title = ""
                        #LOGGER.debug(f"{e=}, {title=}, {link=}")

                    if self.site_name in ["11toon"]:
                        # 이미지 url 추출하여 link로 변경
                        m = re.search(r'url\(\x27(https?)?//[^/]+(?P<link>/.+)\x27\)', e)
                        if m:
                            link = m.group("link")
                            id_str = re.sub(r'/data/toon_category/(?P<id>\d+)', r'\g<id>', link)
                            link = URL.concatenate_url(self.url_prefix, "/bbs/board.php?bo_table=toons&is=" + id_str)

                    # 만화사이트에서 자주 보이는 불필요한 텍스트 제거 ex. <span class="title">만화제목</span>
                    e = re.sub(r'''
<(?P<tag>\w+)[^>]*>\s*
    (
        (애니|영화|게임|방송|음악|기타|유틸(리티)?|스포츠)  (\s*&gt;\s*)?  (극장판|완결|액션|공포/호러|범죄/스릴러|코미디|ᆭᆩSF/판타지|아동(/가족)?|한국영화|다큐|미분류|드라마/멜로|드라마일드|드라마|시사/교양|예능/오락|국내앨범|외국앨범|축구|농구|야구|레슬링|레이싱|격투|유틸리티|미디어|그래픽|드라이버|문서/업무|유아/어린이|모바일|도서/만화|직캠/아이돌|여직캠|남직캠|코스프레)?|
        한글(자막)?|자체자막|자막없음|우리말더빙|일드|무자막|
        한국영화|해외영화|드라마|넷플릭스|영상·음악|애니·만화|게임·유틸|
        만화제목|작가이름|(발행|초성|장르)검색|정렬|검색\s*결과|공지사항|북마크(업데이트)?|주간랭킹 TOP30|나의\s*댓?글\s*반응|
        주간|격주|격월|월간|단행본|단편|완결|연재|정기|비정기|월요일?|화요일?|수요일?|목요일?|금요일?|토요일?|일요일?|
        /액|액션|판타지/무협|판타지|성인/무협|성인|무협/성인|무협/액션/판타지|무협/액션|무협/판타지|무협|무장|라노벨|개그/무협|개그|학원|스토리?|순정|로맨스|로매스|이세계|전생|일상|치유|백합|미분류|시대극|투믹스|카카오페|느와르|15금|18금|19금|가정부|GL|BL/무협|BL|일반|러브코미디|
        오늘|어제|그제|
        (하루|이틀|사흘|나흘)\s*전?|
        [한두세네]\s*[주달]\s*전?|
        (\d+|일|이|삼|사|오|육|칠|팔|구|십일|십이|십)\s*[일주월년]\s*전?|
        \d+[화권부편]
    )
\s*</(?P=tag)>
                    ''', '', e, flags=re.VERBOSE | re.IGNORECASE)
                    # 연속된 공백을 공백 1개로 교체
                    e = re.sub(r'\s+', ' ', e)
                    # #[] 제거
                    e = e.replace(r'#\[]', '')
                    if prev_e == e:
                        break
                    prev_e = e

                # 일부 만화 사이트에서 권 단위 검색결과 노출되는 것을 제거
                #if self.site_name not in ["jmana", "allall", "torrentjok"]:
                #    e = re.sub(r'.*\b\d+[화권부편].*', '', e)

                # 설명 텍스트 제거
                e = re.sub(r'<\w+ class="">.+?</\w+>', '', e)
                # 모든 html 태그 제거
                e = re.sub(r'</?\w+(\s*[\w\-]+="[^"]*")*/?>', ' ', e)
                # #태그 제거
                e = re.sub(r'\s*#\S+', '', e)
                # 행 처음에 연속하는 공백 제거
                e = re.sub(r'^\s+', '', e)
                # 행 마지막에 연속하는 공백 제거
                e = re.sub(r'\s+$', '', e)
                # 연속된 공백을 공백 1개로 교체
                e = re.sub(r'\s+', ' ', e)
                #LOGGER.debug(f"{e=}, {title=}, {link=}")
                if not title and not re.search(r'^\s*$', e):
                    title = e
                    #LOGGER.debug(f"{e=}, {title=}, {link=}")

                if title and link and re.search(r"^\w.*$", title):
                    result_list.append((title, unquote(link)))
                    link = ""
                    title = ""

        return result_list

    def extract_sub_content_from_site_like_agit(self, content: str, keyword: str) -> list[tuple[str, str]]:
        LOGGER.debug(f"# extract_sub_content_from_site_like_agit(keyword={keyword})")
        result_list: list[tuple[str, str]] = []

        content = re.sub(r'^(<html><head>.*</head><body><pre[^>]*>)?var\s+\w+\s+=\s+', '', content)
        if re.search(r';(</pre></body></html>)?$', content):
            content = re.sub(r';(</pre></body></html>)?$', '', content)
        else:
            return []

        data = json.loads(content)
        for item in data:
            if keyword in item["t"]:
                link = URL.concatenate_url(self.url_prefix, item["x"] + ".html")
                result_list.append((item["t"], link))
        return result_list

    def search(self, keyword: str = "") -> list[tuple[str, str]]:
        LOGGER.debug(f"# search(keyword={keyword})")
        self.set_url_postfix_with_keyword(keyword)
        self.set_payload(keyword)
        html = self.get_data_from_site()
        if html:
            return self.extract_sub_content(html, self.extraction_attrs)
        return []

    def search_in_site_like_agit(self, keyword: str) -> list[tuple[str, str]]:
        LOGGER.debug(f"# search_in_site_like_agit(keyword={keyword})")
        url0 = ""
        url1 = ""
        html = self.get_data_from_site()
        if not html:
            return []
        m = re.search(r'src=[\'"](?P<url0>.*/data/webtoon/(\w+_)?webtoon_0(_\d+)?.js\?([v_]=[^\'"]+)?)[\'"]', html)
        if m:
            url0 = m.group("url0")
            if not url0.startswith("http"):
                if url0.startswith("//"):
                    url0 = "https:" + url0
                else:
                    url0 = URL.concatenate_url(self.url_prefix, url0)
        m = re.search(r'src=[\'"](?P<url1>.*/data/webtoon/(\w+_)?webtoon_1(_\d+)?.js\?([v_]=[^\'"]+)?)[\'"]', html)
        if m:
            url1 = m.group("url1")
            if not url1.startswith("http"):
                if url1.startswith("//"):
                    url1 = "https:" + url1
                else:
                    url1 = URL.concatenate_url(self.url_prefix, url1)
        LOGGER.debug(f"url0={url0}")
        LOGGER.debug(f"url1={url1}")

        result_list: list[tuple[str, str]] = []
        for _ in range(self.num_retries):
            content0 = self.get_data_from_site(url0)
            if content0:
                result0 = self.extract_sub_content_from_site_like_agit(content0, keyword)
                result_list.extend(result0)
                if result0:
                    break
            content1 = self.get_data_from_site(url1)
            if content1:
                result1 = self.extract_sub_content_from_site_like_agit(content1, keyword)
                result_list.extend(result1)
                if result1:
                    break
        return result_list


# class JmanaSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "tit"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/comic_list?keyword=" + encoded_keyword


# class ManatokiSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "list-item"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/comic?stx=" + encoded_keyword


# class NewtokiSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "list-item"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/webtoon?stx=" + encoded_keyword


# class CopytoonSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "section-item-title"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search_webtoon.php?stx=" + encoded_keyword


class WfwfSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "searchLink"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_cp949_keyword: str = quote(keyword.encode("cp949"))
        self.url_postfix = "/search.html?q=" + encoded_cp949_keyword


class WtwtSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "gallery"}
        self.method = Method.POST
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        self.url_postfix = "/sh"

    def set_payload(self, keyword: str = "") -> None:
        cp949_keyword = keyword.encode("cp949")
        self.payload = {"search_txt": cp949_keyword}


class XtoonSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "katoon-box"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/index.php/search?key=" + encoded_keyword


class JoatoonSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "p-1"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/toon/search?k=" + encoded_keyword


# class MarumaruSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "media"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword


class FunbeSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "section-item-title"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword


class ToonkorSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "section-item-title"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/bbs/search_webtoon.php?stx=" + encoded_keyword


class EleventoonSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "toons_item"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/bbs/search_stx.php?stx=" + encoded_keyword


# class AllallSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "video_list"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/searchs?skeyword=" + encoded_keyword


# class SkytoonSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "list"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/search?skeyword=" + encoded_keyword


class BlacktoonSite(Site):
    def __init__(self, site_name: str = "") -> None:
        super().__init__(site_name)

    def set_url_postfix_with_keyword(self, keyword: str = "") -> None:
        self.url_postfix = keyword

    def search(self, keyword: str = "") -> list[tuple[str, str]]:
        return self.search_in_site_like_agit(keyword)


# class OrnsonSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "tag_box"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/search?skeyword=" + encoded_keyword


# class FlixSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "post-list"}
#         self.method = Method.POST
#         self.headers = {"Content-Type": "application/x-www-form-urlencoded"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword

#     def set_payload(self, keyword: str = "") -> None:
#         self.payload = {"keyword": keyword}


# class SektoonSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "entry-title"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/?post_type=post&s=" + encoded_keyword


# class AgitSite(Site):
#     def __init__(self, site_name: str = "") -> None:
#         super().__init__(site_name)

#     def set_url_postfix_with_keyword(self, keyword: str = "") -> None:
#         self.url_postfix = ""

#     def search(self, keyword: str = "") -> list[tuple[str, str]]:
#         return self.search_in_site_like_agit(keyword)


# class TorrentJokSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "media-heading"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword


class TorrentQqSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "wr-subject"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/search?q=" + encoded_keyword


class TorrentRjSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "flex-grow truncate"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/search/index?keywords=" + encoded_keyword


class TorrentSeeSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "tit"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/search/index?category=0&keywords=" + encoded_keyword


# class TorrentdiaSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "list-subject"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search.php?search_flag=search&stx=" + encoded_keyword


class TorrentTipSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "page-list"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/search?q=" + encoded_keyword


# class TorrentTtSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "page-list"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/search?q=" + encoded_keyword


# class TorrentmodeSite(Site):
#     def __init__(self, site_name: str) -> None:
#         super().__init__(site_name)
#         self.extraction_attrs = {"class": "list-subject web-subject"}

#     def set_url_postfix_with_keyword(self, keyword: str) -> None:
#         encoded_keyword = quote(keyword)
#         self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword


class MzgtoonSite(Site):
    def __init__(self, site_name: str = "") -> None:
        super().__init__(site_name)
        # url_prefix에서 scheme+netloc만 추출
        parsed = urlparse(self.url_prefix)
        prefix = f"{parsed.scheme}://{parsed.netloc}"
        self.set_url_prefix(prefix)
        # extraction_attrs는 더 이상 사용하지 않음

    def set_url_postfix_with_keyword(self, keyword: str = "") -> None:
        encoded_keyword = quote(keyword)
        # 실제 API 엔드포인트 사용
        self.url_postfix = f"/api/search?q={encoded_keyword}"

    def search(self, keyword: str = "") -> list[tuple[str, str]]:
        self.set_url_postfix_with_keyword(keyword)
        url = self.url_prefix.rstrip("/") + self.url_postfix
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            result: List[Tuple[str, str]] = []
            for item in data.get('toonData', []):
                title = item.get('toon_title')
                toon_id = item.get('toon_id')
                link = f"{self.url_prefix}/webtoon/{toon_id}" if toon_id else None
                if title and link:
                    result.append((str(title), str(link)))
            return result
        except (OSError, IOError, TypeError, ValueError, RuntimeError):
            return []


class SearchManager:
    result_by_site: dict[Site, list[tuple[str, str]]] = {}

    def __init__(self) -> None:
        self.result_by_site = {}

    def worker(self, site: Site, keyword: str) -> None:
        #LOGGER.debug("# worker(site='%s', keyword='%s')", site, keyword)
        self.result_by_site[site] = site.search(keyword)

    def search(self, site_name: str, keyword: str, do_include_torrent_sites: bool = False) -> list[tuple[str, str]]:
        LOGGER.debug("# search(site_name='%s', keyword='%s', do_include_torrent_sites=%r)", site_name, keyword, do_include_torrent_sites)

        # Create site list with exception handling for missing config files
        site_classes = [
            (EleventoonSite, "11toon"),
            #(FunbeSite, "funbe"),
            (JoatoonSite, "joatoon"),
            (ToonkorSite, "toonkor"),
            (TorrentQqSite, "torrentqq"),
            (TorrentRjSite, "torrentrj"),
            (TorrentSeeSite, "torrentsee"),
            (TorrentTipSite, "torrenttip"),
            (XtoonSite, "xtoon"),
            #(AgitSite, "agit"),
            #(AllallSite, "allall"),
            (BlacktoonSite, "blacktoon"),
            #(JmanaSite, "jmana"),
            #(ManatokiSite, "manatoki"),
            #(NewtokiSite, "newtoki"),
            #(SkytoonSite, "skytoon"),
            #(TorrentJokSite, "torrentjok"),
            #(TorrentTtSite, "torrenttt"),
            (WfwfSite, "wfwf"),
            (WtwtSite, "wtwt"),
            (MzgtoonSite, "mzgtoon"),
        ]

        site_list: list[Site] = []
        for site_class, site_name_param in site_classes:
            try:
                site = site_class(site_name_param)
                site_list.append(site)
            except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
                LOGGER.warning(f"Failed to create site {site_name_param}: {e}, skipping")
                continue
            except NotFoundConfigFileError as e:
                # Catch specific exceptions like NotFoundConfigFileError
                LOGGER.warning(f"Failed to create site {site_name_param}: {e}, skipping")
                continue

        result_list: list[tuple[str, str]] = []
        if not site_name:
            # multi-sites
            thread_list: list[Thread] = []
            for site in site_list:
                if not do_include_torrent_sites:
                    if site.site_name.startswith("torrent"):
                        continue
                t = Thread(target=self.worker, kwargs={'site': site, 'keyword': keyword})
                thread_list.append(t)
                t.start()

            for t in thread_list:
                t.join()

            for _, result in self.result_by_site.items():
                result_list.extend(result)
        else:
            # single site
            for site in site_list:
                if site_name == site.site_name:
                    result_list = site.search(keyword)

        return result_list


def main() -> int:
    site_name: str = ""
    do_include_torrent_sites = False
    optlist, args = getopt.getopt(sys.argv[1:], "f:s:t")
    for o, a in optlist:
        if o == "-s":
            site_name = a
        if o == "-t":
            do_include_torrent_sites = True

    keyword = args[0]

    search_manager = SearchManager()
    result_list = search_manager.search(site_name, keyword, do_include_torrent_sites)

    for title, url in result_list:
        print(f"{title}\t\t{url}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
