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
        
    def preprocess_search_result(self, search_result: str) -> str:
        return search_result

    def get_base_url(self) -> str:
        """사이트의 기본 URL을 생성합니다."""
        return URL.get_url_scheme(self.url_prefix) + "://" + URL.get_url_domain(self.url_prefix)

    def get_data_from_site(self, url: str = "") -> Optional[str]:
        LOGGER.debug(f"# get_data_from_site(url={url})")
        if self.site_name:
            work_dir_path = self.get_work_dir()
            site_dir_path = work_dir_path / self.site_name
            crawler: Crawler = Crawler(dir_path=site_dir_path, render_js=self.render_js, method=self.method, headers=self.headers, encoding=self.encoding, timeout=240)
            if not url:
                url = self.get_base_url() + self.url_postfix
                LOGGER.debug(f"url={url}")
            response, error, _ = crawler.run(url=url, data=self.payload)
            del crawler
            return response
        return None

    def extract_sub_content(self, content: str, attrs: dict[str, str]) -> str:
        LOGGER.debug(f"# extract_sub_content(attrs={attrs})")
        element_list: list[Any] = []
        soup = BeautifulSoup(content, "html.parser")
        if soup.div:
            for element in soup.div(text=lambda text: isinstance(text, Comment)):
                element.extract()

        result_list: list[str] = []
            
        for key in attrs.keys():
            if key in ("id", "class"):
                element_list = soup.find_all(attrs={key: attrs[key]})
            elif key == "path":
                if soup.body is not None:
                    path_list = HTMLExtractor.get_node_with_path(soup.body, attrs[key])
                    if path_list:
                        element_list = path_list
            else:
                element_list = [content]

            for element_obj in element_list:
                # HTML 조각 추출
                html_fragment = str(element_obj)
                
                # 주석 제거
                html_fragment = re.sub(r'<!--[^>]*-->', '', html_fragment)
                
                # href 속성의 상대 경로를 절대 경로로 변환
                def replace_href(match):
                    href_value = match.group(1)
                    LOGGER.debug(f"Processing href: '{href_value}', url_prefix: '{self.url_prefix}'")
                    
                    # javascript:;인 경우 빈 문자열로 변경
                    if href_value == "javascript:;":
                        LOGGER.debug("javascript:; found, returning empty href")
                        return 'href=""'
                    elif href_value == "":
                        # 빈 href인 경우 사이트 기본 URL로 교체
                        base_url = self.get_base_url()
                        LOGGER.debug(f"Empty href found, replacing with base_url: {base_url}")
                        result = f'href="{base_url}"'
                        LOGGER.debug(f"Result: {result}")
                        return result
                    elif href_value.startswith('http'):
                        return f'href="{href_value}"'
                    else:
                        # 빈 문자열이 아닌 경우에만 concatenate_url 사용
                        if href_value:
                            absolute_url = URL.concatenate_url(self.url_prefix, href_value)
                            return f'href="{absolute_url}"'
                        else:
                            return f'href="{self.get_base_url()}"'
                
                # href 처리 전후 로그
                LOGGER.debug(f"Before href processing: {html_fragment[:200]}...")
                
                # href="" 패턴을 먼저 직접 처리
                if 'href=""' in html_fragment:
                    LOGGER.debug("Found href=\"\" pattern, replacing directly")
                    html_fragment = html_fragment.replace('href=""', f'href="{self.get_base_url()}"')
                
                # 일반적인 href 처리
                html_fragment = re.sub(r'href="([^"]*)"', replace_href, html_fragment)
                LOGGER.debug(f"After href processing: {html_fragment[:200]}...")
                
                # href가 있는 a 태그에만 target="_blank" 속성 추가
                html_fragment = re.sub(r'<a\b([^>]*href=[^>]*)>', r'<a\1 target="_blank">', html_fragment)
                
                # img 태그 완전 제거
                html_fragment = re.sub(r'<img[^>]*/?>', '', html_fragment)
                
                # SVG 태그와 하위 요소들 완전 제거
                try:
                    soup_fragment = BeautifulSoup(html_fragment, "html.parser")
                    for svg_element in soup_fragment.find_all("svg"):
                        svg_element.decompose()
                    html_fragment = str(soup_fragment)
                except Exception:
                    # SVG 제거 실패 시 정규표현식으로 대체 처리
                    html_fragment = re.sub(r'<svg[^>]*>.*?</svg>', '', html_fragment, flags=re.DOTALL)
                
                # BeautifulSoup을 사용하여 안전하게 속성 제거
                try:
                    soup_fragment = BeautifulSoup(html_fragment, "html.parser")
                    for tag in soup_fragment.find_all():
                        # 제거할 속성들 (href는 유지)
                        attrs_to_remove = ['class', 'id', 'alt', 'style']
                        for attr in attrs_to_remove:
                            if attr in tag.attrs:
                                del tag.attrs[attr]
                        
                        # onclick 등 on으로 시작하는 속성들 제거
                        attrs_to_remove_on = [attr for attr in tag.attrs.keys() if attr.startswith('on')]
                        for attr in attrs_to_remove_on:
                            del tag.attrs[attr]
                        
                        # data-로 시작하는 속성들 제거
                        attrs_to_remove_data = [attr for attr in tag.attrs.keys() if attr.startswith('data-')]
                        for attr in attrs_to_remove_data:
                            del tag.attrs[attr]
                    
                    html_fragment = str(soup_fragment)
                    
                    # BeautifulSoup 처리 후 href="" 다시 확인
                    if 'href=""' in html_fragment:
                        LOGGER.debug("Found href=\"\" after BeautifulSoup processing, replacing again")
                        html_fragment = html_fragment.replace('href=""', f'href="{self.get_base_url()}"')
                except Exception:
                    # BeautifulSoup 처리 실패 시 기존 정규표현식 방식 사용
                    html_fragment = re.sub(r'\s+(class|id|alt|on\w+)=["\'][^"\']*["\']', '', html_fragment)
                    html_fragment = re.sub(r'\s+style=["\'][^"\']*["\']', '', html_fragment)
                    html_fragment = re.sub(r'\s+data-[a-zA-Z0-9_-]*=["\'][^"\']*["\']', '', html_fragment)
                
                # article과 div 태그에 border 스타일 강제 추가
                html_fragment = re.sub(r'<(article|div)([^>]*)>', r'<\1\2 style="border: 1px solid #ccc;">', html_fragment)
                
                # 빈 태그 정리 (속성이 모두 제거된 경우)
                html_fragment = re.sub(r'<(\w+)\s+>', r'<\1>', html_fragment)
                
                # 연속된 공백을 공백 1개로 교체
                html_fragment = re.sub(r'\s+', ' ', html_fragment)
                
                # HTML beautify 적용
                try:
                    soup_fragment = BeautifulSoup(html_fragment, "html.parser")
                    html_fragment = soup_fragment.prettify()
                except Exception:
                    # beautify 실패 시 원본 유지
                    pass
                
                result_list.append(html_fragment)

        return "".join(result_list)

    def extract_sub_content_from_site_like_agit(self, content: str, keyword: str) -> str:
        LOGGER.debug(f"# extract_sub_content_from_site_like_agit(keyword={keyword})")
        result_list: list[str] = []

        content = re.sub(r'^(<html><head>.*</head><body><pre[^>]*>)?var\s+\w+\s+=\s+', '', content)
        if re.search(r';(</pre></body></html>)?$', content):
            content = re.sub(r';(</pre></body></html>)?$', '', content)
        else:
            return ""

        data = json.loads(content)
        for item in data:
            if keyword in item["t"]:
                link = URL.concatenate_url(self.url_prefix, item["x"] + ".html")
                result_str = f"<div>\n<span>{item['t']}</span>\t<span>{link}</span>\n</div>\n"
                result_list.append(result_str)
        return "".join(result_list)

    def search(self, keyword: str = "") -> str:
        LOGGER.debug(f"# search(keyword={keyword})")
        self.set_url_postfix_with_keyword(keyword)
        self.set_payload(keyword)
        html = self.get_data_from_site()
        if html:
            html = self.preprocess_search_result(html)
            return self.extract_sub_content(html, self.extraction_attrs)
        return ""

    def search_in_site_like_agit(self, keyword: str) -> str:
        LOGGER.debug(f"# search_in_site_like_agit(keyword={keyword})")
        url0 = ""
        url1 = ""
        html = self.get_data_from_site()
        if not html:
            return ""
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

        result_list: list[str] = []
        for _ in range(self.num_retries):
            content0 = self.get_data_from_site(url0)
            if content0:
                result0 = self.extract_sub_content_from_site_like_agit(content0, keyword)
                result_list.append(result0)
                if result0:
                    break
            content1 = self.get_data_from_site(url1)
            if content1:
                result1 = self.extract_sub_content_from_site_like_agit(content1, keyword)
                result_list.append(result1)
                if result1:
                    break
        return "".join(result_list)


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


class WfwfSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"bypass": "true"}

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
        self.extraction_attrs = {"class": "grid"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/toon/search?k=" + encoded_keyword


class FunbeSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "list-container"}

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
        self.extraction_attrs = {"id": "library-recents-list"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/bbs/search_stx.php?stx=" + encoded_keyword


class BlacktoonSite(Site):
    def __init__(self, site_name: str = "") -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"id": "toonbook_list"}

    def set_url_postfix_with_keyword(self, keyword: str = "") -> None:
        self.url_postfix = "/index.html#search?" + keyword


class TorrentJokSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "media-heading"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/bbs/search.php?stx=" + encoded_keyword


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


class TorrentTipSite(Site):
    def __init__(self, site_name: str) -> None:
        super().__init__(site_name)
        self.extraction_attrs = {"class": "page-list"}

    def set_url_postfix_with_keyword(self, keyword: str) -> None:
        encoded_keyword = quote(keyword)
        self.url_postfix = "/search?q=" + encoded_keyword


class MzgtoonSite(Site):
    def __init__(self, site_name: str = "") -> None:
        super().__init__(site_name)
        # url_prefix에서 scheme+netloc만 추출
        parsed = urlparse(self.url_prefix)
        prefix = f"{parsed.scheme}://{parsed.netloc}"
        self.set_url_prefix(prefix)
        self.extraction_attrs = {"bypass": "true"}

    def set_url_postfix_with_keyword(self, keyword: str = "") -> None:
        encoded_keyword = quote(keyword)
        # 실제 API 엔드포인트 사용
        self.url_postfix = f"/api/search?q={encoded_keyword}"
        
    def preprocess_search_result(self, search_result: str) -> str:
        # extract from pre tag and convert it into json
        soup = BeautifulSoup(search_result, "html.parser")
        pre_tag = soup.find("pre")
        if pre_tag:
            json_str = pre_tag.text
            data = json.loads(json_str)
        
            # convert json to html
            result_list: list[str] = []
            if "toonData" in data:
                toon_data = data["toonData"]
                for item in toon_data:
                    title = item["toon_title"]
                    link = f"/webtoon/{item['toon_id']}"
                    result_str = f"<div>\n<span>{title}</span>\t<span><a href=\"{link}\">{link}</a></span>\n</div>\n"
                    result_list.append(result_str)
                    
            return "".join(result_list)
        
        return ""


class SearchManager:
    result_by_site: dict[Site, str] = {}

    def __init__(self) -> None:
        self.result_by_site = {}

    def worker(self, site: Site, keyword: str) -> None:
        #LOGGER.debug("# worker(site='%s', keyword='%s')", site, keyword)
        search_result = site.search(keyword)
        self.result_by_site[site] = search_result

    def search_sites(self, site_name: str, keyword: str, do_include_torrent_sites: bool = False) -> str:
        LOGGER.debug("# search(site_name='%s', keyword='%s', do_include_torrent_sites=%r)", site_name, keyword, do_include_torrent_sites)

        # Create site list with exception handling for missing config files
        site_classes = [
            (EleventoonSite, "11toon"),
            (FunbeSite, "funbe"),
            (JoatoonSite, "joatoon"),
            (ToonkorSite, "toonkor"),
            (TorrentQqSite, "torrentqq"),
            (TorrentRjSite, "torrentrj"),
            (TorrentSeeSite, "torrentsee"),
            (TorrentTipSite, "torrenttip"),
            (XtoonSite, "xtoon"),
            (BlacktoonSite, "blacktoon"),
            #(ManatokiSite, "manatoki"),
            #(NewtokiSite, "newtoki"),
            (TorrentJokSite, "torrentjok"),
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

        result_list: list[str] = []
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
                result_list.append(result)
        else:
            # single site
            for site in site_list:
                if site_name == site.site_name:
                    result_list.append(site.search(keyword))

        return "".join(result_list)


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
    result = search_manager.search_sites(site_name, keyword, do_include_torrent_sites)
    print(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
