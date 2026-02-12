from fastapi.responses import JSONResponse
from backend.auth import (
    set_session_cookie,
    clear_session_cookie,
    SESSION_COOKIE_NAME
)


def test_set_and_clear_session_cookie():
    """세션 쿠키 설정 및 삭제 테스트 (SameSite=Lax로 CSRF 방어)"""
    r = JSONResponse({"ok": True})
    set_session_cookie(r, "sid")

    # Set-Cookie 헤더에 세션 쿠키가 포함되어야 함
    headers = [h.decode().lower() for k, h in r.raw_headers if k.decode().lower() == 'set-cookie']
    assert any(SESSION_COOKIE_NAME in h for h in headers)
    # SameSite=Lax 설정 확인
    assert any("samesite=lax" in h for h in headers)

    # clear
    clear_session_cookie(r)
    # After delete_cookie, response still valid
    assert r.status_code == 200
