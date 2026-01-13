from fastapi.responses import JSONResponse
from backend.auth import (
    set_session_cookie, set_csrf_cookie,
    clear_session_cookie, clear_csrf_cookie,
    SESSION_COOKIE_NAME, CSRF_COOKIE_NAME
)


def test_set_and_clear_cookies():
    r = JSONResponse({"ok": True})
    set_session_cookie(r, "sid")
    set_csrf_cookie(r, "csrf")

    # Fast way: Set-Cookie headers should include our keys
    headers = [h.decode().lower() for k, h in r.raw_headers if k.decode().lower() == 'set-cookie']
    assert any(SESSION_COOKIE_NAME in h for h in headers)
    assert any(CSRF_COOKIE_NAME in h for h in headers)

    # clear
    clear_session_cookie(r)
    clear_csrf_cookie(r)
    # After delete_cookie, response still valid
    assert r.status_code == 200
