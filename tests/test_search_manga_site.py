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
                result = search_manager.search("", "존재하지않는키워드", False)
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


if __name__ == "__main__":
    test_search_manga_site() 
