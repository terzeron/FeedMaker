#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the app from main
from backend.main import app

# TestClient 인스턴스 생성
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """테스트 모듈 전체에 대한 설정 및 정리"""
    # 테스트 시작 전, DB 관련 메서드 mock
    with patch('bin.db.DB.create_all_tables'), \
         patch('bin.db.DB.session_ctx') as mock_session_ctx, \
         patch('backend.feed_maker_manager.FeedMakerManager.search') as mock_search, \
         patch('backend.feed_maker_manager.FeedMakerManager.remove_group') as mock_remove_group, \
         patch('backend.feed_maker_manager.FeedMakerManager.get_groups') as mock_get_groups:

        # 세션 컨텍스트 매니저 mock
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__.return_value = mock_session
        mock_session_ctx.return_value.__exit__.return_value = None

        # FeedMakerManager 메서드 mock
        mock_search.return_value = ([], None)
        mock_remove_group.return_value = (True, None)
        mock_get_groups.return_value = ([{"name": "test_group", "is_active": True}], None)

        # FeedMakerManager 인스턴스를 app.state에 설정
        from backend.feed_maker_manager import FeedMakerManager
        app.state.feed_maker_manager = MagicMock(spec=FeedMakerManager)
        app.state.feed_maker_manager.search = mock_search
        app.state.feed_maker_manager.remove_group = mock_remove_group
        app.state.feed_maker_manager.get_groups = mock_get_groups

        # 테스트 실행
        yield

        # 테스트 종료 후 정리
        app.dependency_overrides.clear()

def test_read_groups():
    """GET /groups 엔드포인트 테스트"""
    response = client.get("/groups")
    assert response.status_code == 200
    assert "groups" in response.json()

def test_openapi_endpoint():
    """GET /openapi.json 엔드포인트 테스트"""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["openapi"].startswith("3.")

def test_invalid_endpoint():
    """유효하지 않은 엔드포인트 테스트"""
    response = client.get("/nonexistent")
    assert response.status_code == 404


# CSRF 보호는 SameSite=Lax 쿠키 설정으로 브라우저 레벨에서 처리됨
# 별도의 CSRF 토큰 검증 테스트는 더 이상 필요하지 않음


if __name__ == "__main__":
    pytest.main()
