#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import shutil
import logging.config
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import header_str, Env
from bin.feed_maker import FeedMaker
from bin.html_file_manager import HtmlFileManager
from bin.db import DB
from bin.models import HtmlFileInfo
import logging

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TestHtmlFileManager(unittest.TestCase):
    def setUp(self) -> None:
        # Mock DB config
        self.mock_db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }
        # Mock DB session
        self.mock_session = MagicMock()
        self.mock_query = MagicMock()
        self.mock_session.query.return_value = self.mock_query
        # Patch DB methods
        self.patcher_init = patch('bin.db.DB.init', return_value=None)
        self.patcher_create = patch('bin.db.DB.create_all_tables', return_value=None)
        self.patcher_drop = patch('bin.db.DB.drop_all_tables', return_value=None)
        self.patcher_session = patch('bin.db.DB.session_ctx')
        self.mock_session_ctx = self.patcher_session.start()
        self.mock_session_ctx.return_value.__enter__.return_value = self.mock_session
        self.mock_session_ctx.return_value.__exit__.return_value = None
        self.patcher_init.start()
        self.patcher_create.start()
        self.patcher_drop.start()
        DB.init(self.mock_db_config)
        DB.create_all_tables(self.mock_db_config)

        self.hfm = HtmlFileManager()
        self.test_feed_dir_path = self.hfm.work_dir_path / "my_test_group" / "my_test_feed4"
        self.test_feed_dir_path.mkdir(parents=True, exist_ok=True)
        self.test_feed_name = self.test_feed_dir_path.name
        self.test_rss_file_name = f"{self.test_feed_name}.xml"
        self.img_tag_str_len = FeedMaker.get_size_of_template_with_image_tag(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), self.test_rss_file_name)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_feed_dir_path.parent)
        del self.hfm
        DB.drop_all_tables(self.mock_db_config)
        self.patcher_init.stop()
        self.patcher_create.stop()
        self.patcher_drop.stop()
        self.patcher_session.stop()
        del self.mock_db_config

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

    def test_add_and_remove_html_file_info(self) -> None:
        html_file_path = self.test_feed_dir_path / "html" / "test.html"
        html_file_path.parent.mkdir(parents=True, exist_ok=True)
        html_file_path.write_text("test content")

        def all_side_effect(*args, **kwargs):
            all_side_effect.counter += 1
            if all_side_effect.counter == 1:
                # before add
                return [MagicMock()]
            elif all_side_effect.counter == 2:
                # after add
                return [MagicMock(), MagicMock()]
            else:
                # after remove
                return [MagicMock()]
        
        all_side_effect.counter = 0
        self.mock_query.all.side_effect = all_side_effect

        # Mock DB.session_ctx to always return the same mock session
        with patch('bin.db.DB.session_ctx') as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = self.mock_session
            mock_ctx.return_value.__exit__.return_value = None
            
            # Mock the session's query method to return our mock_query
            self.mock_session.query.return_value = self.mock_query
            
            # Mock the query's where method to return the same mock_query
            self.mock_query.where.return_value = self.mock_query

            with DB.session_ctx() as s:
                rows11 = s.query(HtmlFileInfo).where(HtmlFileInfo.feed_dir_path == str(self.test_feed_dir_path), 
                                                     HtmlFileInfo.file_path.is_not(None), 
                                                     HtmlFileInfo.update_date.is_not(None)).all()
                assert rows11 is not None

            # HtmlFileManager 인스턴스 메서드 호출로 변경
            self.hfm.add_html_file(self.test_feed_dir_path)

            with DB.session_ctx() as s:
                rows12 = s.query(HtmlFileInfo).where(HtmlFileInfo.feed_dir_path == str(self.test_feed_dir_path), 
                                                     HtmlFileInfo.file_path.is_not(None), 
                                                     HtmlFileInfo.update_date.is_not(None)).all()
                assert rows12 is not None
                self.assertEqual(len(rows11) + 1, len(rows12))

            self.hfm.remove_html_file_in_path_from_info("feed_dir_path", self.test_feed_dir_path)

            with DB.session_ctx() as s:
                rows13 = s.query(HtmlFileInfo).where(HtmlFileInfo.feed_dir_path == str(self.test_feed_dir_path), 
                                                     HtmlFileInfo.file_path.is_not(None), 
                                                     HtmlFileInfo.update_date.is_not(None)).all()
                assert rows13 is not None
                self.assertEqual(len(rows11), len(rows13))

    def test_load_all_html_files(self) -> None:
        # Mock query result for HTML files
        mock_row = MagicMock()
        mock_row.file_name = "test_feed"
        mock_row.file_path = "/path/to/test.html"
        mock_row.update_date = "2023-01-01"
        self.mock_query.first.return_value = mock_row

        # Mock DB.session_ctx to always return the same mock session
        with patch('bin.db.DB.session_ctx') as mock_ctx:
            mock_ctx.return_value.__enter__.return_value = self.mock_session
            mock_ctx.return_value.__exit__.return_value = None
            
            # Mock the session's query method to return our mock_query
            self.mock_session.query.return_value = self.mock_query
            
            # Mock the query's where method to return the same mock_query
            self.mock_query.where.return_value = self.mock_query

            self.hfm.load_all_html_files(max_num_feeds=20)

            with DB.session_ctx() as s:
                row = s.query(HtmlFileInfo).where(HtmlFileInfo.file_path.is_not(None)).first()
                assert row is not None
                self.assertIsNotNone(row.file_name)
                self.assertIsNotNone(row.file_path)
                self.assertIsNotNone(row.update_date)


if __name__ == "__main__":
    unittest.main()
