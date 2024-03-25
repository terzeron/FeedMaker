#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import shutil
import logging.config
from pathlib import Path
from bin.feed_maker_util import header_str
from bin.feed_maker import FeedMaker
from bin.html_file_manager import HtmlFileManager
from bin.db_manager import DBManager

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestHtmlFileManager(unittest.TestCase):
    def setUp(self) -> None:
        db = DBManager(os.environ["FM_DB_HOST"], int(os.environ["FM_DB_PORT"]), os.environ["MYSQL_DATABASE"], os.environ["MYSQL_USER"], os.environ["MYSQL_PASSWORD"])
        self.hfm = HtmlFileManager(db)

        self.test_feed_dir_path = self.hfm.work_dir / "my_test_group" / "my_test_feed4"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)

        with self.hfm.db.get_connection_and_cursor() as (connection, cursor):
            self.hfm.db.execute(cursor, "DELETE FROM html_file_info WHERE file_path LIKE 'my_test_group/my_test_feed%/%'")
            self.hfm.db.commit(connection)

    def tearDown(self) -> None:
        with self.hfm.db.get_connection_and_cursor() as (connection, cursor):
            self.hfm.db.execute(cursor, "DELETE FROM html_file_info WHERE file_path LIKE 'my_test_group/my_test_feed%/%'")
            self.hfm.db.commit(connection)

        del self.hfm
        shutil.rmtree(self.test_feed_dir_path.parent)

    def test_get_html_file_name(self):
        expected = "my_test_feed4/html/31d4598.html"
        actual = self.hfm.get_html_file_name(self.test_feed_dir_path / "html" / "31d4598.html")
        self.assertEqual(expected, actual)

    def test_get_html_file_size_map(self):
        result = self.hfm.get_html_file_size_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("size", html_file_info)
            self.assertIn("update_date", html_file_info)

    def test_get_html_file_with_many_image_tag_map(self):
        result = self.hfm.get_html_file_with_many_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_without_image_tag_map(self):
        result = self.hfm.get_html_file_without_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_image_not_found_map(self):
        result = self.hfm.get_html_file_image_not_found_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    @staticmethod
    def _prepare_fixture_for_html_files(html_dir_path: Path):
        # small html file: fc68456.html
        small_html_path = html_dir_path / "fc68456.html"
        with small_html_path.open("w", encoding="utf-8") as f:
            f.write("<div><p>hello</p></div>" * 2)
            f.write(FeedMaker.get_image_tag_str("https://terzeron.com", "my_test_feed4.xml", "https://torrentsee154.com/topic/264735"))

        # big html file: 5d55cb3.html
        big_html_path = html_dir_path / "5d55cb3.html"
        with big_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write("<div><p>hello</p></div>" * 1000)
            f.write(FeedMaker.get_image_tag_str("https://terzeron.com", "my_test_feed4.xml", "https://torrentsee154.com/topic/264741"))

        # html file with many image tags: 8a9aa6d.html
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

        # html file without image tag: dc938b8.html
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

        # html file with image-not-found.png: 7c9aa6d.html
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
        print(html_dir_path)
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row11 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        row21 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        row31 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        row41 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")

        self.hfm.add_html_file(self.test_feed_dir_path)

        row12 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        row22 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        row32 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        row42 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 1, len(row42))

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        row13 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        row23 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        row33 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        row43 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")

        # all the records have been deleted by remove_html_file_in_path_from_info("feed_dir_path")
        self.assertEqual(len(row12) - 1, len(row13))
        self.assertEqual(len(row22) - 1, len(row23))
        self.assertEqual(len(row32) - 1, len(row33))
        self.assertEqual(len(row42) - 1, len(row43))

    def test_add_and_remove_html_file_info_in_path_2(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row11 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        row21 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        row31 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        row41 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")

        self.hfm.add_html_file(self.test_feed_dir_path)

        row12 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        row22 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        row32 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        row42 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")

        self.assertEqual(len(row11) + 1, len(row12))
        self.assertEqual(len(row21) + 1, len(row22))
        self.assertEqual(len(row31) + 1, len(row32))
        self.assertEqual(len(row41) + 1, len(row42))

    def test_add_and_remove_html_file_info_in_path_3(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        self.assertEqual(0, len(row1))

        self.hfm.add_html_file(self.test_feed_dir_path)
        row2 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        self.assertEqual(1, len(row2))

        self.hfm.remove_html_file_in_path_from_info("file_path", html_dir_path / "8a9aa6d.html")
        row3 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        self.assertEqual(0, len(row3))

    def test_add_and_remove_html_file_info_in_path_4(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")

        self.hfm.add_html_file(self.test_feed_dir_path)
        row2 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        self.assertEqual(len(row1) + 1, len(row2))

        self.hfm.remove_html_file_in_path_from_info("file_path", html_dir_path / "dc938b8.html")
        row3 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        self.assertEqual(len(row3), 0)

        self.hfm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7c9aa6d.html")
        row4 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        self.assertEqual(len(row4), 0)

    def test_add_and_remove_html_file_info_in_path_5(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row1 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")

        self.hfm.add_html_file(self.test_feed_dir_path)

        row2 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        self.assertEqual(len(row1) + 1, len(row2))

        self.hfm.remove_html_file_in_path_from_info("file_path", html_dir_path / "7c9aa6d.html")

        row3 = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        self.assertEqual(len(row2) - 1, len(row3))

    def test_add_and_remove_html_file_info_in_path_6(self):
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        TestHtmlFileManager._prepare_fixture_for_html_files(html_dir_path)

        row46 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")
        self.assertEqual(0, len(row46))

        self.hfm.add_html_file(self.test_feed_dir_path)
        row47 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")
        self.assertEqual(1, len(row47))

        self.hfm.remove_html_file_in_path_from_info("file_path", html_dir_path / "fc68456.html")
        row48 = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")
        self.assertEqual(0, len(row48))

    def test_load_all_html_files(self):
        self.hfm.load_all_html_files(max_num_feeds=20)

        row = self.hfm.db.query("SELECT * FROM html_file_info WHERE size > 124 AND size < 434")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertGreater(row[0]["size"], 0)
            self.assertIsNotNone(row[0]["update_date"])

        row = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_many_image_tag > 0")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertGreater(row[0]["count_with_many_image_tag"], 0)

        row = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_without_image_tag > 0")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertGreaterEqual(row[0]["count_without_image_tag"], 0)

        row = self.hfm.db.query("SELECT * FROM html_file_info WHERE count_with_image_not_found > 0")
        self.assertGreaterEqual(len(row), 0)
        if len(row) > 0:
            self.assertIsNotNone(row[0]["file_name"])
            self.assertIsNotNone(row[0]["file_path"])
            self.assertIsNotNone(row[0]["feed_dir_path"])
            self.assertGreaterEqual(row[0]["count_with_image_not_found"], 0)


if __name__ == "__main__":
    unittest.main()
