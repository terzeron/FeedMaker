#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from datetime import datetime, timedelta
from pathlib import Path
from bin.db_manager import DBManager
from bin.problem_manager import ProblemManager
from bin.feed_maker import FeedMaker
from bin.feed_maker_util import header_str, Config, Datetime

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestProblemManager(unittest.TestCase):
    def setUp(self) -> None:
        global_config = Config.get_global_config(Path(__file__).parent / "global_config_minimal.json")
        if not global_config:
            LOGGER.error("can't find global configuration")
            return
        db = DBManager(global_config["db_host"], global_config["db_port"], global_config["db_name"], global_config["db_user"], global_config["db_password"])
        self.pm = ProblemManager(db)
        with self.pm.db.get_connection_and_cursor() as (connection, cursor):
            self.pm.db.execute(cursor, "TRUNCATE feed_alias_name")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_config")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_title_group")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_list_url_count")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_rss_info")
            self.pm.db.execute(cursor, "TRUNCATE element_name_count")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_public_feed_info")
            self.pm.db.execute(cursor, "TRUNCATE html_file_size")
            self.pm.db.execute(cursor, "TRUNCATE html_file_with_many_image_tag")
            self.pm.db.execute(cursor, "TRUNCATE html_file_without_image_tag")
            self.pm.db.execute(cursor, "TRUNCATE html_file_image_not_found")
            self.pm.db.execute(cursor, "TRUNCATE feed_name_progress_info")
            self.pm.db.execute(cursor, "TRUNCATE feed_alias_access_info")
            self.pm.db.commit(connection)

        self.test_feed_dir_path = self.pm.work_dir / "my_test_group" / "my_test_feed"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)


    def tearDown(self) -> None:
        del self.pm
        shutil.rmtree(self.test_feed_dir_path.parent)

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
        actual = self.pm.get_html_file_name(self.test_feed_dir_path / "html" / "31d4598.html")
        self.assertEqual(expected, actual)

    def test_reload_htaccess_file(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()

        row = self.pm.db.query("SELECT * FROM feed_alias_name")
        self.assertGreater(len(row), 0)
        self.assertIsNotNone(row[0]["feed_alias"])
        self.assertIsNotNone(row[0]["feed_name"])
        self.assertGreater(len(self.pm.feed_alias_name_map), 0)
        self.assertGreater(len(self.pm.feed_name_aliases_map), 0)

    def test_get_feed_name_list_url_count_map(self):
        result = self.pm.get_feed_name_list_url_count_map()
        for _, list_url_count in result.items():
            self.assertIn("feed_name", list_url_count)
            self.assertIn("feed_title", list_url_count)
            self.assertIn("group_name", list_url_count)
            self.assertIn("count", list_url_count)

    def test_get_element_name_count_map(self):
        result = self.pm.get_element_name_count_map()
        for _, count in result.items():
            self.assertIn("element_name", count)
            self.assertIn("count", count)

    def test_add_and_remove_config_rss_file(self):
        conf_file_path = self.test_feed_dir_path / "conf.json"
        example_conf_file_path = Path(__file__).parent / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)
        rss_file_path = self.test_feed_dir_path / "my_test_feed.xml"
        example_rss_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        shutil.copy(example_rss_file_path, rss_file_path)

        row11 = self.pm.db.query("SELECT * FROM feed_name_config")
        row21 = self.pm.db.query("SELECT * FROM feed_name_title_group")
        row31 = self.pm.db.query("SELECT * FROM feed_name_list_url_count")
        row41 = self.pm.db.query("SELECT * FROM feed_name_rss_info")

        self.pm.add_config_rss_info(self.test_feed_dir_path)

        row12 = self.pm.db.query("SELECT * FROM feed_name_config")
        row22 = self.pm.db.query("SELECT * FROM feed_name_title_group")
        row32 = self.pm.db.query("SELECT * FROM feed_name_list_url_count")
        row42 = self.pm.db.query("SELECT * FROM feed_name_rss_info")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 1, len(row42))

        self.pm.remove_config_rss_info(self.test_feed_dir_path)

        row13 = self.pm.db.query("SELECT * FROM feed_name_config")
        row23 = self.pm.db.query("SELECT * FROM feed_name_title_group")
        row33 = self.pm.db.query("SELECT * FROM feed_name_list_url_count")
        row43 = self.pm.db.query("SELECT * FROM feed_name_rss_info")

        self.assertEqual(len(row11), len(row13))
        self.assertEqual(len(row21), len(row23))
        self.assertEqual(len(row31), len(row33))
        self.assertEqual(len(row41), len(row43))

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

    def test_get_feed_name_public_feed_info_map(self):
        result = self.pm.get_feed_name_public_feed_info_map()
        for _, public_feed_info in result.items():
            self.assertIn("feed_name", public_feed_info)
            self.assertIn("feed_title", public_feed_info)
            self.assertIn("group_name", public_feed_info)
            self.assertIn("file_path", public_feed_info)
            self.assertIn("upload_date", public_feed_info)
            self.assertIn("size", public_feed_info)
            self.assertIn("num_items", public_feed_info)

    def test_add_and_remove_public_feed_file(self):
        feed_file_path = Path(__file__).parent / "sportsdonga.webtoon.1.result.xml"
        self.pm.add_public_feed_info(feed_file_path)
        self.pm.remove_public_feed_info(feed_file_path)

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

    def test_get_html_file_size_map(self):
        result = self.pm.get_html_file_size_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("size", html_file_info)
            self.assertIn("update_date", html_file_info)

    def test_get_html_file_with_many_image_tag_map(self):
        result = self.pm.get_html_file_with_many_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_without_image_tag_map(self):
        result = self.pm.get_html_file_without_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_image_not_found_map(self):
        result = self.pm.get_html_file_image_not_found_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("group_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def _prepare_fixture_for_html_files(self, html_dir_path: Path):
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

    def test_add_and_remove_html_file_info_in_path_1(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row11 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row21 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row31 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row41 = self.pm.db.query("SELECT * FROM html_file_size")

        self.pm.add_html_info(self.test_feed_dir_path)

        row12 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row22 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row32 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row42 = self.pm.db.query("SELECT * FROM html_file_size")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 1, len(row42))

        self.pm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        row13 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row23 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row33 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row43 = self.pm.db.query("SELECT * FROM html_file_size")

        # all the records have been deleted by remove_html_file_in_path_from_info("feed_dir_path")
        self.assertEqual(0, len(row13))
        self.assertEqual(0, len(row23))
        self.assertEqual(0, len(row33))
        self.assertEqual(0, len(row43))

    def test_add_and_remove_html_file_info_in_path_2(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row11 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row21 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row31 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row41 = self.pm.db.query("SELECT * FROM html_file_size")

        self.pm.add_html_info(self.test_feed_dir_path)

        row12 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        row22 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        row32 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        row42 = self.pm.db.query("SELECT * FROM html_file_size")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 1, len(row42))

    def test_add_and_remove_html_file_info_in_path_3(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        self.assertEqual(0, len(row1))
        self.pm.add_html_info(self.test_feed_dir_path)
        row2 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        self.assertEqual(1, len(row2))
        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "8a9aa6d.html")
        row3 = self.pm.db.query("SELECT * FROM html_file_with_many_image_tag")
        self.assertEqual(0, len(row3))

    def test_add_and_remove_html_file_info_in_path_4(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.pm.add_html_info(self.test_feed_dir_path)
        row2 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.assertEqual(len(row1) + 1, len(row2))

        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "dc938b8.html")
        row3 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.assertEqual(len(row3), 0)
        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7d09d62.html")
        row4 = self.pm.db.query("SELECT * FROM html_file_without_image_tag")
        self.assertEqual(len(row4), 0)

    def test_add_and_remove_html_file_info_in_path_5(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertEqual(0, len(row1))
        self.pm.add_html_info(self.test_feed_dir_path)
        row2 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertEqual(1, len(row2))
        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7c9aa6d.html")
        row3 = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertEqual(0, len(row3))

    def test_add_and_remove_html_file_info_in_path_6(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        row46 = self.pm.db.query("SELECT * FROM html_file_size")
        self.assertEqual(0, len(row46))
        self.pm.add_html_info(self.test_feed_dir_path)
        row47 = self.pm.db.query("SELECT * FROM html_file_size")
        self.assertEqual(1, len(row47))
        self.pm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7d09d62.html")
        row48 = self.pm.db.query("SELECT * FROM html_file_size")
        self.assertEqual(0, len(row48))

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
            self.assertGreaterEqual(row[0]["count"], 0)

        row = self.pm.db.query("SELECT * FROM html_file_image_not_found")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertIsNotNone(row[0]["group_dir_path"])
            self.assertGreaterEqual(row[0]["count"], 0)

    def test_get_feed_name_progress_info_map(self):
        result = self.pm.get_feed_name_progress_info_map()
        for _, progress_info in result.items():
            self.assertIn("feed_name", progress_info)
            self.assertIn("feed_title", progress_info)
            self.assertIn("group_name", progress_info)
            self.assertIn("index", progress_info)
            self.assertIn("count", progress_info)
            self.assertIn("unit_size", progress_info)
            self.assertIn("ratio", progress_info)
            self.assertIn("due_date", progress_info)

    def test_add_and_remove_progress_from_info(self):
        example_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.completed.json"
        conf_file_path = self.test_feed_dir_path / "conf.json"
        shutil.copy(example_conf_file_path, conf_file_path)

        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()

        progress_file_path = self.test_feed_dir_path / "start_idx.txt"
        date_str = Datetime.get_current_time_str()
        with progress_file_path.open("w", encoding="utf-8") as f:
            f.write(f"157\t{date_str}\n")

        row1 = self.pm.db.query("SELECT * FROM feed_name_progress_info")
        self.pm.add_progress_info(self.test_feed_dir_path)
        row2 = self.pm.db.query("SELECT * FROM feed_name_progress_info")
        self.assertEqual(len(row1) + 1, len(row2))
        self.pm.remove_progress_info(self.test_feed_dir_path)
        row3 = self.pm.db.query("SELECT * FROM feed_name_progress_info")
        self.assertEqual(len(row1), len(row3))

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

    def test_add_httpd_access_file_to_info_after_last_log(self):
        self.pm.load_htaccess_file()
        self.pm.load_all_config_rss_files()
        self.pm.load_all_httpd_access_files()
        group_name = "naver"
        feed_name = "navercast"
        test_feed_dir_path = Path(__file__).parent.parent / group_name / feed_name
        feed_alias = feed_name

        # get date from recent log file
        today = datetime.today()
        recent_log_file_date_str = ""
        for i in range(31):
            specific_date = today - timedelta(days=i)
            date_str = specific_date.strftime("%y%m%d")
            access_file_path = self.pm.httpd_access_log_dir / f"access.log.{date_str}"
            if access_file_path.is_file():
                recent_log_file_date_str = date_str
                break

        self.pm.add_httpd_access_info(test_feed_dir_path)
        rows = self.pm.db.query("SELECT * FROM feed_alias_access_info WHERE feed_alias = %s", feed_alias)
        self.assertIsNotNone(rows)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["access_date"].strftime("%y%m%d"), recent_log_file_date_str)

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
            self.assertGreaterEqual(row[0]["is_in_xml_dir"], 0)

    def test_get_feed_alias_status_info_map(self):
        result = self.pm.get_feed_alias_status_info_map()
        for _, status_info in result.items():
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

    def test_update_feed_info(self):
        pass

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
