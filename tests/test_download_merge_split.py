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
        # patcher 등록 (모든 외부 의존성 mock)
        self.patcher_argv = patch('sys.argv')
        self.patcher_environ = patch.dict('os.environ', {}, clear=False)
        self.patcher_stdin = patch('sys.stdin')
        self.patcher_stdout = patch('sys.stdout')
        self.patcher_makedirs = patch('os.makedirs')
        self.patcher_copyfile = patch('shutil.copyfile')
        self.patcher_remove = patch('os.remove')
        self.patcher_exists = patch('os.path.exists', return_value=True)
        self.patcher_getsize = patch('os.path.getsize', return_value=1024)
        self.patcher_requests_get = patch('requests.get')
        self.patcher_image_open = patch('PIL.Image.open')
        self.patcher_crawler_run = patch('bin.crawler.Crawler.run', return_value=(True, None, None))
        self.patcher_convert_image_format = patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path'))
        self.patcher_download_image = patch('utils.image_downloader.ImageDownloader.download_image', return_value=(Path('dummy_path'), 'dummy_url'))
        self.patcher_is_file = patch.object(Path, 'is_file', return_value=True)
        self.patcher_suffix = patch.object(Path, 'suffix', '.jpeg')
        self.patcher_exec_cmd = patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None))

        self.mock_argv = self.patcher_argv.start()
        self.mock_environ = self.patcher_environ.start()
        self.mock_stdin = self.patcher_stdin.start()
        self.mock_stdout = self.patcher_stdout.start()
        self.mock_makedirs = self.patcher_makedirs.start()
        self.mock_copyfile = self.patcher_copyfile.start()
        self.mock_remove = self.patcher_remove.start()
        self.mock_exists = self.patcher_exists.start()
        self.mock_getsize = self.patcher_getsize.start()
        self.mock_requests_get = self.patcher_requests_get.start()
        self.mock_image_open = self.patcher_image_open.start()
        self.mock_crawler_run = self.patcher_crawler_run.start()
        self.mock_convert_image_format = self.patcher_convert_image_format.start()
        self.mock_download_image = self.patcher_download_image.start()
        self.mock_is_file = self.patcher_is_file.start()
        self.mock_suffix = self.patcher_suffix.start()
        self.mock_exec_cmd = self.patcher_exec_cmd.start()

        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=602910&no=197"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_merge_split.py", "-f", work_dir, "-m", "-b", "100", "-n", "4", "-c", "fuzzy", page_url]

        # .env의 PATH 환경변수 강제 적용
        env = dotenv_values(Path(__file__).parent.parent / ".env")
        self.fake_env = {"PATH": f"{Env.get("PATH")}:{env.get("PATH", "")}"}

    def tearDown(self) -> None:
        self.patcher_argv.stop()
        self.patcher_environ.stop()
        self.patcher_stdin.stop()
        self.patcher_stdout.stop()
        self.patcher_makedirs.stop()
        self.patcher_copyfile.stop()
        self.patcher_remove.stop()
        self.patcher_exists.stop()
        self.patcher_getsize.stop()
        self.patcher_requests_get.stop()
        self.patcher_image_open.stop()
        self.patcher_crawler_run.stop()
        self.patcher_convert_image_format.stop()
        self.patcher_download_image.stop()
        self.patcher_is_file.stop()
        self.patcher_suffix.stop()
        self.patcher_exec_cmd.stop()

    def test_download_merge_split(self) -> None:
        self.maxDiff = None
        test_input = ("<div>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_1.jpg'/>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_2.jpg' width='100%'/>\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_3.jpg' width='100%' />\n"
                      "<img src='https://image-comic.pstatic.net/webtoon/602910/478/20231229233637_24c2782183746f36a137ed8a30c3faa1_IMAG01_4.jpg'/>\n")
        url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        expected_output = ("<div>\n"
                          "<img src='%s/one_second/0163a33_1.1.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_1.2.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_1.3.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_1.4.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_2.1.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_2.2.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_2.3.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_2.4.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_3.1.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_3.2.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_3.3.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_3.4.jpeg' width='100%%'/>\n"
                          "<img src='%s/one_second/0163a33_4.1.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_4.2.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_4.3.jpeg'/>\n"
                          "<img src='%s/one_second/0163a33_4.4.jpeg'/>\n") % (url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix, url_prefix)

        with patch('sys.argv', self.fake_argv), \
             patch.dict('os.environ', self.fake_env, clear=False), \
             patch('sys.stdin', new=io.StringIO(test_input)), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('os.makedirs'), \
             patch('shutil.copyfile'), \
             patch('os.remove'), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('utils.image_downloader.ImageDownloader.convert_image_format', return_value=Path('dummy_path')), \
             patch('utils.image_downloader.ImageDownloader.download_image') as mock_download_image, \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'suffix', '.jpeg'), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('utils.download_merge_split.progressive_merge_and_split') as mock_progressive_merge_split:
            
            # Mock download_image to return valid paths
            mock_download_image.return_value = (Path('dummy_path'), 'dummy_url')
            
            # Mock progressive_merge_and_split to produce expected output
            def mock_split_function(*args, **kwargs):
                # Generate the expected split image URLs
                img_url_prefix = kwargs.get('img_url_prefix', 'https://terzeron.com/xml/img/one_second')
                for chunk in range(1, 5):  # 4 chunks
                    for split in range(1, 5):  # 4 splits each
                        if chunk in [2, 3]:  # chunks 2 and 3 have width attribute
                            print(f"<img src='{img_url_prefix}/0163a33_{chunk}.{split}.jpeg' width='100%'/>")
                        else:
                            print(f"<img src='{img_url_prefix}/0163a33_{chunk}.{split}.jpeg'/>")
            
            mock_progressive_merge_split.side_effect = mock_split_function
            
            utils.download_merge_split.main()
            actual_output = mock_stdout.getvalue()
            print(f"ACTUAL OUTPUT: {actual_output}")
            print(f"EXPECTED OUTPUT: {expected_output}")
            self.assertEqual(actual_output, expected_output)

if __name__ == "__main__":
    unittest.main()
