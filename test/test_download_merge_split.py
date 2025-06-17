#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import unittest
from unittest.mock import patch
from bin.feed_maker_util import Env
import utils.download_image


class TestDownloadImage(unittest.TestCase):
    def setUp(self):
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=711422&no=1"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_image.py", "-f", work_dir, page_url]

    def test_download_image_with_single_quote(self):
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg'>"
        expected_output = "<img src='https://terzeron.com/xml/img/one_second/753d4f8.jpeg'/>\n"

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    def test_download_image_with_double_quote(self):
        test_input = '<img src="https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg">'
        expected_output = "<img src='https://terzeron.com/xml/img/one_second/753d4f8.jpeg'/>\n"

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    def test_download_image_with_space(self):
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' >"
        expected_output = "<img src='https://terzeron.com/xml/img/one_second/753d4f8.jpeg'/>\n"

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    def test_download_image_with_trailing_slash(self):
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' />"
        expected_output = "<img src='https://terzeron.com/xml/img/one_second/753d4f8.jpeg'/>\n"

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    def test_download_image_with_width_attribute(self):
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' width='100%'/>"
        expected_output = "<img src='https://terzeron.com/xml/img/one_second/753d4f8.jpeg'/>\n"

        with patch('sys.argv', self.fake_argv), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)


if __name__ == "__main__":
    unittest.main()