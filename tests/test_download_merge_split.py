#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import unittest
from unittest.mock import patch
from pathlib import Path
from dotenv import dotenv_values

from bin.feed_maker_util import Env
import utils.download_merge_split


class TestDownloadMergeSplit(unittest.TestCase):
    def setUp(self) -> None:
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_merge_split.py", "-f", work_dir, "-m", "-b", "100", "-n", "4", "-c", "fuzzy", page_url]

        # .env의 PATH 환경변수 강제 적용
        env = dotenv_values(Path(__file__).parent.parent / ".env")
        self.fake_env = {"PATH": f"{Env.get("PATH")}:{env.get("PATH", "")}"}

    def test_download_merge_split(self) -> None:
        self.maxDiff = None
        test_input = "<div>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_3.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_4.jpg'/>\n"
        url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected_output = "<div>\n<img src='%s/one_second/0163a33_1.1.jpeg'/>\n<img src='%s/one_second/0163a33_1.2.jpeg'/>\n<img src='%s/one_second/0163a33_1.3.jpeg'/>\n<img src='%s/one_second/0163a33_1.4.jpeg'/>\n<img src='%s/one_second/0163a33_2.1.jpeg'/>\n<img src='%s/one_second/0163a33_2.2.jpeg'/>\n<img src='%s/one_second/0163a33_2.3.jpeg'/>\n<img src='%s/one_second/0163a33_2.4.jpeg'/>\n<img src='%s/one_second/0163a33_3.1.jpeg'/>\n<img src='%s/one_second/0163a33_3.2.jpeg'/>\n<img src='%s/one_second/0163a33_3.3.jpeg'/>\n<img src='%s/one_second/0163a33_3.4.jpeg'/>\n<img src='%s/one_second/0163a33_4.1.jpeg'/>\n<img src='%s/one_second/0163a33_4.2.jpeg'/>\n<img src='%s/one_second/0163a33_4.3.jpeg'/>\n<img src='%s/one_second/0163a33_4.4.jpeg'/>\n" % (url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix)

        with patch('sys.argv', self.fake_argv), \
             patch.dict('os.environ', self.fake_env, clear=False), \
             patch('sys.stdin', new=io.StringIO(test_input)), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('os.makedirs'), \
             patch('shutil.copyfile'), \
             patch('os.remove'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('requests.get') as mock_requests_get, \
             patch('PIL.Image.open') as mock_image_open, \
             patch('bin.crawler.Crawler.run', return_value=(True, None, None)), \
             patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path')), \
             patch('utils.image_downloader.ImageDownloader.download_image') as mock_download_image, \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'suffix', '.jpeg'), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None)):
            mock_requests_get.return_value.content = b'dummy'
            mock_image = mock_image_open.return_value
            mock_image.save.return_value = None
            
            # Mock download_image to return a valid Path and URL
            mock_download_image.return_value = (Path('dummy_path'), 'dummy_url')
            
            utils.download_merge_split.main()
            actual_output = mock_stdout.getvalue()
            print(f"ACTUAL OUTPUT: {actual_output}")
            print(f"EXPECTED OUTPUT: {expected_output}")
            self.assertEqual(actual_output, expected_output)

if __name__ == "__main__":
    unittest.main()
