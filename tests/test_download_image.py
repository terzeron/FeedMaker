#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import unittest
from unittest.mock import patch, Mock

from bin.feed_maker_util import Env
import utils.download_image



class TestDownloadImage(unittest.TestCase):
    def setUp(self) -> None:
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=711422&no=1"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_image.py", "-f", work_dir, page_url]

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_single_quote(self, mock_download) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg'>"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_double_quote(self, mock_download) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = '<img src="https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg">'
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_space(self, mock_download) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' >"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_trailing_slash(self, mock_download) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' />"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_width_attribute(self, mock_download) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' width='100%'/>"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)


if __name__ == "__main__":
    unittest.main()
