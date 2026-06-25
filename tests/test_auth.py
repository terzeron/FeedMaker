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

    def test_network_error_does_not_log_access_token(self):
        """네트워크 오류 로깅 시 access_token이 로그 메시지에 노출되면 안 된다"""
        import requests

        secret = "SECRET_FB_TOKEN_VALUE"
        # requests 예외 메시지에 토큰이 포함된 URL이 들어가는 상황을 모사
        exc = requests.RequestException(f"Failed to connect to https://graph.facebook.com/me?access_token={secret}")
        with patch("backend.auth.http_requests.get", side_effect=exc), patch("backend.auth.LOGGER") as mock_logger:
            assert verify_facebook_token(secret, "user@example.com") is False
            logged = " ".join(repr(c.args) for c in mock_logger.error.call_args_list)
            assert secret not in logged, f"access_token leaked into log: {logged}"

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

        session_id = create_session("user@example.com", "User")
        self.assertIsInstance(session_id, str)
        self.assertGreater(len(session_id), 0)
        mock_session.add.assert_called_once()

    @patch("backend.auth.DB.session_ctx")
    def test_facebook_token_not_stored(self, mock_session_ctx) -> None:
        """Facebook access token은 DB에 저장되지 않아야 한다"""
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import create_session

        create_session("user@example.com", "User")
        stored_obj = mock_session.add.call_args[0][0]
        self.assertFalse(hasattr(stored_obj, "facebook_access_token"))

    def test_usersession_model_has_no_token_column(self) -> None:
        """UserSession 모델에 facebook_access_token 컬럼이 없어야 한다"""
        from bin.models import UserSession

        columns = {c.key for c in UserSession.__table__.columns}
        self.assertNotIn("facebook_access_token", columns)

    @patch("backend.auth.DB.session_ctx")
    def test_existing_sessions_preserved_on_login(self, mock_session_ctx) -> None:
        """재로그인 시 동일 계정의 다른 장치 세션은 삭제되지 않는다"""
        mock_session = MagicMock()
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import create_session

        create_session("user@example.com", "User")
        mock_session.query.return_value.filter.return_value.delete.assert_not_called()


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
    def test_sliding_session_extends_expires_at(self, mock_session_ctx) -> None:
        """유효한 세션 접근 시 expires_at이 SESSION_EXPIRY_DAYS만큼 연장된다"""
        mock_user_session = MagicMock()
        original_expires = datetime.now(timezone.utc) + timedelta(days=5)
        mock_user_session.expires_at = original_expires
        mock_user_session.user_email = "user@example.com"
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_user_session
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import SESSION_EXPIRY_DAYS, get_session

        get_session("valid_session_id")

        new_expires = mock_user_session.expires_at
        self.assertGreater(new_expires, original_expires)
        min_expected = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS - 1)
        self.assertGreater(new_expires, min_expected)

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

    @patch("backend.auth.DB.session_ctx")
    def test_cleanup_uses_timezone_aware_now(self, mock_session_ctx) -> None:
        """cleanup_expired_sessions가 timezone-aware datetime으로 필터한다.

        get_session()과 동일한 방식(UTC-aware)으로 처리해야 한다.
        """
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.delete.return_value = 0
        mock_session_ctx.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_session_ctx.return_value.__exit__ = MagicMock(return_value=None)

        from backend.auth import cleanup_expired_sessions
        import backend.auth as auth_module

        captured: list[datetime] = []
        original_now = datetime.now

        def capturing_now(tz=None):
            result = original_now(tz)
            if tz is not None:
                captured.append(result)
            return result

        with patch.object(auth_module, "datetime", wraps=auth_module.datetime) as mock_dt:
            mock_dt.now.side_effect = capturing_now
            cleanup_expired_sessions()

        self.assertTrue(mock_dt.now.called, "datetime.now must be called")
        call_args = mock_dt.now.call_args
        tz_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("tz") or call_args.kwargs.get("timezone")
        self.assertIsNotNone(tz_arg, "cleanup_expired_sessions must pass a timezone to datetime.now")


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
    def test_empty_admin_list_denies_all(self, mock_auth, mock_env) -> None:
        """ADMIN_EMAILS 미설정 시 모든 사용자를 거부 — admin list 없으면 아무도 admin이 아님."""
        mock_user = MagicMock()
        mock_user.user_email = "anyone@example.com"
        mock_auth.return_value = mock_user
        mock_env.return_value = ""

        from backend.auth import require_admin

        with self.assertRaises(HTTPException) as ctx:
            require_admin(MagicMock())
        self.assertEqual(ctx.exception.status_code, 403)


class TestSetAndClearSessionCookie(unittest.TestCase):
    def test_set_session_cookie(self) -> None:
        from backend.auth import set_session_cookie

        response = MagicMock()
        set_session_cookie(response, "test_session_id")
        response.set_cookie.assert_called_once()
        kwargs = response.set_cookie.call_args.kwargs
        self.assertEqual(kwargs["key"], "session_id")
        self.assertTrue(kwargs.get("httponly"), "httponly must be True")
        self.assertTrue(kwargs.get("secure"), "secure must be True")

    def test_clear_session_cookie(self) -> None:
        from backend.auth import clear_session_cookie

        response = MagicMock(spec=JSONResponse)
        clear_session_cookie(response)
        response.delete_cookie.assert_called_once()


class TestRequireAdminRoleSeparation(unittest.TestCase):
    """A4: FM_ADMIN_EMAIL_LIST로 '로그인 가능 != 관리자' 분리."""

    @staticmethod
    def _env_side(values):
        def _get(key, default=""):
            return values.get(key, default)

        return _get

    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_login_allowed_but_not_admin(self, mock_auth, mock_env) -> None:
        """로그인 허용 목록에는 있지만 admin 목록에 없으면 403."""
        mock_user = MagicMock()
        mock_user.user_email = "user@example.com"
        mock_auth.return_value = mock_user
        mock_env.side_effect = self._env_side({"FM_ADMIN_EMAIL_LIST": "admin@example.com", "FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST": "admin@example.com,user@example.com"})

        from backend.auth import require_admin

        with self.assertRaises(HTTPException) as ctx:
            require_admin(MagicMock())
        self.assertEqual(ctx.exception.status_code, 403)

    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_admin_in_admin_list(self, mock_auth, mock_env) -> None:
        mock_user = MagicMock()
        mock_user.user_email = "admin@example.com"
        mock_auth.return_value = mock_user
        mock_env.side_effect = self._env_side({"FM_ADMIN_EMAIL_LIST": "admin@example.com", "FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST": "admin@example.com,user@example.com"})

        from backend.auth import require_admin

        result = require_admin(MagicMock())
        self.assertEqual(result, mock_user)

    @patch("backend.auth.Env.get")
    @patch("backend.auth.require_auth")
    def test_fallback_to_login_list_when_admin_list_unset(self, mock_auth, mock_env) -> None:
        """FM_ADMIN_EMAIL_LIST 미설정 시 로그인 허용 목록으로 폴백(하위 호환)."""
        mock_user = MagicMock()
        mock_user.user_email = "user@example.com"
        mock_auth.return_value = mock_user
        mock_env.side_effect = self._env_side({"FM_ADMIN_EMAIL_LIST": "", "FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST": "user@example.com"})

        from backend.auth import require_admin

        result = require_admin(MagicMock())
        self.assertEqual(result, mock_user)


class TestLoginLockout(unittest.TestCase):
    """A3: 로그인 실패 기반 인메모리 계정 잠금."""

    def setUp(self) -> None:
        import backend.auth as auth_module

        auth_module._login_failures.clear()

    def test_locks_after_max_failures(self) -> None:
        from backend.auth import LOGIN_MAX_FAILURES, is_login_locked, record_login_failure

        email, ip = "victim@example.com", "1.2.3.4"
        self.assertFalse(is_login_locked(email, ip))
        for _ in range(LOGIN_MAX_FAILURES):
            record_login_failure(email, ip)
        self.assertTrue(is_login_locked(email, ip))

    def test_reset_clears_lock(self) -> None:
        from backend.auth import LOGIN_MAX_FAILURES, is_login_locked, record_login_failure, reset_login_failures

        email, ip = "victim2@example.com", "1.2.3.4"
        for _ in range(LOGIN_MAX_FAILURES):
            record_login_failure(email, ip)
        self.assertTrue(is_login_locked(email, ip))
        reset_login_failures(email, ip)
        self.assertFalse(is_login_locked(email, ip))

    def test_below_threshold_not_locked(self) -> None:
        from backend.auth import LOGIN_MAX_FAILURES, is_login_locked, record_login_failure

        email, ip = "victim3@example.com", "1.2.3.4"
        for _ in range(LOGIN_MAX_FAILURES - 1):
            record_login_failure(email, ip)
        self.assertFalse(is_login_locked(email, ip))

    def test_expired_lock_auto_released(self) -> None:
        """locked_until 이 과거면 자동 해제된다."""
        import backend.auth as auth_module
        from backend.auth import is_login_locked

        key = auth_module._login_fail_key("victim4@example.com", "1.2.3.4")
        auth_module._login_failures[key] = {"count": 99, "locked_until": datetime.now(timezone.utc) - timedelta(minutes=1)}
        self.assertFalse(is_login_locked("victim4@example.com", "1.2.3.4"))


class TestAuditLog(unittest.TestCase):
    """A2: 구조화 audit 로그 출력."""

    def test_emits_structured_json(self) -> None:
        from backend.audit import audit_log

        with self.assertLogs("audit", level="INFO") as cm:
            audit_log("login_success", email="user@example.com", outcome="success")
        joined = "\n".join(cm.output)
        self.assertIn("AUDIT", joined)
        self.assertIn("login_success", joined)
        self.assertIn("user@example.com", joined)

    def test_does_not_raise_on_magicmock_request(self) -> None:
        """request가 직렬화 불가 객체여도 예외를 던지지 않는다."""
        from backend.audit import audit_log

        with self.assertLogs("audit", level="INFO"):
            audit_log("admin_action", email="a@b.com", outcome="authorized", request=MagicMock())


class TestRedactHeaders(unittest.TestCase):
    """A1: 로그용 민감 헤더 마스킹."""

    def test_masks_sensitive_headers(self) -> None:
        from bin.feed_maker_util import redact_headers

        result = redact_headers({"Authorization": "Bearer secret", "Cookie": "sid=abc", "User-Agent": "x"})
        self.assertEqual(result["Authorization"], "***REDACTED***")
        self.assertEqual(result["Cookie"], "***REDACTED***")
        self.assertEqual(result["User-Agent"], "x")

    def test_case_insensitive(self) -> None:
        from bin.feed_maker_util import redact_headers

        result = redact_headers({"authorization": "Bearer x"})
        self.assertEqual(result["authorization"], "***REDACTED***")

    def test_none_returns_empty(self) -> None:
        from bin.feed_maker_util import redact_headers

        self.assertEqual(redact_headers(None), {})


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
