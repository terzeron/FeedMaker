#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the app from main
from backend.main import app
from backend.auth import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

# TestClient 인스턴스 생성
client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """테스트 모듈 전체에 대한 설정 및 정리"""
    # verify_csrf_token을 no-op으로 만들기 위해 async 함수로 정의
    async def mock_verify_csrf():
        pass

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
        from backend.main import verify_csrf_token
        app.state.feed_maker_manager = MagicMock(spec=FeedMakerManager)
        app.state.feed_maker_manager.search = mock_search
        app.state.feed_maker_manager.remove_group = mock_remove_group
        app.state.feed_maker_manager.get_groups = mock_get_groups

        # CSRF 검증을 bypass하기 위해 dependency override
        app.dependency_overrides[verify_csrf_token] = mock_verify_csrf

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

@pytest.mark.skip(reason="TestClient cookie handling limitation - CSRF tested in integration tests")
def test_csrf_protection():
    """CSRF 보호 기능 테스트"""
    # CSRF 검증을 실제로 테스트하기 위해 일시적으로 override 제거
    from backend.main import verify_csrf_token
    app.dependency_overrides.pop(verify_csrf_token, None)

    try:
        # 1. 로그인하여 세션 및 CSRF 쿠키 발급
        login_data = {
            "email": "test@example.com",
            "name": "Test User",
            "access_token": "fake-token"
        }
        # 환경 변수 mock 추가
        with patch('bin.feed_maker_util.Env.get', return_value="test@example.com"):
            response = client.post("/auth/login", json=login_data)

        assert response.status_code == 200
        assert CSRF_COOKIE_NAME in client.cookies
        csrf_token = client.cookies[CSRF_COOKIE_NAME]
        assert csrf_token is not None

        # 2. GET 요청은 CSRF 토큰 없이도 성공
        response = client.get("/search/test")
        assert response.status_code == 200

        # 3. CSRF 헤더 없이 DELETE 요청 시 403 에러 발생
        response = client.delete("/groups/some_group")
        assert response.status_code == 403
        assert "CSRF token mismatch" in response.json()["detail"]

        # 4. 잘못된 CSRF 토큰으로 DELETE 요청 시 403 에러 발생
        headers = {CSRF_HEADER_NAME: "wrong-token"}
        response = client.delete("/groups/some_group", headers=headers)
        assert response.status_code == 403
        assert "CSRF token mismatch" in response.json()["detail"]

        # 5. 올바른 CSRF 토큰으로 DELETE 요청 시 성공
        headers = {CSRF_HEADER_NAME: csrf_token}
        response = client.delete("/groups/some_group", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"
    finally:
        # 테스트 완료 후 override 복원
        async def mock_verify_csrf():
            pass
        app.dependency_overrides[verify_csrf_token] = mock_verify_csrf

if __name__ == "__main__":
    pytest.main()
