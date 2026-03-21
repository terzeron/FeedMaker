import asyncio
import types
from unittest.mock import patch

import backend.main as main
from fastapi import HTTPException
from fastapi.responses import JSONResponse


class DummyFeedMakerManager:
    def __init__(self):
        pass

    async def aclose(self):
        return None

    # exec result - failure
    def get_exec_result(self):
        return (None, "exec error")

    # problems - failure
    def get_problems_progress_info(self):
        return (None, "progress error")

    def get_problems_public_feed_info(self):
        return (None, "public feed error")

    def get_problems_html_info(self):
        return (None, "html error")

    def get_problems_element_info(self):
        return (None, "element error")

    def get_problems_list_url_info(self):
        return (None, "list url error")

    def get_problems_status_info(self):
        return (None, "status error")

    # search - failure
    def search(self, keyword):
        return (None, "search error")

    # search_site - failure
    @classmethod
    def search_site(cls, keyword):
        return (None, "search site error")

    # search_site_names
    @classmethod
    def get_search_site_names(cls):
        return ["site1", "site2"]

    # search_single_site
    @classmethod
    def search_single_site(cls, site_name, keyword):
        return ([["title", "https://example.com"]], None)

    # feeds by group
    def get_feeds_by_group(self, group_name):
        return ([{"name": "feed1", "is_active": True}], None)

    # feed info
    def get_feed_info_by_name(self, group_name, feed_name):
        return ({"feed": {"name": feed_name}}, None)

    # save config
    def save_config_file(self, group_name, feed_name, post_data):
        return (True, None)

    # remove feed
    def remove_feed(self, group_name, feed_name):
        return (True, None)

    # remove list
    def remove_list(self, group_name, feed_name):
        return None

    # remove html
    def remove_html(self, group_name, feed_name):
        return None

    def remove_html_file(self, group_name, feed_name, html_file_name):
        return None

    # check running
    def check_running(self, group_name, feed_name):
        return True

    # groups
    def get_groups(self):
        return ([{"name": "group1", "is_active": True}], None)

    # remove group
    def remove_group(self, group_name):
        return (True, None)


class FailingFeedMakerManager(DummyFeedMakerManager):
    """Manager that returns failures for all operations"""

    def get_feeds_by_group(self, group_name):
        return (None, "feeds error")

    def get_feed_info_by_name(self, group_name, feed_name):
        return (None, "feed info error")

    def save_config_file(self, group_name, feed_name, post_data):
        return (None, "save error")

    def remove_feed(self, group_name, feed_name):
        return (None, "remove feed error")

    def check_running(self, group_name, feed_name):
        return None

    def get_groups(self):
        return (None, "groups error")

    def remove_group(self, group_name):
        return (None, "remove group error")

    @classmethod
    def search_single_site(cls, site_name, keyword):
        return (None, "single site error")


# --- exec_result failure ---


def test_get_exec_result_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_exec_result(feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "exec error"


# --- problems failure ---


def test_get_problems_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_problems(main.ProblemType.STATUS, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "status error"


# --- search failure ---


def test_search_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.search("test", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "search error"


# --- search_site failure ---


def test_search_site_failure():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.search_site("test")
    assert r["status"] == "failure"
    assert r["message"] == "search site error"


# --- search_single_site success ---


def test_search_single_site_success():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "success"
    assert r["search_result"] == [["title", "https://example.com"]]


# --- search_single_site error (exception raised) ---


def test_search_single_site_exception():
    class ExcManager(DummyFeedMakerManager):
        @classmethod
        def search_single_site(cls, site_name, keyword):
            raise RuntimeError("connection failed")

    main.FeedMakerManager = ExcManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "failure"
    assert "RuntimeError" in r["message"]


# --- search_single_site error message ---


def test_search_single_site_error_message():
    main.FeedMakerManager = FailingFeedMakerManager
    r = main.search_single_site("site1", "keyword")
    assert r["status"] == "failure"
    assert r["message"] == "single site error"


# --- get_search_site_names ---


def test_get_search_site_names():
    main.FeedMakerManager = DummyFeedMakerManager
    r = main.get_search_site_names()
    assert r["status"] == "success"
    assert r["site_names"] == ["site1", "site2"]


# --- get_feeds_by_group success with is_active ---


def test_get_feeds_by_group_success():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_feeds_by_group("group1", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert "is_active" in r["feeds"][0]


# --- get_feeds_by_group failure ---


def test_get_feeds_by_group_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_feeds_by_group("group1", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "feeds error"


# --- get_feed_info success ---


def test_get_feed_info_success():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["feed_info"]["feed"]["name"] == "f"


# --- get_feed_info failure ---


def test_get_feed_info_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "feed info error"


# --- post_feed_info success ---


def test_post_feed_info_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()

    async def _json():
        return {"key": "value"}

    req = types.SimpleNamespace(json=_json)
    r = asyncio.run(main.post_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- post_feed_info failure ---


def test_post_feed_info_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()

    async def _json():
        return {"key": "value"}

    req = types.SimpleNamespace(json=_json)
    r = asyncio.run(main.post_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "save error"


# --- delete_feed_info success ---


def test_delete_feed_info_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.delete_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- delete_feed_info failure ---


def test_delete_feed_info_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.delete_feed_info("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "remove feed error"


# --- remove_list, remove_html, remove_html_file with require_admin mock ---


def test_remove_list():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_list("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


def test_remove_html():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_html("g", "f", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


def test_remove_html_file():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_html_file("g", "f", "x.html", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- check_running success True ---


def test_check_running_true():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["running_status"] is True


# --- check_running success False ---


def test_check_running_false():
    class FalseRunning(DummyFeedMakerManager):
        def check_running(self, group_name, feed_name):
            return False

    mgr = FalseRunning()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert r["running_status"] is False


# --- check_running error (None) ---


def test_check_running_error():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["running_status"] == "error"


# --- get_groups success with is_active ---


def test_get_groups_success():
    mgr = DummyFeedMakerManager()
    r = asyncio.run(main.get_groups(feed_maker_manager=mgr))
    assert r["status"] == "success"
    assert "is_active" in r["groups"][0]


# --- get_groups failure ---


def test_get_groups_failure():
    mgr = FailingFeedMakerManager()
    r = asyncio.run(main.get_groups(feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "groups error"


# --- remove_group success ---


def test_remove_group_success():
    main.require_admin = lambda _request: None
    mgr = DummyFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_group("g", request=req, feed_maker_manager=mgr))
    assert r["status"] == "success"


# --- remove_group failure ---


def test_remove_group_failure():
    main.require_admin = lambda _request: None
    mgr = FailingFeedMakerManager()
    req = types.SimpleNamespace()
    r = asyncio.run(main.remove_group("g", request=req, feed_maker_manager=mgr))
    assert r["status"] == "failure"
    assert r["message"] == "remove group error"


# --- logout with session_id cookie ---


def test_logout_with_session():
    req = types.SimpleNamespace(cookies={"session_id": "abc123"})
    with patch("backend.main.delete_session") as mock_del, patch("backend.main.clear_session_cookie"):
        r = asyncio.run(main.logout(request=req))
        mock_del.assert_called_once_with("abc123")
    assert r.status_code == 200


# --- logout without session_id cookie ---


def test_logout_without_session():
    req = types.SimpleNamespace(cookies={})
    with patch("backend.main.delete_session") as mock_del, patch("backend.main.clear_session_cookie"):
        r = asyncio.run(main.logout(request=req))
        mock_del.assert_not_called()
    assert r.status_code == 200


# --- get_me authenticated ---


def test_get_me_authenticated():
    req = types.SimpleNamespace()
    session = types.SimpleNamespace(user_email="test@example.com", user_name="Test")
    with patch("backend.main.get_current_user", return_value=session):
        r = asyncio.run(main.get_me(request=req))
    assert r["is_authenticated"] is True
    assert r["email"] == "test@example.com"
    assert r["name"] == "Test"


# --- get_me unauthenticated ---


def test_get_me_unauthenticated():
    req = types.SimpleNamespace()
    with patch("backend.main.get_current_user", return_value=None):
        r = asyncio.run(main.get_me(request=req))
    assert r["is_authenticated"] is False


# --- get_feed_maker_manager AttributeError ---


def test_get_feed_maker_manager_attribute_error():
    req = types.SimpleNamespace(app=types.SimpleNamespace(state=types.SimpleNamespace()))
    try:
        main.get_feed_maker_manager(req)
        assert False, "Should have raised HTTPException"
    except HTTPException as e:
        assert e.status_code == 500
        assert "FeedMakerManager not initialized" in e.detail


# --- value_error_handler ---


def test_value_error_handler():
    req = types.SimpleNamespace()
    exc = ValueError("bad input")
    r = asyncio.run(main.value_error_handler(req, exc))
    assert isinstance(r, JSONResponse)
    assert r.status_code == 400


# --- exception_handler ---


def test_exception_handler():
    req = types.SimpleNamespace()
    exc = RuntimeError("unexpected")
    r = asyncio.run(main.exception_handler(req, exc))
    assert isinstance(r, JSONResponse)
    assert r.status_code == 500
