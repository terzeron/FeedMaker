#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import logging
import logging.config
from typing import Dict, Any
from feed_manager import FeedManager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
LOGGER = logging.getLogger(__name__)

app = FastAPI()
origins = [
    os.environ["FEED_MAKER_URL"] if "FEED_MAKER_URL" in os.environ else "https://127.0.0.1:8081",
    "https://127.0.0.1:8081",
    "https://localhost:8081"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

feed_manager: FeedManager = FeedManager()
feed_manager.scan_all_feeds()


def handle_exception(exc_type, exc_value, exc_traceback):
    LOGGER.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception


@app.get("/exec_result")
async def get_exec_result():
    LOGGER.debug("/exec_result -> get_exec_result()")
    response_object: Dict[str, Any] = {"status": "success"}
    result, error = await feed_manager.get_exec_result()
    if result:
        response_object["exec_result"] = result
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.get("/problems/{data_type}")
async def get_problems(data_type: str):
    LOGGER.debug(f"/problems/{data_type} -> get_problems_{data_type}()")
    response_object: Dict[str, Any] = {"status": "success"}
    error = ""
    if data_type == "progress_info":
        progress_info, error = await feed_manager.get_problems_progress_info()
        if progress_info:
            response_object["result"] = progress_info
    elif data_type == "public_feed_info":
        public_feed_info, error = await feed_manager.get_problems_public_feed_info()
        if public_feed_info:
            response_object["result"] = public_feed_info
    elif data_type == "html_info":
        html_info, error = await feed_manager.get_problems_html_info()
        if html_info:
            response_object["result"] = html_info
    elif data_type == "element_info":
        element_info, error = await feed_manager.get_problems_element_info()
        if element_info:
            response_object["result"] = element_info
    elif data_type == "status_info":
        status_info, error = await feed_manager.get_problems_status_info()
        if status_info:
            response_object["result"] = status_info

    if "result" not in response_object or not response_object["result"]:
        response_object["message"] = error
        response_object["status"] = "failure"
    return response_object


@app.get("/search/{keyword}")
async def search(keyword: str):
    LOGGER.debug(f"/search -> search({keyword})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.search(keyword)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object


@app.get("/search_site/{keyword}")
def search_site(keyword: str):
    LOGGER.debug(f"/search_site -> search_site({keyword})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = feed_manager.search_site(keyword)
    if result or not error:
        response_object["search_result_list"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object


@app.delete("/public_feeds/{feed_name}")
async def remove_public_feed(feed_name: str):
    LOGGER.debug(f"/public_feeds/{feed_name} -> remove_public_feed({feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    await feed_manager.remove_public_feed(feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/groups/{group_name}/site_config")
async def get_site_config(group_name: str):
    LOGGER.debug(f"/groups/{group_name}/site_config -> get_site_config({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.get_site_config(group_name)
    if result:
        response_object["configuration"] = result
        LOGGER.debug(response_object["configuration"])
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object


@app.put("/groups/{group_name}/site_config")
async def save_site_config(group_name: str, request: Request):
    LOGGER.debug("/groups/{group_name}/site_config -> save_site_config({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    post_data = await request.json()
    success_or_fail, error = await feed_manager.save_site_config(group_name, post_data)
    if success_or_fail:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.put("/groups/{group_name}/toggle")
async def toggle_group(group_name: str):
    LOGGER.debug(f"/groups/{group_name}/toggle -> toggle_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.toggle_group(group_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name}")
async def remove_html_file(group_name: str, feed_name: str, html_file_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/htmls/{html_file_name} -> remove_html_file({group_name}, {feed_name}, {html_file_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    await feed_manager.remove_html_file(group_name, feed_name, html_file_name)
    response_object["status"] = "success"
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/htmls")
async def remove_html(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/htmls -> remove_html({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    await feed_manager.remove_html(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}/run")
def run(group_name: str, feed_name: str, request: Request):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/run -> run({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    post_data = await request.json()
    result, error = feed_manager.run(group_name, feed_name, post_data["alias"])
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.put("/groups/{group_name}/feeds/{feed_name}/toggle")
async def toggle_feed(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/toggle -> toggle_feed({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.toggle_feed(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["new_name"] = result
    else:
        response_object["message"] = error
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/list")
async def remove_list(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/list -> remove_list({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    await feed_manager.remove_list(group_name, feed_name)
    response_object["status"] = "success"
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}/alias")
async def get_alias(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/alias -> get_alias({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.get_alias(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["alias"] = result
    else:
        response_object["message"] = error
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}/alias")
async def delete_alias(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/alias -> remove_alias({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.remove_alias(group_name, feed_name)
    if result:
        response_object["status"] = "success"
        response_object["alias"] = result
    else:
        response_object["message"] = error
    return response_object


@app.put("/groups/{group_name}/feeds/{feed_name}/rename/{new_alias}")
async def rename_alias(group_name: str, feed_name: str, new_alias: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/rename/{new_alias} -> rename_alias({group_name}, {feed_name}, {new_alias})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.rename_alias(group_name, feed_name, new_alias)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}/check_running")
async def check_running(group_name: str, feed_name: str):
    # LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name}/check_running, {request.method} -> check_running({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result = await feed_manager.check_running(group_name, feed_name)
    response_object["status"] = "success"
    response_object["running_status"] = result
    return response_object


@app.get("/groups/{group_name}/feeds/{feed_name}")
async def get_feed_info(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name} -> get_feed_info({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    feed_info, error = await feed_manager.get_feed_info_by_name(group_name, feed_name)
    if feed_info or not error:
        # success in case of feed without configuration
        response_object["feed_info"] = feed_info
        LOGGER.debug(response_object["feed_info"])
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.post("/groups/{group_name}/feeds/{feed_name}")
async def post_feed_info(group_name: str, feed_name: str, request: Request):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name} -> save_config_file({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    post_data = await request.json()
    result, error = await feed_manager.save_config_file(group_name, feed_name, post_data)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.delete("/groups/{group_name}/feeds/{feed_name}")
async def delete_feed_info(group_name: str, feed_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds/{feed_name} -> remove_feed({group_name}, {feed_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.remove_feed(group_name, feed_name)
    if result:
        response_object["status"] = "success"
    else:
        response_object["message"] = error
    return response_object


@app.get("/groups/{group_name}/feeds")
async def get_feeds_by_group(group_name: str):
    LOGGER.debug(f"/groups/{group_name}/feeds -> get_feeds_by_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.get_feeds_by_group(group_name)
    if result or not error:
        # success in case of group without any feed
        response_object["feeds"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object


@app.delete("/groups/{group_name}")
async def remove_group(group_name: str):
    LOGGER.debug(f"/groups/{group_name} -> remove_group({group_name})")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.remove_group(group_name)
    if result or not error:
        response_object["feeds"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object


@app.get("/groups")
async def get_groups():
    LOGGER.debug("/groups -> get_groups()")
    response_object: Dict[str, Any] = {"status": "failure"}
    result, error = await feed_manager.get_groups()
    if result:
        response_object["groups"] = result
        response_object["status"] = "success"
        LOGGER.debug(result)
    else:
        response_object["message"] = error
    return response_object
