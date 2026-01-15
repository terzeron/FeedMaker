#!/usr/bin/env python
# -*- coding: utf-8 -*-

import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
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

# CSRF configuration
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def generate_session_id() -> str:
    """Generate a secure random session ID"""
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    """Generate a secure random CSRF token"""
    return secrets.token_urlsafe(32)


def create_session(user_email: str, user_name: str, facebook_access_token: str) -> str:
    """Create a new session in the database and return session ID"""
    session_id = generate_session_id()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_EXPIRY_DAYS)

    with DB.session_ctx() as session:
        user_session = UserSession(
            session_id=session_id,
            user_email=user_email,
            user_name=user_name,
            facebook_access_token=facebook_access_token,
            expires_at=expires_at
        )
        session.add(user_session)

    LOGGER.info(f"Created session for user {user_email}")
    return session_id


def get_session(session_id: str) -> Optional[UserSession]:
    """Get session from database and validate expiry"""
    if not session_id:
        LOGGER.warning("get_session: Empty session_id provided")
        return None

    LOGGER.info(f"get_session: Looking up session_id {session_id[:20]}...")
    with DB.session_ctx() as session:
        user_session = session.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()

        if not user_session:
            LOGGER.warning(f"get_session: No session found in DB for {session_id[:20]}...")
            return None

        # Check if session is expired
        # DB에서 가져온 datetime이 timezone-naive일 수 있으므로 UTC로 처리
        expires_at = user_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            LOGGER.info(f"Session {session_id[:20]}... expired")
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
        user_session = session.query(UserSession).filter(
            UserSession.session_id == session_id
        ).first()

        if user_session:
            session.delete(user_session)
            LOGGER.info(f"Deleted session {session_id}")
            return True

    return False


def cleanup_expired_sessions() -> int:
    """Clean up expired sessions from database"""
    # DB가 timezone-naive로 저장하므로 비교도 timezone-naive로 수행
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with DB.session_ctx() as session:
        count = session.query(UserSession).filter(
            UserSession.expires_at < now
        ).delete()
        LOGGER.info(f"Cleaned up {count} expired sessions")
        return count


def get_current_user(request: Request) -> Optional[UserSession]:
    """Get current authenticated user from session cookie"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    LOGGER.info(f"get_current_user: session_id from cookie = {session_id}")
    if not session_id:
        LOGGER.warning("get_current_user: No session_id cookie found")
        return None

    user_session = get_session(session_id)
    if user_session:
        LOGGER.info(f"get_current_user: Found valid session for {user_session.user_email}")
    else:
        LOGGER.warning(f"get_current_user: No valid session found for session_id {session_id}")
    return user_session


def require_auth(request: Request) -> UserSession:
    """Dependency that requires authentication"""
    user_session = get_current_user(request)
    if not user_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user_session


def set_session_cookie(response: Response, session_id: str) -> None:
    """Set session cookie with secure flags"""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,  # Prevent XSS attacks
        secure=True,  # HTTPS only (required for SameSite=none)
        samesite="none",  # Allow cross-origin cookies
        path="/",
        domain=".terzeron.com"  # Allow cookie sharing across subdomains
    )


def set_csrf_cookie(response: Response, csrf_token: str) -> None:
    """Set CSRF cookie that is readable by JS"""
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=COOKIE_MAX_AGE,
        httponly=False,  # Must be readable by frontend JS
        secure=True,  # HTTPS only (required for SameSite=none)
        samesite="none",  # Allow cross-origin cookies
        path="/",
        domain=".terzeron.com"  # Allow cookie sharing across subdomains
    )


def clear_session_cookie(response: JSONResponse) -> None:
    """Clear session cookie"""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        domain=".terzeron.com"  # Must match the domain used when setting
    )


def clear_csrf_cookie(response: Response) -> None:
    """Clear CSRF cookie"""
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        domain=".terzeron.com"  # Must match the domain used when setting
    )
