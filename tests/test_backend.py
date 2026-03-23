#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the app from main
from backend.main import app
from bin.models import UserSession
from backend.auth import set_session_cookie, clear_session_cookie, SESSION_COOKIE_NAME  # noqa: F401, E501
import asyncio
import types
import backend.main as main
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import sys
import unittest
import backend.main as bmain

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
    with (
        patch("bin.db.DB.create_all_tables"),
        patch("bin.db.DB.session_ctx") as mock_session_ctx,
        patch("backend.feed_maker_manager.FeedMakerManager.search") as mock_search,
        patch("backend.feed_maker_manager.FeedMakerManager.remove_group") as mock_remove_group,
        patch("backend.feed_maker_manager.FeedMakerManager.get_groups") as mock_get_groups,
        patch("backend.main.get_current_user", return_value=_make_fake_user_session()),
    ):
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
    with patch("backend.main.get_current_user", return_value=None):
        response = client.get("/groups")
        assert response.status_code == 401

        response = client.delete("/groups/test_group")
        assert response.status_code == 401


def test_auth_endpoints_exempt():
    """인증 엔드포인트는 미들웨어 인증 없이 접근 가능"""
    with patch("backend.main.get_current_user", return_value=None):
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["is_authenticated"] is False


def test_login_rejects_invalid_facebook_token():
    """위조된 Facebook 토큰으로 로그인 시 401 반환"""
    with patch("backend.main.verify_facebook_token", return_value=False):
        response = client.post("/auth/login", json={"email": "test@example.com", "name": "Test", "access_token": "fake_token"})
        assert response.status_code == 401


def test_login_rejects_unallowed_email():
    """유효한 토큰이지만 허용되지 않은 이메일이면 403 반환"""
    with patch("backend.main.verify_facebook_token", return_value=True), patch("backend.main.Env.get", return_value="allowed@example.com"):
        response = client.post("/auth/login", json={"email": "notallowed@example.com", "name": "Test", "access_token": "valid_token"})
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


def test_value_error_does_not_leak_internal_details():
    """ValueError 발생 시 내부 에러 상세가 응답에 노출되지 않는지 확인"""
    from backend.feed_maker_manager import FeedMakerManager

    secret_detail = "secret_db_table_users at /var/lib/data"
    mock_mgr = MagicMock(spec=FeedMakerManager)
    mock_mgr.get_site_config.side_effect = ValueError(secret_detail)
    app.state.feed_maker_manager = mock_mgr

    response = client.get("/groups/testgroup/site_config")
    assert response.status_code == 400
    body = response.json()
    assert body["message"] == "Invalid input"
    assert secret_detail not in str(body)


def test_docs_endpoint_disabled():
    """Swagger UI(/docs) 비활성화 확인"""
    response = client.get("/docs")
    assert response.status_code == 404


def test_redoc_endpoint_disabled():
    """ReDoc(/redoc) 비활성화 확인"""
    response = client.get("/redoc")
    assert response.status_code == 404


class DummyFeedMakerManager:
    def __init__(self):
        pass

    async def aclose(self):
        return None

    # exec result - failure
    def get_exec_result(self):
        return (None, "exec error")

    # problems - failure
    def get_problems_progress_info(self):
        return (None, "progress error")

    def get_problems_public_feed_info(self):
        return (None, "public feed error")

    def get_problems_html_info(self):
        return (None, "html error")

    def get_problems_element_info(self):
        return (None, "element error")

    def get_problems_list_url_info(self):
        return (None, "list url error")

    def get_problems_status_info(self):
        return (None, "status error")

    # search - failure
    def search(self, keyword):
        return (None, "search error")

    # search_site - failure
    @classmethod
    def search_site(cls, keyword):
        return (None, "search site error")

    # search_site_names
    @classmethod
    def get_search_site_names(cls):
        return ["site1", "site2"]

    # search_single_site
    @classmethod
    def search_single_site(cls, site_name, keyword):
        return ([["title", "https://example.com"]], None)

    # feeds by group
    def get_feeds_by_group(self, group_name):
        return ([{"name": "feed1", "is_active": True}], None)

    # feed info
    def get_feed_info_by_name(self, group_name, feed_name):
        return ({"feed": {"name": feed_name}}, None)

    # save config
    def save_config_file(self, group_name, feed_name, post_data):
        return (True, None)

    # remove feed
    def remove_feed(self, group_name, feed_name):
        return (True, None)

    # remove list
    def remove_list(self, group_name, feed_name):
        return None

    # remove html
    def remove_html(self, group_name, feed_name):
        return None

    def remove_html_file(self, group_name, feed_name, html_file_name):
        return None

    # check running
    def check_running(self, group_name, feed_name):
        return True

    # groups
    def get_groups(self):
        return ([{"name": "group1", "is_active": True}], None)

    # remove group
    def remove_group(self, group_name):
        return (True, None)


class FailingFeedMakerManager(DummyFeedMakerManager):
    """Manager that returns failures for all operations"""

    def get_feeds_by_group(self, group_name):
        return (None, "feeds error")

    def get_feed_info_by_name(self, group_name, feed_name):
        return (None, "feed info error")

    def save_config_file(self, group_name, feed_name, post_data):
        return (None, "save error")

    def remove_feed(self, group_name, feed_name):
        return (None, "remove feed error")

    def check_running(self, group_name, feed_name):
        return None

    def get_groups(self):
        return (None, "groups error")

    def remove_group(self, group_name):
        return (None, "remove group error")

    @classmethod
    def search_single_site(cls, site_name, keyword):
        return (None, "single site error")


# --- exec_result failure ---


def test_get_exec_result_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_exec_result(feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "exec error"


# --- problems failure ---


def test_get_problems_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_problems(main.ProblemType.STATUS, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "status error"


# --- search failure ---


def test_search_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.search("test", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "search error"


# --- search_site failure ---


def test_search_site_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.search_site("test")
    assert r["status"] == "failure"
    assert r["message"] == "search site error"


# --- search_single_site success ---


def test_search_single_site_success():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "success"
    assert r["search_result"] == [["title", "https://example.com"]]


# --- search_single_site error (exception raised) ---


def test_search_single_site_exception():
    class ExcManager(DummyFeedMakerManager):
        @classmethod
        def search_single_site(cls, site_name, keyword):
            raise RuntimeError("connection failed")

    main.FeedMakerManager = ExcManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "failure"
    assert "RuntimeError" in r["message"]


# --- search_single_site error message ---


def test_search_single_site_error_message():
    main.FeedMakerManager = FailingFeedMakerManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "failure"
    assert r["message"] == "single site error"


# --- get_search_site_names ---


def test_get_search_site_names():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.get_search_site_names()
    assert r["status"] == "success"
    assert r["site_names"] == ["site1", "site2"]


# --- get_feeds_by_group success with is_active ---


def test_get_feeds_by_group_success():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_feeds_by_group("group1", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert "is_active" in r["feeds"][0]


# --- get_feeds_by_group failure ---


def test_get_feeds_by_group_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_feeds_by_group("group1", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "feeds error"


# --- get_feed_info success ---


def test_get_feed_info_success():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["feed_info"]["feed"]["name"] == "f"


# --- get_feed_info failure ---


def test_get_feed_info_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "feed info error"


# --- post_feed_info success ---


def test_post_feed_info_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()

    async def _json():
        return {"key": "value"}

    req = types.SimpleNamespace(json=_json)
    r = asyncio.run(main.post_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- post_feed_info failure ---


def test_post_feed_info_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()

    async def _json():
        return {"key": "value"}

    req = types.SimpleNamespace(json=_json)
    r = asyncio.run(main.post_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "save error"


# --- delete_feed_info success ---


def test_delete_feed_info_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.delete_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- delete_feed_info failure ---


def test_delete_feed_info_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.delete_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "remove feed error"


# --- remove_list, remove_html, remove_html_file with require_admin mock ---


def test_remove_list():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_list("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


def test_remove_html():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_html("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


def test_remove_html_file():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_html_file("g", "f", "x.html", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- check_running success True ---


def test_check_running_true():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["running_status"] is True


# --- check_running success False ---


def test_check_running_false():
    class FalseRunning(DummyFeedMakerManager):
        def check_running(self, group_name, feed_name):
            return False

    mgr = FalseRunning()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["running_status"] is False


# --- check_running error (None) ---


def test_check_running_error():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["running_status"] == "error"


# --- get_groups success with is_active ---


def test_get_groups_success():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_groups(feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert "is_active" in r["groups"][0]


# --- get_groups failure ---


def test_get_groups_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_groups(feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "groups error"


# --- remove_group success ---


def test_remove_group_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_group("g", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- remove_group failure ---


def test_remove_group_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_group("g", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "remove group error"


# --- logout with session_id cookie ---


def test_logout_with_session():
    req = types.SimpleNamespace(cookies={"session_id": "abc123"})
    with patch("backend.main.delete_session") as mock_del, patch("backend.main.clear_session_cookie"):
        r = asyncio.run(main.logout(request=req))
        mock_del.assert_called_once_with("abc123")
    assert r.status_code == 200


# --- logout without session_id cookie ---


def test_logout_without_session():
    req = types.SimpleNamespace(cookies={})
    with patch("backend.main.delete_session") as mock_del, patch("backend.main.clear_session_cookie"):
        r = asyncio.run(main.logout(request=req))
        mock_del.assert_not_called()
    assert r.status_code == 200


# --- get_me authenticated ---


def test_get_me_authenticated():
    req = types.SimpleNamespace()
    session = types.SimpleNamespace(user_email="test@example.com", user_name="Test", profile_picture_url="https://example.com/pic.jpg")
    with patch("backend.main.get_current_user", return_value=session):
        r = asyncio.run(main.get_me(request=req))
    assert r["is_authenticated"] is True
    assert r["email"] == "test@example.com"
    assert r["name"] == "Test"
    assert r["profile_picture_url"] == "https://example.com/pic.jpg"


def test_get_me_authenticated_without_picture():
    req = types.SimpleNamespace()
    session = types.SimpleNamespace(user_email="test@example.com", user_name="Test", profile_picture_url=None)
    with patch("backend.main.get_current_user", return_value=session):
        r = asyncio.run(main.get_me(request=req))
    assert r["is_authenticated"] is True
    assert r["profile_picture_url"] is None


# --- get_me unauthenticated ---


def test_get_me_unauthenticated():
    req = types.SimpleNamespace()
    with patch("backend.main.get_current_user", return_value=None):
        r = asyncio.run(main.get_me(request=req))
    assert r["is_authenticated"] is False


# --- get_feed_maker_manager AttributeError ---


def test_get_feed_maker_manager_attribute_error():
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace()))
    try:
        main.get_feed_maker_manager(req)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert "FeedMakerManager not initialized" in e.detail


# --- value_error_handler ---


def test_value_error_handler():
    req = types.SimpleNamespace()
    exc = ValueError("bad input")
    r = asyncio.run(main.value_error_handler(req, exc))
    assert isinstance(r, JSONResponse)
    assert r.status_code == 400


# --- exception_handler ---


def test_exception_handler():
    req = types.SimpleNamespace()
    exc = RuntimeError("unexpected")
    r = asyncio.run(main.exception_handler(req, exc))
    assert isinstance(r, JSONResponse)
    assert r.status_code == 500


# ────────────────────────────────────────────────────────
# From test_remaining_gaps.py: backend/main.py 추가 테스트
# ────────────────────────────────────────────────────────


class TestBackendLogin(unittest.TestCase):
    """Login endpoint: lines 121-132"""

    def test_login_success(self):
        with patch.object(bmain, "verify_facebook_token", return_value=True), patch.object(bmain, "Env") as mock_env, patch.object(bmain, "create_session", return_value="session123") as mock_create, patch.object(bmain, "set_session_cookie"):
            mock_env.get.return_value = "user@example.com"
            request = bmain.LoginRequest(email="user@example.com", name="User", access_token="tok", profile_picture_url="https://example.com/pic.jpg")
            response = asyncio.run(bmain.login(request))
            self.assertEqual(response.status_code, 200)
            mock_create.assert_called_once_with("user@example.com", "User", "tok", "https://example.com/pic.jpg")

    def test_login_create_session_exception(self):
        with patch.object(bmain, "verify_facebook_token", return_value=True), patch.object(bmain, "Env") as mock_env, patch.object(bmain, "create_session", side_effect=RuntimeError("db error")):
            mock_env.get.return_value = "user@example.com"
            request = bmain.LoginRequest(email="user@example.com", name="User", access_token="tok")

            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(bmain.login(request))
            self.assertEqual(ctx.exception.status_code, 500)


class TestBackendMiddleware(unittest.TestCase):
    """OPTIONS request: lines 62-63"""

    def test_options_request_passes_through(self):
        mock_request = MagicMock()
        mock_request.method = "OPTIONS"

        mock_response = MagicMock()

        async def mock_call_next(req):
            return mock_response

        response = asyncio.run(bmain.auth_middleware(mock_request, mock_call_next))
        self.assertEqual(response, mock_response)


class TestBackendExcepthook(unittest.TestCase):
    """handle_exception: line 85"""

    def test_handle_exception(self):
        try:
            raise ValueError("test error")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            bmain.handle_exception(exc_type, exc_value, exc_tb)


class TestBackendFailureEndpoints(unittest.TestCase):
    """Lines 305-307, 322-323, 337-338, 351-352, 385-386, 399-400"""

    def _make_failing_manager(self):
        mgr = MagicMock()
        mgr.extract_titles_from_public_feed.return_value = ("FILE_NOT_FOUND", "file not found")
        mgr.get_site_config.return_value = (None, "config error")
        mgr.save_site_config.return_value = (None, "save error")
        mgr.toggle_group.return_value = (None, "toggle error")
        mgr.toggle_feed.return_value = (None, "toggle feed error")
        mgr.run.return_value = (None, "run error")
        return mgr

    def test_extract_titles_failure(self):
        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.extract_titles_from_public_feed("f", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")
        self.assertEqual(r["error_code"], "FILE_NOT_FOUND")

    def test_get_site_config_failure(self):
        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.get_site_config("g", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_save_site_config_failure(self):
        bmain.require_admin = lambda _: None
        mgr = self._make_failing_manager()

        async def _json():
            return {}

        req = types.SimpleNamespace(json=_json)
        r = asyncio.run(bmain.save_site_config("g", request=req, feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_toggle_group_failure(self):
        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.toggle_group("g", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_toggle_feed_failure(self):
        mgr = self._make_failing_manager()
        r = asyncio.run(bmain.toggle_feed("g", "f", feed_maker_manager=mgr))
        self.assertEqual(r["status"], "failure")

    def test_run_feed_failure(self):
        bmain.require_admin = lambda _: None
        mgr = self._make_failing_manager()
        req = MagicMock()
        r = bmain.run_feed("g", "f", request=req, feed_maker_manager=mgr)
        self.assertEqual(r["status"], "failure")


# ────────────────────────────────────────────────────────
# From test_backend_auth_cookies.py: 세션 쿠키 테스트
# ────────────────────────────────────────────────────────


def test_set_and_clear_session_cookie():
    """세션 쿠키 설정 및 삭제 테스트 (SameSite=Lax로 CSRF 방어)"""
    r = JSONResponse({"ok": True})
    set_session_cookie(r, "sid")

    # Set-Cookie 헤더에 세션 쿠키가 포함되어야 함
    headers = [h.decode().lower() for k, h in r.raw_headers if k.decode().lower() == "set-cookie"]
    assert any(SESSION_COOKIE_NAME in h for h in headers)
    # SameSite=Lax 설정 확인
    assert any("samesite=lax" in h for h in headers)

    # clear
    clear_session_cookie(r)
    # After delete_cookie, response still valid
    assert r.status_code == 200


# ────────────────────────────────────────────────────────
# From test_backend_main_endpoints.py: 엔드포인트 직접 호출 테스트
# ────────────────────────────────────────────────────────


class DummyFeedMakerManagerEndpoints:
    def __init__(self):
        pass

    async def aclose(self):
        return None

    # exec result
    def get_exec_result(self):
        return ("# hello", None)

    # problems
    def get_problems_progress_info(self):
        return ([{"a": 1}], None)

    def get_problems_public_feed_info(self):
        return ([{"a": 2}], None)

    def get_problems_html_info(self):
        return ({"html_file_size_map": [], "html_file_with_many_image_tag_map": [], "html_file_without_image_tag_map": [], "html_file_image_not_found_map": []}, None)

    def get_problems_element_info(self):
        return ([{"b": 1}], None)

    def get_problems_list_url_info(self):
        return ([{"c": 1}], None)

    def get_problems_status_info(self):
        return ([{"status": 1}], None)

    # search
    def search(self, keyword):
        return ([{"feed_name": "feed1", "group_name": "g", "feed_title": "t"}], None)

    @classmethod
    def search_site(cls, keyword):
        return ([["title", "https://example.com"]], None)

    # public feeds
    def remove_public_feed(self, feed_name):
        return None

    def extract_titles_from_public_feed(self, feed_name):
        return (["t1", "t2"], None)

    # site config
    def get_site_config(self, group_name):
        return ({"k": 1}, None)

    def save_site_config(self, group_name, data):
        return (True, None)

    # toggle
    def toggle_group(self, group_name):
        return (f"_{group_name}", None)

    def toggle_feed(self, feed_name):
        return (f"_{feed_name}", None)

    # html operations
    def remove_html_file(self, group_name, feed_name, html_file_name):
        return None

    def remove_html(self, group_name, feed_name):
        return None

    # run/check/feed info
    def run(self, group_name, feed_name):
        return (True, None)

    def check_running(self, group_name, feed_name):
        return True

    def get_feed_info_by_name(self, group_name, feed_name):
        return ({"feed": {"name": feed_name}}, None)


def test_exec_and_search_and_problems_endpoints():
    # monkeypatch manager classmethod for search_site
    main.FeedMakerManager = DummyFeedMakerManagerEndpoints
    mgr = DummyFeedMakerManagerEndpoints()

    r = asyncio.run(main.get_exec_result(feed_maker_manager=mgr))
    assert r["status"] == "success"

    r = asyncio.run(main.get_problems(main.ProblemType.STATUS, feed_maker_manager=mgr))
    assert r["status"] == "success"

    r = asyncio.run(main.search("test", feed_maker_manager=mgr))
    assert r["status"] == "success" and "is_active" in r["feeds"][0]

    r = main.search_site("test")
    assert r["status"] == "success"


def test_group_and_feed_mutations_unit():
    main.FeedMakerManager = DummyFeedMakerManagerEndpoints
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManagerEndpoints()

    assert (asyncio.run(main.get_site_config("g", feed_maker_manager=mgr)))["status"] == "success"

    async def _json():
        return {"a": 1}

    req = types.SimpleNamespace(json=_json)
    assert (asyncio.run(main.save_site_config("g", request=req, feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.toggle_group("g", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.toggle_feed("g", "f", feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.extract_titles_from_public_feed("f", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.remove_public_feed("f", request=req, feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.remove_html_file("g", "f", "x.html", request=req, feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.remove_html("g", "f", request=req, feed_maker_manager=mgr)))["status"] == "success"

    assert main.run_feed("g", "f", request=req, feed_maker_manager=mgr)["status"] == "success"
    assert (asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr)))["status"] == "success"


def test_lifespan_startup_shutdown():
    """lifespan context manager: startup creates tables and manager, shutdown closes → covers L33-37"""
    from backend.main import lifespan, app as test_app

    with patch("backend.main.DB") as mock_db, patch("backend.main.FeedMakerManager") as mock_fmm_cls:
        mock_fmm = MagicMock()
        mock_fmm_cls.return_value = mock_fmm

        async def _run():
            async with lifespan(test_app):
                mock_db.create_all_tables.assert_called_once()
                assert test_app.state.feed_maker_manager is mock_fmm
            mock_fmm.aclose.assert_called_once()

        asyncio.run(_run())


class TestFeedServingEndpoints:
    """Feed serving + tracking pixel endpoints (auth-exempt)"""

    def test_serve_feed_returns_xml(self, tmp_path):
        xml_content = '<?xml version="1.0"?><rss><channel><title>Test</title></channel></rss>'
        xml_file = tmp_path / "testfeed.xml"
        xml_file.write_text(xml_content)

        with patch("backend.main.FEED_DIR", tmp_path), patch("backend.main.FEED_DIR_RESOLVED", tmp_path.resolve()), patch("backend.main.AccessLogManager.record_feed_access") as mock_record, patch("backend.main.get_current_user", return_value=None):
            response = client.get("/feed/testfeed.xml")
            assert response.status_code == 200
            assert "xml" in response.headers["content-type"]
            assert "<title>Test</title>" in response.text
            mock_record.assert_called_once_with("testfeed")

    def test_serve_feed_not_found(self, tmp_path):
        with patch("backend.main.FEED_DIR", tmp_path), patch("backend.main.FEED_DIR_RESOLVED", tmp_path.resolve()), patch("backend.main.get_current_user", return_value=None):
            response = client.get("/feed/nonexistent.xml")
            assert response.status_code == 404

    def test_serve_feed_path_traversal_blocked(self, tmp_path):
        with patch("backend.main.FEED_DIR", tmp_path), patch("backend.main.FEED_DIR_RESOLVED", tmp_path.resolve()), patch("backend.main.get_current_user", return_value=None):
            response = client.get("/feed/..%2F..%2Fetc%2Fpasswd.xml")
            assert response.status_code in (400, 404)

    def test_tracking_pixel_returns_image(self, tmp_path):
        img_dir = tmp_path / "img"
        img_dir.mkdir()
        pixel_file = img_dir / "1x1.jpg"
        pixel_file.write_bytes(b"\xff\xd8\xff\xe0")  # minimal JPEG header

        with patch("backend.main.TRACKING_PIXEL_PATH", pixel_file), patch("backend.main.AccessLogManager.record_item_view") as mock_record, patch("backend.main.get_current_user", return_value=None):
            response = client.get("/feed/img/1x1.jpg?feed=myfeed.xml&item=item001")
            assert response.status_code == 200
            assert "image" in response.headers["content-type"]
            mock_record.assert_called_once_with("myfeed")

    def test_tracking_pixel_without_item_param(self, tmp_path):
        img_dir = tmp_path / "img"
        img_dir.mkdir()
        pixel_file = img_dir / "1x1.jpg"
        pixel_file.write_bytes(b"\xff\xd8\xff\xe0")

        with patch("backend.main.TRACKING_PIXEL_PATH", pixel_file), patch("backend.main.AccessLogManager.record_item_view"), patch("backend.main.get_current_user", return_value=None):
            response = client.get("/feed/img/1x1.jpg?feed=myfeed.xml")
            assert response.status_code == 200

    def test_feed_endpoints_are_auth_exempt(self):
        """Verify /feed/ prefix is exempt from authentication"""
        from backend.main import _is_auth_exempt

        assert _is_auth_exempt("/feed/something.xml")
        assert _is_auth_exempt("/feed/img/1x1.jpg")
        assert not _is_auth_exempt("/groups")
        assert not _is_auth_exempt("/exec_result")


if __name__ == "__main__":
    pytest.main()
