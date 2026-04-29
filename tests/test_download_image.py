#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from bin.feed_maker_util import Env
import utils.download_image


class TestDownloadImage(unittest.TestCase):
    def setUp(self) -> None:
        page_url = "https://comic.naver.com/webtoon/detail.nhn?titleId=711422&no=1"
        work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.fake_argv = ["download_image.py", "-f", work_dir, page_url]

        # feed_dir_path.is_dir() 체크와 Config 초기화를 mock
        self._patcher_is_dir = patch("pathlib.Path.is_dir", return_value=True)
        self._patcher_mkdir = patch("pathlib.Path.mkdir")
        mock_config_instance = MagicMock()
        mock_config_instance.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        self._patcher_config = patch("utils.download_image.Config", return_value=mock_config_instance)
        self._patcher_is_dir.start()
        self._patcher_mkdir.start()
        self._patcher_config.start()

    def tearDown(self) -> None:
        self._patcher_config.stop()
        self._patcher_mkdir.stop()
        self._patcher_is_dir.stop()

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_single_quote(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.webp")

        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg'>"
        expected_output = "<img src='%s/one_second/753d4f8.webp'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_double_quote(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.webp")

        test_input = '<img src="https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg">'
        expected_output = "<img src='%s/one_second/753d4f8.webp'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_space(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.webp")

        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' >"
        expected_output = "<img src='%s/one_second/753d4f8.webp'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_trailing_slash(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.webp")

        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' />"
        expected_output = "<img src='%s/one_second/753d4f8.webp'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_width_attribute(self, mock_download: MagicMock) -> None:
        # Mock image download operations
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/753d4f8.webp")

        test_input = "<img src='https://image-comic.pstatic.net/webtoon/725586/247/20240118173811_a4fcf1cbd0e4a0d0b38a6b773ba58282_IMAG01_1.jpg' width='100%'/>"
        expected_output = "<img src='%s/one_second/753d4f8.webp' width='100%%'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_complex_text_and_images(self, mock_download: MagicMock) -> None:
        """복합적인 텍스트와 이미지가 섞여있는 케이스 테스트 (텍스트1-이미지1-텍스트2-이미지2-텍스트3)"""
        # Mock image download operations returning different URLs for each image
        mock_download.side_effect = [(True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image1.webp"), (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image2.webp"), (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/image3.png")]

        # 한 라인에 텍스트와 이미지가 여러 개 섞인 복합적인 케이스
        test_input = "<div align='center'>처음 텍스트입니다.</div> <img src='https://example.com/image1.jpg'/> <p>중간 텍스트입니다.</p> <img src='https://example.com/image2.jpg' width='100%'> <span>더 많은 중간 텍스트</span> <img src='https://example.com/image3.jpg' alt='test'/> <div>마지막 텍스트입니다.</div>"

        expected_output = ("<div align='center'>처음 텍스트입니다.</div>\n<img src='%s/one_second/image1.webp'/>\n<p>중간 텍스트입니다.</p>\n<img src='%s/one_second/image2.webp' width='100%%'/>\n<span>더 많은 중간 텍스트</span>\n<img src='%s/one_second/image3.png'/>\n<div>마지막 텍스트입니다.</div>\n") % (
            Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
            Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
            Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"),
        )

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_with_multiple_images_in_one_line(self, mock_download: MagicMock) -> None:
        """한 라인에 여러 이미지가 연속으로 있는 케이스 테스트"""
        # Mock image download operations
        mock_download.side_effect = [
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img1.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img2.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img3.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img4.webp"),
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/img5.webp"),
        ]

        # 실제 HTML 파일과 유사한 형태
        test_input = (
            "<div align='left'>프라모델 작업 과정입니다.</div> "
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
            "<p>완성된 모습입니다.</p>"
        )

        expected_output = (
            "<div align='left'>프라모델 작업 과정입니다.</div>\n"
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
            "<p>완성된 모습입니다.</p>\n"
        ) % (Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"), Env.get("WEB_SERVICE_IMAGE_URL_PREFIX"))

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_download_image_failure_case(self, mock_download: MagicMock) -> None:
        """이미지 다운로드 실패 케이스 테스트"""
        # Mock image download failure
        mock_download.side_effect = [
            (None, None),  # 첫 번째 이미지 실패
            (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/one_second/success.webp"),  # 두 번째 성공
            (None, None),  # 세 번째 실패
        ]

        test_input = "<p>시작 텍스트</p><img src='https://example.com/fail1.jpg'/><p>중간 텍스트</p><img src='https://example.com/success.jpg'/><p>더 많은 텍스트</p><img src='https://example.com/fail2.jpg'/><p>끝 텍스트</p>"

        expected_output = ("<p>시작 텍스트</p>\n<img src='not_found.png' alt='not exist or size 0'/>\n<p>중간 텍스트</p>\n<img src='%s/one_second/success.webp'/>\n<p>더 많은 텍스트</p>\n<img src='not_found.png' alt='not exist or size 0'/>\n<p>끝 텍스트</p>\n") % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)

    @patch("utils.download_image.Crawler")
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
        with patch("sys.argv", self.fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            utils.download_image.main()

            # Then
            # The output should be the placeholder, because the domain is blocked.
            self.assertEqual(mock_stdout.getvalue(), expected_output)
            # And the crawler's download method should NOT have been called.
            mock_crawler_instance.run.assert_not_called()

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_exclude_ad_image_from_different_domain(self, mock_download: MagicMock) -> None:
        """exclude_ad_images=True일 때 외부 도메인 이미지가 제거되는지 확인"""
        dengeki_dir = Env.get("FM_WORK_DIR") + "/plamodel/dengeki"
        fake_argv = ["download_image.py", "-f", dengeki_dir, "https://hobby.dengeki.com/news/123/"]

        test_input = "<p>기사 텍스트</p><img src='https://ws-fe.amazon-adsystem.com/widgets/q?ServiceVersion=123'/><p>더 많은 텍스트</p>"
        expected_output = "<p>기사 텍스트</p>\n<p>더 많은 텍스트</p>\n"

        mock_config_instance = MagicMock()
        mock_config_instance.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": True}

        with patch("sys.argv", fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("pathlib.Path.is_dir", return_value=True), patch("pathlib.Path.mkdir"), patch("utils.download_image.Config", return_value=mock_config_instance):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)
            mock_download.assert_not_called()

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_keep_same_origin_image_when_exclude_ad_images_enabled(self, mock_download: MagicMock) -> None:
        """exclude_ad_images=True여도 same-origin 이미지는 정상 다운로드"""
        mock_download.return_value = (True, f"{Env.get('WEB_SERVICE_IMAGE_URL_PREFIX')}/dengeki/abc123.webp")

        dengeki_dir = Env.get("FM_WORK_DIR") + "/plamodel/dengeki"
        fake_argv = ["download_image.py", "-f", dengeki_dir, "https://hobby.dengeki.com/news/123/"]

        test_input = "<img src='https://hobby.dengeki.com/ss/hobby/uploads/2024/image.jpg'/>"
        expected_output = "<img src='%s/dengeki/abc123.webp'/>\n" % Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")

        mock_config_instance = MagicMock()
        mock_config_instance.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": True}

        with patch("sys.argv", fake_argv), patch("sys.stdin", new=io.StringIO(test_input)), patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("pathlib.Path.is_dir", return_value=True), patch("pathlib.Path.mkdir"), patch("utils.download_image.Config", return_value=mock_config_instance):
            utils.download_image.main()
            self.assertEqual(mock_stdout.getvalue(), expected_output)
            mock_download.assert_called_once()


# ────────────────────────────────────────────────────────
# From test_remaining_gaps.py: download_image 추가 테스트
# ────────────────────────────────────────────────────────
class TestGetBaseDomain(unittest.TestCase):
    """_get_base_domain: lines 23, 25, 26"""

    def test_two_parts_returns_as_is(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("example.com"), "example.com")

    def test_co_kr_suffix_returns_last_three(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("www.example.co.kr"), "example.co.kr")

    def test_three_plus_parts_returns_last_two(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("sub.example.com"), "example.com")

    def test_single_part(self):
        from utils.download_image import _get_base_domain

        self.assertEqual(_get_base_domain("localhost"), "localhost")


class TestIsSameOrigin(unittest.TestCase):
    """_is_same_origin: lines 32, 34, 37"""

    def test_img_no_scheme_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("https://example.com/page", "/images/a.jpg"))

    def test_img_data_scheme_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("https://example.com", "data:image/png;base64,abc"))

    def test_img_data_scheme_with_hostname_returns_true(self):
        """data:// 형태의 URL도 same-origin으로 취급 (line 33-34)"""
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("https://example.com", "data://host/image"))

    def test_page_no_hostname_returns_true(self):
        from utils.download_image import _is_same_origin

        self.assertTrue(_is_same_origin("/local/path", "https://cdn.example.com/a.png"))


class TestReplaceImgTagError(unittest.TestCase):
    """replace_img_tag: lines 61-63 (OSError path)"""

    @patch("utils.download_image.ImageDownloader.download_image", side_effect=OSError("disk full"))
    def test_download_os_error_returns_error_tag(self, _mock_dl):
        from utils.download_image import replace_img_tag

        mock_match = MagicMock()
        mock_match.group.side_effect = lambda key: {"img_url": "https://example.com/img.jpg", 0: "<img src='https://example.com/img.jpg'/>"}[key]
        crawler = MagicMock()
        result = replace_img_tag(mock_match, crawler=crawler, feed_img_dir_path=Path("/tmp"), quality=75)
        self.assertIn("error occurred", result)


class TestDownloadImageMain(unittest.TestCase):
    """main(): lines 74-75 (-q), 78-79 (bad dir), 98-99 (no img), 110, 115-117 (tail)"""

    def setUp(self):
        self.work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_quality_option(self, mock_dl, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "-q", "50", "https://example.com/page"]
        stdin_data = "<img src='https://example.com/img.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("img", out.getvalue())

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_quality_before_feed_dir(self, mock_dl, _is_dir, _mkdir, mock_config):
        """-q 옵션이 -f 앞에 올 때 (branch 74->71 커버)"""
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-q", "50", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/img.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("img", out.getvalue())

    @patch("pathlib.Path.is_dir", return_value=False)
    def test_directory_not_found(self, _is_dir):
        argv = ["download_image.py", "-f", "/nonexistent/dir", "https://example.com"]
        with patch("sys.argv", argv):
            ret = utils.download_image.main()
            self.assertEqual(ret, -1)

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    def test_line_without_img_tag(self, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<p>Hello world</p>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("Hello world", out.getvalue())

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_trailing_whitespace_after_last_element(self, mock_dl, _is_dir, _mkdir, mock_config):
        """이미지 태그 뒤에 공백만 있는 경우 (branch 116->exit 커버)"""
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        # 이미지 태그 뒤에 공백만 있음 -> tail.strip()이 빈 문자열
        stdin_data = "<img src='https://example.com/img.jpg'/>   "
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            # 공백은 출력되지 않아야 함
            self.assertNotIn("   ", out.getvalue())

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_tail_text_after_last_element(self, mock_dl, _is_dir, _mkdir, mock_config):
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/img.jpg'/>some tail text"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            output = out.getvalue()
            self.assertIn("tail text", output)


class TestNewOptions(unittest.TestCase):
    """신규 옵션 --keep-img-meta-only / --dedupe-consecutive-images /
    --remove-not-found-images / --replace-nbsp / --strip-wrapper-tags /
    --exclude-img-url-pattern 테스트"""

    def setUp(self) -> None:
        self.work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.img_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self._patcher_is_dir = patch("pathlib.Path.is_dir", return_value=True)
        self._patcher_mkdir = patch("pathlib.Path.mkdir")
        mock_cfg = MagicMock()
        mock_cfg.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        self._patcher_config = patch("utils.download_image.Config", return_value=mock_cfg)
        self._patcher_is_dir.start()
        self._patcher_mkdir.start()
        self._patcher_config.start()

    def tearDown(self) -> None:
        self._patcher_config.stop()
        self._patcher_mkdir.stop()
        self._patcher_is_dir.stop()

    def _run(self, extra_args: list, stdin_data: str, mock_dl_side_effect=None, mock_dl_return=None):
        argv = ["download_image.py", "-f", self.work_dir] + extra_args + ["https://example.com/page"]
        with patch("utils.image_downloader.ImageDownloader.download_image") as mock_dl, patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            if mock_dl_side_effect is not None:
                mock_dl.side_effect = mock_dl_side_effect
            elif mock_dl_return is not None:
                mock_dl.return_value = mock_dl_return
            ret = utils.download_image.main()
        return ret, out.getvalue()

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_keep_img_meta_only_discards_non_img_elements(self, mock_dl: MagicMock) -> None:
        """--keep-img-meta-only: meta/style/img만 출력, div/p 등 제거"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/a.webp")
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<div>본문 텍스트</div><img src='https://example.com/1.jpg'/><p>설명</p>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertIn("<img src=", output)
        self.assertNotIn("<div>", output)
        self.assertNotIn("<p>", output)
        self.assertNotIn("본문 텍스트", output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_keep_img_meta_only_preserves_meta_and_style(self, mock_dl: MagicMock) -> None:
        """--keep-img-meta-only: meta/style 라인은 그대로 출력"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/a.webp")
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<meta charset='utf-8'/>\n<style>body{}</style>\n<div>skip</div>\n<img src='https://example.com/1.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertIn("<meta", output)
        self.assertIn("<style>", output)
        self.assertNotIn("<div>", output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_dedupe_consecutive_images(self, mock_dl: MagicMock) -> None:
        """--keep-img-meta-only --dedupe-consecutive-images: 연속 중복 이미지 제거"""
        url = f"{self.img_prefix}/one_second/same.webp"
        mock_dl.return_value = (True, url)
        argv = ["download_image.py", "--keep-img-meta-only", "--dedupe-consecutive-images", "-f", self.work_dir, "https://example.com/page"]
        # 동일 이미지가 두 번 연속
        stdin_data = "<img src='https://example.com/1.jpg'/>\n<img src='https://example.com/1.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue().count("<img src="), 1)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_dedupe_consecutive_images_different_urls(self, mock_dl: MagicMock) -> None:
        """--dedupe-consecutive-images: 다른 이미지는 모두 출력"""
        mock_dl.side_effect = [(True, f"{self.img_prefix}/one_second/a.webp"), (True, f"{self.img_prefix}/one_second/b.webp")]
        argv = ["download_image.py", "--keep-img-meta-only", "--dedupe-consecutive-images", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/1.jpg'/>\n<img src='https://example.com/2.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue().count("<img src="), 2)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_remove_not_found_images_skips_placeholder_in_src(self, mock_dl: MagicMock) -> None:
        """--remove-not-found-images: src에 image-not-found.png 포함 이미지 제거"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/ok.webp")
        argv = ["download_image.py", "--keep-img-meta-only", "--remove-not-found-images", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/image-not-found.png'/>\n<img src='https://example.com/ok.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertEqual(output.count("<img src="), 1)
        self.assertNotIn("image-not-found.png", output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_remove_not_found_images_suppresses_not_found_output(self, mock_dl: MagicMock) -> None:
        """--remove-not-found-images: 다운로드 실패 시 not_found.png 출력 억제"""
        mock_dl.return_value = (None, None)
        argv = ["download_image.py", "--keep-img-meta-only", "--remove-not-found-images", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/broken.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        self.assertNotIn("not_found", out.getvalue())

    def test_replace_nbsp(self) -> None:
        """--replace-nbsp: NBSP( )를 일반 공백으로 치환"""
        argv = ["download_image.py", "--replace-nbsp", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "텍스트 사이의 NBSP"
        with patch("utils.image_downloader.ImageDownloader.download_image"), patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertNotIn(" ", output)
        self.assertIn("텍스트 사이의 NBSP", output)

    def test_strip_wrapper_tags(self) -> None:
        """--strip-wrapper-tags: article/html/head/body 태그 제거"""
        argv = ["download_image.py", "--strip-wrapper-tags", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<html><head></head><body><article>내용</article></body></html>"
        with patch("utils.image_downloader.ImageDownloader.download_image"), patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertNotIn("<html>", output)
        self.assertNotIn("<body>", output)
        self.assertNotIn("<head>", output)
        self.assertNotIn("<article>", output)
        self.assertNotIn("</html>", output)
        self.assertIn("내용", output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_exclude_img_url_pattern(self, mock_dl: MagicMock) -> None:
        """--exclude-img-url-pattern: 패턴 일치 이미지 URL 제거"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/ok.webp")
        argv = ["download_image.py", "--exclude-img-url-pattern", r"ad\.example\.com", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://ad.example.com/banner.jpg'/><img src='https://example.com/ok.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        output = out.getvalue()
        self.assertNotIn("ad.example.com", output)
        self.assertIn("ok.webp", output)

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_remove_not_found_images_in_default_mode(self, mock_dl: MagicMock) -> None:
        """--remove-not-found-images: keep-img-meta-only 없이 기본 모드에서도 동작"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/ok.webp")
        argv = ["download_image.py", "--remove-not-found-images", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://example.com/image-not-found.png'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        self.assertNotIn("<img", out.getvalue())
        mock_dl.assert_not_called()

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_exclude_img_url_pattern_in_default_mode(self, mock_dl: MagicMock) -> None:
        """--exclude-img-url-pattern: 기본 모드에서도 패턴 일치 이미지 제거"""
        mock_dl.return_value = (True, f"{self.img_prefix}/one_second/ok.webp")
        argv = ["download_image.py", "--exclude-img-url-pattern", r"blocked\.com", "-f", self.work_dir, "https://example.com/page"]
        stdin_data = "<img src='https://blocked.com/img.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
        self.assertEqual(ret, 0)
        self.assertNotIn("<img", out.getvalue())
        mock_dl.assert_not_called()


class TestIsSameOriginBlockedDomains(unittest.TestCase):
    """_is_same_origin with data: scheme via replace_img_tag (lines 33-34)"""

    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_data_url_not_excluded_when_exclude_ad_images(self, mock_download: MagicMock) -> None:
        """exclude_ad_images=True일 때 data: URL은 same-origin으로 취급되어 제외되지 않음"""
        from utils.download_image import replace_img_tag

        mock_download.return_value = (True, "http://example.com/img.webp")
        mock_match = MagicMock()
        data_url = "data:image/png;base64,iVBORw0KGgo="
        mock_match.group.side_effect = lambda key: {"img_url": data_url, 0: f"<img src='{data_url}'/>"}[key]
        crawler = MagicMock()
        result = replace_img_tag(mock_match, crawler=crawler, feed_img_dir_path=Path("/tmp"), quality=75, page_url="https://example.com/page", exclude_ad_images=True)
        # data: URL은 same-origin이므로 정상 처리됨
        self.assertIn("img", result)
        mock_download.assert_called_once()


class TestSplitAndPrintTextBetweenElements(unittest.TestCase):
    """split_and_print: bare text between elements (lines 109-110)"""

    def setUp(self):
        self.work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"

    @patch("utils.download_image.Config")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_dir", return_value=True)
    @patch("utils.image_downloader.ImageDownloader.download_image")
    def test_bare_text_between_img_elements(self, mock_dl, _is_dir, _mkdir, mock_config):
        """이미지 태그 사이에 태그로 감싸지지 않은 텍스트가 있는 경우"""
        mock_config.return_value.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        mock_dl.return_value = (True, f"{img_url_prefix}/one_second/abc.webp")

        argv = ["download_image.py", "-f", self.work_dir, "https://example.com/page"]
        # 태그 사이에 bare text "중간텍스트"가 있음
        stdin_data = "<img src='https://example.com/a.jpg'/>중간텍스트<img src='https://example.com/b.jpg'/>"
        with patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            ret = utils.download_image.main()
            self.assertEqual(ret, 0)
            self.assertIn("중간텍스트", out.getvalue())


class TestMainBlock(unittest.TestCase):
    """if __name__ == '__main__' block (lines 125-126)"""

    def test_main_block(self):
        """__main__ 블록이 sys.exit(main())을 호출하는지 확인"""
        argv = ["download_image.py", "-f", "/nonexistent", "http://example.com"]
        with patch("sys.argv", argv), patch("pathlib.Path.is_dir", return_value=False):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(str(Path(utils.download_image.__file__)), run_name="__main__")
            # main()이 -1을 반환하므로 sys.exit(-1) 호출
            self.assertEqual(cm.exception.code, -1)


class TestReplaceImgTagRemoveNotFound(unittest.TestCase):
    """replace_img_tag: remove_not_found_images=True 경로 (lines 68-74)"""

    @patch("utils.download_image.ImageDownloader.download_image", return_value=(None, None))
    def test_falsy_new_img_url_with_remove_not_found_returns_empty(self, _mock_dl):
        """download_image가 (None, None)을 반환하고 remove_not_found_images=True → '' 반환 (line 69)"""
        from utils.download_image import replace_img_tag

        mock_match = MagicMock()
        mock_match.group.side_effect = lambda key: {"img_url": "https://example.com/img.jpg", 0: "<img src='https://example.com/img.jpg'/>"}[key]
        crawler = MagicMock()
        result = replace_img_tag(mock_match, crawler=crawler, feed_img_dir_path=Path("/tmp"), quality=75, remove_not_found_images=True)
        self.assertEqual(result, "")

    @patch("utils.download_image.ImageDownloader.download_image", side_effect=OSError("disk full"))
    def test_os_error_with_remove_not_found_returns_empty(self, _mock_dl):
        """download_image가 OSError 발생하고 remove_not_found_images=True → '' 반환 (line 74)"""
        from utils.download_image import replace_img_tag

        mock_match = MagicMock()
        mock_match.group.side_effect = lambda key: {"img_url": "https://example.com/img.jpg", 0: "<img src='https://example.com/img.jpg'/>"}[key]
        crawler = MagicMock()
        result = replace_img_tag(mock_match, crawler=crawler, feed_img_dir_path=Path("/tmp"), quality=75, remove_not_found_images=True)
        self.assertEqual(result, "")


class TestKeepImgMetaOnly(unittest.TestCase):
    """main()의 keep_img_meta_only 경로 미커버 분기 테스트 (lines 163-188)"""

    def setUp(self) -> None:
        self.work_dir = Env.get("FM_WORK_DIR") + "/naver/one_second"
        self.img_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
        self._patcher_is_dir = patch("pathlib.Path.is_dir", return_value=True)
        self._patcher_mkdir = patch("pathlib.Path.mkdir")
        mock_cfg = MagicMock()
        mock_cfg.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": False}
        self._patcher_config = patch("utils.download_image.Config", return_value=mock_cfg)
        self._patcher_is_dir.start()
        self._patcher_mkdir.start()
        self._patcher_config.start()

    def tearDown(self) -> None:
        self._patcher_config.stop()
        self._patcher_mkdir.stop()
        self._patcher_is_dir.stop()

    def _run(self, argv: list, stdin_data: str, mock_dl_config=None):
        with patch("utils.image_downloader.ImageDownloader.download_image") as mock_dl, patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out:
            if mock_dl_config is not None:
                mock_dl_config(mock_dl)
            ret = utils.download_image.main()
        return ret, out.getvalue()

    def test_exclude_ad_images_cross_origin_skipped(self) -> None:
        """--keep-img-meta-only + exclude_ad_images=True + cross-origin 이미지 → 이미지 출력 없음 (line 163-165)"""
        page_url = "https://comic.naver.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, page_url]
        stdin_data = "<img src='https://ws-fe.amazon-adsystem.com/banner.jpg'/>"

        mock_cfg = MagicMock()
        mock_cfg.get_extraction_configs.return_value = {"user_agent": "", "exclude_ad_images": True}

        with patch("utils.image_downloader.ImageDownloader.download_image") as mock_dl, patch("sys.argv", argv), patch("sys.stdin", new=io.StringIO(stdin_data)), patch("sys.stdout", new_callable=io.StringIO) as out, patch("utils.download_image.Config", return_value=mock_cfg):
            ret = utils.download_image.main()

        self.assertEqual(ret, 0)
        self.assertEqual(out.getvalue(), "")
        mock_dl.assert_not_called()

    def test_exclude_img_url_pattern_skipped(self) -> None:
        """--keep-img-meta-only + --exclude-img-url-pattern + 패턴 매칭 URL → 이미지 출력 없음 (line 166-167)"""
        page_url = "https://example.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "--exclude-img-url-pattern", r"ads\.", "-f", self.work_dir, page_url]
        stdin_data = "<img src='https://ads.example.com/banner.jpg'/>"

        def configure(mock_dl):
            mock_dl.return_value = (None, None)

        ret, output = self._run(argv, stdin_data, mock_dl_config=configure)
        self.assertEqual(ret, 0)
        self.assertEqual(output, "")

    def test_data_image_svg_skipped(self) -> None:
        """--keep-img-meta-only + data:image/svg src → 이미지 출력 없음 (line 168-169)"""
        page_url = "https://example.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, page_url]
        stdin_data = "<img src='data:image/svg+xml,<svg xmlns=\"http://www.w3.org/2000/svg\"/>' />"

        def configure(mock_dl):
            mock_dl.return_value = (None, None)

        ret, output = self._run(argv, stdin_data, mock_dl_config=configure)
        self.assertEqual(ret, 0)
        self.assertEqual(output, "")

    def test_download_success_with_width_preserved(self) -> None:
        """--keep-img-meta-only + download 성공 + width 속성 → width 보존하며 출력 (lines 177-178)"""
        page_url = "https://example.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, page_url]
        new_url = f"{self.img_prefix}/one_second/abc.webp"
        stdin_data = "<img src='https://example.com/img.jpg' width='100%'/>"

        def configure(mock_dl):
            mock_dl.return_value = (True, new_url)

        ret, output = self._run(argv, stdin_data, mock_dl_config=configure)
        self.assertEqual(ret, 0)
        self.assertIn(new_url, output)
        self.assertIn("width='100%'", output)

    def test_download_failure_none_none_without_remove_not_found(self) -> None:
        """--keep-img-meta-only + download 실패(None,None) + remove_not_found=False → not_found.png 출력 (lines 183-184)"""
        page_url = "https://example.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, page_url]
        stdin_data = "<img src='https://example.com/broken.jpg'/>"

        def configure(mock_dl):
            mock_dl.return_value = (None, None)

        ret, output = self._run(argv, stdin_data, mock_dl_config=configure)
        self.assertEqual(ret, 0)
        self.assertIn("not_found.png", output)
        self.assertIn("not exist or size 0", output)

    def test_download_os_error_without_remove_not_found(self) -> None:
        """--keep-img-meta-only + download OSError + remove_not_found=False → error placeholder 출력 (lines 185-188)"""
        page_url = "https://example.com/page"
        argv = ["download_image.py", "--keep-img-meta-only", "-f", self.work_dir, page_url]
        stdin_data = "<img src='https://example.com/broken.jpg'/>"

        def configure(mock_dl):
            mock_dl.side_effect = OSError("connection refused")

        ret, output = self._run(argv, stdin_data, mock_dl_config=configure)
        self.assertEqual(ret, 0)
        self.assertIn("not_found.png", output)
        self.assertIn("error occurred", output)


if __name__ == "__main__":
    unittest.main()
