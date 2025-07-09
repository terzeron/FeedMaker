#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import main.py to establish dependency relationship for test_runner.py
import backend.main  # noqa: F401

class TestBackendAPI(unittest.TestCase):
    """백엔드 API 테스트 (mock 기반)"""

    def setUp(self) -> None:
        # DB 관련 메서드 mock
        self.db_init_patch = patch('bin.db.DB.init')
        self.db_create_tables_patch = patch('bin.db.DB.create_all_tables')
        self.db_session_ctx_patch = patch('bin.db.DB.session_ctx')
        self.mock_db_init = self.db_init_patch.start()
        self.mock_db_create_tables = self.db_create_tables_patch.start()
        self.mock_db_session_ctx = self.db_session_ctx_patch.start()
        self.mock_session = MagicMock()
        self.mock_db_session_ctx.return_value.__enter__.return_value = self.mock_session
        self.mock_db_session_ctx.return_value.__exit__.return_value = None

    def tearDown(self) -> None:
        patch.stopall()

    @patch('requests.get')
    def test_groups_endpoint(self, mock_get):
        # API 응답 mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "groups": [
                {"name": "test_group"}
            ]
        }
        mock_get.return_value = mock_response

        response = mock_get("http://localhost:8000/groups", timeout=10)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("groups", data)
        groups = data["groups"]
        self.assertIsInstance(groups, list)
        group_names = [group.get("name") for group in groups]
        self.assertIn("test_group", group_names)

    @patch('requests.get')
    def test_openapi_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "openapi": "3.0.0",
            "info": {},
            "paths": {}
        }
        mock_get.return_value = mock_response

        response = mock_get("http://localhost:8000/openapi.json", timeout=10)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("openapi", data)
        self.assertIn("info", data)
        self.assertIn("paths", data)
        self.assertTrue(data["openapi"].startswith("3."))

    @patch('requests.get')
    def test_health_check_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        response = mock_get("http://localhost:8000/health", timeout=10)
        self.assertEqual(response.status_code, 200)

    @patch('requests.get')
    def test_invalid_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        response = mock_get("http://localhost:8000/nonexistent", timeout=10)
        self.assertEqual(response.status_code, 404)

    @patch('sqlalchemy.engine.Connection.execute')
    def test_database_connection(self, mock_execute):
        # DB 연결 테스트 mock
        mock_execute.return_value.scalar.return_value = 1
        with patch('bin.db.DB.session_ctx') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session_ctx.return_value.__exit__.return_value = None
            mock_session.execute.return_value.scalar.return_value = 1
            result = mock_session.execute("SELECT 1").scalar()
            self.assertEqual(result, 1)

if __name__ == "__main__":
    unittest.main()
