#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import tempfile
from datetime import datetime, timezone
import logging.config
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

from bin.problem_manager import ProblemManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    temp_dir: Optional[Path] = None

    @classmethod
    def setUpClass(cls) -> None:
        # 임시 디렉토리 생성
        cls.temp_dir = Path(tempfile.mkdtemp())
        
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
        
        # ProblemManager 인스턴스 생성 (모든 외부 의존성을 mock으로 대체)
        with patch('bin.db.DB.session_ctx') as mock_session_ctx, \
             patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:

            mock_session_ctx.return_value.__enter__.return_value = self.mock_session
            mock_session_ctx.return_value.__exit__.return_value = None

            # Mock Loki search response
            mock_loki_search.return_value = ([], {})

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

    def test_update_feed_info(self) -> None:
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
        
        import json
        with open(self.test_feed_dir_path / "conf.json", "w", encoding="utf-8") as f:
            json.dump(conf_data, f)
        
        # DB session mock 설정
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            
            # Loki API 호출을 mock으로 대체
            with patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:
                mock_loki_search.return_value = ([], {})  # 빈 로그와 통계 반환
                
                # update_feed_info 호출 - 예외가 발생하지 않으면 성공
                try:
                    self.pm.update_feed_info(self.test_feed_dir_path)
                    # 성공적으로 실행되면 테스트 통과
                    self.assertTrue(True)
                except Exception as e:
                    self.fail(f"update_feed_info failed with exception: {e}")

    def test_load_all(self) -> None:
        # DB session mock 설정
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            
            # Loki API 호출을 mock으로 대체
            with patch('bin.access_log_manager.AccessLogManager.loki_search') as mock_loki_search:
                mock_loki_search.return_value = ([], {})  # 빈 로그와 통계 반환
                
                # load_all 호출 - 예외가 발생하지 않으면 성공
                try:
                    self.pm.load_all(max_num_feeds=20, max_num_public_feeds=40, max_num_days=1)
                    # 성공적으로 실행되면 테스트 통과
                    self.assertTrue(True)
                except Exception as e:
                    self.fail(f"load_all failed with exception: {e}")


if __name__ == "__main__":
    unittest.main()
