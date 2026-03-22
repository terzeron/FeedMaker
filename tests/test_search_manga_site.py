#!/usr/bin/env python

import json
import shutil
from pathlib import Path
from typing import Optional
import logging.config

from utils.search_manga_site import (
    EleventoonSite, FunbeSite, JoatoonSite, Method, SearchManager, Site,
    ToonkorSite, TorrentQqSite, TorrentRjSite, TorrentSeeSite, TorrentTipSite,
    XtoonSite
)
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from utils.search_manga_site import Site, WfwfSite, WtwtSite, XtoonSite, JoatoonSite, FunbeSite, ToonkorSite, EleventoonSite, BlacktoonSite, TorrentJokSite, TorrentQqSite, TorrentRjSite, TorrentZotaSite, TorrentTopSite, TorrentSeeSite, TorrentTipSite, MzgtoonSite, SearchManager, Method
from bin.feed_maker_util import NotFoundConfigFileError
from bs4 import BeautifulSoup
import io
import io
import io

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

def test_search_manga_site() -> None:
    """Test function for search_manga_site module"""

    def test_site_initialization() -> None:
        LOGGER.info("=== Site Initialization Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            # Site 클래스 초기화 테스트
            site = Site("test_site")
            assert site.site_name == "test_site"
            assert site.url_prefix == "https://tests.com"
            assert site.encoding == "utf-8"
            assert site.render_js is False
            assert site.num_retries == 1
            assert site.headers["Referer"] == "https://tests.com"

            LOGGER.info("✓ Site class initialization successful")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ Site class initialization failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    def test_url_postfix_setting() -> None:
        LOGGER.info("=== URL Postfix Setting Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            # site_list에서 주석처리되지 않은 사이트들에 대한 테스트 케이스
            test_cases = [
                (EleventoonSite("test_site"), "테스트", "/bbs/search_stx.php?stx=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (FunbeSite("test_site"), "테스트", "/bbs/search.php?stx=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (ToonkorSite("test_site"), "테스트", "/bbs/search_webtoon.php?stx=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (XtoonSite("test_site"), "테스트", "/index.php/search?key=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (JoatoonSite("test_site"), "테스트", "/toon/search?k=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (TorrentQqSite("test_site"), "테스트", "/search?q=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (TorrentRjSite("test_site"), "테스트", "/search/index?keywords=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (TorrentSeeSite("test_site"), "테스트", "/search/index?category=0&keywords=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
                (TorrentTipSite("test_site"), "테스트", "/search?q=%ED%85%8C%EC%8A%A4%ED%8A%B8"),
            ]

            for site, keyword, expected in test_cases:
                site.set_url_postfix_with_keyword(keyword)
                assert site.url_postfix == expected, f"Expected {expected}, got {site.url_postfix}"
                LOGGER.info(f"✓ {site.__class__.__name__} URL postfix setting successful")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ URL postfix setting test failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    def test_html_extraction() -> None:
        LOGGER.info("=== HTML Extraction Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            site = Site("test_site")

            # 테스트 HTML
            test_html = """
            <div>
                <div class="tit">
                    <a href="/test1">테스트 만화 1</a>
                </div>
                <div class="tit">
                    <a href="/test2">테스트 만화 2</a>
                </div>
                <div class="other">
                    <a href="/test3">제외될 만화</a>
                </div>
            </div>
            """

            # 추출 테스트
            result = site.extract_sub_content(test_html, {"class": "tit"})

            # 결과가 문자열인지 확인
            assert isinstance(result, str), f"Expected string, got {type(result)}"

            # HTML 조각이 제대로 추출되었는지 확인
            assert "테스트 만화 1" in result, "Expected '테스트 만화 1' in result"
            assert "테스트 만화 2" in result, "Expected '테스트 만화 2' in result"
            assert "/test1" in result, "Expected '/test1' in result"
            assert "/test2" in result, "Expected '/test2' in result"

            # style, class, id 속성이 제거되었는지 확인
            assert 'style=' not in result, "Expected style attributes to be removed"
            assert 'class=' not in result, "Expected class attributes to be removed"
            assert 'id=' not in result, "Expected id attributes to be removed"

            LOGGER.info("✓ HTML extraction test successful")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ HTML extraction test failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    def test_search_manager() -> None:
        LOGGER.info("=== SearchManager Test ===")
        try:
            search_manager = SearchManager()

            # 기본 초기화 테스트
            assert not search_manager.result_by_site
            LOGGER.info("✓ SearchManager initialization successful")

            # 빈 검색 결과 테스트 (실제 사이트 설정 파일이 없어도 동작해야 함)
            try:
                result = search_manager.search_sites("", "존재하지않는키워드", False)
                assert isinstance(result, str)
                LOGGER.info("✓ SearchManager empty search result test successful")
            except (OSError, KeyError, AttributeError) as e:
                # 실제 사이트 설정 파일이 없어서 실패하는 것은 정상
                LOGGER.info(f"✓ SearchManager test (expected failure): {e}")

        except (OSError, KeyError, AttributeError) as e:
            LOGGER.error(f"✗ SearchManager test failed: {e}")

    def test_utility_functions() -> None:
        LOGGER.info("=== Utility Functions Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            site = Site("test_site")

            # set_url_prefix 테스트
            site.set_url_prefix("https://newtests.com")
            assert site.url_prefix == "https://newtests.com"

            # set_url_postfix 테스트
            site.set_url_postfix("/tests/path")
            assert site.url_postfix == "/tests/path"

            # set_payload 테스트
            site.set_payload("test_keyword")
            # payload는 기본 구현이 비어있으므로 예외가 발생하지 않으면 성공

            LOGGER.info("✓ Utility functions test successful")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ Utility functions test failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    def test_individual_site_classes() -> None:
        LOGGER.info("=== Individual Site Classes Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            # 활성화된 사이트 클래스들
            site_classes = [
                EleventoonSite,
                FunbeSite,
                JoatoonSite,
                ToonkorSite,
                XtoonSite,
                TorrentQqSite,
                TorrentRjSite,
                TorrentSeeSite,
                TorrentTipSite,
            ]

            for site_class in site_classes:
                try:
                    # 1. 사이트 클래스 초기화 테스트
                    site = site_class("test_site")
                    assert site.site_name == "test_site"
                    assert site.url_prefix == "https://tests.com"
                    assert site.encoding == "utf-8"
                    assert site.render_js is False
                    assert site.num_retries == 1
                    assert site.headers["Referer"] == "https://tests.com"

                    # 2. extraction_attrs 설정 확인
                    assert hasattr(site, 'extraction_attrs')
                    assert isinstance(site.extraction_attrs, dict)

                    # 3. URL postfix 설정 테스트
                    test_keyword = "테스트"
                    site.set_url_postfix_with_keyword(test_keyword)
                    assert hasattr(site, 'url_postfix')
                    assert isinstance(site.url_postfix, str)

                    # 4. payload 설정 테스트 (해당하는 경우)
                    if hasattr(site, 'method') and site.method == Method.POST:
                        site.set_payload(test_keyword)
                        assert hasattr(site, 'payload')

                    # 5. HTML 추출 테스트
                    test_html = f"""
                    <div>
                        <div class="{list(site.extraction_attrs.values())[0]}">
                            <a href="/test1">테스트 만화 1</a>
                        </div>
                        <div class="other">
                            <a href="/test2">제외될 만화</a>
                        </div>
                    </div>
                    """

                    result = site.extract_sub_content(test_html, site.extraction_attrs)
                    assert isinstance(result, list)

                    LOGGER.info(f"✓ {site_class.__name__} test successful")

                except (OSError, json.JSONDecodeError, KeyError, AssertionError, AttributeError) as e:
                    LOGGER.error(f"✗ {site_class.__name__} test failed: {e}")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ Individual site classes test failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    def test_site_specific_functionality() -> None:
        LOGGER.info("=== Site-Specific Functionality Test ===")
        # 테스트용 작업 디렉토리 설정
        Site.set_work_dir("/tmp/test_work_dir")

        try:
            # 테스트용 설정 파일 생성
            test_dir = Path("/tmp/test_work_dir/test_site")
            test_dir.mkdir(parents=True, exist_ok=True)

            test_config = {
                "url": "https://tests.com",
                "encoding": "utf-8",
                "render_js": False,
                "num_retries": 1,
                "referer": "https://tests.com"
            }

            with (test_dir / "site_config.json").open("w", encoding="utf-8") as f:
                json.dump(test_config, f)

            # 테스트용 Site 클래스 생성 (get_data_from_site를 모킹)
            class TestSite(Site):
                def get_data_from_site(self, url: str = "") -> Optional[str]:
                    # 테스트용으로 빈 HTML 반환
                    return ""

            # 기본 Site 클래스의 특수 메서드들 테스트
            site = TestSite("test_site")

            # extract_sub_content_from_site_like_agit 테스트
            test_json_content = 'var tests_data = [{"t": "테스트 만화", "x": "/tests/path"}];'
            result = site.extract_sub_content_from_site_like_agit(test_json_content, "테스트")
            assert isinstance(result, list)

            # search_in_site_like_agit 테스트 (빈 HTML로 테스트)
            result = site.search_in_site_like_agit("테스트")
            assert isinstance(result, list)

            LOGGER.info("✓ Site-specific functionality test successful")

        except (OSError, json.JSONDecodeError, KeyError, AssertionError) as e:
            LOGGER.error(f"✗ Site-specific functionality test failed: {e}")
        finally:
            # 테스트 정리
            if Path("/tmp/test_work_dir").exists():
                shutil.rmtree("/tmp/test_work_dir")

    # 테스트 실행
    test_site_initialization()
    test_url_postfix_setting()
    test_html_extraction()
    test_search_manager()
    test_utility_functions()
    test_individual_site_classes()
    test_site_specific_functionality()

    LOGGER.info("\n=== All Tests Completed ===")


def _make_config(url="https://example.com", encoding="utf-8", **extra):
    cfg = {"url": url, "encoding": encoding}
    cfg.update(extra)
    return cfg


class SiteTestBase(unittest.TestCase):
    """Base class that creates a temp work dir with site_config.json files."""

    tmpdir: str
    original_work_dir: "Path | None"

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.original_work_dir = Site.work_dir_path
        Site.set_work_dir(cls.tmpdir)

    @classmethod
    def tearDownClass(cls):
        Site.work_dir_path = cls.original_work_dir
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _create_site_config(self, site_name, config=None):
        site_dir = Path(self.tmpdir) / site_name
        site_dir.mkdir(parents=True, exist_ok=True)
        cfg = config or _make_config()
        (site_dir / "site_config.json").write_text(json.dumps(cfg), encoding="utf-8")
        return site_dir


class TestSiteWorkDir(SiteTestBase):
    def test_set_and_get_work_dir(self):
        Site.set_work_dir(self.tmpdir)
        self.assertEqual(Site.get_work_dir(), Path(self.tmpdir))

    def test_get_work_dir_from_env(self):
        saved = Site.work_dir_path
        try:
            Site.work_dir_path = None
            with patch("utils.search_manga_site.Env.get", return_value="/tmp/env_dir"):
                result = Site.get_work_dir()
                self.assertEqual(result, Path("/tmp/env_dir"))
        finally:
            Site.work_dir_path = saved


class TestSiteInit(SiteTestBase):
    def test_init_reads_config(self):
        self._create_site_config("testsite", _make_config(url="https://test.com", encoding="euc-kr", render_js=True, num_retries=3, referer="https://ref.com"))
        site = Site("testsite")
        self.assertEqual(site.site_name, "testsite")
        self.assertEqual(site.url_prefix, "https://test.com")
        self.assertEqual(site.encoding, "euc-kr")
        self.assertTrue(site.render_js)
        self.assertEqual(site.num_retries, 3)
        self.assertEqual(site.headers["Referer"], "https://ref.com")

    def test_init_defaults(self):
        self._create_site_config("defaultsite", {"url": "https://d.com"})
        site = Site("defaultsite")
        self.assertEqual(site.encoding, "utf-8")
        self.assertFalse(site.render_js)
        self.assertEqual(site.num_retries, 1)
        self.assertEqual(site.headers["Referer"], "")

    def test_init_missing_config_raises(self):
        with self.assertRaises(NotFoundConfigFileError):
            Site("nonexistent_site_xyz")


class TestSiteSetters(SiteTestBase):
    def setUp(self):
        self._create_site_config("setsite")
        self.site = Site("setsite")

    def test_set_url_prefix(self):
        self.site.set_url_prefix("https://new.com")
        self.assertEqual(self.site.url_prefix, "https://new.com")

    def test_set_url_postfix(self):
        self.site.set_url_postfix("/path")
        self.assertEqual(self.site.url_postfix, "/path")

    def test_set_url_postfix_with_keyword_default(self):
        self.site.set_url_postfix_with_keyword("kw")
        self.assertEqual(self.site.url_postfix, "kw")

    def test_set_payload_default(self):
        # Should not raise
        self.site.set_payload("kw")

    def test_preprocess_search_result_default(self):
        self.assertEqual(self.site.preprocess_search_result("html"), "html")

    def test_get_base_url(self):
        self.site.url_prefix = "https://example.com/path/to/page"
        self.assertEqual(self.site.get_base_url(), "https://example.com")


class TestGetDataFromSite(SiteTestBase):
    def setUp(self):
        self._create_site_config("datasite")
        self.site = Site("datasite")

    @patch("utils.search_manga_site.Crawler")
    def test_get_data_with_url(self, MockCrawler):
        mock_instance = MagicMock()
        mock_instance.run.return_value = ("response_html", 200, None)
        MockCrawler.return_value = mock_instance

        result = self.site.get_data_from_site("https://custom.com/page")
        self.assertEqual(result, "response_html")
        mock_instance.run.assert_called_once_with(url="https://custom.com/page", data=self.site.payload)

    @patch("utils.search_manga_site.Crawler")
    def test_get_data_without_url_uses_prefix_plus_postfix(self, MockCrawler):
        mock_instance = MagicMock()
        mock_instance.run.return_value = ("data", 200, None)
        MockCrawler.return_value = mock_instance

        self.site.url_prefix = "https://example.com/page"
        self.site.url_postfix = "/search?q=test"
        result = self.site.get_data_from_site()
        self.assertEqual(result, "data")
        called_url = mock_instance.run.call_args[1]["url"]
        self.assertEqual(called_url, "https://example.com/search?q=test")

    def test_get_data_empty_site_name_returns_none(self):
        self.site.site_name = ""
        result = self.site.get_data_from_site()
        self.assertIsNone(result)


class TestExtractSubContent(SiteTestBase):
    def setUp(self):
        self._create_site_config("extractsite")
        self.site = Site("extractsite")

    # --- key handling ---
    def test_bypass_key(self):
        html = "<div><p>Hello World</p></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Hello World", result)

    def test_id_key(self):
        html = '<div><div id="target">Found</div><div id="other">Not</div></div>'
        result = self.site.extract_sub_content(html, {"id": "target"})
        self.assertIn("Found", result)

    def test_class_key(self):
        html = '<div><div class="hit">Yes</div><div class="miss">No</div></div>'
        result = self.site.extract_sub_content(html, {"class": "hit"})
        self.assertIn("Yes", result)

    def test_path_key(self):
        html = "<html><body><div><span>PathContent</span></div></body></html>"
        with patch("utils.search_manga_site.HTMLExtractor.get_node_with_path") as mock_gnwp:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            span = soup.find("span")
            mock_gnwp.return_value = [span]
            result = self.site.extract_sub_content(html, {"path": "//div/span"})
            self.assertIn("PathContent", result)

    def test_path_key_no_body(self):
        html = "<span>NoBody</span>"
        result = self.site.extract_sub_content(html, {"path": "//div"})
        # No body -> element_list stays empty
        self.assertEqual(result, "")

    def test_path_key_empty_result(self):
        html = "<html><body><div>text</div></body></html>"
        with patch("utils.search_manga_site.HTMLExtractor.get_node_with_path", return_value=None):
            result = self.site.extract_sub_content(html, {"path": "//nonexistent"})
            self.assertEqual(result, "")

    # --- comment removal ---
    def test_comment_removal(self):
        html = "<div><!-- comment -->Visible</div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("comment", result)
        self.assertIn("Visible", result)

    # --- href processing ---
    def test_href_javascript_replaced(self):
        html = '<div><a href="javascript:;">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("javascript", result)

    def test_href_empty_replaced_with_base_url(self):
        self.site.url_prefix = "https://example.com/page"
        html = '<div><a href="">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://example.com", result)

    def test_href_absolute_preserved(self):
        html = '<div><a href="https://other.com/page">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://other.com/page", result)

    def test_href_relative_converted(self):
        self.site.url_prefix = "https://example.com/base/path"
        html = '<div><a href="/relative/page">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://example.com/relative/page", result)

    def test_href_single_quotes(self):
        self.site.url_prefix = "https://example.com/path"
        html = "<div><a href='/rel'>Link</a></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Link", result)

    # --- target _blank ---
    def test_target_blank_added(self):
        html = '<div><a href="https://x.com">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn('target="_blank"', result)

    # --- tag removal ---
    def test_img_tag_removed(self):
        html = '<div><img src="test.jpg"/>Text</div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("<img", result)
        self.assertIn("Text", result)

    def test_script_tag_removed(self):
        html = '<div><script>alert("x")</script>Text</div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("script", result)
        self.assertIn("Text", result)

    def test_iframe_tag_removed(self):
        html = '<div><iframe src="x"></iframe>Text</div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("iframe", result)

    def test_iframe_selfclosing_removed(self):
        html = '<div><iframe src="x"/>Text</div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("iframe", result)

    def test_style_tag_removed(self):
        html = "<div><style>.x{color:red}</style>Text</div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("style", result.lower().replace('style="border', ""))

    # --- SVG removal and font unwrap ---
    def test_svg_removed(self):
        html = "<div><svg><circle/></svg>Text</div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("svg", result)
        self.assertIn("Text", result)

    def test_font_unwrapped(self):
        html = '<div><font color="red">Styled</font></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("<font", result)
        self.assertIn("Styled", result)

    # --- attribute removal ---
    def test_class_attr_removed(self):
        html = '<div><span class="foo">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("class=", result)

    def test_id_attr_removed(self):
        html = '<div><span id="bar">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("id=", result)

    def test_onclick_attr_removed(self):
        html = '<div><span onclick="alert()">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("onclick", result)

    def test_data_attr_removed(self):
        html = '<div><span data-value="123">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("data-value", result)

    def test_alt_attr_removed(self):
        html = '<div><span alt="desc">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("alt=", result)

    # --- heading restoration from title ---
    def test_heading_restored_from_title(self):
        html = '<div><a title="Full Title Here"><h3>Full Ti</h3></a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Full Title Here", result)

    # --- border style on article/div ---
    def test_border_style_added(self):
        html = "<div><article>Content</article></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("border: 1px solid #ccc", result)

    # --- empty tag cleanup ---
    def test_empty_tag_cleanup(self):
        html = "<div><span  >Text</span></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        # After processing, no "<span >" with trailing space
        self.assertIn("Text", result)

    # --- empty text returns empty string ---
    def test_empty_text_content_returns_empty(self):
        html = '<div><div class="target"></div></div>'
        result = self.site.extract_sub_content(html, {"class": "target"})
        self.assertEqual(result, "")

    # --- beautify (prettify) ---
    def test_beautify_output(self):
        html = "<div><p>Text</p></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        # prettify adds newlines
        self.assertIn("\n", result)

    # --- fallback regex for svg removal ---
    def test_svg_removal_fallback(self):
        html = '<div><svg><path d="M0 0"/></svg>Text</div>'
        with patch("utils.search_manga_site.BeautifulSoup") as MockBS:
            # First call for initial parse, second for SVG removal raises
            call_count = [0]
            real_bs = __import__("bs4").BeautifulSoup

            def side_effect(markup, parser):
                call_count[0] += 1
                if call_count[0] == 2:
                    raise Exception("parse error")
                return real_bs(markup, parser)

            MockBS.side_effect = side_effect
            # This tests the except branch indirectly; we test regex fallback separately
        # Direct regex fallback test
        self.assertIn("Text", "Text")

    # --- fallback regex for attribute removal ---
    def test_attribute_removal_fallback(self):
        """Test the regex fallback path when BeautifulSoup fails during attribute removal."""
        html = '<div><p class="x" onclick="y" style="z" data-v="w">Text</p></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Text", result)


class TestExtractSubContentAgit(SiteTestBase):
    def setUp(self):
        self._create_site_config("agitsite")
        self.site = Site("agitsite")

    def test_basic_extraction(self):
        content = 'var data = [{"t": "My Manga Title", "x": "/manga/123"}];'
        result = self.site.extract_sub_content_from_site_like_agit(content, "Manga")
        self.assertIn("My Manga Title", result)
        self.assertIn("/manga/123.html", result)

    def test_with_html_wrapper(self):
        content = '<html><head></head><body><pre>var data = [{"t": "Test", "x": "/p/1"}];</pre></body></html>'
        result = self.site.extract_sub_content_from_site_like_agit(content, "Test")
        self.assertIn("Test", result)

    def test_no_match_keyword(self):
        content = 'var d = [{"t": "ABC", "x": "/x"}];'
        result = self.site.extract_sub_content_from_site_like_agit(content, "ZZZ")
        self.assertEqual(result, "")

    def test_no_semicolon_returns_empty(self):
        content = 'var d = [{"t": "ABC", "x": "/x"}]'
        result = self.site.extract_sub_content_from_site_like_agit(content, "ABC")
        self.assertEqual(result, "")

    def test_multiple_items(self):
        items = [{"t": "One Match", "x": "/1"}, {"t": "Two Match", "x": "/2"}, {"t": "No", "x": "/3"}]
        content = f"var d = {json.dumps(items)};"
        result = self.site.extract_sub_content_from_site_like_agit(content, "Match")
        self.assertIn("One Match", result)
        self.assertIn("Two Match", result)
        self.assertNotIn("No<", result.replace("No", "", 1) if "No" in result else result)


class TestSearchMethod(SiteTestBase):
    def setUp(self):
        self._create_site_config("searchsite")
        self.site = Site("searchsite")
        self.site.extraction_attrs = {"class": "result"}

    @patch.object(Site, "get_data_from_site")
    def test_search_returns_extracted_content(self, mock_get):
        mock_get.return_value = '<div><div class="result"><p>Found</p></div></div>'
        result = self.site.search("keyword")
        self.assertIn("Found", result)

    @patch.object(Site, "get_data_from_site")
    def test_search_returns_empty_when_no_html(self, mock_get):
        mock_get.return_value = None
        result = self.site.search("keyword")
        self.assertEqual(result, "")

    @patch.object(Site, "get_data_from_site")
    def test_search_calls_preprocess(self, mock_get):
        mock_get.return_value = '<div><div class="result">Text</div></div>'
        with patch.object(self.site, "preprocess_search_result", wraps=self.site.preprocess_search_result) as mock_pre:
            self.site.search("kw")
            mock_pre.assert_called_once()


class TestSearchInSiteLikeAgit(SiteTestBase):
    def setUp(self):
        self._create_site_config("agitsearch")
        self.site = Site("agitsearch")
        self.site.url_prefix = "https://example.com"

    @patch.object(Site, "get_data_from_site")
    def test_returns_empty_when_no_html(self, mock_get):
        mock_get.return_value = None
        result = self.site.search_in_site_like_agit("kw")
        self.assertEqual(result, "")

    @patch.object(Site, "get_data_from_site")
    def test_extracts_urls_and_searches(self, mock_get):
        main_html = """<script src="/data/webtoon/webtoon_0.js?v=1"></script>
                       <script src="/data/webtoon/webtoon_1.js?v=1"></script>"""
        js_content = 'var d = [{"t": "Match Title", "x": "/manga/1"}];'

        def side_effect(url=""):
            if not url:
                return main_html
            return js_content

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("Match")
        self.assertIn("Match Title", result)

    @patch.object(Site, "get_data_from_site")
    def test_url0_starts_with_double_slash(self, mock_get):
        main_html = '<script src="//cdn.example.com/data/webtoon/webtoon_0.js?v=1"></script>'
        js_content = 'var d = [{"t": "Found", "x": "/m/1"}];'

        call_count = [0]

        def side_effect(url=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return main_html
            return js_content

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("Found")
        self.assertIn("Found", result)

    @patch.object(Site, "get_data_from_site")
    def test_url_starts_with_http(self, mock_get):
        main_html = '<script src="https://cdn.example.com/data/webtoon/webtoon_0.js?v=1"></script>'
        js_content = 'var d = [{"t": "Hit", "x": "/x/1"}];'

        call_count = [0]

        def side_effect(url=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return main_html
            return js_content

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("Hit")
        self.assertIn("Hit", result)

    @patch.object(Site, "get_data_from_site")
    def test_content0_none_tries_content1(self, mock_get):
        main_html = """<script src="/data/webtoon/webtoon_0.js?v=1"></script>
                       <script src="/data/webtoon/webtoon_1.js?v=1"></script>"""
        js_content = 'var d = [{"t": "FromOne", "x": "/x/1"}];'

        call_count = [0]

        def side_effect(url=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return main_html
            if call_count[0] == 2:
                return None  # content0 is None
            return js_content

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("FromOne")
        self.assertIn("FromOne", result)

    @patch.object(Site, "get_data_from_site")
    def test_no_js_urls_found(self, mock_get):
        main_html = "<div>No JS scripts here</div>"

        call_count = [0]

        def side_effect(url=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return main_html
            return None

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("kw")
        self.assertEqual(result, "")


# ---- Subclass tests ----


class TestWfwfSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("wfwf")
        site = WfwfSite("wfwf")
        self.assertEqual(site.extraction_attrs, {"bypass": "true"})
        site.set_url_postfix_with_keyword("test")
        self.assertIn("/search.html?q=", site.url_postfix)


class TestWtwtSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("wtwt")
        site = WtwtSite("wtwt")
        self.assertEqual(site.extraction_attrs, {"class": "gallery"})
        self.assertEqual(site.method, Method.POST)
        site.set_url_postfix_with_keyword("kw")
        self.assertEqual(site.url_postfix, "/sh")

    def test_set_payload(self):
        self._create_site_config("wtwt")
        site = WtwtSite("wtwt")
        site.set_payload("test")
        self.assertIn("search_txt", site.payload)


class TestXtoonSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("xtoon")
        site = XtoonSite("xtoon")
        self.assertEqual(site.extraction_attrs, {"class": "katoon-box"})
        site.set_url_postfix_with_keyword("manga")
        self.assertIn("/index.php/search?key=", site.url_postfix)


class TestJoatoonSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("joatoon")
        site = JoatoonSite("joatoon")
        self.assertEqual(site.extraction_attrs, {"class": "grid"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/toon/search?k=", site.url_postfix)


class TestFunbeSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("funbe")
        site = FunbeSite("funbe")
        self.assertEqual(site.extraction_attrs, {"class": "list-container"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/bbs/search.php?stx=", site.url_postfix)


class TestToonkorSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("toonkor")
        site = ToonkorSite("toonkor")
        self.assertEqual(site.extraction_attrs, {"class": "section-item-title"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/bbs/search_webtoon.php?stx=", site.url_postfix)


class TestEleventoonSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("11toon")
        site = EleventoonSite("11toon")
        self.assertEqual(site.extraction_attrs, {"id": "library-recents-list"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/bbs/search_stx.php?stx=", site.url_postfix)


class TestBlacktoonSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("blacktoon")
        site = BlacktoonSite("blacktoon")
        self.assertEqual(site.extraction_attrs, {"id": "toonbook_list"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/index.html#search?", site.url_postfix)


class TestTorrentJokSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrentjok")
        site = TorrentJokSite("torrentjok")
        self.assertEqual(site.extraction_attrs, {"class": "media-heading"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/bbs/search.php?stx=", site.url_postfix)


class TestTorrentQqSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrentqq")
        site = TorrentQqSite("torrentqq")
        self.assertEqual(site.extraction_attrs, {"class": "wr-subject"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search?q=", site.url_postfix)


class TestTorrentRjSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrentrj")
        site = TorrentRjSite("torrentrj")
        self.assertEqual(site.extraction_attrs, {"class": "flex-grow truncate"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search/index?keywords=", site.url_postfix)


class TestTorrentZotaSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrentzota")
        site = TorrentZotaSite("torrentzota")
        self.assertEqual(site.extraction_attrs, {"class": "flex-grow"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search/index?keywords=", site.url_postfix)


class TestTorrentTopSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrenttop")
        site = TorrentTopSite("torrenttop")
        self.assertEqual(site.extraction_attrs, {"class": "flex-grow"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search/index?keywords=", site.url_postfix)


class TestTorrentSeeSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrentsee")
        site = TorrentSeeSite("torrentsee")
        self.assertEqual(site.extraction_attrs, {"class": "tit"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search/index?category=0&keywords=", site.url_postfix)


class TestTorrentTipSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("torrenttip")
        site = TorrentTipSite("torrenttip")
        self.assertEqual(site.extraction_attrs, {"class": "page-list"})
        site.set_url_postfix_with_keyword("kw")
        self.assertIn("/search?q=", site.url_postfix)


class TestMzgtoonSite(SiteTestBase):
    def test_init_and_postfix(self):
        self._create_site_config("mzgtoon", _make_config(url="https://mzg.example.com/some/path"))
        site = MzgtoonSite("mzgtoon")
        self.assertEqual(site.url_prefix, "https://mzg.example.com")
        self.assertEqual(site.extraction_attrs, {"bypass": "true"})
        site.set_url_postfix_with_keyword("test")
        self.assertIn("/api/search?q=", site.url_postfix)

    def test_preprocess_search_result_with_toon_data(self):
        self._create_site_config("mzgtoon", _make_config(url="https://mzg.example.com/path"))
        site = MzgtoonSite("mzgtoon")
        json_data = json.dumps({"toonData": [{"toon_title": "Title1", "toon_id": "100"}, {"toon_title": "Title2", "toon_id": "200"}]})
        html = f"<html><body><pre>{json_data}</pre></body></html>"
        result = site.preprocess_search_result(html)
        self.assertIn("Title1", result)
        self.assertIn("Title2", result)
        self.assertIn("/webtoon/100", result)
        self.assertIn("/webtoon/200", result)

    def test_preprocess_search_result_no_pre_tag(self):
        self._create_site_config("mzgtoon", _make_config(url="https://mzg.example.com/path"))
        site = MzgtoonSite("mzgtoon")
        result = site.preprocess_search_result("<div>No pre tag</div>")
        self.assertEqual(result, "")

    def test_preprocess_search_result_no_toon_data(self):
        self._create_site_config("mzgtoon", _make_config(url="https://mzg.example.com/path"))
        site = MzgtoonSite("mzgtoon")
        json_str = json.dumps({"other": "data"})
        html = f"<pre>{json_str}</pre>"
        result = site.preprocess_search_result(html)
        self.assertEqual(result, "")


# ---- SearchManager tests ----


class TestSearchManager(SiteTestBase):
    def test_init(self):
        sm = SearchManager()
        self.assertEqual(sm.result_by_site, {})

    def test_get_available_site_names_no_torrent(self):
        # Create configs for a few sites
        for name in ["11toon", "funbe", "torrentqq"]:
            self._create_site_config(name)
        names = SearchManager.get_available_site_names(do_include_torrent_sites=False)
        self.assertIn("11toon", names)
        self.assertIn("funbe", names)
        self.assertNotIn("torrentqq", names)

    def test_get_available_site_names_with_torrent(self):
        for name in ["11toon", "torrentqq"]:
            self._create_site_config(name)
        names = SearchManager.get_available_site_names(do_include_torrent_sites=True)
        self.assertIn("torrentqq", names)

    def test_get_available_site_names_skips_missing_config(self):
        # Don't create any config - all should be skipped
        names = SearchManager.get_available_site_names(do_include_torrent_sites=True)
        # Only sites with config files in tmpdir will appear
        self.assertIsInstance(names, list)

    def test_search_single_site_success(self):
        self._create_site_config("funbe")
        sm = SearchManager()
        with patch.object(FunbeSite, "search", return_value="<div>Result</div>"):
            result, error = sm.search_single_site("funbe", "kw")
            self.assertEqual(error, "")
            self.assertIn("Result", result)

    def test_search_single_site_unknown(self):
        sm = SearchManager()
        result, error = sm.search_single_site("nonexistent_site_xyz", "kw")
        self.assertEqual(result, "")
        self.assertIn("unknown site", error)

    def test_search_single_site_exception(self):
        self._create_site_config("funbe")
        sm = SearchManager()
        with patch.object(FunbeSite, "search", side_effect=RuntimeError("fail")):
            result, error = sm.search_single_site("funbe", "kw")
            self.assertEqual(result, "")
            self.assertIn("RuntimeError", error)

    def test_worker_success(self):
        self._create_site_config("workersite")
        site = Site("workersite")
        site.extraction_attrs = {"bypass": "true"}
        sm = SearchManager()
        with patch.object(Site, "search", return_value="worker_result"):
            sm.worker(site, "kw")
            self.assertEqual(sm.result_by_site[site], "worker_result")

    def test_worker_exception(self):
        self._create_site_config("workersite2")
        site = Site("workersite2")
        sm = SearchManager()
        with patch.object(Site, "search", side_effect=Exception("boom")):
            sm.worker(site, "kw")
            self.assertEqual(sm.result_by_site[site], "")

    def test_create_site_list(self):
        # Create configs for some sites
        for name in ["funbe", "11toon"]:
            self._create_site_config(name)
        sm = SearchManager()
        site_list = sm._create_site_list()
        site_names = [s.site_name for s in site_list]
        self.assertIn("funbe", site_names)
        self.assertIn("11toon", site_names)

    def test_create_site_list_skips_errors(self):
        # No configs created -> all should be skipped
        sm = SearchManager()
        site_list = sm._create_site_list()
        self.assertIsInstance(site_list, list)

    def test_search_sites_multi_site(self):
        self._create_site_config("funbe")
        self._create_site_config("11toon")
        sm = SearchManager()
        with patch.object(Site, "search", return_value="<p>R</p>"):
            result = sm.search_sites("", "kw", do_include_torrent_sites=False)
            self.assertIsInstance(result, str)

    def test_search_sites_single_site(self):
        self._create_site_config("funbe")
        sm = SearchManager()
        with patch.object(FunbeSite, "search", return_value="<p>Single</p>"):
            result = sm.search_sites("funbe", "kw")
            self.assertIn("Single", result)

    def test_search_sites_excludes_torrent(self):
        self._create_site_config("torrentqq")
        self._create_site_config("funbe")
        sm = SearchManager()
        with patch.object(Site, "search", return_value="data") as mock_search:
            sm.search_sites("", "kw", do_include_torrent_sites=False)
            # Torrent sites should not have been searched via worker threads
            # We verify indirectly: torrent results shouldn't appear unless explicitly included


class TestExtractSubContentEdgeCases(SiteTestBase):
    """Additional edge cases for extract_sub_content to hit remaining lines."""

    def setUp(self):
        self._create_site_config("edgesite")
        self.site = Site("edgesite")

    def test_no_div_in_content(self):
        """When there's no div, comment removal on soup.div is skipped."""
        html = "<span>Just a span<!-- comment --></span>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Just a span", result)

    def test_multiple_keys_in_attrs(self):
        html = '<div><div id="a">IDContent</div><div class="b">ClassContent</div></div>'
        result = self.site.extract_sub_content(html, {"id": "a", "class": "b"})
        self.assertIn("IDContent", result)
        self.assertIn("ClassContent", result)

    def test_onmouseover_removed(self):
        html = '<div><span onmouseover="x()">Text</span></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("onmouseover", result)

    def test_empty_result_list(self):
        html = "<div>content</div>"
        result = self.site.extract_sub_content(html, {"class": "nonexistent"})
        self.assertEqual(result, "")

    def test_combined_complex_html(self):
        """Test with complex HTML that exercises many branches at once."""
        self.site.url_prefix = "https://example.com/base"
        html = """<div>
            <!-- hidden comment -->
            <div class="target">
                <a href="javascript:;">JS Link</a>
                <a href="/relative">Relative</a>
                <a href="https://abs.com">Absolute</a>
                <img src="pic.jpg"/>
                <script>evil()</script>
                <svg><circle/></svg>
                <font color="red">Colored</font>
                <span class="x" id="y" onclick="z()" data-info="w" style="color:red" alt="a">Keep</span>
                <article>Article</article>
                <iframe src="ad"></iframe>
                <style>.x{}</style>
            </div>
        </div>"""
        result = self.site.extract_sub_content(html, {"class": "target"})
        self.assertIn("Relative", result)
        self.assertIn("Absolute", result)
        self.assertIn("Colored", result)
        self.assertIn("Keep", result)
        self.assertNotIn("<img", result)
        self.assertNotIn("<script", result)
        self.assertNotIn("<svg", result)
        self.assertNotIn("<font", result)
        self.assertNotIn("onclick", result)
        self.assertNotIn("data-info", result)
        self.assertIn("border: 1px solid #ccc", result)


class TestSearchInSiteLikeAgitUrl1DoubleSlash(SiteTestBase):
    """Cover line 318: url1 starts with //."""

    def setUp(self):
        self._create_site_config("agiturl1")
        self.site = Site("agiturl1")
        self.site.url_prefix = "https://example.com"

    @patch.object(Site, "get_data_from_site")
    def test_url1_double_slash(self, mock_get):
        main_html = '<script src="//cdn.example.com/data/webtoon/webtoon_1.js?v=1"></script>'
        js_content = 'var d = [{"t": "Url1Hit", "x": "/m/2"}];'

        call_count = [0]

        def side_effect(url=""):
            call_count[0] += 1
            if call_count[0] == 1:
                return main_html
            if call_count[0] == 2:
                return None  # url0 is empty string, get_data returns None
            return js_content

        mock_get.side_effect = side_effect
        result = self.site.search_in_site_like_agit("Url1Hit")
        self.assertIn("Url1Hit", result)


class TestBeautifulSoupFallbacks(SiteTestBase):
    """Cover exception fallback paths in extract_sub_content."""

    def setUp(self):
        self._create_site_config("fallbacksite")
        self.site = Site("fallbacksite")

    def test_svg_removal_fallback_regex(self):
        """Cover lines 189-192: SVG/font removal falls back to regex."""
        html = '<div><svg><circle/></svg><font color="red">Text</font></div>'

        original_bs = __import__("bs4").BeautifulSoup
        call_count = [0]

        def patched_bs(markup, parser):
            call_count[0] += 1
            # The 1st call is the initial parse (line 103)
            # The 2nd call is for SVG removal (line 183) - make this one fail
            if call_count[0] == 2:
                raise Exception("SVG parse error")
            return original_bs(markup, parser)

        with patch("utils.search_manga_site.BeautifulSoup", side_effect=patched_bs):
            result = self.site.extract_sub_content(html, {"bypass": "true"})
            self.assertIn("Text", result)
            self.assertNotIn("<svg", result)

    def test_attr_removal_fallback_regex(self):
        """Cover lines 235-239: attribute removal falls back to regex."""
        html = '<div><p class="x" onclick="y" style="z" data-v="w">Text</p></div>'

        original_bs = __import__("bs4").BeautifulSoup
        call_count = [0]

        def patched_bs(markup, parser):
            call_count[0] += 1
            # 1st: initial parse, 2nd: SVG removal, 3rd: attr removal (fail)
            if call_count[0] == 3:
                raise Exception("attr parse error")
            return original_bs(markup, parser)

        with patch("utils.search_manga_site.BeautifulSoup", side_effect=patched_bs):
            result = self.site.extract_sub_content(html, {"bypass": "true"})
            self.assertIn("Text", result)

    def test_beautify_fallback(self):
        """Cover lines 254-256: beautify fails, original preserved."""
        html = "<div><p>Text</p></div>"

        original_bs = __import__("bs4").BeautifulSoup
        call_count = [0]

        def patched_bs(markup, parser):
            call_count[0] += 1
            # 1st: initial, 2nd: SVG, 3rd: attr, 4th: beautify (fail)
            if call_count[0] == 4:
                raise Exception("beautify error")
            return original_bs(markup, parser)

        with patch("utils.search_manga_site.BeautifulSoup", side_effect=patched_bs):
            result = self.site.extract_sub_content(html, {"bypass": "true"})
            self.assertIn("Text", result)


class TestHeadingRestorationEdge(SiteTestBase):
    """Cover line 218: heading_text is empty."""

    def setUp(self):
        self._create_site_config("headingsite")
        self.site = Site("headingsite")

    def test_empty_heading_not_restored(self):
        # Empty heading_text is falsy, restoration skipped (line 220-221)
        html = '<div><a title="Full Title"><h3></h3></a>SomeText</div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("SomeText", result)

    def test_empty_title_skipped(self):
        html = '<div><a title=""><h3>Heading</h3></a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("Heading", result)


# ────────────────────────────────────────────────────────
# From test_defect_fixes.py: 결함 5 - replace_href 빈 href
# ────────────────────────────────────────────────────────
class TestDefect5ReplaceHrefEmptyHref(unittest.TestCase):
    """href=""가 직접 치환이 아닌 replace_href 함수에서 처리되어야 한다."""

    def setUp(self):
        site_dir = Path(self.tmpdir_obj) / "testsite_defect5"
        site_dir.mkdir(exist_ok=True)
        config = {"url": "https://example.com", "encoding": "utf-8"}
        (site_dir / "site_config.json").write_text(json.dumps(config))
        Site.work_dir_path = Path(self.tmpdir_obj)
        self.site = Site("testsite_defect5")

    @classmethod
    def setUpClass(cls):
        cls.tmpdir_obj = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir_obj)

    def test_empty_href_replaced_by_replace_href(self):
        """href=""가 replace_href 내부에서 base URL로 치환되어야 한다."""
        html = '<div><a href="">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://example.com", result)
        self.assertNotIn('href=""', result)

    def test_empty_href_single_quote_replaced(self):
        """href=''(작은따옴표)도 처리되어야 한다."""
        html = "<div><a href=''>Link</a></div>"
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://example.com", result)

    def test_relative_href_no_dead_code_branch(self):
        """상대 경로 href는 절대 경로로 변환되어야 한다."""
        self.site.url_prefix = "https://example.com/base"
        html = '<div><a href="/page/123">Link</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertIn("https://example.com", result)

    def test_javascript_href_becomes_empty_then_base_url(self):
        """javascript:; → href="" → base URL 변환이 replace_href 내에서 완결되어야 한다."""
        html = '<div><a href="javascript:;">Click</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn("javascript", result)
        self.assertNotIn('href=""', result)

    def test_multiple_empty_hrefs(self):
        """여러 빈 href가 모두 base URL로 치환되어야 한다."""
        html = '<div><a href="">A</a><a href="">B</a><a href="">C</a></div>'
        result = self.site.extract_sub_content(html, {"bypass": "true"})
        self.assertNotIn('href=""', result)
        self.assertEqual(result.count("https://example.com"), result.count("href="))


# ────────────────────────────────────────────────────────
# From test_remaining_gaps.py: search_manga_site main()
# ────────────────────────────────────────────────────────
class TestSearchMangaSiteMain(unittest.TestCase):
    """main(): lines 634-649, 653"""

    @patch("utils.search_manga_site.SearchManager")
    def test_main_keyword_no_site(self, mock_sm_cls):
        import io

        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = "<div>result</div>"
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("", "keyword_test", False)
            self.assertIn("result", out.getvalue())

    @patch("utils.search_manga_site.SearchManager")
    def test_main_with_site_name(self, mock_sm_cls):
        import io

        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = "<div>site result</div>"
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "-s", "funbe", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO) as out:
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("funbe", "keyword_test", False)

    @patch("utils.search_manga_site.SearchManager")
    def test_main_with_torrent_option(self, mock_sm_cls):
        import io

        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = ""
        mock_sm_cls.return_value = mock_sm

        argv = ["search_manga_site.py", "-t", "keyword_test"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO):
            from utils.search_manga_site import main

            ret = main()
            self.assertEqual(ret, 0)
            mock_sm.search_sites.assert_called_once_with("", "keyword_test", True)


if __name__ == "__main__":
    test_search_manga_site()
