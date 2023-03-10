#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from problem_manager import ProblemManager
from feed_maker import FeedMaker
from feed_maker_util import header_str


class TestProblemManager(unittest.TestCase):
    def setUp(self) -> None:
        self.pm = ProblemManager()
        self.pm.db.execute("TRUNCATE feed_alias_name")
        self.pm.db.execute("TRUNCATE feed_name_config")
        self.pm.db.execute("TRUNCATE feed_name_title_group")
        self.pm.db.execute("TRUNCATE feed_name_list_url_count")
        self.pm.db.execute("TRUNCATE feed_name_rss_info")
        self.pm.db.execute("TRUNCATE element_name_count")
        self.pm.db.execute("TRUNCATE feed_name_public_feed_info")
        self.pm.db.execute("TRUNCATE html_file_size")
        self.pm.db.execute("TRUNCATE html_file_with_many_image_tag")
        self.pm.db.execute("TRUNCATE html_file_without_image_tag")
        self.pm.db.execute("TRUNCATE html_file_image_not_found")
        self.pm.db.execute("TRUNCATE feed_name_progress_info")
        self.pm.db.execute("TRUNCATE feed_alias_access_info")

    def tearDown(self) -> None:
        del self.pm

    def _first_item(self, d: Dict[str, Any]):
        first_key = list(d.keys())[0]
        return d[first_key]

    def test_convert_path_to_str(self):
        self.assertEqual(self.pm.convert_path_to_str(ProblemManager.work_dir), ".")
        self.assertEqual(self.pm.convert_path_to_str(ProblemManager.public_feed_dir), ".")
        self.assertEqual(self.pm.convert_path_to_str(ProblemManager.httpd_access_log_dir), os.environ["HOME"] + "/apps/logs")
        self.assertEqual(self.pm.convert_path_to_str(ProblemManager.htaccess_file), "../.htaccess")

    def test_convert_datetime_to_str(self):
        d = "2022-01-01"
        self.assertEqual("2022-01-01", self.pm.convert_datetime_to_str(d))

        d = "2022-12-30 12:12:12"
        self.assertEqual("2022-12-30 12:12:12", self.pm.convert_datetime_to_str(d))

        d = "2018-01-31"
        self.assertEqual("2018-01-31", self.pm.convert_datetime_to_str(d))

        d = "01-31"
        self.assertEqual("01-31", self.pm.convert_datetime_to_str(d))

        dt = datetime.strptime("2018-01-13", "%Y-%m-%d")
        self.assertEqual("18-01-13", self.pm.convert_datetime_to_str(dt))

        dt = datetime.strptime("2018-01-31 17:04:11", "%Y-%m-%d %H:%M:%S")
        self.assertEqual("18-01-31", self.pm.convert_datetime_to_str(dt))

    def test_get_html_file_name(self):
        expected = "my_test_feed/html/31d4598.html"
        actual = self.pm.get_html_file_name(Path("/Users/terzeron/workspace/fma/my_test_group/my_test_feed/html/31d4598.html"))
        self.assertEqual(expected, actual)

    def test_add_and_remove_html_file_info_in_path(self):
        html_dir_path = self.pm.work_dir / "my_test_group" / "my_test_feed" / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        small_html_path = html_dir_path / "7d09d62.html"
        with small_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)

        minimal_html_path = html_dir_path / "fc68456.html"
        with minimal_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write(FeedMaker.get_image_tag_str("https://terzeron.com", "my_test_feed.xml", "https://torrentsee154.com/topic/264735"))

        big_html_path = html_dir_path / "5d55cb3.html"
        with big_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write(FeedMaker.get_image_tag_str("https://terzeron.com", "my_test_feed.xml", "https://torrentsee154.com/topic/264741"))

        many_image_tag_html_path = html_dir_path / "8a9aa6d.html"
        with many_image_tag_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write('''
<div>
<a href='https://torrentmode28.com/ani/2340'><i></i><span>이전</span></a>
<a href='https://torrentmode28.com/ani/2338'><i></i><span>다음</span></a>
<a href='https://torrentmode28.com/ani'><i></i><span>목록</span></a>
</div>
<img src='https://terzeron.com/img/1x1.jpg?feed=torrentmode.xml&item=8a9aa6d'/>
<img src='https://terzeron.com/img/1x1.jpg?feed=torrentmode.xml&item=8a9aa6d'/>
            ''')

        no_image_tag_html_path = html_dir_path / "dc938b8.html"
        with no_image_tag_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write('''
<p>찐:종합게임동아리</p>
<p>트라우마로 인해 일부러 게임을 피하며 살아온 '김 진'.
진이는 신입생 환영회에서 만난 '정진아'의 제안으로 우연히 동아리에 들어가게 되는데...
알고 보니 동아리의 정체는 전력을 다해 게임을 즐기는 종합게임동아리였다!
게임에 항상 진심인 승부욕 강한 여섯 청춘들의 즐거운 동아리 활동!!</p>
<p><img src='https://image-comic.pstatic.net/webtoon/771018/thumbnail/thumbnail_IMAG21_3762818380117075513.jpg'></p>
            ''')

        image_not_found_html_path = html_dir_path / "7c9aa6d.html"
        with image_not_found_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write('''
<img src='https://terzeron.com/image-not-found.png' alt='not exist or size 0'/>
<img src='https://terzeron.com/image-not-found.png' alt='not exist or size 0'/>
<img src='https://terzeron.com/image-not-found.png' alt='not exist or size 0'/>
<img src='https://terzeron.com/img/1x1.jpg?feed=torrentmode.xml&item=7c9aa6d'/>
            ''')

        row11 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row21 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row31 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row41 = self.pm.db.query("SELECT * FROM html_file_size")

        self.pm.add_html_files_in_path_to_info(html_dir_path.parent)

        row12 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row22 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row32 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row42 = self.pm.db.query("SELECT * FROM html_file_size")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 2, len(row42))

        self.pm.remove_html_file_in_path_from_info("feed_dir_path", html_dir_path.parent)

        row13 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row23 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row33 = self.pm.db.query("SELECT * FROM html_file_image_not_found")

        self.assertEqual(len(row12), len(row13) + 1)
        self.assertEqual(len(row22), len(row23) + 1)
        self.assertEqual(len(row32), len(row33) + 1)

        self.pm.add_html_files_in_path_to_info(html_dir_path.parent)
        self.pm.remove_html_file_in_path_from_info("group_dir_path", html_dir_path.parent.parent)

        row14 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row24 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row34 = self.pm.db.query("SELECT * FROM html_file_image_not_found")

        self.assertEqual(len(row13), len(row14))
        self.assertEqual(len(row23), len(row24))
        self.assertEqual(len(row33), len(row34))

        self.pm.add_html_files_in_path_to_info(html_dir_path.parent)
        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "8a9aa6d.html")
        row15 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        self.assertEqual(len(row14), len(row15))

        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "dc938b8.html")
        row25 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.assertEqual(len(row24), len(row25))

        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7c9aa6d.html")
        row35 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertEqual(len(row34), len(row35))

    def test_get_feed_alias_status_info_map(self):
        result = self.pm.get_feed_alias_status_info_map()
        for feed_alias, status_info in result.items():
            self.assertIn("feed_alias", status_info)
            self.assertIn("feed_name", status_info)
            self.assertIn("feed_title", status_info)
            self.assertIn("group_name", status_info)
            self.assertIn("htaccess", status_info)
            self.assertIn("http_request", status_info)
            self.assertIn("public_html", status_info)
            self.assertIn("feedmaker", status_info)
            self.assertIn("access_date", status_info)
            self.assertIn("view_date", status_info)
            self.assertIn("upload_date", status_info)
            self.assertIn("update_date", status_info)
            self.assertIn("access_date", status_info)
            self.assertIn("file_path", status_info)

    def test_get_feed_name_progress_info_map(self):
        result = self.pm.get_feed_name_progress_info_map()
        for feed_name, progress_info in result.items():
            self.assertIn("feed_name", progress_info)
            self.assertIn("feed_title", progress_info)
            self.assertIn("group_name", progress_info)
            self.assertIn("index", progress_info)
            self.assertIn("count", progress_info)
            self.assertIn("unit_size", progress_info)
            self.assertIn("ratio", progress_info)
            self.assertIn("due_date", progress_info)

    def test_get_feed_name_public_feed_info_map(self):
        result = self.pm.get_feed_name_public_feed_info_map()
        for feed_name, public_feed_info in result.items():
            self.assertIn("feed_name", public_feed_info)
            self.assertIn("feed_title", public_feed_info)
            self.assertIn("group_name", public_feed_info)
            self.assertIn("file_path", public_feed_info)
            self.assertIn("upload_date", public_feed_info)
            self.assertIn("size", public_feed_info)
            self.assertIn("num_items", public_feed_info)

    def test_get_html_file_size_map(self):
        result = self.pm.get_html_file_size_map()
        for html_file, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("size", html_file_info)
            self.assertIn("update_date", html_file_info)

    def test_get_html_file_with_many_image_tag_map(self):
        result = self.pm.get_html_file_with_many_image_tag_map()
        for html_file, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_without_image_tag_map(self):
        result = self.pm.get_html_file_without_image_tag_map()
        for html_file, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_image_not_found_map(self):
        result = self.pm.get_html_file_image_not_found_map()
        for html_file, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_feed_name_list_url_count_map(self):
        result = self.pm.get_feed_name_list_url_count_map()
        for feed_name, list_url_count in result.items():
            self.assertIn("feed_name", list_url_count)
            self.assertIn("feed_title", list_url_count)
            self.assertIn("group_name", list_url_count)
            self.assertIn("count", list_url_count)

    def test_get_element_name_count_map(self):
        result = self.pm.get_element_name_count_map()
        for element_name, count in result.items():
            self.assertIn("element_name", count)
            self.assertIn("count", count)

    def test_load_htaccess_file(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()

        row = self.pm.db.query("SELECT * FROM feed_alias_name")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_alias"])
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertGreater(len(self.pm.feed_alias_name_map), 0)
        self.assertGreater(len(self.pm.feed_name_aliases_map), 0)

    def test_load_all_config_rss_files(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()

        row = self.pm.db.query("SELECT * FROM feed_name_config")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["config"])
        self.assertGreater(len(self.pm.feed_name_config_map), 0)

        row = self.pm.db.query("SELECT * FROM feed_name_title_group")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["feed_title"])
        self.assertIsNotNone(row[0]["group_name"])
        self.assertGreater(len(self.pm.feed_name_title_map), 0)

        row = self.pm.db.query("SELECT * FROM feed_name_list_url_count")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["feed_title"])
        self.assertIsNotNone(row[0]["group_name"])
        self.assertGreater(row[0]["count"], 0)

        row = self.pm.db.query("SELECT * FROM feed_name_rss_info")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["update_date"])

        row = self.pm.db.query("SELECT * FROM element_name_count")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["element_name"])
        self.assertGreater(row[0]["count"], 0)

    def test_load_all_public_feed_files(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()
        self.pm.load_all_public_feed_files()

        row = self.pm.db.query("SELECT * FROM feed_name_public_feed_info")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertIsNotNone(row[0]["feed_title"])
        self.assertIsNotNone(row[0]["group_name"])
        self.assertIsNotNone(row[0]["file_path"])
        self.assertIsNotNone(row[0]["upload_date"])
        self.assertGreater(row[0]["file_size"], 0)
        self.assertGreater(row[0]["num_items"], 0)

    def test_load_all_html_files(self):
        self.pm.load_all_html_files()

        row = self.pm.db.query("SELECT * FROM html_file_size")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertIsNotNone(row[0]["group_dir_path"])
            self.assertGreater(row[0]["size"], 0)
            self.assertIsNotNone(row[0]["update_date"])

        row = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertIsNotNone(row[0]["group_dir_path"])
            self.assertGreater(row[0]["count"], 0)

        row = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertIsNotNone(row[0]["group_dir_path"])
            self.assertGreater(row[0]["count"], 0)

        row = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertIsNotNone(row[0]["group_dir_path"])
            self.assertGreater(row[0]["count"], 0)

    def test_load_all_progress_info_from_files(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()
        self.pm.load_all_progress_info_from_files()

        row = self.pm.db.query("SELECT * FROM feed_name_progress_info")
        self.assertGreater(len(row[0]), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["feed_name"])
            self.assertIsNotNone(row[0]["feed_title"])
            self.assertIsNotNone(row[0]["group_name"])
            self.assertGreaterEqual(row[0]["idx"], 0)
            self.assertGreaterEqual(row[0]["count"], 0)
            self.assertGreaterEqual(row[0]["unit_size"], 0.0)
            self.assertGreaterEqual(row[0]["progress_ratio"], 0.0)
            self.assertIsNotNone(row[0]["due_date"])

    def test_load_all_httpd_access_files(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()
        self.pm.load_all_httpd_access_files()

        row = self.pm.db.query("SELECT * FROM feed_alias_access_info")
        self.assertGreater(len(row[0]), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["feed_alias"])
            self.assertIsNotNone(row[0]["feed_name"])
            self.assertIsNotNone(row[0]["access_date"])
            self.assertGreaterEqual(row[0]["access_status"], 0)
            self.assertIsNotNone(row[0]["view_date"])
            self.assertGreaterEqual(row[0]["view_status"], 0)
            self.assertGreaterEqual(row[0]["is_in_xml_dir"], 0)

    def test_load_all(self):
        self.pm.load_all()

        row = self.pm.db.query("SELECT * FROM feed_alias_status_info")
        self.assertGreaterEqual(len(row[0]), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["feed_alias"])
            self.assertIsNotNone(row[0]["feed_name"])
            self.assertIsNotNone(row[0]["feed_title"])
            self.assertIsNotNone(row[0]["group_name"])
            self.assertGreaterEqual(row[0]["htaccess"], 0)
            self.assertGreaterEqual(row[0]["http_request"], 0)
            self.assertGreaterEqual(row[0]["public_html"], 0)
            self.assertGreaterEqual(row[0]["feedmaker"], 0)

        row = self.pm.db.query("SELECT * FROM feed_alias_status_info WHERE NOT ( http_request IS NULL AND htaccess IS NULL AND public_html IS NULL AND feedmaker IS NULL ) AND NOT ( http_request IS NOT NULL AND htaccess IS NULL AND public_html IS NULL AND feedmaker IS NULL AND access_date IS NOT NULL AND DATEDIFF(access_date, current_date) > %s ) AND NOT ( http_request IS NOT NULL AND htaccess IS NOT NULL AND public_html IS NOT NULL AND feedmaker IS NOT NULL AND ( access_date IS NOT NULL AND DATEDIFF(current_date, access_date) < %s OR view_date IS NOT NULL AND DATEDIFF(current_date, view_date) < %s ) )", ProblemManager.num_days, ProblemManager.num_days, ProblemManager.num_days)
        self.assertGreaterEqual(len(row), 0)


if __name__ == "__main__":
    unittest.main()
