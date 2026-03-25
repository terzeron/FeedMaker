#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock


from backend.auth import verify_facebook_token
import unittest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class TestVerifyFacebookToken:
    def test_valid_token(self):
        """유효한 토큰과 일치하는 이메일이면 True"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "user@example.com"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("valid_token", "user@example.com") is True

    def test_email_mismatch(self):
        """토큰의 이메일과 요청 이메일이 다르면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "real@example.com"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("valid_token", "fake@example.com") is False

    def test_invalid_token(self):
        """Facebook API가 오류 응답을 반환하면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("invalid_token", "user@example.com") is False

    def test_network_error(self):
        """네트워크 오류 시 False"""
        import requests

        with patch("backend.auth.http_requests.get", side_effect=requests.RequestException("timeout")):
            assert verify_facebook_token("token", "user@example.com") is False

    def test_no_email_in_response(self):
        """Facebook 응답에 email 필드가 없으면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "User"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("token", "user@example.com") is False


class TestGetCookieDomain(unittest.TestCase):
    @patch("backend.auth.Env.get")
    def test_normal_domain(self, mock_env) -> None:
        mock_env.return_value = "https://fm.terzeron.com"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        self.assertEqual(result, ".terzeron.com")

    @patch("backend.auth.Env.get")
    def test_localhost(self, mock_env) -> None:
        mock_env.return_value = "https://localhost:8080"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        self.assertIsNone(result)

    @patch("backend.auth.Env.get")
    def test_ip_address(self, mock_env) -> None:
        mock_env.return_value = "https://127.0.0.1:8080"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        self.assertIsNone(result)

    @patch("backend.auth.Env.get")
    def test_empty_url(self, mock_env) -> None:
        mock_env.return_value = ""
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        self.assertIsNone(result)

    @patch("backend.auth.Env.get")
    def test_no_hostname(self, mock_env) -> None:
        mock_env.return_value = "not-a-url"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        # urlparse may not extract hostname from malformed URL
        # Just check it doesn't crash
        self.assertTrue(result is None or isinstance(result, str))

    @patch("backend.auth.Env.get")
    def test_single_part_domain(self, mock_env) -> None:
        mock_env.return_value = "https://localhost"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        self.assertIsNone(result)


class TestGenerateSessionId(unittest.TestCase):
    def test_generates_unique_ids(self) -> None:
        from backend.auth import generate_session_id

        ids = {generate_session_id() for _ in range(100)}
        self.assertEqual(len(ids), 100)

    def test_reasonable_length(self) -> None:
        from backend.auth import generate_session_id

        sid = generate_session_id()
        self.assertGreater(len(sid), 32)


class TestCreateSession(unittest.TestCase):
    @patch("backend.auth.DB.session_ctx")
    def test_creates_session(self, mock_session_ctx) -> None:
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import create_session

        session_id = create_session("user@example.com", "User", "token123")
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 0)
        mock_session.add.assert_called_once()


class TestGetSession(unittest.TestCase):
    @patch("backend.auth.DB.session_ctx")
    def test_empty_session_id(self, mock_session_ctx) -> None:
        from backend.auth import get_session

        result = get_session("")
        self.assertIsNone(result)
        mock_session_ctx.assert_not_called()

    @patch("backend.auth.DB.session_ctx")
    def test_session_not_found(self, mock_session_ctx) -> None:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import get_session

        result = get_session("nonexistent_session_id")
        self.assertIsNone(result)

    @patch("backend.auth.DB.session_ctx")
    def test_expired_session(self, mock_session_ctx) -> None:
        mock_user_session = MagicMock()
        mock_user_session.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user_session
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import get_session

        result = get_session("expired_session_id")
        self.assertIsNone(result)
        mock_session.delete.assert_called_once_with(mock_user_session)

    @patch("backend.auth.DB.session_ctx")
    def test_valid_session(self, mock_session_ctx) -> None:
        mock_user_session = MagicMock()
        mock_user_session.expires_at = datetime.now(timezone.utc) + timedelta(days=10)
        mock_user_session.user_email = "user@example.com"
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user_session
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import get_session

        result = get_session("valid_session_id")
        self.assertIsNotNone(result)
        self.assertEqual(result.user_email, "user@example.com")

    @patch("backend.auth.DB.session_ctx")
    def test_timezone_naive_session(self, mock_session_ctx) -> None:
        """DB에서 timezone-naive datetime이 올 수 있음"""
        naive_dt = datetime(2099, 1, 1, 0, 0, 0)  # naive (no tzinfo)
        mock_user_session = MagicMock()
        mock_user_session.expires_at = naive_dt
        mock_user_session.user_email = "user@example.com"
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user_session
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import get_session

        result = get_session("naive_tz_session")
        self.assertIsNotNone(result)


class TestDeleteSession(unittest.TestCase):
    @patch("backend.auth.DB.session_ctx")
    def test_empty_session_id(self, mock_session_ctx) -> None:
        from backend.auth import delete_session

        result = delete_session("")
        self.assertFalse(result)

    @patch("backend.auth.DB.session_ctx")
    def test_delete_existing(self, mock_session_ctx) -> None:
        mock_user_session = MagicMock()
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user_session
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import delete_session

        result = delete_session("session_to_delete")
        self.assertTrue(result)
        mock_session.delete.assert_called_once()

    @patch("backend.auth.DB.session_ctx")
    def test_delete_nonexistent(self, mock_session_ctx) -> None:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import delete_session

        result = delete_session("nonexistent")
        self.assertFalse(result)


class TestCleanupExpiredSessions(unittest.TestCase):
    @patch("backend.auth.DB.session_ctx")
    def test_cleanup_returns_deleted_count(self, mock_session_ctx) -> None:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.delete.return_value = 5
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import cleanup_expired_sessions

        count = cleanup_expired_sessions()
        self.assertEqual(count, 5)
        # filter가 UserSession.expires_at 조건으로 호출되었는지 확인
        mock_session.query.assert_called_once()
        mock_session.query.return_value.filter.assert_called_once()

    @patch("backend.auth.DB.session_ctx")
    def test_cleanup_zero_expired(self, mock_session_ctx) -> None:
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.delete.return_value = 0
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import cleanup_expired_sessions

        count = cleanup_expired_sessions()
        self.assertEqual(count, 0)


class TestGetCurrentUser(unittest.TestCase):
    def test_no_cookie(self) -> None:
        request = MagicMock()
        request.cookies.get.return_value = None

        from backend.auth import get_current_user

        result = get_current_user(request)
        self.assertIsNone(result)

    @patch("backend.auth.get_session")
    def test_valid_cookie(self, mock_get_session) -> None:
        mock_user = MagicMock()
        mock_user.user_email = "user@example.com"
        mock_get_session.return_value = mock_user

        request = MagicMock()
        request.cookies.get.return_value = "valid_session"

        from backend.auth import get_current_user

        result = get_current_user(request)
        self.assertEqual(result.user_email, "user@example.com")

    @patch("backend.auth.get_session")
    def test_invalid_cookie(self, mock_get_session) -> None:
        mock_get_session.return_value = None

        request = MagicMock()
        request.cookies.get.return_value = "invalid_session"

        from backend.auth import get_current_user

        result = get_current_user(request)
        self.assertIsNone(result)


class TestRequireAuth(unittest.TestCase):
    @patch("backend.auth.get_current_user")
    def test_authenticated(self, mock_get_user) -> None:
        mock_user = MagicMock()
        mock_get_user.return_value = mock_user

        from backend.auth import require_auth

        result = require_auth(MagicMock())
        self.assertEqual(result, mock_user)

    @patch("backend.auth.get_current_user")
    def test_not_authenticated(self, mock_get_user) -> None:
        mock_get_user.return_value = None

        from backend.auth import require_auth

        with self.assertRaises(HTTPException) as ctx:
            require_auth(MagicMock())
        self.assertEqual(ctx.exception.status_code, 401)


class TestRequireAdmin(unittest.TestCase):
    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_admin_user(self, mock_auth, mock_env) -> None:
        mock_user = MagicMock()
        mock_user.user_email = "admin@example.com"
        mock_auth.return_value = mock_user
        mock_env.return_value = "admin@example.com,other@example.com"

        from backend.auth import require_admin

        result = require_admin(MagicMock())
        self.assertEqual(result, mock_user)

    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_non_admin_user(self, mock_auth, mock_env) -> None:
        mock_user = MagicMock()
        mock_user.user_email = "nobody@example.com"
        mock_auth.return_value = mock_user
        mock_env.return_value = "admin@example.com"

        from backend.auth import require_admin

        with self.assertRaises(HTTPException) as ctx:
            require_admin(MagicMock())
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_empty_admin_list_allows_all(self, mock_auth, mock_env) -> None:
        """ADMIN_EMAILS 미설정 시 모든 인증된 사용자를 허용하는 의도적 동작.
        보안 관점: 초기 설정 전이나 개발 환경에서 admin 제한 없이 운영하기 위함."""
        mock_user = MagicMock()
        mock_user.user_email = "anyone@example.com"
        mock_auth.return_value = mock_user
        mock_env.return_value = ""

        from backend.auth import require_admin

        result = require_admin(MagicMock())
        self.assertEqual(result, mock_user)


class TestSetAndClearSessionCookie(unittest.TestCase):
    def test_set_session_cookie(self) -> None:
        from backend.auth import set_session_cookie

        response = MagicMock()
        set_session_cookie(response, "test_session_id")
        response.set_cookie.assert_called_once()
        call_kwargs = response.set_cookie.call_args
        self.assertEqual(call_kwargs.kwargs.get("key") or call_kwargs[1].get("key", call_kwargs[0][0] if call_kwargs[0] else None), "session_id")

    def test_clear_session_cookie(self) -> None:
        from backend.auth import clear_session_cookie

        response = MagicMock(spec=JSONResponse)
        clear_session_cookie(response)
        response.delete_cookie.assert_called_once()


class TestGetCookieDomainSinglePartHost(unittest.TestCase):
    """get_cookie_domain: single-part host that is not localhost/IP → covers L51"""

    @patch("backend.auth.Env.get")
    def test_single_part_non_localhost(self, mock_env) -> None:
        # "intranet" hostname - single part, not localhost, not IP
        mock_env.return_value = "https://intranet"
        from backend.auth import get_cookie_domain

        result = get_cookie_domain()
        # len(parts) == 1, so falls through to return None at line 51
        self.assertIsNone(result)
