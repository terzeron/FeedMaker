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
        test_input = "<div>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_3.jpg'/>\n<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_4.jpg'/>\n"
        url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected_output = "<div>\n<img src='%s/one_second/0163a33_1.1.jpeg'/>\n<img src='%s/one_second/0163a33_1.2.jpeg'/>\n<img src='%s/one_second/0163a33_2.1.jpeg'/>\n<img src='%s/one_second/0163a33_3.1.jpeg'/>\n<img src='%s/one_second/0163a33_3.2.jpeg'/>\n<img src='%s/one_second/0163a33_4.1.jpeg'/>\n<img src='%s/one_second/0163a33_4.2.jpeg'/>\n" % (url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix)

        with patch('sys.argv', self.fake_argv), patch.dict('os.environ', self.fake_env, clear=False), patch('sys.stdin', new=io.StringIO(test_input)), patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            utils.download_merge_split.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)


if __name__ == "__main__":
    unittest.main()
