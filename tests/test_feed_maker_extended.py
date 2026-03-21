#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import logging.config
from pathlib import Path
from datetime import timedelta
import unittest

from bin.feed_maker import FeedMaker
from bin.feed_maker_util import Config, Datetime, URL, Env, header_str

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestCmpIntOrStr(unittest.TestCase):
    def test_both_numeric(self) -> None:
        a = {"sf": "10"}
        b = {"sf": "3"}
        self.assertGreater(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_numeric_equal(self) -> None:
        a = {"sf": "5"}
        b = {"sf": "5"}
        self.assertEqual(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_numeric_less(self) -> None:
        a = {"sf": "2"}
        b = {"sf": "10"}
        self.assertLess(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_less(self) -> None:
        a = {"sf": "apple"}
        b = {"sf": "banana"}
        self.assertLess(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_greater(self) -> None:
        a = {"sf": "banana"}
        b = {"sf": "apple"}
        self.assertGreater(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_both_string_equal(self) -> None:
        a = {"sf": "same"}
        b = {"sf": "same"}
        self.assertEqual(FeedMaker._cmp_int_or_str(a, b), 0)

    def test_mixed_numeric_and_string(self) -> None:
        # One numeric, one string -> string comparison
        a = {"sf": "10"}
        b = {"sf": "abc"}
        result = FeedMaker._cmp_int_or_str(a, b)
        self.assertIsInstance(result, int)


class TestCmpToKey(unittest.TestCase):
    def test_sorting_with_cmp_to_key(self) -> None:
        items = [{"sf": "10"}, {"sf": "2"}, {"sf": "5"}]
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        sorted_items = sorted(items, key=key_func)
        self.assertEqual([d["sf"] for d in sorted_items], ["2", "5", "10"])

    def test_comparator_lt_gt_eq(self) -> None:
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        k1 = key_func({"sf": "1"})
        k2 = key_func({"sf": "2"})
        k3 = key_func({"sf": "2"})

        self.assertTrue(k1 < k2)
        self.assertTrue(k2 > k1)
        self.assertTrue(k2 == k3)
        self.assertTrue(k1 <= k2)
        self.assertTrue(k2 >= k1)
        self.assertTrue(k1 != k2)

    def test_eq_with_non_k_type(self) -> None:
        key_func = FeedMaker._cmp_to_key(FeedMaker._cmp_int_or_str)
        k1 = key_func({"sf": "1"})
        self.assertEqual(k1.__eq__("not_a_K"), NotImplemented)
        self.assertEqual(k1.__ne__("not_a_K"), NotImplemented)


class TestGetImageTagStr(unittest.TestCase):
    def test_generates_image_tag(self) -> None:
        result = FeedMaker.get_image_tag_str("https://example.com", "feed.xml", "http://item.com/page/1")
        self.assertIn("https://example.com", result)
        self.assertIn("feed.xml", result)
        self.assertIn("1x1.jpg", result)
        self.assertTrue(result.startswith("<img"))

    def test_default_item_url(self) -> None:
        result = FeedMaker.get_image_tag_str("https://example.com", "feed.xml")
        md5 = URL.get_short_md5_name(URL.get_url_path("any_url"))
        self.assertIn(md5, result)


class TestGetSizeOfTemplateWithImageTag(unittest.TestCase):
    def test_returns_positive_int(self) -> None:
        size = FeedMaker.get_size_of_template_with_image_tag("https://example.com", "feed.xml")
        self.assertGreater(size, 0)
        # Should be header + newline + image_tag + newline
        image_tag = FeedMaker.get_image_tag_str("https://example.com", "feed.xml")
        expected = len(header_str) + len("\n") + len(image_tag) + len("\n")
        self.assertEqual(size, expected)


class TestIsImageTagInHtmlFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "fm_ext_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.html_file = self.work_dir / "test.html"

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_tag_found(self) -> None:
        self.html_file.write_text("<html><img src='test'/></html>", encoding="utf-8")
        self.assertTrue(FeedMaker._is_image_tag_in_html_file(self.html_file, "<img src='test'/>"))

    def test_tag_not_found(self) -> None:
        self.html_file.write_text("<html><p>no image</p></html>", encoding="utf-8")
        self.assertFalse(FeedMaker._is_image_tag_in_html_file(self.html_file, "<img src='test'/>"))


class TestAppendImageTagToHtmlFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "fm_ext_test_append"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.html_file = self.work_dir / "test.html"

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def test_appends_tag(self) -> None:
        self.html_file.write_text("<html></html>", encoding="utf-8")
        FeedMaker._append_image_tag_to_html_file(self.html_file, "<img src='tag'/>")
        content = self.html_file.read_text(encoding="utf-8")
        self.assertIn("<img src='tag'/>", content)
        self.assertTrue(content.endswith("\n"))


class TestGetHtmlFilePath(unittest.TestCase):
    def test_constructs_path(self) -> None:
        html_dir = Path("/tmp/html")
        result = FeedMaker._get_html_file_path(html_dir, "http://example.com/page/1")
        self.assertEqual(result.parent, html_dir)
        self.assertTrue(result.name.endswith(".html"))
        # Should use md5 of url path
        expected_md5 = URL.get_short_md5_name(URL.get_url_path("http://example.com/page/1"))
        self.assertEqual(result.name, f"{expected_md5}.html")


class TestGetListFilePath(unittest.TestCase):
    def test_constructs_path(self) -> None:
        list_dir = Path("/tmp/newlist")
        result = FeedMaker._get_list_file_path(list_dir, "20240101")
        self.assertEqual(result, list_dir / "20240101.txt")


class TestGetSizeOfTemplate(unittest.TestCase):
    def test_returns_header_plus_newline(self) -> None:
        size = FeedMaker._get_size_of_template()
        self.assertEqual(size, len(header_str) + 1)


class TestReadOldFeedListFromFile(unittest.TestCase):
    def setUp(self) -> None:
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "fm_ext_test_feed_list"
        self.feed_dir = self.work_dir / "test_feed"
        self.feed_dir.mkdir(parents=True, exist_ok=True)
        self.list_dir = self.feed_dir / "newlist"
        self.list_dir.mkdir(exist_ok=True)
        self.html_dir = self.feed_dir / "html"
        self.html_dir.mkdir(exist_ok=True)

        self.sample_conf_file = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file = self.feed_dir / Config.DEFAULT_CONF_FILE
        if self.sample_conf_file.is_file():
            shutil.copy(self.sample_conf_file, self.conf_file)

        self.rss_file = self.feed_dir / "test.xml"
        self.rss_file.touch()

    def tearDown(self) -> None:
        shutil.rmtree(self.work_dir, ignore_errors=True)

    def _make_maker(self) -> FeedMaker:
        return FeedMaker(feed_dir_path=self.feed_dir, do_collect_by_force=False, do_collect_only=False, rss_file_path=self.rss_file)

    def test_no_collection_conf_returns_empty(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {}
        result = maker._read_old_feed_list_from_file()
        self.assertEqual(result, [])

    def test_not_completed_reads_recent_list_file(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = FeedMaker._get_list_file_path(self.list_dir, date_str)
        list_file.write_text("http://example.com/1\tTitle1\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://example.com/1")
        self.assertEqual(result[0][1], "Title1")

    def test_not_completed_searches_past_days(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        # No file for today, but file exists for 2 days ago
        dt = Datetime.get_current_time()
        past_date_str = Datetime.get_short_date_str(dt - timedelta(days=2))
        list_file = FeedMaker._get_list_file_path(self.list_dir, past_date_str)
        list_file.write_text("http://example.com/old\tOldTitle\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "http://example.com/old")

    def test_not_completed_no_list_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(result, [])

    def test_completed_reads_all_list_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": True}

        # Create multiple list files
        (self.list_dir / "20240101.txt").write_text("http://a.com/1\tA\n", encoding="utf-8")
        (self.list_dir / "20240102.txt").write_text("http://b.com/2\tB\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 2)
        links = [r[0] for r in result]
        self.assertIn("http://a.com/1", links)
        self.assertIn("http://b.com/2", links)

    def test_completed_skips_hidden_files(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": True}

        (self.list_dir / ".hidden").write_text("should be skipped\n", encoding="utf-8")
        (self.list_dir / "20240101.txt").write_text("http://a.com/1\tA\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)

    def test_metadata_parsing(self) -> None:
        maker = self._make_maker()
        maker.collection_conf = {"is_completed": False}

        dt = Datetime.get_current_time()
        date_str = Datetime.get_short_date_str(dt)
        list_file = FeedMaker._get_list_file_path(self.list_dir, date_str)
        list_file.write_text("http://example.com/1\tTitle1\tmeta1\tmeta2\n", encoding="utf-8")

        result = maker._read_old_feed_list_from_file()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][2], ["meta1", "meta2"])


if __name__ == "__main__":
    unittest.main()
