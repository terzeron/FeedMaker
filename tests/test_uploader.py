#!/usr/bin/env python
# -*- coding: utf-8 -*-


import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bin.uploader import Uploader


class UploaderTest(unittest.TestCase):
    fixtures_dir = Path(__file__).parent
    rss_fixture_1 = fixtures_dir / "sportsdonga.webtoon.1.result.xml"
    rss_fixture_2 = fixtures_dir / "sportsdonga.webtoon.2.result.xml"

    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.public_dir = self.temp_dir / "public"
        self.public_dir.mkdir()
        self.feed_dir = self.temp_dir / "feed"
        self.feed_dir.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def _make_rss(self, src_fixture: Path) -> Path:
        """fixture를 임시 피드 디렉토리에 복사하여 rss_file_path 반환"""
        dst = self.feed_dir / "test_feed.xml"
        shutil.copy(src_fixture, dst)
        return dst

    @patch("bin.uploader.Env.get")
    def test_first_upload(self, mock_env_get) -> None:
        """최초 업로드: .old 없음 → 업로드 성공"""
        mock_env_get.return_value = str(self.public_dir)
        rss = self._make_rss(self.rss_fixture_1)

        result = Uploader.upload(rss)

        self.assertEqual(result, 0)
        self.assertTrue((self.public_dir / rss.name).is_file())
        self.assertTrue(rss.with_suffix(".xml.old").is_file())

    @patch("bin.uploader.Env.get")
    def test_upload_skipped_when_unchanged_and_public_exists(self, mock_env_get) -> None:
        """내용 동일 + public 파일 존재 → 업로드 건너뜀"""
        mock_env_get.return_value = str(self.public_dir)
        rss = self._make_rss(self.rss_fixture_1)
        # .old 파일 생성 (동일 내용)
        shutil.copy(rss, rss.with_suffix(".xml.old"))
        # public 파일도 존재
        shutil.copy(rss, self.public_dir / rss.name)
        old_mtime = (self.public_dir / rss.name).stat().st_mtime

        result = Uploader.upload(rss)

        self.assertEqual(result, 0)
        # public 파일이 덮어쓰여지지 않았으므로 mtime 동일
        self.assertEqual((self.public_dir / rss.name).stat().st_mtime, old_mtime)

    @patch("bin.uploader.Env.get")
    def test_upload_forced_when_unchanged_but_public_missing(self, mock_env_get) -> None:
        """내용 동일하지만 public 파일 없음 → 업로드 수행"""
        mock_env_get.return_value = str(self.public_dir)
        rss = self._make_rss(self.rss_fixture_1)
        # .old 파일 생성 (동일 내용)
        shutil.copy(rss, rss.with_suffix(".xml.old"))
        # public 파일은 없음

        result = Uploader.upload(rss)

        self.assertEqual(result, 0)
        self.assertTrue((self.public_dir / rss.name).is_file())

    @patch("bin.uploader.Env.get")
    def test_upload_when_content_changed(self, mock_env_get) -> None:
        """내용 변경됨 → 업로드 수행"""
        mock_env_get.return_value = str(self.public_dir)
        rss = self._make_rss(self.rss_fixture_1)
        # .old 파일은 다른 내용
        shutil.copy(self.rss_fixture_2, rss.with_suffix(".xml.old"))

        result = Uploader.upload(rss)

        self.assertEqual(result, 0)
        self.assertTrue((self.public_dir / rss.name).is_file())

    @patch("bin.uploader.Env.get")
    def test_upload_fails_when_no_rss_file(self, mock_env_get) -> None:
        """RSS 파일 없음 → 실패"""
        mock_env_get.return_value = str(self.public_dir)
        rss = self.feed_dir / "nonexistent.xml"

        result = Uploader.upload(rss)

        self.assertEqual(result, -1)
        self.assertFalse((self.public_dir / rss.name).is_file())


if __name__ == "__main__":
    unittest.main()
