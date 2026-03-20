#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the app from main
from backend.main import app
from bin.models import UserSession

# TestClient 인스턴스 생성
client = TestClient(app)

# 인증된 세션을 시뮬레이션하기 위한 mock 세션 쿠키
FAKE_SESSION_ID = "test-session-id-for-unit-tests"


def _make_fake_user_session():
    s = MagicMock(spec=UserSession)
    s.user_email = "test@example.com"
    s.user_name = "Test User"
    return s


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """테스트 모듈 전체에 대한 설정 및 정리"""
    # 테스트 시작 전, DB 관련 메서드 mock
    with patch('bin.db.DB.create_all_tables'), \
         patch('bin.db.DB.session_ctx') as mock_session_ctx, \
         patch('backend.feed_maker_manager.FeedMakerManager.search') as mock_search, \
         patch('backend.feed_maker_manager.FeedMakerManager.remove_group') as mock_remove_group, \
         patch('backend.feed_maker_manager.FeedMakerManager.get_groups') as mock_get_groups, \
         patch('backend.main.get_current_user', return_value=_make_fake_user_session()):

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
    """OpenAPI 비활성화 확인 테스트"""
    response = client.get("/openapi.json")
    assert response.status_code == 404

def test_invalid_endpoint():
    """유효하지 않은 엔드포인트 테스트"""
    response = client.get("/nonexistent")
    assert response.status_code == 404


# CSRF 보호는 SameSite=Lax 쿠키 설정으로 브라우저 레벨에서 처리됨
# 별도의 CSRF 토큰 검증 테스트는 더 이상 필요하지 않음


def test_unauthenticated_request_rejected():
    """인증 없이 보호된 엔드포인트 접근 시 401 반환"""
    with patch('backend.main.get_current_user', return_value=None):
        response = client.get("/groups")
        assert response.status_code == 401

        response = client.delete("/groups/test_group")
        assert response.status_code == 401


def test_auth_endpoints_exempt():
    """인증 엔드포인트는 미들웨어 인증 없이 접근 가능"""
    with patch('backend.main.get_current_user', return_value=None):
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["is_authenticated"] is False


def test_login_rejects_invalid_facebook_token():
    """위조된 Facebook 토큰으로 로그인 시 401 반환"""
    with patch('backend.main.verify_facebook_token', return_value=False):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "name": "Test",
            "access_token": "fake_token"
        })
        assert response.status_code == 401


def test_login_rejects_unallowed_email():
    """유효한 토큰이지만 허용되지 않은 이메일이면 403 반환"""
    with patch('backend.main.verify_facebook_token', return_value=True), \
         patch('backend.main.Env.get', return_value="allowed@example.com"):
        response = client.post("/auth/login", json={
            "email": "notallowed@example.com",
            "name": "Test",
            "access_token": "valid_token"
        })
        assert response.status_code == 403


def test_path_traversal_returns_400():
    """경로 탐색 공격이 400 Bad Request로 거부되는지 확인"""
    # _validate_name이 ValueError를 발생시키면 ValueError 핸들러가 400 반환
    from backend.feed_maker_manager import FeedMakerManager
    mock_mgr = MagicMock(spec=FeedMakerManager)
    mock_mgr.get_site_config.side_effect = ValueError("Invalid group_name: '..etc'")
    app.state.feed_maker_manager = mock_mgr

    response = client.get("/groups/..etc/site_config")
    assert response.status_code == 400
    assert "Invalid" in response.json()["message"]


if __name__ == "__main__":
    pytest.main()
