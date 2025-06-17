#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from pathlib import Path

from test.test_common import TestCommon
from bin.feed_maker_util import header_str, Env
from bin.feed_maker import FeedMaker
from bin.html_file_manager import HtmlFileManager
from bin.db import DB
from bin.models import HtmlFileInfo


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestHtmlFileManager(unittest.TestCase):
    mysql_container = None

    @classmethod
    def setUpClass(cls) -> None:
        cls.mysql_container = TestCommon.prepare_mysql_container()
        DB.init(TestCommon.get_db_config(cls.mysql_container))

    @classmethod
    def tearDownClass(cls) -> None:
        TestCommon.dispose_mysql_container(cls.mysql_container)

    def setUp(self) -> None:
        self.db_config = TestCommon.get_db_config(self.__class__.mysql_container)
        DB.create_all_tables(self.db_config)

        self.hfm = HtmlFileManager()

        self.test_feed_dir_path = self.hfm.work_dir_path / "my_test_group" / "my_test_feed4"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)
        self.test_feed_name = self.test_feed_dir_path.name
        self.test_rss_file_name = f"{self.test_feed_name}.xml"
        self.img_tag_str_len = FeedMaker.get_size_of_template_with_image_tag(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)

        del self.hfm

        DB.drop_all_tables(self.db_config)
        del self.db_config

    def test_get_html_file_name(self) -> None:
        expected = "my_test_feed4/html/31d4598.html"
        actual = self.hfm.get_html_file_name(self.test_feed_dir_path / "html" / "31d4598.html")
        self.assertEqual(expected, actual)

    def test_get_html_file_size_map(self) -> None:
        result = self.hfm.get_html_file_size_map(self.test_feed_name)
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("size", html_file_info)
            self.assertIn("update_date", html_file_info)

    def test_get_html_file_with_many_image_tag_map(self) -> None:
        result = self.hfm.get_html_file_with_many_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_without_image_tag_map(self) -> None:
        result = self.hfm.get_html_file_without_image_tag_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def test_get_html_file_image_not_found_map(self) -> None:
        result = self.hfm.get_html_file_image_not_found_map()
        for _, html_file_info in result.items():
            self.assertIn("file_name", html_file_info)
            self.assertIn("file_path", html_file_info)
            self.assertIn("feed_dir_path", html_file_info)
            self.assertIn("count", html_file_info)

    def _prepare_fixture_for_html_files(self, html_dir_path: Path) -> None:
        # small html file: fc68456.html
        small_file = "fc68456.html"
        small_html_path = html_dir_path / small_file
        with small_html_path.open("w", encoding="utf-8") as f:
            f.write("<div><p>hello</p></div>" * 2)
            f.write(FeedMaker.get_image_tag_str(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name, "https://torrentsee154.com/topic/264735"))

        # html file with many image tags: 8a9aa6d.html
        with_many_tags_file = "8a9aa6d.html"
        many_image_tag_html_path = html_dir_path / with_many_tags_file
        with many_image_tag_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write('''
<div>
<a href='https://torrentmode28.com/ani/2340'><i></i><span>이전</span></a>
<a href='https://torrentmode28.com/ani/2338'><i></i><span>다음</span></a>
<a href='https://torrentmode28.com/ani'><i></i><span>목록</span></a>
</div>
            ''')
            f.write(FeedMaker.get_image_tag_str(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name, "https://torrentsee154.com/topic/264741") + "\n")
            f.write(FeedMaker.get_image_tag_str(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name, "https://torrentsee154.com/topic/264741") + "\n")
            f.write(FeedMaker.get_image_tag_str(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name, "https://torrentsee154.com/topic/264741") + "\n")


        # html file without image tag: dc938b8.html
        without_tags_file = "dc938b8.html"
        no_image_tag_html_path = html_dir_path / without_tags_file
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
        with_not_found_file = "7c9aa6d.html"
        image_not_found_html_path = html_dir_path / with_not_found_file

        with image_not_found_html_path.open("w", encoding="utf-8") as f:
            f.write(header_str)
            f.write('''
<img src='%s/image-not-found.png' alt='not exist or size 0'/>
<img src='%s/image-not-found.png' alt='not exist or size 0'/>
<img src='%s/image-not-found.png' alt='not exist or size 0'/>
            ''' % (Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")))
            f.write(FeedMaker.get_image_tag_str(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name, "https://torrentsee154.com/topic/264741"))

    def test_add_and_remove_html_file_info_in_path_with_small_size(self) -> None:
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        with DB.session_ctx() as s:
            rows1 = s.query(HtmlFileInfo).where(HtmlFileInfo.size < self.img_tag_str_len).all()
            assert rows1 is not None

        self.hfm.add_html_file(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows2 = s.query(HtmlFileInfo).where(HtmlFileInfo.size < self.img_tag_str_len).all()
            assert rows2 is not None
            self.assertEqual(len(rows1) + 1, len(rows2))

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows3 = s.query(HtmlFileInfo).where(HtmlFileInfo.size < self.img_tag_str_len).all()
            assert rows3 is not None
            self.assertEqual(len(rows2) - 1, len(rows3))

    def test_add_and_remove_html_file_info_in_path_with_many_tags(self) -> None:
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        with DB.session_ctx() as s:
            rows1 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_many_image_tag > 0).all()
            assert rows1 is not None

        self.hfm.add_html_file(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows2 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_many_image_tag > 0).all()
            assert rows2 is not None
            self.assertEqual(len(rows1) + 1, len(rows2))

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows3 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_many_image_tag > 0).all()
            assert rows3 is not None
            self.assertEqual(len(rows2) - 1, len(rows3))

    def test_add_and_remove_html_file_info_in_path_without_tags(self) -> None:
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        with DB.session_ctx() as s:
            rows1 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_without_image_tag > 0).all()
            assert rows1 is not None

        self.hfm.add_html_file(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows2 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_without_image_tag > 0).all()
            assert rows2 is not None
            self.assertEqual(len(rows1) + 1, len(rows2))

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows3 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_without_image_tag > 0).all()
            assert rows3 is not None
            self.assertEqual(len(rows2) - 1, len(rows3))

    def test_add_and_remove_html_file_info_in_path_with_not_found(self) -> None:
        html_dir_path = self.test_feed_dir_path / "html"
        html_dir_path.mkdir(parents=True, exist_ok=True)

        self._prepare_fixture_for_html_files(html_dir_path)

        with DB.session_ctx() as s:
            rows1 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_image_not_found > 0).all()
            assert rows1 is not None

        self.hfm.add_html_file(self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows2 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_image_not_found > 0).all()
            assert rows2 is not None
            self.assertEqual(len(rows1) + 1, len(rows2))

        self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

        with DB.session_ctx() as s:
            rows3 = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_image_not_found > 0).all()
            assert rows3 is not None
            self.assertEqual(len(rows2) - 1, len(rows3))

    def test_load_all_html_files(self) -> None:
        self.hfm.load_all_html_files(max_num_feeds=20)

        with DB.session_ctx() as s:
            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.size < self.img_tag_str_len).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 0)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.file_name)
                self.assertIsNotNone(row.file_path)
                self.assertIsNotNone(row.feed_dir_path)
                self.assertIsNotNone(row.update_date)

            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_many_image_tag > 0).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 0)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.file_name)
                self.assertIsNotNone(row.file_path)
                self.assertIsNotNone(row.feed_dir_path)
                self.assertGreater(row.count_with_many_image_tag, 0)

            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_without_image_tag > 0).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 0)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.file_name)
                self.assertIsNotNone(row.file_path)
                self.assertIsNotNone(row.feed_dir_path)
                self.assertGreaterEqual(row.count_without_image_tag, 0)

            rows = s.query(HtmlFileInfo).where(HtmlFileInfo.count_with_image_not_found > 0).all()
            assert rows is not None
            self.assertGreaterEqual(len(rows), 0)
            for row in rows:
                assert row is not None
                self.assertIsNotNone(row.file_name)
                self.assertIsNotNone(row.file_path)
                self.assertIsNotNone(row.feed_dir_path)
                self.assertGreaterEqual(row.count_with_image_not_found, 0)


if __name__ == "__main__":
    unittest.main()
