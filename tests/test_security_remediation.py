"""Regression tests for browser and Facebook trust boundaries."""

from unittest.mock import MagicMock, patch
import time

import pytest
from fastapi.testclient import TestClient
from fastapi.responses import Response
from backend import auth, main


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize("origin", [None, "null", "https://blog.terzeron.com", "https://fm.terzeron.com.evil.example"])
def test_csrf_rejects_unsafe_requests(method, origin):
    headers = {} if origin is None else {"Origin": origin}
    with patch.object(main, "get_current_user", return_value=MagicMock()):
        response = TestClient(main.app).request(method, "/auth/logout", headers=headers)
    assert response.status_code == 403


def test_allowed_origin_logout():
    with patch.object(main, "origins", ["https://fm.terzeron.com"]), patch.object(main, "delete_session"):
        response = TestClient(main.app).post("/auth/logout", headers={"Origin": "https://fm.terzeron.com"})
    assert response.status_code == 200


def test_cookie_host_boundary():
    response = Response()
    auth.set_session_cookie(response, "test")
    cookie = response.headers["set-cookie"]
    assert "__Host-" in cookie
    assert "Domain=" not in cookie
    assert "Secure" in cookie and "HttpOnly" in cookie and "Path=/" in cookie


def token_response(data):
    return MagicMock(status_code=200, json=MagicMock(return_value=data))


@pytest.mark.parametrize("changes", [{"app_id": "other"}, {"is_valid": False}, {"expires_at": 1}, {"user_id": ""}, {"type": "PAGE"}, {"expires_at": "bad"}, {"data_access_expires_at": 1}])
def test_facebook_rejects_untrusted_debug_data(changes):
    data = {"app_id": "app", "is_valid": True, "type": "USER", "user_id": "user", "expires_at": int(time.time()) + 3600}
    data.update(changes)
    with patch.object(auth.Env, "get", side_effect=lambda key, default="": {"FM_FACEBOOK_APP_ID": "app", "FM_FACEBOOK_APP_SECRET": "secret"}.get(key, default)), patch.object(auth.http_requests, "get", return_value=token_response({"data": data})) as get:
        assert auth.verify_facebook_token("token", "user@example.com") is False
        assert get.call_count == 1


def test_facebook_validates_user_and_app():
    data = {"app_id": "app", "is_valid": True, "type": "USER", "user_id": "user", "expires_at": int(time.time()) + 3600}
    with patch.object(auth.Env, "get", side_effect=lambda key, default="": {"FM_FACEBOOK_APP_ID": "app", "FM_FACEBOOK_APP_SECRET": "secret"}.get(key, default)), patch.object(auth.http_requests, "get", side_effect=[token_response({"data": data}), token_response({"id": "user", "email": "user@example.com"})]):
        assert auth.verify_facebook_token("token", "user@example.com") is True


def test_facebook_missing_config_fails_closed():
    with patch.object(auth.Env, "get", return_value=""), patch.object(auth.http_requests, "get") as get:
        assert auth.verify_facebook_token("token", "user@example.com") is False
        get.assert_not_called()


@pytest.mark.parametrize("user", [{"id": "other", "email": "user@example.com"}, {"id": "user", "email": "other@example.com"}, [], None])
def test_facebook_rejects_mismatched_identity(user):
    data = {"app_id": "app", "is_valid": True, "type": "USER", "user_id": "user", "expires_at": int(time.time()) + 3600}
    with patch.object(auth.Env, "get", side_effect=lambda key, default="": {"FM_FACEBOOK_APP_ID": "app", "FM_FACEBOOK_APP_SECRET": "secret"}.get(key, default)), patch.object(auth.http_requests, "get", side_effect=[token_response({"data": data}), token_response(user)]):
        assert auth.verify_facebook_token("token", "user@example.com") is False


@pytest.mark.parametrize("peer,expected", [("10.1.202.68", "198.51.100.7"), ("203.0.113.1", "203.0.113.1")])
def test_proxy_trust_chain(peer, expected):
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    async def echo(scope, receive, send):
        await Response(scope["client"][0])(scope, receive, send)

    app = ProxyHeadersMiddleware(echo, trusted_hosts="127.0.0.1,10.1.0.0/16")
    client = TestClient(app, client=(peer, 1234))
    response = client.get("/", headers={"X-Forwarded-For": "192.0.2.123, 198.51.100.7, 10.1.202.72"})
    assert response.text == expected


def test_proxy_runs_before_auth_and_rate_limit():
    stack = [m.cls.__name__ for m in main.app.user_middleware]
    assert stack.index("ProxyHeadersMiddleware") < stack.index("BaseHTTPMiddleware")


def test_legacy_domain_cookie_is_not_accepted():
    request = MagicMock(cookies={"session_id": "legacy"})
    with patch.object(auth, "get_session") as get:
        assert auth.get_current_user(request) is None
        get.assert_not_called()


def test_text_plain_json_from_other_subdomain_rejected():
    client = TestClient(main.app)
    response = client.post("/auth/login", content='{"email":"admin@example.com"}', headers={"Origin": "https://blog.terzeron.com", "Content-Type": "text/plain"})
    assert response.status_code == 403


def test_api_responses_carry_hsts():
    response = TestClient(main.app).get("/auth/me")
    assert response.headers["strict-transport-security"] == "max-age=31536000"


def test_facebook_rejection_logs_reason_without_token():
    data = {"app_id": "other", "is_valid": True, "type": "USER", "user_id": "user", "expires_at": int(time.time()) + 3600}
    with patch.object(auth.Env, "get", side_effect=lambda key, default="": {"FM_FACEBOOK_APP_ID": "app", "FM_FACEBOOK_APP_SECRET": "secret"}.get(key, default)), patch.object(auth.http_requests, "get", return_value=token_response({"data": data})), patch.object(auth, "LOGGER") as logger:
        assert auth.verify_facebook_token("secret-token-value", "user@example.com") is False
    logged = " ".join(str(arg) for call in logger.warning.call_args_list for arg in call.args)
    assert "token issued for another app" in logged
    assert "secret-token-value" not in logged
