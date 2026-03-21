#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import logging.config
from pathlib import Path
from datetime import timedelta
import unittest
from unittest.mock import patch

from bin.feed_maker import FeedMaker
from bin.feed_maker_util import Config, Datetime, Env, header_str, NotFoundConfigItemError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class FeedMakerMakeTestBase(unittest.TestCase):
    """Base class that creates a FeedMaker instance with real dirs and mocked config."""

    def setUp(self) -> None:
        self.group_name = "naver"
        self.feed_name = "test_make_feed"
        self.feed_dir_path = Path(Env.get("FM_WORK_DIR")) / self.group_name / self.feed_name
        self.feed_dir_path.mkdir(parents=True, exist_ok=True)
        self.rss_file_path = self.feed_dir_path / f"{self.feed_name}.xml"
        self.rss_file_path.touch()

        sample_conf = Path(__file__).parent / "conf.naverwebtoon.json"
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        shutil.copy(sample_conf, conf_file)

        self.maker = FeedMaker(feed_dir_path=self.feed_dir_path, do_collect_by_force=False, do_collect_only=False, rss_file_path=self.rss_file_path)
        config = Config(feed_dir_path=self.feed_dir_path)
        self.maker.collection_conf = config.get_collection_configs()
        self.maker.extraction_conf = config.get_extraction_configs()
        self.maker.rss_conf = config.get_rss_configs()
        # avoid running download_image.py
        self.maker.extraction_conf["post_process_script_list"] = []

        self.html_dir = self.feed_dir_path / "html"
        self.list_dir = self.feed_dir_path / "newlist"
        self.img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

    def tearDown(self) -> None:
        if hasattr(self.maker, "failed_urls_cache_file") and self.maker.failed_urls_cache_file.exists():
            self.maker.failed_urls_cache_file.unlink(missing_ok=True)
        del self.maker
        shutil.rmtree(self.feed_dir_path, ignore_errors=True)
        feed_img = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / self.feed_name
        shutil.rmtree(feed_img, ignore_errors=True)


# ---------------------------------------------------------------------------
# _make_html_file tests
# ---------------------------------------------------------------------------
class TestMakeHtmlFileExistingWithImageTag(FeedMakerMakeTestBase):
    """Existing HTML file that has image tag -> returns True (old feed)."""

    def test_existing_file_with_image_tag(self) -> None:
        item_url = "http://example.com/page/1"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        image_tag = FeedMaker.get_image_tag_str(self.img_url_prefix, self.rss_file_path.name, item_url)
        # write file larger than template+image_tag size
        html_path.write_text(header_str + "\n" + image_tag + "\n" + "A" * 500, encoding="utf-8")

        result = self.maker._make_html_file(item_url, "Title1")
        self.assertTrue(result)


class TestMakeHtmlFileExistingWithoutImageTag(FeedMakerMakeTestBase):
    """Existing HTML file without image tag -> removes file, returns False."""

    def test_existing_file_without_image_tag(self) -> None:
        item_url = "http://example.com/page/2"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        # write file larger than template+image_tag but NO image tag
        html_path.write_text(header_str + "\n" + "B" * 500, encoding="utf-8")

        result = self.maker._make_html_file(item_url, "Title2")
        self.assertFalse(result)
        self.assertFalse(html_path.is_file())


class TestMakeHtmlFileCrawlerFails(FeedMakerMakeTestBase):
    """Crawler returns error -> returns False."""

    def test_crawler_fails(self) -> None:
        item_url = "http://example.com/page/fail_crawl"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = (None, "connection error", None)

            result = self.maker._make_html_file(item_url, "Fail")
            self.assertFalse(result)


class TestMakeHtmlFileExtractorFails(FeedMakerMakeTestBase):
    """Extractor returns empty content -> returns False."""

    def test_extractor_fails(self) -> None:
        item_url = "http://example.com/page/fail_extract"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Fail")
            self.assertFalse(result)


class TestMakeHtmlFileBypassExtraction(FeedMakerMakeTestBase):
    """bypass_element_extraction=True skips extractor."""

    def test_bypass_extraction(self) -> None:
        item_url = "http://example.com/page/bypass"
        self.maker.extraction_conf["bypass_element_extraction"] = True
        big_content = header_str + "\n" + "C" * 500

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = (big_content, None, None)

            result = self.maker._make_html_file(item_url, "Bypass")
            self.assertTrue(result)

        self.maker.extraction_conf.pop("bypass_element_extraction", None)


class TestMakeHtmlFilePostProcessScript(FeedMakerMakeTestBase):
    """post_process_script_list is executed."""

    def test_post_process_script(self) -> None:
        item_url = "http://example.com/page/postproc"
        big_content = header_str + "\n" + "D" * 500
        self.maker.extraction_conf["post_process_script_list"] = ["my_script.py"]

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=big_content), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(big_content, None)), patch("shutil.which", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "PostProc")
            self.assertTrue(result)

        self.maker.extraction_conf["post_process_script_list"] = []


class TestMakeHtmlFilePostProcessFails(FeedMakerMakeTestBase):
    """post_process_script fails -> returns False."""

    def test_post_process_fails(self) -> None:
        item_url = "http://example.com/page/postfail"
        self.maker.extraction_conf["post_process_script_list"] = ["fail_script.py"]
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value="<html>ok</html>"), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(None, "script error")), patch("shutil.which", return_value=None):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "PostFail")
            self.assertFalse(result)

        self.maker.extraction_conf["post_process_script_list"] = []


class TestMakeHtmlFileSizeTooSmall(FeedMakerMakeTestBase):
    """Created file smaller than template -> excluded, returns False."""

    def test_size_too_small(self) -> None:
        item_url = "http://example.com/page/small"
        tiny_content = "tiny"  # much smaller than template

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=tiny_content):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Small")
            self.assertFalse(result)


class TestMakeHtmlFileExceptionDuringCreation(FeedMakerMakeTestBase):
    """Exception during HTML creation -> returns False."""

    def test_exception_during_creation(self) -> None:
        item_url = "http://example.com/page/exc"
        self.maker.rss_conf["ignore_broken_link"] = "1 hour"

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls:
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.side_effect = RuntimeError("boom")

            result = self.maker._make_html_file(item_url, "Exc")
            self.assertFalse(result)


class TestMakeHtmlFileThresholdCheck(FeedMakerMakeTestBase):
    """threshold_to_remove_html_with_incomplete_image triggers removal."""

    def test_threshold_removes_html(self) -> None:
        item_url = "http://example.com/page/threshold"
        big_content = header_str + "\n" + "E" * 500
        self.maker.extraction_conf["threshold_to_remove_html_with_incomplete_image"] = 1

        with (
            patch("bin.feed_maker.Crawler") as mock_crawler_cls,
            patch("bin.feed_maker.Extractor.extract_content", return_value=big_content),
            patch("bin.feed_maker.FileManager.get_incomplete_image_list", return_value=["img1", "img2"]),
            patch("bin.feed_maker.FileManager.remove_image_files_with_zero_size"),
            patch("bin.feed_maker.FileManager.remove_html_file_without_cached_image_files"),
        ):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "Threshold")
            self.assertFalse(result)

        self.maker.extraction_conf.pop("threshold_to_remove_html_with_incomplete_image", None)


class TestMakeHtmlFileNoExtractionConf(FeedMakerMakeTestBase):
    """No extraction_conf -> returns False early."""

    def test_no_extraction_conf(self) -> None:
        self.maker.extraction_conf = {}
        result = self.maker._make_html_file("http://example.com/x", "X")
        self.assertFalse(result)


class TestMakeHtmlFilePostProcessSystemProgram(FeedMakerMakeTestBase):
    """Post-process script found in system path (/usr/bin) uses simple command."""

    def test_system_program_path(self) -> None:
        item_url = "http://example.com/page/sysprog"
        big_content = header_str + "\n" + "F" * 500
        self.maker.extraction_conf["post_process_script_list"] = ["sed s/a/b/"]

        with patch("bin.feed_maker.Crawler") as mock_crawler_cls, patch("bin.feed_maker.Extractor.extract_content", return_value=big_content), patch("bin.feed_maker_util.Process.exec_cmd", return_value=(big_content, None)) as mock_exec, patch("shutil.which", return_value="/usr/bin/sed"):
            mock_crawler_cls.get_option_str.return_value = ""
            inst = mock_crawler_cls.return_value
            inst.run.return_value = ("<html>raw</html>", None, None)

            result = self.maker._make_html_file(item_url, "SysProg")
            self.assertTrue(result)
            # system program: command without -f option
            cmd_arg = mock_exec.call_args[0][0]
            self.assertNotIn("-f", cmd_arg)

        self.maker.extraction_conf["post_process_script_list"] = []


# ---------------------------------------------------------------------------
# _get_index_data tests
# ---------------------------------------------------------------------------
class TestGetIndexDataFileExists(FeedMakerMakeTestBase):
    """start_idx.txt exists with valid data."""

    def test_file_exists_with_data(self) -> None:
        mtime_str = "2025-01-15T10:00:00+00:00"
        self.maker.start_index_file_path.write_text(f"10\t{mtime_str}\n", encoding="utf-8")
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 10)
        self.assertEqual(end, 10 + self.maker.window_size)
        self.assertIsNotNone(mtime)


class TestGetIndexDataFileNotExist(FeedMakerMakeTestBase):
    """start_idx.txt does not exist -> creates it."""

    def test_file_not_exist(self) -> None:
        self.maker.start_index_file_path.unlink(missing_ok=True)
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 1)
        self.assertEqual(end, 1 + self.maker.window_size)
        self.assertIsNotNone(mtime)
        self.assertTrue(self.maker.start_index_file_path.is_file())


class TestGetIndexDataFileExistsNoMatch(FeedMakerMakeTestBase):
    """start_idx.txt exists but has no matching data -> fallback to default."""

    def test_file_exists_no_match(self) -> None:
        self.maker.start_index_file_path.write_text("invalid_content\n", encoding="utf-8")
        start, end, mtime = self.maker._get_index_data()
        self.assertEqual(start, 1)
        self.assertEqual(end, 1 + self.maker.window_size)


# ---------------------------------------------------------------------------
# _write_index_data tests
# ---------------------------------------------------------------------------
class TestWriteIndexDataWithIncrement(FeedMakerMakeTestBase):
    """increment_size > 0 triggers write."""

    def test_increment_write(self) -> None:
        past = Datetime.get_current_time() - timedelta(days=2)
        self.maker.collection_conf["unit_size_per_day"] = 2
        next_idx, ts_str = self.maker._write_index_data(5, past)
        self.assertGreater(next_idx, 5)
        self.assertIsNotNone(ts_str)
        self.assertTrue(self.maker.start_index_file_path.is_file())


class TestWriteIndexDataInitialWrite(FeedMakerMakeTestBase):
    """do_write_initially=True triggers write even with 0 increment."""

    def test_initial_write(self) -> None:
        now = Datetime.get_current_time()
        next_idx, ts_str = self.maker._write_index_data(1, now, do_write_initially=True)
        self.assertEqual(next_idx, 1)
        self.assertIsNotNone(ts_str)


class TestWriteIndexDataNoWrite(FeedMakerMakeTestBase):
    """No increment and not initial -> no write."""

    def test_no_write(self) -> None:
        now = Datetime.get_current_time()
        self.maker.collection_conf["unit_size_per_day"] = 0
        next_idx, ts_str = self.maker._write_index_data(1, now, do_write_initially=False)
        self.assertEqual(next_idx, 1)
        self.assertIsNone(ts_str)


# ---------------------------------------------------------------------------
# _fetch_old_feed_list_window tests
# ---------------------------------------------------------------------------
class TestFetchOldFeedListWindow(FeedMakerMakeTestBase):
    """Normal window slicing."""

    def test_normal_window(self) -> None:
        old_list = [("http://example.com/1", "Title1", []), ("http://example.com/2", "Title2", []), ("http://example.com/3", "Title3", [])]
        # sort_field_pattern from config: "no=(\d+)\t" won't match these URLs
        # so matched_count will be 0, and sorted_feed_list = feed_id_sort_field_list (unsorted)
        self.maker.collection_conf["sort_field_pattern"] = r"example.com/(\d+)"
        self.maker.window_size = 2
        # ensure start_idx file
        self.maker.start_index_file_path.unlink(missing_ok=True)

        result = self.maker._fetch_old_feed_list_window(old_list)
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result), 2)


class TestFetchOldFeedListWindowNoMtime(FeedMakerMakeTestBase):
    """_get_index_data returns None mtime -> returns None."""

    def test_no_mtime(self) -> None:
        old_list = [("http://example.com/1", "T", [])]
        self.maker.collection_conf["sort_field_pattern"] = r"example.com/(\d+)"

        with patch.object(self.maker, "_get_index_data", return_value=(0, 0, None)):
            result = self.maker._fetch_old_feed_list_window(old_list)
            self.assertIsNone(result)


class TestFetchOldFeedListWindowNoSortFieldPattern(FeedMakerMakeTestBase):
    """Missing sort_field_pattern raises NotFoundConfigItemError."""

    def test_no_sort_field_pattern(self) -> None:
        self.maker.collection_conf["sort_field_pattern"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._fetch_old_feed_list_window([("http://a.com/1", "T", [])])


# ---------------------------------------------------------------------------
# _get_recent_feed_list tests
# ---------------------------------------------------------------------------
class TestGetRecentFeedList(FeedMakerMakeTestBase):
    """Delegates to NewlistCollector."""

    def test_delegates_to_collector(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_cls:
            mock_cls.return_value.collect.return_value = [("http://x.com/1", "X", [])]
            result = self.maker._get_recent_feed_list()
            self.assertEqual(len(result), 1)
            mock_cls.assert_called_once()


# ---------------------------------------------------------------------------
# _get_new_feeds tests
# ---------------------------------------------------------------------------
class TestGetNewFeeds(FeedMakerMakeTestBase):
    """Filters items not in old list."""

    def test_filters_new(self) -> None:
        recent = [("http://a.com/1", "A", []), ("http://b.com/2", "B", [])]
        old = [("http://a.com/1", "A", [])]
        result = self.maker._get_new_feeds(recent, old)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://b.com/2")

    def test_no_new_feeds(self) -> None:
        recent = [("http://a.com/1", "A", [])]
        old = [("http://a.com/1", "A", [])]
        result = self.maker._get_new_feeds(recent, old)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _diff_feeds_and_make_htmls tests
# ---------------------------------------------------------------------------
class TestDiffFeedsAndMakeHtmls(FeedMakerMakeTestBase):
    """Merges new + old and calls _make_html_file."""

    def test_new_and_old_merge(self) -> None:
        recent = [("http://a.com/1", "A", []), ("http://b.com/2", "B", [])]
        old = [("http://a.com/1", "A", [])]

        with patch.object(self.maker, "_make_html_file", return_value=True):
            result = self.maker._diff_feeds_and_make_htmls(recent, old)
            self.assertGreaterEqual(len(result), 1)
            self.assertLessEqual(len(result), self.maker.window_size)


class TestDiffFeedsHtmlFailure(FeedMakerMakeTestBase):
    """_make_html_file returns False -> item not in merged list."""

    def test_html_failure_excluded(self) -> None:
        recent = [("http://a.com/1", "A", [])]
        old: list = []

        with patch.object(self.maker, "_make_html_file", return_value=False):
            result = self.maker._diff_feeds_and_make_htmls(recent, old)
            self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# _generate_rss_feed tests
# ---------------------------------------------------------------------------
class TestGenerateRssFeed(FeedMakerMakeTestBase):
    """RSS generation, file comparison, rename."""

    def test_generates_rss(self) -> None:
        item_url = "http://example.com/rss/1"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        html_path.write_text(header_str + "\ncontent here\n", encoding="utf-8")

        merged = [(item_url, "RSSTitle", [])]
        result = self.maker._generate_rss_feed(merged)
        self.assertTrue(result)
        self.assertTrue(self.rss_file_path.is_file())

    def test_no_rss_conf(self) -> None:
        self.maker.rss_conf = {}
        result = self.maker._generate_rss_feed([])
        self.assertFalse(result)

    def test_same_content_no_rename(self) -> None:
        """When new RSS is same as existing, temp file is deleted."""
        item_url = "http://example.com/rss/same"
        html_path = FeedMaker._get_html_file_path(self.html_dir, item_url)
        html_path.write_text(header_str + "\ncontent\n", encoding="utf-8")

        merged = [(item_url, "Same", [])]
        # Generate first time
        self.maker._generate_rss_feed(merged)
        # Generate again (same content)
        with patch("bin.feed_maker.Data.compare_two_rss_files", return_value=True):
            result = self.maker._generate_rss_feed(merged)
            self.assertTrue(result)


class TestGenerateRssFeedMissingTitle(FeedMakerMakeTestBase):
    """Missing rss_title raises NotFoundConfigItemError."""

    def test_missing_title(self) -> None:
        self.maker.rss_conf["rss_title"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._generate_rss_feed([])


class TestGenerateRssFeedMissingLink(FeedMakerMakeTestBase):
    """Missing rss_link raises NotFoundConfigItemError."""

    def test_missing_link(self) -> None:
        self.maker.rss_conf["rss_link"] = ""
        with self.assertRaises(NotFoundConfigItemError):
            self.maker._generate_rss_feed([])


# ---------------------------------------------------------------------------
# make() tests
# ---------------------------------------------------------------------------
class TestMakeIsCompletedPath(FeedMakerMakeTestBase):
    """make() with is_completed=True uses _fetch_old_feed_list_window."""

    def test_is_completed(self) -> None:
        # Write list files for completed feed
        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = self.list_dir / f"{date_str}.txt"
        list_file.write_text("http://example.com/c/1\tC1\n", encoding="utf-8")

        # Set is_completed in config file
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        import json

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["is_completed"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch.object(FeedMaker, "_fetch_old_feed_list_window", return_value=[("http://example.com/c/1", "C1", [])]) as mock_fetch, patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            result = self.maker.make()
            self.assertTrue(result)
            mock_fetch.assert_called_once()


class TestMakeNormalPath(FeedMakerMakeTestBase):
    """make() normal (not completed) path."""

    def test_normal_path(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)


class TestMakeCollectOnly(FeedMakerMakeTestBase):
    """make() with do_collect_only skips RSS generation."""

    def test_collect_only(self) -> None:
        self.maker.do_collect_only = True

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_generate_rss_feed") as mock_gen:
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)
            mock_gen.assert_not_called()


class TestMakeIgnoreOldList(FeedMakerMakeTestBase):
    """make() with ignore_old_list clears old list before diff."""

    def test_ignore_old_list(self) -> None:
        # Write list file so old_feed_list is non-empty initially
        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = self.list_dir / f"{date_str}.txt"
        list_file.write_text("http://example.com/old/1\tOld1\n", encoding="utf-8")

        # Set ignore_old_list in the config
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        import json

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["ignore_old_list"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]) as mock_diff, patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)
            # old_feed_list should have been cleared
            call_args = mock_diff.call_args
            old_list_arg = call_args[1].get("old_feed_list", call_args[0][1])
            self.assertEqual(old_list_arg, [])


class TestMakeRecentFeedListEmpty(FeedMakerMakeTestBase):
    """make() returns False when recent feed list is empty."""

    def test_empty_recent(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector:
            mock_collector.return_value.collect.return_value = []

            result = self.maker.make()
            self.assertFalse(result)


class TestMakeGenerateRssFails(FeedMakerMakeTestBase):
    """make() returns False when _generate_rss_feed fails."""

    def test_rss_generation_fails(self) -> None:
        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=False):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertFalse(result)


class TestMakeForceCollect(FeedMakerMakeTestBase):
    """make() with do_collect_by_force sets is_completed=False."""

    def test_force_collect(self) -> None:
        self.maker.do_collect_by_force = True

        with patch("bin.feed_maker.NewlistCollector") as mock_collector, patch.object(FeedMaker, "_diff_feeds_and_make_htmls", return_value=[("http://x.com/1", "X", [])]), patch.object(FeedMaker, "_generate_rss_feed", return_value=True), patch("bin.feed_maker.Uploader.upload"):
            mock_collector.return_value.collect.return_value = [("http://x.com/1", "X", [])]

            result = self.maker.make()
            self.assertTrue(result)


class TestMakeCompletedWindowEmpty(FeedMakerMakeTestBase):
    """make() with is_completed returns False when window is empty."""

    def test_completed_empty_window(self) -> None:
        conf_file = self.feed_dir_path / Config.DEFAULT_CONF_FILE
        import json

        with conf_file.open("r", encoding="utf-8") as f:
            conf_data = json.load(f)
        conf_data["configuration"]["collection"]["is_completed"] = True
        with conf_file.open("w", encoding="utf-8") as f:
            json.dump(conf_data, f)

        with patch.object(FeedMaker, "_fetch_old_feed_list_window", return_value=[]):
            result = self.maker.make()
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
