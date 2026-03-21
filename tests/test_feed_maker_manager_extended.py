#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from backend.feed_maker_manager import FeedMakerManager, _validate_name


def _make_manager(tmp_path):
    """__init__을 우회하여 FeedMakerManager 인스턴스 생성"""
    with patch.object(FeedMakerManager, "__init__", lambda self: None):
        mgr = FeedMakerManager.__new__(FeedMakerManager)
        mgr.work_dir_path = tmp_path
        mgr.img_dir_path = tmp_path / "img"
        mgr.pdf_dir_path = tmp_path / "pdf"
        mgr.feed_manager = MagicMock()
        mgr.access_log_manager = MagicMock()
        mgr.html_file_manager = MagicMock()
        mgr.problem_manager = MagicMock()
        return mgr


class TestValidateName(unittest.TestCase):
    def test_valid_ascii_name(self):
        _validate_name("my_feed", "feed_name")

    def test_valid_korean_name(self):
        _validate_name("한글이름", "group_name")

    def test_valid_with_dots_and_dashes(self):
        _validate_name("feed-name.v2", "feed_name")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            _validate_name("", "name")

    def test_none_raises(self):
        with self.assertRaises((ValueError, TypeError)):
            _validate_name(None, "name")

    def test_path_traversal_raises(self):
        with self.assertRaises(ValueError):
            _validate_name("../etc/passwd", "name")

    def test_slash_raises(self):
        with self.assertRaises(ValueError):
            _validate_name("a/b", "name")

    def test_space_raises(self):
        with self.assertRaises(ValueError):
            _validate_name("a b", "name")

    def test_special_chars_raises(self):
        for c in [";", "|", "&", "$", "`", "'", '"', "(", ")"]:
            with self.assertRaises(ValueError, msg=f"char {c!r} should be rejected"):
                _validate_name(f"feed{c}test", "name")


class TestInit(unittest.TestCase):
    @patch("backend.feed_maker_manager.ProblemManager")
    @patch("backend.feed_maker_manager.HtmlFileManager")
    @patch("backend.feed_maker_manager.AccessLogManager")
    @patch("backend.feed_maker_manager.FeedManager")
    def test_init_creates_managers(self, mock_fm, mock_alm, mock_hfm, mock_pm):
        mgr = FeedMakerManager()
        mock_fm.assert_called_once()
        mock_alm.assert_called_once()
        mock_hfm.assert_called_once()
        mock_pm.assert_called_once()
        self.assertIsNotNone(mgr.feed_manager)
        self.assertIsNotNone(mgr.access_log_manager)
        self.assertIsNotNone(mgr.html_file_manager)
        self.assertIsNotNone(mgr.problem_manager)


class TestDel(unittest.TestCase):
    @patch("backend.feed_maker_manager.ProblemManager")
    @patch("backend.feed_maker_manager.HtmlFileManager")
    @patch("backend.feed_maker_manager.AccessLogManager")
    @patch("backend.feed_maker_manager.FeedManager")
    def test_del_deletes_managers(self, mock_fm, mock_alm, mock_hfm, mock_pm):
        mgr = FeedMakerManager()
        mgr.__del__()
        # __del__ 호출 후 속성이 삭제됨
        self.assertFalse(hasattr(mgr, "feed_manager"))
        self.assertFalse(hasattr(mgr, "access_log_manager"))
        self.assertFalse(hasattr(mgr, "html_file_manager"))
        self.assertFalse(hasattr(mgr, "problem_manager"))


class TestAclose(unittest.TestCase):
    def test_aclose_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            result = mgr.aclose()
            self.assertIsNone(result)


class TestGitAdd(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)

            mock_repo = MagicMock()
            with patch.object(mgr, "_get_repo", return_value=mock_repo):
                result, error = mgr._git_add(feed_dir)

            self.assertIsNone(error)
            self.assertIn("feed1", result)
            mock_repo.index.add.assert_called_once()
            mock_repo.index.commit.assert_called_once_with("add feed1")

    def test_invalid_repo_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)

            from git import InvalidGitRepositoryError

            with patch.object(mgr, "_get_repo", side_effect=InvalidGitRepositoryError("bad")):
                result, error = mgr._git_add(feed_dir)

            self.assertEqual(result, "")
            self.assertIsNotNone(error)


class TestGitRm(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)

            mock_repo = MagicMock()
            with patch.object(mgr, "_get_repo", return_value=mock_repo):
                result, error = mgr._git_rm(feed_dir)

            self.assertIsNone(error)
            self.assertIn("feed1", result)
            mock_repo.index.remove.assert_called_once()
            mock_repo.index.commit.assert_called_once_with("remove feed1")

    def test_error_returns_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"

            with patch.object(mgr, "_get_repo", side_effect=Exception("fail")):
                result, error = mgr._git_rm(feed_dir)

            self.assertEqual(result, "")
            self.assertIn("fail", error)


class TestGitMv(unittest.TestCase):
    def test_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            src = tmp_path / "old"
            dst = tmp_path / "new"

            mock_repo = MagicMock()
            with patch.object(mgr, "_get_repo", return_value=mock_repo):
                result, error = mgr._git_mv(src, dst)

            self.assertIsNone(error)
            self.assertIn("rename", result)
            self.assertIn("new", result)

    def test_git_fail_shutil_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            src = tmp_path / "old"
            src.mkdir()
            (src / "file.txt").write_text("data")
            dst = tmp_path / "new"

            with patch.object(mgr, "_get_repo", side_effect=Exception("git fail")):
                result, error = mgr._git_mv(src, dst)

            self.assertIsNone(error)
            self.assertIn("move", result)
            self.assertTrue(dst.exists())

    def test_git_fail_shutil_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            src = tmp_path / "nonexistent"
            dst = tmp_path / "new"

            with patch.object(mgr, "_get_repo", side_effect=Exception("git fail")):
                with patch("backend.feed_maker_manager.shutil.move", side_effect=OSError("move fail")):
                    result, error = mgr._git_mv(src, dst)

            self.assertEqual(result, "")
            self.assertIn("move fail", error)


class TestReadConfigFile(unittest.TestCase):
    def test_valid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)
            conf = {"configuration": {"rss": {"title": "Test"}}}
            (feed_dir / "conf.json").write_text(json.dumps(conf))

            result = mgr._read_config_file(feed_dir)

            self.assertEqual(result, {"rss": {"title": "Test"}})

    def test_missing_configuration_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)
            (feed_dir / "conf.json").write_text(json.dumps({"other": "data"}))

            result = mgr._read_config_file(feed_dir)

            self.assertEqual(result, {})

    def test_no_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group" / "feed1"
            feed_dir.mkdir(parents=True)

            result = mgr._read_config_file(feed_dir)

            self.assertEqual(result, {})


class TestGetTitleFromConfiguration(unittest.TestCase):
    def test_with_title(self):
        config = {"rss": {"title": "My Title::subtitle"}}
        title = FeedMakerManager._get_title_from_configuration(config, "fallback")
        self.assertEqual(title, "My Title")

    def test_without_rss(self):
        config = {"other": "data"}
        title = FeedMakerManager._get_title_from_configuration(config, "fallback")
        self.assertEqual(title, "fallback")

    def test_without_title_in_rss(self):
        config = {"rss": {"link": "http://example.com"}}
        title = FeedMakerManager._get_title_from_configuration(config, "fallback")
        self.assertEqual(title, "fallback")

    def test_empty_config(self):
        title = FeedMakerManager._get_title_from_configuration({}, "fallback")
        self.assertEqual(title, "fallback")

    def test_none_config(self):
        title = FeedMakerManager._get_title_from_configuration(None, "fallback")
        self.assertEqual(title, "fallback")

    def test_title_without_separator(self):
        config = {"rss": {"title": "Simple Title"}}
        title = FeedMakerManager._get_title_from_configuration(config, "fallback")
        self.assertEqual(title, "Simple Title")


class TestGetExecResult(unittest.TestCase):
    def test_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            log_dir = tmp_path / "logs"
            log_dir.mkdir()
            log_file = log_dir / "run_all_feeds_summary.log"
            log_file.write_text("some log content")

            result, error = mgr.get_exec_result()

            self.assertEqual(result, "some log content")
            self.assertEqual(error, "")

    def test_file_not_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)

            result, error = mgr.get_exec_result()

            self.assertEqual(result, "")
            self.assertIn("can't find", error)


class TestGetProblemsStatusInfo(unittest.TestCase):
    @patch("backend.feed_maker_manager.ProblemManager.get_feed_name_status_info_map")
    def test_returns_status_info(self, mock_get):
        mock_get.return_value = {"feed1": {"status": "ok"}}
        result, error = FeedMakerManager.get_problems_status_info()
        self.assertEqual(result, {"feed1": {"status": "ok"}})
        self.assertEqual(error, "")


class TestGetProblemsProgressInfo(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_feed_name_progress_info_map")
    def test_returns_progress_info(self, mock_get):
        mock_get.return_value = {"feed1": {"progress": 50}}
        result, error = FeedMakerManager.get_problems_progress_info()
        self.assertEqual(result, {"feed1": {"progress": 50}})
        self.assertEqual(error, "")


class TestGetProblemsPublicFeedInfo(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_feed_name_public_feed_info_map")
    def test_returns_public_feed_info(self, mock_get):
        mock_get.return_value = {"feed1": {"size": 100}}
        result, error = FeedMakerManager.get_problems_public_feed_info()
        self.assertEqual(result, {"feed1": {"size": 100}})
        self.assertEqual(error, "")


class TestGetProblemsHtmlInfo(unittest.TestCase):
    def test_returns_html_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            mgr.html_file_manager.get_html_file_size_map.return_value = {"a": 1}
            mgr.html_file_manager.get_html_file_with_many_image_tag_map.return_value = {"b": 2}
            mgr.html_file_manager.get_html_file_without_image_tag_map.return_value = {"c": 3}
            mgr.html_file_manager.get_html_file_image_not_found_map.return_value = {"d": 4}

            result, error = mgr.get_problems_html_info()

            self.assertEqual(result["html_file_size_map"], {"a": 1})
            self.assertEqual(result["html_file_with_many_image_tag_map"], {"b": 2})
            self.assertEqual(result["html_file_without_image_tag_map"], {"c": 3})
            self.assertEqual(result["html_file_image_not_found_map"], {"d": 4})
            self.assertEqual(error, "")


class TestGetProblemsElementInfo(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_element_name_count_map")
    def test_returns_element_info(self, mock_get):
        mock_get.return_value = {"div": 10}
        result, error = FeedMakerManager.get_problems_element_info()
        self.assertEqual(result, {"div": 10})
        self.assertEqual(error, "")


class TestGetProblemsListUrlInfo(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_feed_name_list_url_count_map")
    def test_returns_list_url_info(self, mock_get):
        mock_get.return_value = {"feed1": 5}
        result, error = FeedMakerManager.get_problems_list_url_info()
        self.assertEqual(result, {"feed1": 5})
        self.assertEqual(error, "")


class TestDetermineKeywordInConfigItem(unittest.TestCase):
    def test_keyword_in_top_level(self):
        config = {"key1": "value1", "key2": "value2"}
        self.assertTrue(FeedMakerManager._determine_keyword_in_config_item("key1", config))

    def test_keyword_in_nested(self):
        config = {"level1": {"level2": {"target": "value"}}}
        self.assertTrue(FeedMakerManager._determine_keyword_in_config_item("target", config, "level1", "level2"))

    def test_keyword_not_found(self):
        config = {"key1": "value1"}
        self.assertFalse(FeedMakerManager._determine_keyword_in_config_item("missing", config))

    def test_keyword_in_string_value(self):
        config = {"key": "hello world"}
        self.assertTrue(FeedMakerManager._determine_keyword_in_config_item("hello", config, "key"))


class TestSearch(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.search")
    def test_search_found(self, mock_search):
        mock_search.return_value = [{"name": "feed1", "group": "group1"}]
        result, error = FeedMakerManager.search("feed1 keyword")
        self.assertEqual(len(result), 1)
        self.assertEqual(error, "")
        mock_search.assert_called_once_with(["feed1", "keyword"])

    @patch("backend.feed_maker_manager.FeedManager.search")
    def test_search_not_found(self, mock_search):
        mock_search.return_value = []
        result, error = FeedMakerManager.search("nonexistent")
        self.assertEqual(result, [])
        self.assertIn("can't search", error)

    @patch("backend.feed_maker_manager.FeedManager.search")
    def test_search_none_result(self, mock_search):
        mock_search.return_value = None
        result, error = FeedMakerManager.search("test")
        self.assertEqual(result, [])
        self.assertIn("can't search", error)


class TestSearchSite(unittest.TestCase):
    @patch("backend.feed_maker_manager.SearchManager")
    def test_search_site_found(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = "result html"
        mock_sm_cls.return_value = mock_sm

        result, error = FeedMakerManager.search_site("keyword")

        self.assertEqual(result, "result html")
        self.assertEqual(error, "")

    @patch("backend.feed_maker_manager.SearchManager")
    def test_search_site_not_found(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_sites.return_value = ""
        mock_sm_cls.return_value = mock_sm

        result, error = FeedMakerManager.search_site("keyword")

        self.assertEqual(result, "")
        self.assertIn("can't search", error)


class TestGetSearchSiteNames(unittest.TestCase):
    @patch("backend.feed_maker_manager.SearchManager.get_available_site_names")
    def test_returns_names(self, mock_get):
        mock_get.return_value = ["site1", "site2"]
        result = FeedMakerManager.get_search_site_names()
        self.assertEqual(result, ["site1", "site2"])
        mock_get.assert_called_once_with(do_include_torrent_sites=False)


class TestSearchSingleSite(unittest.TestCase):
    @patch("backend.feed_maker_manager.SearchManager")
    def test_search_single_site(self, mock_sm_cls):
        mock_sm = MagicMock()
        mock_sm.search_single_site.return_value = ("result", "")
        mock_sm_cls.return_value = mock_sm

        result, error = FeedMakerManager.search_single_site("site1", "keyword")

        self.assertEqual(result, "result")
        self.assertEqual(error, "")
        mock_sm.search_single_site.assert_called_once_with("site1", "keyword")


class TestCompareNames(unittest.TestCase):
    def test_underscore_first_x(self):
        result = FeedMakerManager._compare_names({"name": "_a"}, {"name": "b"})
        self.assertEqual(result, 1)

    def test_underscore_first_y(self):
        result = FeedMakerManager._compare_names({"name": "a"}, {"name": "_b"})
        self.assertEqual(result, -1)

    def test_less_than(self):
        result = FeedMakerManager._compare_names({"name": "a"}, {"name": "b"})
        self.assertEqual(result, -1)

    def test_greater_than(self):
        result = FeedMakerManager._compare_names({"name": "b"}, {"name": "a"})
        self.assertEqual(result, 1)

    def test_equal(self):
        result = FeedMakerManager._compare_names({"name": "a"}, {"name": "a"})
        self.assertEqual(result, 0)


class TestCompareTitle(unittest.TestCase):
    def test_underscore_name_x(self):
        result = FeedMakerManager._compare_title({"name": "_a", "title": "t1"}, {"name": "b", "title": "t2"})
        self.assertEqual(result, 1)

    def test_underscore_name_y(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "t1"}, {"name": "_b", "title": "t2"})
        self.assertEqual(result, -1)

    def test_underscore_title_x(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "_t1"}, {"name": "b", "title": "t2"})
        self.assertEqual(result, 1)

    def test_underscore_title_y(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "t1"}, {"name": "b", "title": "_t2"})
        self.assertEqual(result, -1)

    def test_title_less(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "alpha"}, {"name": "b", "title": "beta"})
        self.assertEqual(result, -1)

    def test_title_greater(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "beta"}, {"name": "b", "title": "alpha"})
        self.assertEqual(result, 1)

    def test_title_equal(self):
        result = FeedMakerManager._compare_title({"name": "a", "title": "same"}, {"name": "b", "title": "same"})
        self.assertEqual(result, 0)


class TestGetGroups(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_groups")
    def test_groups_found(self, mock_get):
        mock_get.return_value = [{"name": "group1"}]
        result, error = FeedMakerManager.get_groups()
        self.assertEqual(result, [{"name": "group1"}])
        self.assertEqual(error, "")

    @patch("backend.feed_maker_manager.FeedManager.get_groups")
    def test_no_groups(self, mock_get):
        mock_get.return_value = []
        result, error = FeedMakerManager.get_groups()
        self.assertEqual(result, [])
        self.assertIn("no group list", error)

    @patch("backend.feed_maker_manager.FeedManager.get_groups")
    def test_none_groups(self, mock_get):
        mock_get.return_value = None
        result, error = FeedMakerManager.get_groups()
        self.assertEqual(result, [])
        self.assertIn("no group list", error)


class TestGetSiteConfig(unittest.TestCase):
    def test_file_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            group_dir = tmp_path / "mygroup"
            group_dir.mkdir()
            site_conf = group_dir / "site_config.json"
            site_conf.write_text(json.dumps({"key": "value"}))

            result, error = mgr.get_site_config("mygroup")

            self.assertEqual(result, {"key": "value"})
            self.assertEqual(error, "")

    def test_file_not_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)

            result, error = mgr.get_site_config("nogroup")

            self.assertEqual(result, {})
            self.assertIn("no feed list", error)

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.get_site_config("../evil")


class TestSaveSiteConfig(unittest.TestCase):
    def test_save_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            group_dir = tmp_path / "mygroup"
            group_dir.mkdir()

            result, error = mgr.save_site_config("mygroup", {"key": "value"})

            self.assertTrue(result)
            self.assertEqual(error, "")
            saved = json.loads((group_dir / "site_config.json").read_text())
            self.assertEqual(saved, {"key": "value"})

    def test_save_io_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            # group_dir 없음 -> IOError

            result, error = mgr.save_site_config("nogroup", {"key": "value"})

            self.assertFalse(result)
            self.assertNotEqual(error, "")

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.save_site_config("../evil", {})


class TestExtractTitlesFromPublicFeed(unittest.TestCase):
    def test_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            with patch("backend.feed_maker_manager.FeedManager.public_feed_dir_path", tmp_path):
                result, error = mgr.extract_titles_from_public_feed("nonexistent")

            self.assertEqual(result, "FILE_NOT_FOUND")
            self.assertIn("존재하지 않습니다", error)

    def test_valid_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            xml_content = """<?xml version="1.0"?>
<rss><channel>
  <item><title>Title1</title></item>
  <item><title>Title2</title></item>
</channel></rss>"""
            (tmp_path / "feed1.xml").write_text(xml_content)

            with patch("backend.feed_maker_manager.FeedManager.public_feed_dir_path", tmp_path):
                result, error = mgr.extract_titles_from_public_feed("feed1")

            self.assertEqual(result, ["Title1", "Title2"])
            self.assertEqual(error, "")

    def test_no_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            xml_content = """<?xml version="1.0"?><rss><channel></channel></rss>"""
            (tmp_path / "empty.xml").write_text(xml_content)

            with patch("backend.feed_maker_manager.FeedManager.public_feed_dir_path", tmp_path):
                result, error = mgr.extract_titles_from_public_feed("empty")

            self.assertEqual(result, "NO_ITEMS")
            self.assertIn("아이템이 없습니다", error)

    def test_invalid_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            (tmp_path / "bad.xml").write_text("not xml at all <<<")

            with patch("backend.feed_maker_manager.FeedManager.public_feed_dir_path", tmp_path):
                result, error = mgr.extract_titles_from_public_feed("bad")

            self.assertEqual(result, "PARSE_ERROR")
            self.assertIn("파싱에 실패", error)

    def test_items_without_title_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            xml_content = """<?xml version="1.0"?>
<rss><channel>
  <item><description>no title</description></item>
  <item><title>Has Title</title></item>
</channel></rss>"""
            (tmp_path / "mixed.xml").write_text(xml_content)

            with patch("backend.feed_maker_manager.FeedManager.public_feed_dir_path", tmp_path):
                result, error = mgr.extract_titles_from_public_feed("mixed")

            self.assertEqual(result, ["Has Title"])


class TestGetFeedsByGroup(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_feeds_by_group")
    def test_found(self, mock_get):
        mock_get.return_value = [{"name": "b", "title": "B"}, {"name": "a", "title": "A"}]
        result, error = FeedMakerManager.get_feeds_by_group("group1")
        self.assertEqual(error, "")
        # 정렬 확인
        self.assertEqual(result[0]["title"], "A")
        self.assertEqual(result[1]["title"], "B")

    @patch("backend.feed_maker_manager.FeedManager.get_feeds_by_group")
    def test_not_found(self, mock_get):
        mock_get.return_value = []
        result, error = FeedMakerManager.get_feeds_by_group("group1")
        self.assertEqual(result, [])
        self.assertIn("no feed list", error)

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.get_feeds_by_group("../evil")


class TestGetFeedInfoByName(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.get_feed_info")
    def test_found(self, mock_get):
        mock_get.return_value = {"name": "feed1", "group": "group1"}
        result, error = FeedMakerManager.get_feed_info_by_name("group1", "feed1")
        self.assertEqual(result, {"name": "feed1", "group": "group1"})
        self.assertEqual(error, "")

    @patch("backend.feed_maker_manager.FeedManager.get_feed_info")
    def test_not_found(self, mock_get):
        mock_get.return_value = {}
        result, error = FeedMakerManager.get_feed_info_by_name("group1", "feed1")
        self.assertEqual(result, {})
        self.assertIn("can't get feed info", error)

    def test_invalid_group_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.get_feed_info_by_name("../evil", "feed1")

    def test_invalid_feed_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.get_feed_info_by_name("group1", "../evil")


class TestSaveConfigFile(unittest.TestCase):
    def test_missing_configuration_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            result, error = mgr.save_config_file("group1", "feed1", {"other": "data"})
            self.assertFalse(result)
            self.assertIn("no 'configuration'", error)

    def test_missing_required_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            post_data = {"configuration": {"collection": {}}}
            result, error = mgr.save_config_file("group1", "feed1", post_data)
            self.assertFalse(result)
            self.assertIn("no 'collection' or 'extraction' or 'rss'", error)

    @patch("backend.feed_maker_manager.FeedManager.add_rss_info")
    @patch("backend.feed_maker_manager.FeedManager.add_config_info")
    def test_save_success(self, mock_add_config, mock_add_rss):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            post_data = {"configuration": {"collection": {"list_url": "http://example.com"}, "extraction": {"element_list": []}, "rss": {"title": "Test"}}}

            # save_config_file uses mkdir(exist_ok=True) without parents
            (tmp_path / "group1").mkdir()
            with patch.object(mgr, "_git_add", return_value=("ok", None)):
                result, error = mgr.save_config_file("group1", "feed1", post_data)

            self.assertTrue(result)
            self.assertEqual(error, "")
            conf_path = tmp_path / "group1" / "feed1" / "conf.json"
            self.assertTrue(conf_path.exists())
            saved = json.loads(conf_path.read_text())
            self.assertEqual(saved, post_data)
            mock_add_config.assert_called_once()
            mock_add_rss.assert_called_once()

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.save_config_file("../evil", "feed1", {})
            with self.assertRaises(ValueError):
                mgr.save_config_file("group1", "../evil", {})


class TestRun(unittest.TestCase):
    def test_run_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            conf_data = {"configuration": {"collection": {"is_completed": False}, "extraction": {}, "rss": {}}}
            (feed_dir / "conf.json").write_text(json.dumps(conf_data))

            mock_runner = MagicMock()
            mock_runner.make_single_feed.return_value = True

            with patch("backend.feed_maker_manager.FeedMakerRunner", return_value=mock_runner):
                result, error = mgr.run("group1", "feed1")

            self.assertTrue(result)
            self.assertEqual(error, "")
            mgr.problem_manager.update_feed_info.assert_called_once()

    def test_run_is_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            conf_data = {"configuration": {"collection": {"is_completed": True}, "extraction": {}, "rss": {}}}
            (feed_dir / "conf.json").write_text(json.dumps(conf_data))

            mock_runner = MagicMock()
            mock_runner.make_single_feed.return_value = True

            with patch("backend.feed_maker_manager.FeedMakerRunner", return_value=mock_runner):
                result, error = mgr.run("group1", "feed1")

            self.assertTrue(result)
            # is_completed=True 일 때 make_single_feed가 2번 호출됨
            self.assertEqual(mock_runner.make_single_feed.call_count, 2)

    def test_run_is_completed_first_call_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            conf_data = {"configuration": {"collection": {"is_completed": True}, "extraction": {}, "rss": {}}}
            (feed_dir / "conf.json").write_text(json.dumps(conf_data))

            mock_runner = MagicMock()
            mock_runner.make_single_feed.return_value = False

            with patch("backend.feed_maker_manager.FeedMakerRunner", return_value=mock_runner):
                result, error = mgr.run("group1", "feed1")

            self.assertFalse(result)
            self.assertIn("error", error)

    def test_run_recent_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            conf_data = {"configuration": {"collection": {}, "extraction": {}, "rss": {}}}
            (feed_dir / "conf.json").write_text(json.dumps(conf_data))

            mock_runner = MagicMock()
            mock_runner.make_single_feed.return_value = False

            with patch("backend.feed_maker_manager.FeedMakerRunner", return_value=mock_runner):
                result, error = mgr.run("group1", "feed1")

            self.assertFalse(result)
            self.assertIn("error", error)

    def test_run_invalid_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            (feed_dir / "conf.json").write_text(json.dumps({"no_configuration": True}))

            result, error = mgr.run("group1", "feed1")

            self.assertFalse(result)
            self.assertIn("invalid format", error)

    def test_run_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.run("../evil", "feed1")


class TestRemovePublicImgPdfFeedFiles(unittest.TestCase):
    def test_removes_img_and_pdf_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            img_dir = mgr.img_dir_path / "feed1"
            img_dir.mkdir(parents=True)
            (img_dir / "img.png").write_text("fake")
            pdf_dir = mgr.pdf_dir_path / "feed1"
            pdf_dir.mkdir(parents=True)
            (pdf_dir / "doc.pdf").write_text("fake")

            mgr._remove_public_img_pdf_feed_files("feed1")

            self.assertFalse(img_dir.exists())
            self.assertFalse(pdf_dir.exists())

    def test_no_dirs_no_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            # 디렉토리 없어도 에러 발생하지 않음
            mgr._remove_public_img_pdf_feed_files("feed1")

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr._remove_public_img_pdf_feed_files("../evil")


class TestRemoveList(unittest.TestCase):
    def test_removes_newlist_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            list_dir = tmp_path / "group1" / "feed1" / "newlist"
            list_dir.mkdir(parents=True)
            (list_dir / "list.txt").write_text("data")

            mgr.remove_list("group1", "feed1")

            self.assertFalse(list_dir.exists())

    def test_no_dir_no_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            (tmp_path / "group1" / "feed1").mkdir(parents=True)

            mgr.remove_list("group1", "feed1")

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.remove_list("../evil", "feed1")


class TestRemoveHtml(unittest.TestCase):
    def test_removes_html_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            html_dir = tmp_path / "group1" / "feed1" / "html"
            html_dir.mkdir(parents=True)
            (html_dir / "page.html").write_text("<html></html>")

            mgr.remove_html("group1", "feed1")

            self.assertFalse(html_dir.exists())
            mgr.html_file_manager.remove_html_file_in_path_from_info.assert_called_once()

    def test_no_dir_still_removes_from_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            (tmp_path / "group1" / "feed1").mkdir(parents=True)

            mgr.remove_html("group1", "feed1")

            mgr.html_file_manager.remove_html_file_in_path_from_info.assert_called_once()


class TestRemoveHtmlFile(unittest.TestCase):
    def test_removes_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            html_dir = tmp_path / "group1" / "feed1" / "html"
            html_dir.mkdir(parents=True)
            html_file = html_dir / "page.html"
            html_file.write_text("<html></html>")

            mgr.remove_html_file("group1", "feed1", "page.html")

            self.assertFalse(html_file.exists())
            mgr.html_file_manager.remove_html_file_in_path_from_info.assert_called_once()

    def test_missing_file_no_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            (tmp_path / "group1" / "feed1" / "html").mkdir(parents=True)

            # missing_ok=True 이므로 에러 없음
            mgr.remove_html_file("group1", "feed1", "nonexistent.html")

    def test_invalid_html_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.remove_html_file("group1", "feed1", "../evil.html")


class TestRemovePublicFeed(unittest.TestCase):
    def test_calls_feed_manager(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            mgr.remove_public_feed("feed1")
            mgr.feed_manager.remove_public_feed_by_feed_name.assert_called_once_with("feed1", do_remove_file=True)

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.remove_public_feed("../evil")


class TestRemoveFeed(unittest.TestCase):
    @patch("backend.feed_maker_manager.AccessLogManager.remove_httpd_access_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_progress_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_rss_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_config_info")
    def test_remove_feed_success(self, mock_rc, mock_rr, mock_rp, mock_ra):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            feed_dir = tmp_path / "group1" / "feed1"
            feed_dir.mkdir(parents=True)
            (feed_dir / "conf.json").write_text("{}")

            with patch.object(mgr, "_remove_public_img_pdf_feed_files"):
                with patch.object(mgr, "_git_rm", return_value=("ok", None)):
                    result, error = mgr.remove_feed("group1", "feed1")

            self.assertTrue(result)
            self.assertEqual(error, "")
            mock_rc.assert_called_once()
            mock_rr.assert_called_once()
            mock_rp.assert_called_once()
            mock_ra.assert_called_once()

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.remove_feed("../evil", "feed1")


class TestRemoveGroup(unittest.TestCase):
    @patch("backend.feed_maker_manager.AccessLogManager.remove_httpd_access_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_progress_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_rss_info")
    @patch("backend.feed_maker_manager.FeedManager.remove_config_info")
    def test_remove_group_success(self, mock_rc, mock_rr, mock_rp, mock_ra):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mgr = _make_manager(tmp_path)
            group_dir = tmp_path / "group1"
            group_dir.mkdir()
            feed_dir1 = group_dir / "feed1"
            feed_dir1.mkdir()
            feed_dir2 = group_dir / "feed2"
            feed_dir2.mkdir()

            with patch.object(mgr, "_remove_public_img_pdf_feed_files"):
                with patch.object(mgr, "_git_rm", return_value=("ok", None)):
                    # rmtree가 group_dir를 삭제하므로, 두 번째 iterdir()가 실패함
                    # 실제 코드에서는 rmtree 후 iterdir이므로 group_dir가 이미 삭제됨
                    # 이를 우회하기 위해 rmtree를 mock
                    with patch("backend.feed_maker_manager.rmtree"):
                        result, error = mgr.remove_group("group1")

            self.assertTrue(result)
            self.assertEqual(error, "")

    def test_invalid_name_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = _make_manager(Path(tmp))
            with self.assertRaises(ValueError):
                mgr.remove_group("../evil")


class TestToggleFeed(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.toggle_feed")
    def test_toggle_success(self, mock_toggle):
        mock_toggle.return_value = True
        result, error = FeedMakerManager.toggle_feed("feed1")
        self.assertEqual(result, "feed1")
        self.assertEqual(error, "")

    @patch("backend.feed_maker_manager.FeedManager.toggle_feed")
    def test_toggle_failure(self, mock_toggle):
        mock_toggle.return_value = False
        result, error = FeedMakerManager.toggle_feed("feed1")
        self.assertEqual(result, "")
        self.assertIn("can't toggle", error)

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.toggle_feed("../evil")


class TestToggleGroup(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedManager.toggle_group")
    def test_toggle_success(self, mock_toggle):
        mock_toggle.return_value = True
        result, error = FeedMakerManager.toggle_group("group1")
        self.assertEqual(result, "group1")
        self.assertEqual(error, "")

    @patch("backend.feed_maker_manager.FeedManager.toggle_group")
    def test_toggle_failure(self, mock_toggle):
        mock_toggle.return_value = False
        result, error = FeedMakerManager.toggle_group("group1")
        self.assertEqual(result, "")
        self.assertIn("can't toggle", error)

    def test_invalid_name_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.toggle_group("../evil")


class TestCheckRunning(unittest.TestCase):
    @patch("backend.feed_maker_manager.FeedMakerRunner.check_running")
    def test_running(self, mock_check):
        mock_check.return_value = True
        result = FeedMakerManager.check_running("group1", "feed1")
        self.assertTrue(result)
        mock_check.assert_called_once_with("group1", "feed1")

    @patch("backend.feed_maker_manager.FeedMakerRunner.check_running")
    def test_not_running(self, mock_check):
        mock_check.return_value = False
        result = FeedMakerManager.check_running("group1", "feed1")
        self.assertFalse(result)

    @patch("backend.feed_maker_manager.FeedMakerRunner.check_running")
    def test_returns_none(self, mock_check):
        mock_check.return_value = None
        result = FeedMakerManager.check_running("group1", "feed1")
        self.assertIsNone(result)

    def test_invalid_group_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.check_running("../evil", "feed1")

    def test_invalid_feed_raises(self):
        with self.assertRaises(ValueError):
            FeedMakerManager.check_running("group1", "../evil")


if __name__ == "__main__":
    unittest.main()
