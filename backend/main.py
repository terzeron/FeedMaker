#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import logging
import logging.config
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Type, Optional
from types import TracebackType
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.feed_maker_manager import FeedMakerManager
from bin.feed_maker_util import Env

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # pylint: disable=redefined-outer-name
    app.state.feed_maker_manager = FeedMakerManager()
    try:
        yield
    finally:
        await app.state.feed_maker_manager.aclose()


app = FastAPI(lifespan=lifespan)
frontend_url = Env.get("FM_FRONTEND_URL")
origins = [
    frontend_url,
    "https://127.0.0.1:8081",
    "https://localhost:8081"
]

app.add_middleware(
    CORSMiddleware,  # type: ignore
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def get_feed_maker_manager(request: Request) -> "FeedMakerManager":
    try:
        return request.app.state.feed_maker_manager
    except AttributeError as e:
        raise HTTPException(500, detail="FeedMakerManager not initialized, {e}") from e


@app.exception_handler(Exception)
async def exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    logging.exception("An error occurred")
    return JSONResponse(status_code=500, content={"message": "Internal server error"})


def handle_exception(exc_type: Type[BaseException], exc_value: BaseException, exc_traceback: Optional[TracebackType]) -> None:
    LOGGER.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


@app.get("/exec_result")
async def get_exec_result(feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/exec_result -> get_exec_result()")
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.get_exec_result()
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
    result, error = await handler()
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
    result, error = await feed_maker_manager.search(keyword)
    if result or not error:
        response_object["feeds"] = result
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
    result, error = await FeedMakerManager.search_site(keyword)
    if result or not error:
        response_object["search_result_list"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/public_feeds/{feed_name}")
async def remove_public_feed(feed_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /public_feeds/%s -> remove_public_feed(%s)", feed_name, feed_name)
    response_object: dict[str, Any] = {}
    await feed_maker_manager.remove_public_feed(feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/groups/{group_name}/site_config")
async def get_site_config(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/site_config -> get_site_config(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.get_site_config(group_name)
    if result or not error:
        response_object["configuration"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/site_config")
async def save_site_config(group_name: str, request: Request,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.debug("/groups/%s/site_config -> save_site_config(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    post_data = await request.json()
    success_or_fail, error = await feed_maker_manager.save_site_config(group_name, post_data)
    if success_or_fail or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/toggle")
async def toggle_group(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("PUT /groups/%s/toggle -> toggle_group(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.toggle_group(group_name)
    if result or not error:
        response_object["new_name"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name}")
async def remove_html_file(group_name: str, feed_name: str, html_file_name: str,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/htmls/%s -> remove_html_file(%s, %s, %s)", group_name, feed_name,
                html_file_name, group_name, feed_name, html_file_name)
    response_object: dict[str, Any] = {}
    await feed_maker_manager.remove_html_file(group_name, feed_name, html_file_name)
    response_object["status"] = "success"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls")
async def remove_html(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/htmls -> remove_html(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    await feed_maker_manager.remove_html(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}/run")
def run(group_name: str, feed_name: str, _request: Request,
        feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("POST /groups/%s/feeds/%s/run -> run(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = feed_maker_manager.run(group_name, feed_name)
    if result or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.put("/groups/{group_name}/feeds/{feed_name}/toggle")
async def toggle_feed(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("/groups/%s/feeds/%s/toggle -> toggle_feed(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.toggle_feed(feed_name)
    if result or not error:
        response_object["new_name"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/list")
async def remove_list(group_name: str, feed_name: str,
                      feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s/list -> remove_list(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    await feed_maker_manager.remove_list(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}/check_running")
async def check_running(group_name: str, feed_name: str,
                        feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    # LOGGER.info("/groups/%s/feeds/%s/check_running -> check_running(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result = await feed_maker_manager.check_running(group_name, feed_name)
    if result:
        response_object["running_status"] = result
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
    feed_info, error = await feed_maker_manager.get_feed_info_by_name(group_name, feed_name)
    if feed_info or not error:
        # success in case of feed without configuration
        response_object["feed_info"] = feed_info
        LOGGER.debug(response_object.get("feed_info", ""))
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}")
async def post_feed_info(group_name: str, feed_name: str, request: Request,
                         feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("POST /groups/%s/feeds/%s -> save_config_file(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    post_data = await request.json()
    result, error = await feed_maker_manager.save_config_file(group_name, feed_name, post_data)
    if result or not error:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}")
async def delete_feed_info(group_name: str, feed_name: str,
                           feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s/feeds/%s -> remove_feed(%s, %s)", group_name, feed_name, group_name, feed_name)
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.remove_feed(group_name, feed_name)
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
    result, error = await feed_maker_manager.get_feeds_by_group(group_name)
    if result or not error:
        # success in case of group without any feed
        response_object["feeds"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.delete("/groups/{group_name}")
async def remove_group(group_name: str, feed_maker_manager: FeedMakerManager = Depends(get_feed_maker_manager)) -> dict[str, Any]:
    LOGGER.info("DELETE /groups/%s -> remove_group(%s)", group_name, group_name)
    response_object: dict[str, Any] = {}
    result, error = await feed_maker_manager.remove_group(group_name)
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
    result, error = await feed_maker_manager.get_groups()
    if result or not error:
        response_object["groups"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
