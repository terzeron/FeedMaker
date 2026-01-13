#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import logging
import logging.config
from enum import Enum
from pathlib import Path
from typing import Any, Type, Optional
from types import TracebackType
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from backend.feed_maker_manager import FeedMakerManager
from backend.auth import (
    require_auth, create_session, delete_session, cleanup_expired_sessions,
    get_current_user, set_session_cookie, clear_session_cookie,
    generate_csrf_token, set_csrf_cookie, clear_csrf_cookie,
    CSRF_COOKIE_NAME, CSRF_HEADER_NAME
)
from bin.feed_maker_util import Env
from bin.db import DB
from bin.models import UserSession

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    DB.create_all_tables()
    app.state.feed_maker_manager = FeedMakerManager()
    yield
    # Shutdown
    app.state.feed_maker_manager.aclose()


app = FastAPI(lifespan=lifespan)

frontend_url = Env.get("FM_FRONTEND_URL")
origins = [
    frontend_url,
    "https://127.0.0.1:8081",
    "https://localhost:8081",
    "https://127.0.0.1:8082",
    "https://localhost:8082"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"]
)


def get_feed_maker_manager(request: Request) -> "FeedMakerManager":
    try:
        return request.app.state.feed_maker_manager
    except AttributeError as e:
        raise HTTPException(500, detail="FeedMakerManager not initialized, {e}") from e


async def verify_csrf_token(request: Request):
    """Dependency to verify CSRF token for state-changing methods"""
    if request.method in ["POST", "PUT", "DELETE"]:
        csrf_token_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        csrf_token_header = request.headers.get(CSRF_HEADER_NAME)

        if not csrf_token_cookie or not csrf_token_header or csrf_token_cookie != csrf_token_header:
            raise HTTPException(status_code=403, detail="CSRF token mismatch")


@app.exception_handler(Exception)
async def exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    logging.exception("An error occurred")
    return JSONResponse(status_code=500, content={"message": "Internal server error"})


def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Optional[TracebackType]) -> None:
    LOGGER.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


# Pydantic models for authentication requests
class LoginRequest(BaseModel):
    email: str
    name: str
    access_token: str


# Authentication endpoints
@app.post("/auth/login")
async def login(request: LoginRequest) -> JSONResponse:
    """
    로그인 엔드포인트
    - Facebook 로그인 성공 후 호출
    - 서버에 세션 생성하고 httpOnly 쿠키 설정
    - 허용된 이메일만 로그인 가능
    """
    LOGGER.info(f"POST /auth/login -> login({request.email})")

    # 허용된 이메일 목록 확인
    login_allowed_email_list = Env.get("FM_FACEBOOK_LOGIN_ALLOWED_EMAIL_LIST", "").split(",")
    if request.email not in login_allowed_email_list:
        LOGGER.warning(f"Unauthorized login attempt from {request.email}")
        raise HTTPException(status_code=403, detail="이메일이 허용되지 않았습니다.")

    # 세션 생성
    try:
        session_id = create_session(request.email, request.name, request.access_token)
        csrf_token = generate_csrf_token()

        response = JSONResponse(content={
            "status": "success",
            "message": "로그인되었습니다."
        })

        # httpOnly 쿠키 설정
        set_session_cookie(response, session_id)
        set_csrf_cookie(response, csrf_token)

        return response
    except Exception as e:
        LOGGER.error(f"Login failed for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="로그인 중 오류가 발생했습니다.")


@app.post("/auth/logout")
async def logout(request: Request) -> JSONResponse:
    """
    로그아웃 엔드포인트
    - 서버의 세션 삭제
    - httpOnly 쿠키 제거
    """
    LOGGER.info("POST /auth/logout -> logout()")

    session_id = request.cookies.get("session_id")
    if session_id:
        delete_session(session_id)

    response = JSONResponse(content={
        "status": "success",
        "message": "로그아웃되었습니다."
    })

    # 쿠키 제거
    clear_session_cookie(response)
    clear_csrf_cookie(response)

    return response


@app.get("/auth/me")
async def get_me(request: Request) -> dict[str, Any]:
    """
    현재 로그인 상태 확인 엔드포인트
    - httpOnly 쿠키에서 세션 확인
    - 로그인 여부와 사용자 정보 반환
    """
    LOGGER.info(f"/auth/me called, cookies: {request.cookies}")
    user_session = get_current_user(request)

    if not user_session:
        LOGGER.warning("/auth/me: No valid user session found")
        return {
            "is_authenticated": False
        }

    LOGGER.info(f"/auth/me: User authenticated: {user_session.user_email}")
    return {
        "is_authenticated": True,
        "email": user_session.user_email,
        "name": user_session.user_name
    }


@app.get("/exec_result")
async def get_exec_result(
    feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager),
    user_session: UserSession = Depends(require_auth)
) -> dict[str, Any]:
    LOGGER.info("/exec_result -> get_exec_result()")
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.get_exec_result()
    if result:
        response_object["exec_result"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


class ProblemType(str, Enum):
    PROGRESS = "progress_info"
    PUBLIC_FEED = "public_feed_info"
    HTML = "html_info"
    ELEMENT = "element_info"
    LIST_URL = "list_url_info"
    STATUS = "status_info"


@app.get("/problems/{problem_type}")
async def get_problems(problem_type: ProblemType,
                       feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/problems/%r -> get_problems_%r()", problem_type, problem_type)
    response_object: dict[str, Any] = {}
    info_methods = {
        ProblemType.PROGRESS: feed_maker_manager.get_problems_progress_info,
        ProblemType.PUBLIC_FEED: feed_maker_manager.get_problems_public_feed_info,
        ProblemType.HTML: feed_maker_manager.get_problems_html_info,
        ProblemType.ELEMENT: feed_maker_manager.get_problems_element_info,
        ProblemType.LIST_URL: feed_maker_manager.get_problems_list_url_info,
        ProblemType.STATUS: feed_maker_manager.get_problems_status_info,
    }

    handler = info_methods.get(problem_type)
    if not handler:
        raise HTTPException(404, f"Problem type {problem_type} not found")
    result, error = handler()
    if result or not error:
        response_object["result"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"

    return response_object


@app.get("/search/{keyword}")
async def search(keyword: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/search -> search(%s)", keyword)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.search(keyword)
    if result or not error:
        # is_active 필드가 없는 경우 추가
        response_object["feeds"] = [
            {
                **feed,
                "is_active": feed.get("is_active") if "is_active" in feed else not feed["feed_name"].startswith("_")
            }
            for feed in result
        ]
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.get("/search_site/{keyword}")
async def search_site(keyword: str) -> dict[str, Any]:
    LOGGER.info("/search_site -> search_site(%s)", keyword)
    response_object: dict[str, Any] = {}
    result, error = FeedMakerManager.search_site(keyword)
    if result or not error:
        response_object["search_result"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/public_feeds/{feed_name}", dependencies=[Depends(verify_csrf_token)])
async def remove_public_feed(feed_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /public_feeds/%s -> remove_public_feed(%s)", feed_name, feed_name)
    response_object: dict[str, Any] = {}
    feed_maker_manager.remove_public_feed(feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/public_feeds/{feed_name}/item_titles")
async def extract_titles_from_public_feed(feed_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("GET /public_feeds/%s/item_titles -> extract_titles_from_public_feed(%s)", feed_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.extract_titles_from_public_feed(feed_name)

    if isinstance(result, list):
        response_object["status"] = "success"
        response_object["item_titles"] = result
    else:
        # result is an error code string like "FILE_NOT_FOUND"
        response_object["status"] = "failure"
        response_object["message"] = error
        response_object["error_code"] = result

    return response_object


@app.get("/groups/{group_name}/site_config")
async def get_site_config(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/site_config -> get_site_config(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.get_site_config(group_name)
    if result or not error:
        response_object["configuration"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/site_config", dependencies=[Depends(verify_csrf_token)])
async def save_site_config(group_name: str, request: Request,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.debug("/groups/%s/site_config -> save_site_config(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    post_data = await request.json()
    success_or_fail, error = feed_maker_manager.save_site_config(group_name, post_data)
    if success_or_fail or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/toggle", dependencies=[Depends(verify_csrf_token)])
async def toggle_group(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("PUT /groups/%s/toggle -> toggle_group(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.toggle_group(group_name)
    if result or not error:
        response_object["new_name"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name}", dependencies=[Depends(verify_csrf_token)])
async def remove_html_file(group_name: str, feed_name: str, html_file_name: str,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/htmls/%s -> remove_html_file(%s, %s, %s)", group_name, feed_name,
                html_file_name, group_name, feed_name, html_file_name)
    response_object: dict[str, Any] = {}
    feed_maker_manager.remove_html_file(group_name, feed_name, html_file_name)
    response_object["status"] = "success"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls", dependencies=[Depends(verify_csrf_token)])
async def remove_html(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/htmls -> remove_html(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    feed_maker_manager.remove_html(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}/run", dependencies=[Depends(verify_csrf_token)])
def run_feed(group_name: str, feed_name: str, _request: Request,
        feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("POST /groups/%s/feeds/%s/run -> run_feed(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.run(group_name, feed_name)
    if result or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/feeds/{feed_name}/toggle", dependencies=[Depends(verify_csrf_token)])
async def toggle_feed(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/feeds/%s/toggle -> toggle_feed(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.toggle_feed(feed_name)
    if result or not error:
        response_object["new_name"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/list", dependencies=[Depends(verify_csrf_token)])
async def remove_list(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/list -> remove_list(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    feed_maker_manager.remove_list(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}/check_running")
async def check_running(group_name: str, feed_name: str,
                        feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    # LOGGER.info("/groups/%s/feeds/%s/check_running -> check_running(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result = feed_maker_manager.check_running(group_name, feed_name)
    if result is not None:
        response_object["running_status"] = bool(result)
        response_object["status"] = "success"
    else:
        response_object["running_status"] = "error"
        response_object["status"] = "failure"
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}")
async def get_feed_info(group_name: str, feed_name: str,
                        feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/feeds/%s -> get_feed_info(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    feed_info, error = feed_maker_manager.get_feed_info_by_name(group_name, feed_name)
    if feed_info or not error:
        # success in case of feed without configuration
        response_object["feed_info"] = feed_info
        LOGGER.debug(response_object.get("feed_info", ""))
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}", dependencies=[Depends(verify_csrf_token)])
async def post_feed_info(group_name: str, feed_name: str, request: Request,
                         feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("POST /groups/%s/feeds/%s -> save_config_file(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    post_data = await request.json()
    result, error = feed_maker_manager.save_config_file(group_name, feed_name, post_data)
    if result or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}", dependencies=[Depends(verify_csrf_token)])
async def delete_feed_info(group_name: str, feed_name: str,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s -> remove_feed(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.remove_feed(group_name, feed_name)
    if result or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.get("/groups/{group_name}/feeds")
async def get_feeds_by_group(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/feeds -> get_feeds_by_group(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.get_feeds_by_group(group_name)
    if result or not error:
        # success in case of group without any feed
        # is_active 필드가 없는 경우 추가
        response_object["feeds"] = [
            {
                **feed,
                "is_active": feed.get("is_active") if "is_active" in feed else not feed["name"].startswith("_")
            }
            for feed in result
        ]
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}", dependencies=[Depends(verify_csrf_token)])
async def remove_group(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s -> remove_group(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.remove_group(group_name)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.get("/groups")
async def get_groups(feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.debug("/groups -> get_groups()")
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.get_groups()
    if result or not error:
        # is_active 필드가 없는 경우 추가
        response_object["groups"] = [
            {
                **group,
                "is_active": group.get("is_active") if "is_active" in group else not group["name"].startswith("_")
            }
            for group in result
        ]
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


if __name__ == "__main__":
    LOGGER.debug("# main()")
    uvicorn.run(app, host="0.0.0.0", port=8010)
