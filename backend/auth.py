#!/usr/bin/env python
# -*- coding: utf-8 -*-

import secrets
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import requests as http_requests
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from bin.db import DB
from bin.models import UserSession
from bin.feed_maker_util import Env
from backend.audit import audit_log

LOGGER = logging.getLogger(__name__)

# Session configuration
SESSION_COOKIE_NAME = "__Host-fm_session"
SESSION_EXPIRY_DAYS = 30
# 생성 시점 기준 절대 상한. sliding 갱신으로도 이 시각을 넘길 수 없어, 탈취된 세션이
# 접근만으로 무기한 연장되는 것을 막는다.
SESSION_MAX_LIFETIME_DAYS = 30
COOKIE_MAX_AGE = SESSION_EXPIRY_DAYS * 24 * 60 * 60  # seconds


def _as_utc(value: datetime) -> datetime:
    """DB에서 온 timezone-naive datetime을 UTC로 간주해 aware datetime으로 만든다."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def get_cookie_domain() -> Optional[str]:
    """API host 전용 쿠키: Domain 속성을 발급하지 않는다."""
    return None


# 쿠키 도메인 (앱 시작 시 한 번만 계산)
COOKIE_DOMAIN = get_cookie_domain()


def _reject_facebook_token(reason: str) -> bool:
    """거부 사유만 남긴다. token·응답 본문은 credential일 수 있어 기록하지 않는다."""
    LOGGER.warning("Facebook token verification rejected: %s", reason)
    return False


def verify_facebook_token(access_token: str, expected_email: str) -> bool:
    """토큰의 앱, 사용자, 만료와 이메일을 확인한다. 설정 누락은 거부한다."""
    app_id = Env.get("FM_FACEBOOK_APP_ID", "")
    app_secret = Env.get("FM_FACEBOOK_APP_SECRET", "")
    if not app_id or not app_secret:
        LOGGER.error("Facebook app credentials are not configured")
        return False
    try:
        response = http_requests.get("https://graph.facebook.com/debug_token", params={"input_token": access_token}, headers={"Authorization": f"Bearer {app_id}|{app_secret}"}, timeout=10)
        if response.status_code != 200:
            return _reject_facebook_token(f"debug_token status {response.status_code}")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            return _reject_facebook_token("debug_token payload malformed")
        if data.get("is_valid") is not True:
            return _reject_facebook_token("token not valid")
        if data.get("app_id") != app_id:
            return _reject_facebook_token("token issued for another app")
        if data.get("type") != "USER" or not data.get("user_id"):
            return _reject_facebook_token("not a user token")
        now = datetime.now(timezone.utc).timestamp()
        expires_at = data.get("expires_at")
        if type(expires_at) is not int or expires_at <= now:
            return _reject_facebook_token("token expired")
        data_expires = data.get("data_access_expires_at", 0)
        if type(data_expires) is not int or data_expires < 0 or (data_expires != 0 and data_expires <= now):
            return _reject_facebook_token("data access expired")
        response = http_requests.get("https://graph.facebook.com/me", params={"fields": "id,email"}, headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        if response.status_code != 200:
            return _reject_facebook_token(f"me status {response.status_code}")
        user = response.json()
        if not isinstance(user, dict) or user.get("id") != data["user_id"]:
            return _reject_facebook_token("user id mismatch")
        if user.get("email") != expected_email:
            return _reject_facebook_token("email mismatch")
        return True
    except (http_requests.RequestException, ValueError) as e:
        # URL과 응답·예외 본문에는 credential이 포함될 수 있다.
        LOGGER.error("Facebook token verification failed: %s", type(e).__name__)
        return False


def generate_session_id() -> str:
    """Generate a secure random session ID"""
    return secrets.token_urlsafe(48)


def create_session(user_email: str, user_name: str, profile_picture_url: Optional[str] = None) -> str:
    """Create a new session in the database and return session ID"""
    session_id = generate_session_id()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=SESSION_EXPIRY_DAYS)

    with DB.session_ctx() as session:
        # created_at은 절대 상한 계산의 기준이므로 server_default에 맡기지 않고 명시적으로 채운다.
        user_session = UserSession(session_id=session_id, user_email=user_email, user_name=user_name, profile_picture_url=profile_picture_url, created_at=now, expires_at=expires_at)
        session.add(user_session)

    LOGGER.info(f"Created session for user {user_email}")
    return session_id


def get_session(session_id: str) -> Optional[UserSession]:
    """Get session from database and validate expiry"""
    if not session_id:
        LOGGER.warning("get_session: Empty session_id provided")
        return None

    LOGGER.debug("get_session: Looking up session_id %s...", session_id[:8])
    with DB.session_ctx() as session:
        user_session = session.query(UserSession).filter(UserSession.session_id == session_id).first()

        if not user_session:
            LOGGER.warning("get_session: No session found for %s...", session_id[:8])
            return None

        # Check if session is expired
        # DB에서 가져온 datetime이 timezone-naive일 수 있으므로 UTC로 처리
        expires_at = _as_utc(user_session.expires_at)
        now = datetime.now(timezone.utc)

        if expires_at < now:
            LOGGER.info("Session %s... expired", session_id[:8])
            session.delete(user_session)
            return None

        # 생성 시점 기준 절대 상한. 상한을 넘긴 세션은 sliding 갱신 대상이 아니라 폐기 대상이다.
        created_at = user_session.created_at
        if isinstance(created_at, datetime):
            max_expires_at: Optional[datetime] = _as_utc(created_at) + timedelta(days=SESSION_MAX_LIFETIME_DAYS)
        else:
            # created_at은 NOT NULL이라 정상 경로에서는 발생하지 않는다. 상한을 적용할 근거가
            # 없을 때 전체 사용자를 잠그지는 않되, 조용히 넘기지 않도록 경고를 남긴다.
            LOGGER.warning("Session %s... has no usable created_at; absolute lifetime cap not applied", session_id[:8])
            max_expires_at = None

        if max_expires_at is not None and max_expires_at < now:
            LOGGER.info("Session %s... reached absolute lifetime limit (%d days)", session_id[:8], SESSION_MAX_LIFETIME_DAYS)
            session.delete(user_session)
            return None

        # Sliding session: extend expiry on every access (절대 상한 이내로만)
        user_session.last_accessed_at = now
        new_expires_at = now + timedelta(days=SESSION_EXPIRY_DAYS)
        user_session.expires_at = min(new_expires_at, max_expires_at) if max_expires_at is not None else new_expires_at
        LOGGER.info(f"get_session: Valid session found for {user_session.user_email}")

        return user_session


def delete_session(session_id: str) -> bool:
    """Delete session from database"""
    if not session_id:
        return False

    with DB.session_ctx() as session:
        user_session = session.query(UserSession).filter(UserSession.session_id == session_id).first()

        if user_session:
            session.delete(user_session)
            LOGGER.info("Deleted session %s...", session_id[:8])
            return True

    return False


def cleanup_expired_sessions() -> int:
    """Clean up expired sessions from database"""
    now = datetime.now(timezone.utc)
    with DB.session_ctx() as session:
        count = session.query(UserSession).filter(UserSession.expires_at < now).delete()
        LOGGER.info(f"Cleaned up {count} expired sessions")
        return count


def get_current_user(request: Request) -> Optional[UserSession]:
    """Get current authenticated user from session cookie"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        LOGGER.debug("get_current_user: No session_id cookie found")
        return None

    user_session = get_session(session_id)
    if user_session:
        LOGGER.debug("get_current_user: Valid session for %s", user_session.user_email)
    else:
        LOGGER.warning("get_current_user: Invalid session %s...", session_id[:8])
    return user_session


def require_auth(request: Request) -> UserSession:
    """Dependency that requires authentication"""
    user_session = get_current_user(request)
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user_session


def get_login_allowed_email_set() -> set[str]:
    raw = Env.get("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "")
    return {email.strip() for email in raw.split(",") if email.strip()}


def _get_admin_email_set() -> set[str]:
    """관리자 이메일 집합.

    이 서비스는 운영자 전용이고 비관리자 role이 존재하지 않으므로, 기본 모델은
    '로그인 가능 == 관리자'다(로그인 허용 목록 자체가 권한 경계다).
    운영자가 아닌 계정을 로그인 허용 목록에 추가해야 할 때만 FM_ADMIN_EMAIL_LIST로
    관리자를 좁힌다(opt-in). 미설정은 정상 상태이므로 경고하지 않는다.
    """
    raw = Env.get("FM_ADMIN_EMAIL_LIST", "").strip()
    if raw:
        return {email.strip() for email in raw.split(",") if email.strip()}
    return get_login_allowed_email_set()


def require_admin(request: Request) -> UserSession:
    """Dependency that requires admin privileges"""
    user_session = require_auth(request)
    admin_emails = _get_admin_email_set()
    if not admin_emails or user_session.user_email not in admin_emails:
        audit_log("admin_denied", email=user_session.user_email, outcome="forbidden", request=request)
        raise HTTPException(status_code=403, detail="Not authorized")
    audit_log("admin_action", email=user_session.user_email, outcome="authorized", request=request)
    return user_session


# --- Brute-force 방어: 로그인 실패 기반 계정 잠금 (인메모리) ---
LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT_MINUTES = 15
_login_fail_lock = threading.Lock()
# key -> {"count": int, "locked_until": Optional[datetime]}
_login_failures: dict[str, dict[str, Any]] = {}


def _login_fail_key(email: str, client_ip: str) -> str:
    return f"{email.lower()}|{client_ip}"


def is_login_locked(email: str, client_ip: str) -> bool:
    """현재 잠금 상태면 True. 만료된 잠금은 자동 해제한다."""
    key = _login_fail_key(email, client_ip)
    now = datetime.now(timezone.utc)
    with _login_fail_lock:
        entry = _login_failures.get(key)
        if not entry:
            return False
        locked_until = entry.get("locked_until")
        if locked_until and locked_until > now:
            return True
        if locked_until and locked_until <= now:
            _login_failures.pop(key, None)
        return False


def record_login_failure(email: str, client_ip: str) -> None:
    """로그인 실패 1회 기록. 임계치 도달 시 잠금을 건다."""
    key = _login_fail_key(email, client_ip)
    now = datetime.now(timezone.utc)
    with _login_fail_lock:
        entry = _login_failures.get(key) or {"count": 0, "locked_until": None}
        entry["count"] += 1
        if entry["count"] >= LOGIN_MAX_FAILURES:
            entry["locked_until"] = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        _login_failures[key] = entry


def reset_login_failures(email: str, client_ip: str) -> None:
    """로그인 성공 시 실패 카운터를 초기화한다."""
    key = _login_fail_key(email, client_ip)
    with _login_fail_lock:
        _login_failures.pop(key, None)


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie with secure flags"""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # Prevent XSS attacks
        secure=True,  # HTTPS only
        samesite="lax",  # same-site CSRF는 Origin 검증으로 차단
        path="/",
        domain=COOKIE_DOMAIN,  # None: host 전용
    )


def clear_session_cookie(response: JSONResponse) -> None:
    """Clear session cookie"""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=COOKIE_DOMAIN,  # Must match the domain used when setting
        # __Host- 쿠키는 Secure 없는 Set-Cookie를 브라우저가 거부한다. 삭제에도 필요하다.
        secure=True,
        httponly=True,
    )
