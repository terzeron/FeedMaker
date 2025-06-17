#!/usr/bin/env python
# -*- coding: utf-8 -*-


import shutil
import unittest
from unittest.mock import patch, Mock
import logging.config
from pathlib import Path
from bin.feed_maker_util import Env, FileManager


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def assert_in_mock_logger(message: str, mock_logger: Mock, do_submatch: bool = False) -> bool:
    for mock_call in mock_logger.call_args_list:
        formatted_message = mock_call.args[0] % mock_call.args[1:]
        if do_submatch:
            if message in formatted_message:
                return True
        else:
            if formatted_message == message:
                return True
    return False


class FileManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.group_name = "naver"
        self.feed_name = "certain_webtoon"
        self.feed_dir_path = Path(Env.get("FM_WORK_DIR")) / self.group_name / self.feed_name
        self.feed_dir_path.mkdir(exist_ok=True)
        self.sample_conf_file_path = Path(__file__).parent / "conf.naverwebtoon.json"
        self.conf_file_path = self.feed_dir_path / "conf.json"
        shutil.copy(self.sample_conf_file_path, self.conf_file_path)

        self.rss_file_path = self.feed_dir_path / f"{self.feed_name}.xml"
        self.rss_file_path.touch()
        self.old_rss_file_path = self.rss_file_path.with_suffix(self.rss_file_path.suffix + ".old")
        self.old_rss_file_path.touch()
        self.start_index_file_path = self.feed_dir_path / "start_idx.txt"
        self.start_index_file_path.touch()
        self.garbage_file_path = self.feed_dir_path / "nohup.out"
        self.garbage_file_path.touch()

        self.list_dir_path = self.feed_dir_path / "newlist"
        self.list_dir_path.mkdir(exist_ok=True)
        self.list_file_path = self.list_dir_path / "20211108.txt"
        self.list_file_path.touch()

        self.html_dir_path = self.feed_dir_path / "html"
        self.html_dir_path.mkdir(exist_ok=True)

        # empty html file
        self.html_file1_path = self.html_dir_path / "0abcdef.html"
        self.html_file1_path.touch()

        # html file without cached image
        self.html_file2_path = self.html_dir_path / "1234567.html"
        self.non_cached_img_file = "567890a.png"
        with open(self.html_file2_path, "w", encoding="utf-8") as outfile:
            outfile.write(f"<img src='{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/{self.feed_name}/{self.non_cached_img_file}'/>\n")

        self.feed_img_dir_path: Path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / self.feed_name
        self.feed_img_dir_path.mkdir(exist_ok=True)
        self.img_file1_path = self.feed_img_dir_path / "e7e0b83"
        self.img_file1_path.touch()
        self.img_file2_path = self.feed_img_dir_path / "e7e0b83.jpg"
        self.img_file2_path.touch()
        self.img_file3_path = self.feed_img_dir_path / "e7e0b83_part.jpg"
        self.img_file3_path.touch()
        self.img_file4_path = self.feed_img_dir_path / "e7e0b83_part.1.jpg"
        self.img_file4_path.touch()
        self.empty_img_file_path = self.feed_img_dir_path / "empty.png"
        self.empty_img_file_path.touch()

    def tearDown(self) -> None:
        self.garbage_file_path.unlink(missing_ok=True)

        self.html_file1_path.unlink(missing_ok=True)
        self.html_file2_path.unlink(missing_ok=True)
        shutil.rmtree(self.html_dir_path)

        self.empty_img_file_path.unlink(missing_ok=True)

    def test__get_cache_info_common_postfix(self) -> None:
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"
        actual = FileManager._get_cache_info_common_postfix(img_url)
        expected = "e7e0b83"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part")
        expected = "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part", index=0)
        expected = "e7e0b83_part"
        self.assertEqual(expected, actual)

        actual = FileManager._get_cache_info_common_postfix(img_url, postfix="part", index=1)
        expected = "e7e0b83_part.1"
        self.assertEqual(expected, actual)

    def test_get_cache_url(self) -> None:
        url_prefix = "%s/test" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"

        actual = FileManager.get_cache_url(url_prefix, img_url)
        expected = "%s/test/e7e0b83" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, suffix=".jpg")
        expected = "%s/test/e7e0b83.jpg" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part", suffix=".jpg")
        expected = "%s/test/e7e0b83_part.jpg" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part", index=0, suffix=".jpg")
        expected = "%s/test/e7e0b83_part.jpg" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_url(url_prefix, img_url, postfix="part", index=1, suffix=".jpg")
        expected = "%s/test/e7e0b83_part.1.jpg" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self.assertEqual(expected, actual)

    def test_get_cache_file_path(self) -> None:
        img_url = "https://image-comic.pstatic.net/webtoon/759457/50/20211007123156_e8e0d3210b1b5222a92a0d12de7068b3_IMAG01_1.jpg"
        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url)
        expected = self.feed_img_dir_path / "e7e0b83"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, suffix=".jpg")
        expected = self.feed_img_dir_path / "e7e0b83.jpg"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part", suffix=".jpg")
        expected = self.feed_img_dir_path / "e7e0b83_part.jpg"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part", index=0, suffix=".jpg")
        expected = self.feed_img_dir_path / "e7e0b83_part.jpg"
        self.assertEqual(expected, actual)

        actual = FileManager.get_cache_file_path(self.feed_img_dir_path, img_url, postfix="part", index=1, suffix=".jpg")
        expected = self.feed_img_dir_path / "e7e0b83_part.1.jpg"
        self.assertEqual(expected, actual)

    def test_get_incomplete_image(self) -> None:
        expected = ["567890a.png"]
        actual = FileManager.get_incomplete_image_list(self.html_file2_path)
        self.assertEqual(expected, actual)

    def test_remove_html_file_without_cached_image_files(self) -> None:
        self.assertTrue(self.html_file2_path.is_file())
        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_html_file_without_cached_image_files(self.html_file2_path)
            self.assertTrue(assert_in_mock_logger(f"* '{self.group_name}/{self.feed_name}/html/{self.html_file2_path.name}' deleted (due to ['{self.non_cached_img_file}'])", mock_info, do_submatch=True))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_html_files_without_cached_image_files(self) -> None:
        self.assertTrue(self.html_file2_path.is_file())
        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_html_files_without_cached_image_files(self.feed_dir_path, self.feed_img_dir_path)
            self.assertTrue(assert_in_mock_logger("# deleting html files without cached image files", mock_info))
            self.assertTrue(assert_in_mock_logger(f"* '{self.group_name}/{self.feed_name}/html/{self.html_file2_path.name}' deleted (due to ['{self.non_cached_img_file}'])", mock_info, do_submatch=True))

        self.assertFalse(self.html_file2_path.is_file())

    def test_remove_temporary_files(self) -> None:
        self.assertTrue(self.garbage_file_path.is_file())
        with patch.object(LOGGER, "info") as _:
            FileManager.remove_temporary_files(self.feed_dir_path)

        self.assertFalse(self.garbage_file_path.is_file())

    def test_remove_all_files(self) -> None:
        self.assertTrue(self.rss_file_path.is_file())
        self.assertTrue(self.start_index_file_path.is_file())
        self.assertTrue(self.garbage_file_path.is_file())
        self.assertTrue(self.list_file_path.is_file())
        self.assertTrue(self.html_file1_path.is_file())

        with patch.object(LOGGER, "info") as mock_info:
            FileManager.remove_all_files(self.feed_dir_path)

            self.assertTrue(assert_in_mock_logger("# deleting all files (html files, list files, rss file, various temporary files)", mock_info))
            self.assertTrue(assert_in_mock_logger("# deleting temporary files", mock_info))

        self.assertFalse(self.rss_file_path.is_file())
        self.assertFalse(self.start_index_file_path.is_file())
        self.assertFalse(self.garbage_file_path.is_file())
        self.assertFalse(self.list_file_path.is_file())
        self.assertFalse(self.html_file1_path.is_file())


if __name__ == "__main__":
    unittest.main()
