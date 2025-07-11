#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import unittest
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Env
import utils.download_image


class TestDownloadImage(unittest.TestCase):
    def setUp(self) -> None:
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=711422&no=1"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_image.py", "-f", work_dir, page_url]

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_single_quote(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg'>"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_double_quote(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = '<img src="https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg">'
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_space(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' >"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_trailing_slash(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' />"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_width_attribute(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.jpeg")
        
        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' width='100%'/>"
        expected_output = "<img src='%s/one_second/753d4f8.jpeg' width='100%%'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_complex_text_and_images(self, mock_download: MagicMock) -> None:
        """복합적인 텍스트와 이미지가 섞여있는 케이스 테스트 (텍스트1-이미지1-텍스트2-이미지2-텍스트3)"""
        # Mock image download operations returning different URLs for each image
        mock_download.side_effect = [
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image1.jpeg"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image2.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image3.png")
        ]
        
        # 한 라인에 텍스트와 이미지가 여러 개 섞인 복합적인 케이스
        test_input = ("<div align='center'>처음 텍스트입니다.</div> "
                     "<img src='https://example.com/image1.jpg'/> "
                     "<p>중간 텍스트입니다.</p> "
                     "<img src='https://example.com/image2.jpg' width='100%'> "
                     "<span>더 많은 중간 텍스트</span> "
                     "<img src='https://example.com/image3.jpg' alt='test'/> "
                     "<div>마지막 텍스트입니다.</div>")
        
        expected_output = ("<div align='center'>처음 텍스트입니다.</div>\n"
                          "<img src='%s/one_second/image1.jpeg'/>\n"
                          "<p>중간 텍스트입니다.</p>\n"
                          "<img src='%s/one_second/image2.webp' width='100%%'/>\n"
                          "<span>더 많은 중간 텍스트</span>\n"
                          "<img src='%s/one_second/image3.png'/>\n"
                          "<div>마지막 텍스트입니다.</div>\n") % (
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"))

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_with_multiple_images_in_one_line(self, mock_download: MagicMock) -> None:
        """한 라인에 여러 이미지가 연속으로 있는 케이스 테스트"""
        # Mock image download operations
        mock_download.side_effect = [
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img1.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img2.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img3.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img4.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img5.webp")
        ]
        
        # 실제 HTML 파일과 유사한 형태
        test_input = ("<div align='left'>프라모델 작업 과정입니다.</div> "
                     "<center>첫 번째 이미지</center> "
                     "<center><img src='https://example.com/image1.jpg'/></center> "
                     "<p>작업 설명 텍스트</p> "
                     "<center><img src='https://example.com/image2.jpg'/></center> "
                     "<p>더 많은 설명</p> "
                     "<center><img src='https://example.com/image3.jpg'/></center> "
                     "<p>추가 설명</p> "
                     "<center><img src='https://example.com/image4.jpg'/></center> "
                     "<p>마지막 단계</p> "
                     "<center><img src='https://example.com/image5.jpg'/></center> "
                     "<p>완성된 모습입니다.</p>")
        
        expected_output = ("<div align='left'>프라모델 작업 과정입니다.</div>\n"
                          "<center>첫 번째 이미지</center>\n"
                          "<center><img src='%s/one_second/img1.webp'/></center>\n"
                          "<p>작업 설명 텍스트</p>\n"
                          "<center><img src='%s/one_second/img2.webp'/></center>\n"
                          "<p>더 많은 설명</p>\n"
                          "<center><img src='%s/one_second/img3.webp'/></center>\n"
                          "<p>추가 설명</p>\n"
                          "<center><img src='%s/one_second/img4.webp'/></center>\n"
                          "<p>마지막 단계</p>\n"
                          "<center><img src='%s/one_second/img5.webp'/></center>\n"
                          "<p>완성된 모습입니다.</p>\n") % (
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
                              Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"))

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.image_downloader.ImageDownloader.download_image')
    def test_download_image_failure_case(self, mock_download: MagicMock) -> None:
        """이미지 다운로드 실패 케이스 테스트"""
        # Mock image download failure
        mock_download.side_effect = [
            (None, None),  # 첫 번째 이미지 실패
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/success.webp"),  # 두 번째 성공
            (None, None)   # 세 번째 실패
        ]
        
        test_input = ("<p>시작 텍스트</p>"
                     "<img src='https://example.com/fail1.jpg'/>"
                     "<p>중간 텍스트</p>"
                     "<img src='https://example.com/success.jpg'/>"
                     "<p>더 많은 텍스트</p>"
                     "<img src='https://example.com/fail2.jpg'/>"
                     "<p>끝 텍스트</p>")
        
        expected_output = ("<p>시작 텍스트</p>\n"
                          "<img src='not_found.png' alt='not exist or size 0'/>\n"
                          "<p>중간 텍스트</p>\n"
                          "<img src='%s/one_second/success.webp'/>\n"
                          "<p>더 많은 텍스트</p>\n"
                          "<img src='not_found.png' alt='not exist or size 0'/>\n"
                          "<p>끝 텍스트</p>\n") % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch('utils.download_image.Crawler')
    def test_skip_download_for_blocked_domain(self, mock_crawler_class: MagicMock) -> None:
        """차단된 도메인의 이미지는 다운로드를 건너뛰는지 테스트"""
        # Given: We patch the Crawler class to control its instances.
        # The instance's `run` method (the actual download call) should not be called.
        mock_crawler_instance = MagicMock()
        mock_crawler_class.return_value = mock_crawler_instance

        test_input = "<div><img src='http://image.egloos.com/image.jpg'/></div>"
        # The logic inside ImageDownloader.download_image should see the blocked domain,
        # return (None, None), and cause replace_img_tag to produce a "not_found" image.
        expected_output = "<div><img src='not_found.png' alt='not exist or size 0'/></div>\n"

        # When
        with (
            patch("sys.argv", self.fake_argv),
            patch("sys.stdin", new=io.StringIO(test_input)),
            patch("sys.stdout", new_callable=io.StringIO) as mock_stdout,
        ):
            utils.download_image.main()

            # Then
            # The output should be the placeholder, because the domain is blocked.
            self.assertEqual(mock_stdout.getvalue(), expected_output)
            # And the crawler's download method should NOT have been called.
            mock_crawler_instance.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
