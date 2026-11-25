"""허용 목록 변경이 기존 세션과 HTTP 인증에 즉시 적용되는지 검사한다."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import URL
from sqlalchemy.pool import StaticPool

from backend import auth, main
from bin.db import _DataSource
from bin.models import UserSession


@pytest.fixture
def session_store(monkeypatch):
    # 운영 DB 설정을 사용하지 않고 실제 commit/delete 경로를 검사한다.
    source = _DataSource(URL.create("sqlite", database=":memory:"), poolclass=StaticPool, connect_args={"check_same_thread": False})
    UserSession.__table__.create(source.engine)
    monkeypatch.setattr(auth.DB, "session_ctx", source.session)
    monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "user@example.com")
    monkeypatch.setenv("FM_ADMIN_EMAIL_LIST", "")
    try:
        yield source
    finally:
        source.dispose()


def test_removed_account_session_is_persistently_revoked(session_store, monkeypatch):
    session_id = auth.create_session("user@example.com", "User")
    assert auth.get_session(session_id) is not None

    monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "other@example.com")
    assert auth.get_session(session_id) is None
    with session_store.session() as session:
        assert session.get(UserSession, session_id) is None

    # 다시 허용해도 이미 폐기한 쿠키는 다시 유효해지지 않는다.
    monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "user@example.com")
    assert auth.get_session(session_id) is None


@pytest.mark.parametrize("allowed", [None, "", " \t, , "])
def test_missing_or_empty_allowlist_revokes_session(session_store, monkeypatch, allowed):
    session_id = auth.create_session("user@example.com", "User")
    # 관리자 목록을 별도로 유지해도 로그인 허용 목록을 우회할 수 없다.
    monkeypatch.setenv("FM_ADMIN_EMAIL_LIST", "user@example.com")
    if allowed is None:
        monkeypatch.delenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST")
    else:
        monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", allowed)

    assert auth.get_session(session_id) is None
    with session_store.session() as session:
        assert session.get(UserSession, session_id) is None


def test_still_allowed_account_keeps_session(session_store, monkeypatch):
    removed_id = auth.create_session("removed@example.com", "Removed")
    allowed_id = auth.create_session("user@example.com", "User")
    monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", " user@example.com, other@example.com ")

    assert auth.get_session(removed_id) is None
    allowed = auth.get_session(allowed_id)
    assert allowed is not None
    assert allowed.user_email == "user@example.com"
    with session_store.session() as session:
        assert session.get(UserSession, removed_id) is None
        assert session.get(UserSession, allowed_id) is not None


@pytest.mark.parametrize("method,path", [("GET", "/groups"), ("DELETE", "/groups/revoked-test")])
def test_revoked_session_cannot_read_or_write_and_reports_logged_out(session_store, monkeypatch, method, path):
    session_id = auth.create_session("user@example.com", "User")
    manager = MagicMock()
    manager.get_groups.return_value = ([], None)
    monkeypatch.setattr(main.app, "dependency_overrides", {main.get_feed_maker_manager: lambda: manager})
    monkeypatch.setattr(main, "origins", ["https://fm.example.test"])
    client = TestClient(main.app, base_url="https://fm.example.test", headers={"Origin": "https://fm.example.test"})
    client.cookies.set(auth.SESSION_COOKIE_NAME, session_id)
    try:
        assert client.get("/auth/me").json()["is_authenticated"] is True
        monkeypatch.setenv("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "other@example.com")

        response = client.request(method, path)
        assert response.status_code == 401
        assert "set-cookie" not in response.headers
        assert client.get("/auth/me").json() == {"is_authenticated": False}
        manager.get_groups.assert_not_called()
        manager.remove_group.assert_not_called()
        with session_store.session() as session:
            assert session.get(UserSession, session_id) is None
    finally:
        client.close()
