#!/usr/bin/env python
# -*- coding: utf-8 -*-

import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse
import requests as http_requests
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from bin.db import DB
from bin.models import UserSession
from bin.feed_maker_util import Env

LOGGER = logging.getLogger(__name__)

# Session configuration
SESSION_COOKIE_NAME = "session_id"
SESSION_EXPIRY_DAYS = 30
COOKIE_MAX_AGE = SESSION_EXPIRY_DAYS * 24 * 60 * 60  # seconds


def get_cookie_domain() -> Optional[str]:
    """
    프론트엔드 URL에서 쿠키 공유를 위한 공통 도메인 추출
    예: https://fm.terzeron.com -> .terzeron.com
    """
    frontend_url = Env.get("FM_FRONTEND_URL")
    if not frontend_url:
        LOGGER.warning("FM_FRONTEND_URL not set, cookie domain will be None")
        return None

    parsed = urlparse(frontend_url)
    host = parsed.hostname
    if not host:
        return None

    # localhost나 IP 주소인 경우 도메인 설정 안 함
    if host in ("localhost", "127.0.0.1") or host.replace(".", "").isdigit():
        return None

    # 서브도메인을 제거하고 루트 도메인 추출 (예: fm.terzeron.com -> terzeron.com)
    parts = host.split(".")
    if len(parts) >= 2:
        # 마지막 두 부분을 루트 도메인으로 사용 (예: terzeron.com)
        root_domain = ".".join(parts[-2:])
        return f".{root_domain}"

    return None


# 쿠키 도메인 (앱 시작 시 한 번만 계산)
COOKIE_DOMAIN = get_cookie_domain()


def verify_facebook_token(access_token: str, expected_email: str) -> bool:
    """Facebook Graph API로 토큰 유효성과 이메일 일치 여부를 검증"""
    try:
        response = http_requests.get("https://graph.facebook.com/me", params={"fields": "email", "access_token": access_token}, timeout=10)
        if response.status_code != 200:
            LOGGER.warning("Facebook token verification failed: status %d", response.status_code)
            return False
        fb_data = response.json()
        fb_email = fb_data.get("email")
        if fb_email != expected_email:
            LOGGER.warning("Facebook token email mismatch: expected=%s, got=%s", expected_email, fb_email)
            return False
        return True
    except http_requests.RequestException as e:
        LOGGER.error("Facebook token verification request failed: %s", e)
        return False


def generate_session_id() -> str:
    """Generate a secure random session ID"""
    return secrets.token_urlsafe(48)


def create_session(user_email: str, user_name: str, access_token: Optional[str] = None) -> str:
    """Create a new session in the database and return session ID"""
    session_id = generate_session_id()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)

    with DB.session_ctx() as session:
        user_session = UserSession(session_id=session_id, user_email=user_email, user_name=user_name, facebook_access_token=access_token, expires_at=expires_at)
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
        expires_at = user_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            LOGGER.info("Session %s... expired", session_id[:8])
            session.delete(user_session)
            return None

        # Update last accessed time
        user_session.last_accessed_at = datetime.now(timezone.utc)
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
    # DB가 timezone-naive로 저장하므로 비교도 timezone-naive로 수행
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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


def _get_admin_email_set() -> set[str]:
    raw = Env.get("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "")
    return {email.strip() for email in raw.split(",") if email.strip()}


def require_admin(request: Request) -> UserSession:
    """Dependency that requires admin privileges"""
    user_session = require_auth(request)
    admin_emails = _get_admin_email_set()
    if admin_emails and user_session.user_email not in admin_emails:
        raise HTTPException(status_code=403, detail="Not authorized")
    return user_session


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie with secure flags"""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # Prevent XSS attacks
        secure=True,  # HTTPS only
        samesite="lax",  # CSRF protection: 외부 사이트 POST 요청 시 쿠키 미전송
        path="/",
        domain=COOKIE_DOMAIN,  # Allow cookie sharing across subdomains
    )


def clear_session_cookie(response: JSONResponse) -> None:
    """Clear session cookie"""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=COOKIE_DOMAIN,  # Must match the domain used when setting
    )
