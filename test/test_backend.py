#!/usr/bin/env python


from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_exec_result():
    response = client.get("/exec_result")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "exec_result" in response.json()


def test_get_problems_progress_info():
    response = client.get("/problems/progress_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    for key, value in result.items():
        assert "feed_name" in value
        assert "feed_title" in value
        assert "group_name" in value
        assert "current_index" in value
        assert "total_item_count" in value
        assert "unit_size_per_day" in value
        assert "progress_ratio" in value
        assert "due_date" in value


def test_get_problems_public_feed_info():
    response = client.get("/problems/public_feed_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    for key, value in result.items():
        assert "feed_name" in value
        assert "feed_title" in value
        assert "group_name" in value
        assert "file_size" in value
        assert "num_items" in value
        assert "upload_date" in value


def test_get_problems_html_info():
    response = client.get("/problems/html_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    if result:
        for key, value in result.items():
            if "html_file_size_map" in value:
                for k, v in value["html_file_size_map"].items():
                    assert "file_name" in v
                    assert "file_path" in v

            if "html_file_with_many_image_tag" in value:
                for k, v in value["html_file_with_many_image_tag"].items():
                    assert "file_name" in v
                    assert "file_path" in v
                    assert "feed_dir_path" in v
                    assert "count" in v
                    assert "update_date" in v

            if "html_file_without_image_tag" in value:
                for k, v in value["html_file_without_image_tag"].items():
                    assert "file_name" in v
                    assert "file_path" in v
                    assert "feed_dir_path" in v
                    assert "count" in v
                    assert "update_date" in v

            if "html_file_image_not_found" in value:
                for k, v in value["html_file_image_not_found"].items():
                    assert "file_name" in v
                    assert "file_path" in v
                    assert "feed_dir_path" in v
                    assert "count" in v
                    assert "update_date" in v


def test_get_problems_element_info():
    response = client.get("/problems/element_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    for key, value in result.items():
        assert "element_name" in value
        assert "count" in value


def test_get_problems_list_url_info():
    response = client.get("/problems/list_url_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    for key, value in result.items():
        assert "feed_name" in value
        assert "feed_title" in value
        assert "group_name" in value
        assert "count" in value


def test_get_problems_status_info():
    response = client.get("/problems/status_info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "result" in response.json()
    result = response.json()["result"]
    for key, value in result.items():
        assert "feed_name" in value
        assert "feed_title" in value
        assert "group_name" in value
        assert "http_request" in value
        assert "access_date" in value
        assert "view_date" in value
        assert "feedmaker" in value
        assert "update_date" in value
        assert "public_html" in value
        assert "file_path" in value
        assert "upload_date" in value


def test_search():
    response = client.get("/search/a")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "feeds" in response.json()
    feeds = response.json()["feeds"]
    for feed in feeds:
        assert "feed_name" in feed
        assert "feed_title" in feed
        assert "group_name" in feed


def test_search_site():
    response = client.get("/search_site/무림")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "search_result_list" in response.json()
    search_result_list = response.json()["search_result_list"]
    for search_result in search_result_list:
        assert len(search_result) == 2
        assert search_result[1].startswith("http")


def test_get_site_config():
    response = client.get("/groups/wfwf/site_config")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "configuration" in response.json()
    configuration = response.json()["configuration"]
    assert "url" in configuration
    assert "keyword" in configuration


def test_check_running():
    response = client.get("/groups/naver/feeds/ai_doctor/check_running")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "running_status" in response.json()
    assert response.json()["running_status"] in ("error", True, False)


def test_get_feed_info():
    response = client.get("/groups/naver/feeds/ai_doctor/info")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "feed_info" in response.json()
    feed_info = response.json()["feed_info"]
    assert "feed_name" in feed_info
    assert "feed_title" in feed_info
    assert "config" in feed_info
    assert "config_modify_date" in feed_info
    assert "collection_info" in feed_info
    assert "collect_date" in feed_info["collection_info"]
    assert "total_item_count" in feed_info["collection_info"]
    assert "public_feed_info" in feed_info
    assert "public_feed_file_path" in feed_info["public_feed_info"]
    assert "file_size" in feed_info["public_feed_info"]
    assert "num_items" in feed_info["public_feed_info"]
    assert "upload_date" in feed_info["public_feed_info"]
    assert "progress_info" in feed_info
    assert "current_index" in feed_info["progress_info"]
    assert "total_item_count" in feed_info["progress_info"]
    assert "unit_size_per_day" in feed_info["progress_info"]
    assert "progress_ratio" in feed_info["progress_info"]
    assert "due_date" in feed_info["progress_info"]


def test_get_feeds_by_group():
    response = client.get("/groups/naver/feeds")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "feeds" in response.json()
    feeds = response.json()["feeds"]
    for feed in feeds:
        assert "name" in feed
        assert "title" in feed


def test_get_groups():
    response = client.get("/groups")
    assert response.status_code == 200
    assert "status" in response.json() and "success" == response.json()["status"]
    assert "groups" in response.json()
    groups = response.json()["groups"]
    for group in groups:
        assert "name" in group
        assert "num_feeds" in group
