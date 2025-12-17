import backend.main as main
import types


class DummyFeedMakerManager:
    def __init__(self):
        pass

    async def aclose(self):
        return None

    # exec result
    def get_exec_result(self):
        return ("# hello", None)

    # problems
    def get_problems_progress_info(self):
        return ([{"a": 1}], None)

    def get_problems_public_feed_info(self):
        return ([{"a": 2}], None)

    def get_problems_html_info(self):
        return ({
            "html_file_size_map": [],
            "html_file_with_many_image_tag_map": [],
            "html_file_without_image_tag_map": [],
            "html_file_image_not_found_map": [],
        }, None)

    def get_problems_element_info(self):
        return ([{"b": 1}], None)

    def get_problems_list_url_info(self):
        return ([{"c": 1}], None)

    def get_problems_status_info(self):
        return ([{"status": 1}], None)

    # search
    def search(self, keyword):
        return ([{"feed_name": "feed1", "group_name": "g", "feed_title": "t"}], None)

    @classmethod
    def search_site(cls, keyword):
        return ([
            ["title", "https://example.com"],
        ], None)

    # public feeds
    def remove_public_feed(self, feed_name):
        return None

    def extract_titles_from_public_feed(self, feed_name):
        return (["t1", "t2"] , None)

    # site config
    def get_site_config(self, group_name):
        return ({"k": 1}, None)

    def save_site_config(self, group_name, data):
        return (True, None)

    # toggle
    def toggle_group(self, group_name):
        return (f"_{group_name}", None)

    def toggle_feed(self, feed_name):
        return (f"_{feed_name}", None)

    # html operations
    def remove_html_file(self, group_name, feed_name, html_file_name):
        return None

    def remove_html(self, group_name, feed_name):
        return None

    # run/check/feed info
    def run(self, group_name, feed_name):
        return (True, None)

    def check_running(self, group_name, feed_name):
        return True

    def get_feed_info_by_name(self, group_name, feed_name):
        return ({"feed": {"name": feed_name}}, None)


import asyncio


def test_exec_and_search_and_problems_endpoints():
    # monkeypatch manager classmethod for search_site
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()

    r = asyncio.run(main.get_exec_result(feed_maker_manager=mgr))
    assert r["status"] == "success"

    r = asyncio.run(main.get_problems(main.ProblemType.STATUS, feed_maker_manager=mgr))
    assert r["status"] == "success"

    r = asyncio.run(main.search("test", feed_maker_manager=mgr))
    assert r["status"] == "success" and "is_active" in r["feeds"][0]

    r = asyncio.run(main.search_site("test"))
    assert r["status"] == "success"


def test_group_and_feed_mutations_unit():
    main.FeedMakerManager = DummyFeedMakerManager
    mgr = DummyFeedMakerManager()

    assert (asyncio.run(main.get_site_config("g", feed_maker_manager=mgr)))["status"] == "success"
    async def _json():
        return {"a": 1}
    req = types.SimpleNamespace(json=_json)
    assert (asyncio.run(main.save_site_config("g", request=req, feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.toggle_group("g", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.toggle_feed("g", "f", feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.extract_titles_from_public_feed("f", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.remove_public_feed("f", feed_maker_manager=mgr)))["status"] == "success"

    assert (asyncio.run(main.remove_html_file("g", "f", "x.html", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.remove_html("g", "f", feed_maker_manager=mgr)))["status"] == "success"

    assert main.run_feed("g", "f", _request=None, feed_maker_manager=mgr)["status"] == "success"
    assert (asyncio.run(main.check_running("g", "f", feed_maker_manager=mgr)))["status"] == "success"
    assert (asyncio.run(main.get_feed_info("g", "f", feed_maker_manager=mgr)))["status"] == "success"
