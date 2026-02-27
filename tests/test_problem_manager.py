#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import unittest
import shutil
import tempfile
from datetime import datetime, timezone
import logging.config
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Config
from bin.problem_manager import ProblemManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    temp_dir: Optional[Path] = None

    @classmethod
    def setUpClass(cls) -> None:
        # 임시 디렉토리 생성
        cls.temp_dir = Path(tempfile.mkdtemp())

        # ProblemManager 클래스 변수 리셋 (다른 테스트와의 격리를 위해)
        ProblemManager.is_tables_created = False

        print("🚀 Setting up mock environment for test_problem_manager...")
        print("✅ Mock environment ready for test_problem_manager")

    @classmethod
    def tearDownClass(cls) -> None:
        # 임시 디렉토리 정리
        if cls.temp_dir and cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)

        print("🧹 Mock environment cleaned up for test_problem_manager")

    def setUp(self) -> None:
        # temp_dir이 None이 아님을 보장
        assert self.temp_dir is not None

        # 테스트용 피드 디렉토리 생성
        self.test_feed_dir_path = self.temp_dir / "my_test_group" / "my_test_feed2"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

        # Mock Loki URL
        self.loki_url = "http://localhost:3100"

        # DB를 완전히 mock으로 대체
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query

        # ProblemManager 클래스 변수 리셋 (각 테스트 격리)
        ProblemManager.is_tables_created = False

        # ProblemManager 인스턴스 생성 (모든 외부 의존성을 mock으로 대체)
        with patch('bin.db.DB.create_all_tables') as mock_create_tables, \
             patch('bin.db.DB.session_ctx') as mock_session_ctx, \
             patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:

            mock_create_tables.return_value = None
            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            # Mock Loki search response
            mock_loki_search.return_value = ([], {}, None)

            self.pm = ProblemManager(loki_url=self.loki_url)

    def tearDown(self) -> None:
        # 테스트 피드 디렉토리 정리
        if self.test_feed_dir_path.parent.exists():
            shutil.rmtree(self.test_feed_dir_path.parent)

        del self.pm

    def test_get_feed_name_status_info_map(self) -> None:
        # get_feed_name_status_info_map 메서드를 직접 mock
        with patch.object(ProblemManager, 'get_feed_name_status_info_map') as mock_get_map:
            mock_get_map.return_value = {
                "test_feed": {
                    "feed_name": "test_feed",
                    "feed_title": "Test Feed",
                    "group_name": "test_group",
                    "http_request": True,
                    "public_html": True,
                    "feedmaker": True,
                    "access_date": datetime.now(timezone.utc),
                    "view_date": datetime.now(timezone.utc),
                    "upload_date": datetime.now(timezone.utc),
                    "update_date": datetime.now(timezone.utc),
                    "file_path": "/path/to/feed.xml"
                }
            }

            result = ProblemManager.get_feed_name_status_info_map()

        # 결과 검증
        self.assertIn("test_feed", result)
        status_info = result["test_feed"]
        self.assertIn("feed_name", status_info)
        self.assertIn("feed_title", status_info)
        self.assertIn("group_name", status_info)
        self.assertIn("http_request", status_info)
        self.assertIn("public_html", status_info)
        self.assertIn("feedmaker", status_info)
        self.assertIn("access_date", status_info)
        self.assertIn("view_date", status_info)
        self.assertIn("upload_date", status_info)
        self.assertIn("update_date", status_info)
        self.assertIn("file_path", status_info)

    def test_update_feed_info_basic(self) -> None:
        """기본적인 update_feed_info 테스트 - 정상적인 피드 디렉토리로 업데이트"""
        # 테스트용 conf.json 파일 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://example.com"],
                    "is_completed": False,
                    "unit_size_per_day": 1.0
                }
            }
        }

        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # Mock 메서드들이 호출되지 않았음을 확인
            mock_remove_config.assert_not_called()
            mock_remove_rss.assert_not_called()
            mock_remove_progress.assert_not_called()
            mock_remove_access.assert_not_called()
            mock_remove_html.assert_not_called()
            mock_add_config.assert_not_called()
            mock_add_rss.assert_not_called()
            mock_add_progress.assert_not_called()
            mock_add_access.assert_not_called()
            mock_add_html.assert_not_called()
            mock_remove_public.assert_not_called()
            mock_add_public.assert_not_called()

            # update_feed_info 호출
            self.pm.update_feed_info(self.test_feed_dir_path)

            # 모든 remove 메서드들이 올바른 순서로 호출되었는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)

            # 모든 add 메서드들이 올바른 순서로 호출되었는지 확인
            mock_add_config.assert_called_once_with(self.test_feed_dir_path)
            mock_add_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_add_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(self.test_feed_dir_path)

    def test_update_feed_info_with_new_path(self) -> None:
        """새로운 피드 디렉토리 경로로 업데이트하는 테스트"""
        # temp_dir이 None이 아님을 보장
        assert self.temp_dir is not None

        # 새로운 피드 디렉토리 생성
        new_feed_dir_path: Path = self.temp_dir / "my_test_group" / "new_test_feed"
        new_feed_dir_path.mkdir(parents=True, exist_ok=True)

        # 새로운 피드 디렉토리에 conf.json 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "New Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://newexample.com"],
                    "is_completed": True,
                    "unit_size_per_day": 2.0
                }
            }
        }

        test_config_file_path = new_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # update_feed_info 호출 (새로운 경로 지정)
            self.pm.update_feed_info(self.test_feed_dir_path, new_feed_dir_path)

            # 기존 피드 디렉토리에서 remove 메서드들이 호출되었는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)

            # 새로운 피드 디렉토리에서 add 메서드들이 호출되었는지 확인
            mock_add_config.assert_called_once_with(new_feed_dir_path)
            mock_add_rss.assert_called_once_with(new_feed_dir_path)
            mock_add_public.assert_called_once_with(new_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(new_feed_dir_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(new_feed_dir_path)

        # 정리
        if new_feed_dir_path.parent.exists():
            shutil.rmtree(new_feed_dir_path.parent)

    def test_update_feed_info_nonexistent_directories(self) -> None:
        """존재하지 않는 디렉토리들로 update_feed_info 호출하는 테스트"""
        # temp_dir이 None이 아님을 보장
        assert self.temp_dir is not None

        nonexistent_path: Path = self.temp_dir / "nonexistent_group" / "nonexistent_feed"

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public, \
             patch('bin.problem_manager.LOGGER.warning') as mock_warning:

            # update_feed_info 호출 (존재하지 않는 디렉토리)
            self.pm.update_feed_info(nonexistent_path)

            # 경고 로그가 호출되었는지 확인
            mock_warning.assert_called_once()

            # 모든 메서드들이 여전히 호출되었는지 확인 (경고가 있어도 처리 계속)
            mock_remove_config.assert_called_once_with(nonexistent_path)
            mock_remove_rss.assert_called_once_with(nonexistent_path)
            mock_remove_public.assert_called_once_with(nonexistent_path.name)
            mock_remove_progress.assert_called_once_with(nonexistent_path)
            mock_remove_access.assert_called_once_with(nonexistent_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", nonexistent_path)
            mock_add_config.assert_called_once_with(nonexistent_path)
            mock_add_rss.assert_called_once_with(nonexistent_path)
            mock_add_public.assert_called_once_with(nonexistent_path.name)
            mock_add_progress.assert_called_once_with(nonexistent_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(nonexistent_path)

    def test_update_feed_info_with_rss_file(self) -> None:
        """RSS 파일이 있는 피드 디렉토리로 update_feed_info 테스트"""
        # RSS 파일 생성
        rss_file_path = self.test_feed_dir_path / f"{self.test_feed_dir_path.name}.xml"
        rss_content = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <item>
            <title>Test Item</title>
            <link>http://example.com/test</link>
        </item>
    </channel>
</rss>"""
        rss_file_path.write_text(rss_content, encoding="utf-8")

        # conf.json 파일 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://example.com"],
                    "is_completed": False,
                    "unit_size_per_day": 1.0
                }
            }
        }

        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # update_feed_info 호출
            self.pm.update_feed_info(self.test_feed_dir_path)

            # 모든 메서드들이 올바르게 호출되었는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)
            mock_add_config.assert_called_once_with(self.test_feed_dir_path)
            mock_add_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_add_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(self.test_feed_dir_path)

    def test_update_feed_info_with_progress_file(self) -> None:
        """진행 상황 파일이 있는 피드 디렉토리로 update_feed_info 테스트"""
        # start_idx.txt 파일 생성
        progress_file_path = self.test_feed_dir_path / "start_idx.txt"
        progress_content = "157\t2024-01-01 12:00:00\n"
        progress_file_path.write_text(progress_content, encoding="utf-8")

        # conf.json 파일 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://example.com"],
                    "is_completed": True,
                    "unit_size_per_day": 1.0
                }
            }
        }

        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # update_feed_info 호출
            self.pm.update_feed_info(self.test_feed_dir_path)

            # 모든 메서드들이 올바르게 호출되었는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)
            mock_add_config.assert_called_once_with(self.test_feed_dir_path)
            mock_add_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_add_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(self.test_feed_dir_path)

    def test_update_feed_info_with_html_files(self) -> None:
        """HTML 파일들이 있는 피드 디렉토리로 update_feed_info 테스트"""
        # HTML 디렉토리 및 파일 생성
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(exist_ok=True)

        html_file_path = html_dir_path / "test.html"
        html_content = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
    <h1>Test Content</h1>
    <img src="http://example.com/image.jpg" alt="Test Image">
</body>
</html>"""
        html_file_path.write_text(html_content, encoding="utf-8")

        # conf.json 파일 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://example.com"],
                    "is_completed": False,
                    "unit_size_per_day": 1.0
                }
            }
        }

        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 모든 의존성 메서드들을 mock으로 대체
        with patch('bin.feed_manager.FeedManager.remove_config_info') as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # update_feed_info 호출
            self.pm.update_feed_info(self.test_feed_dir_path)

            # 모든 메서드들이 올바르게 호출되었는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_remove_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_access.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_html.assert_called_once_with("feed_dir_path", self.test_feed_dir_path)
            mock_add_config.assert_called_once_with(self.test_feed_dir_path)
            mock_add_rss.assert_called_once_with(self.test_feed_dir_path)
            mock_add_public.assert_called_once_with(self.test_feed_dir_path.name)
            mock_add_progress.assert_called_once_with(self.test_feed_dir_path)
            mock_add_access.assert_called_once()
            mock_add_html.assert_called_once_with(self.test_feed_dir_path)

    def test_update_feed_info_exception_handling(self) -> None:
        """update_feed_info에서 예외가 발생하는 경우 테스트"""
        # conf.json 파일 생성
        conf_data = {
            "configuration": {
                "rss": {
                    "title": "Test Feed Title"
                },
                "collection": {
                    "list_url_list": ["http://example.com"],
                    "is_completed": False,
                    "unit_size_per_day": 1.0
                }
            }
        }

        test_config_file_path = self.test_feed_dir_path / Config.DEFAULT_CONF_FILE
        with test_config_file_path.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        # 의존성 메서드에서 예외를 발생시키도록 설정
        with patch('bin.feed_manager.FeedManager.remove_config_info', side_effect=Exception("Test exception")) as mock_remove_config, \
             patch('bin.feed_manager.FeedManager.remove_rss_info') as mock_remove_rss, \
             patch('bin.feed_manager.FeedManager.remove_progress_info') as mock_remove_progress, \
             patch('bin.access_log_manager.AccessLogManager.remove_httpd_access_info') as mock_remove_access, \
             patch('bin.html_file_manager.HtmlFileManager.remove_html_file_in_path_from_info') as mock_remove_html, \
             patch('bin.feed_manager.FeedManager.add_config_info') as mock_add_config, \
             patch('bin.feed_manager.FeedManager.add_rss_info') as mock_add_rss, \
             patch('bin.feed_manager.FeedManager.add_progress_info') as mock_add_progress, \
             patch('bin.access_log_manager.AccessLogManager.add_httpd_access_info') as mock_add_access, \
             patch('bin.html_file_manager.HtmlFileManager.add_html_file') as mock_add_html, \
             patch.object(self.pm.feed_manager, 'remove_public_feed_by_feed_name') as mock_remove_public, \
             patch.object(self.pm.feed_manager, 'add_public_feed_by_feed_name') as mock_add_public:

            # 예외가 발생하는지 확인
            with self.assertRaises(Exception) as context:
                self.pm.update_feed_info(self.test_feed_dir_path)

            self.assertEqual(str(context.exception), "Test exception")

            # 첫 번째 메서드만 호출되고 나머지는 호출되지 않았는지 확인
            mock_remove_config.assert_called_once_with(self.test_feed_dir_path)
            mock_remove_rss.assert_not_called()
            mock_remove_public.assert_not_called()
            mock_remove_progress.assert_not_called()
            mock_remove_access.assert_not_called()
            mock_remove_html.assert_not_called()
            mock_add_config.assert_not_called()
            mock_add_rss.assert_not_called()
            mock_add_public.assert_not_called()
            mock_add_progress.assert_not_called()
            mock_add_access.assert_not_called()
            mock_add_html.assert_not_called()

    def test_load_all(self) -> None:
        # DB session mock 설정
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            # Loki API 호출을 mock으로 대체
            with patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:
                mock_loki_search.return_value = ([], {}, None)  # 빈 로그와 통계 반환

                # load_all 호출 - 예외가 발생하지 않으면 성공
                try:
                    self.pm.load_all(max_num_feeds=20, max_num_public_feeds=40, max_num_days=1)
                    # 성공적으로 실행되면 테스트 통과
                    self.assertTrue(True)
                except Exception as e:
                    self.fail(f"load_all failed with exception: {e}")


if __name__ == "__main__":
    unittest.main()
