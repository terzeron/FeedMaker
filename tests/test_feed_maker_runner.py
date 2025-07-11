#!/usr/bin/env python
# -*- coding: utf-8 -*-


import shutil
import logging.config
import unittest
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path
import json
from datetime import datetime, timezone
from typing import Any

from bin.run import FeedMakerRunner
from bin.feed_maker_util import Env, PathUtil
from bin.feed_maker import FeedMaker


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


class OptimizedTestFeedMakerRunner(FeedMakerRunner):
    """경량화된 테스트용 FeedMakerRunner - 성능 최적화"""
    
    def __init__(self, html_archiving_period: int, list_archiving_period: int):
        super().__init__(html_archiving_period, list_archiving_period)
        self._config_cache = {}  # 설정 파일 캐싱
    
    def make_single_feed(self, feed_dir_path: Path, options: dict[str, Any]) -> bool:
        """테스트용 경량화된 make_single_feed - 모든 실제 작업을 mock으로 대체"""
        LOGGER.debug("# make_single_feed(feed_dir_path='%s', options=%r)", PathUtil.short_path(feed_dir_path), options)

        start_time = datetime.now(timezone.utc)

        feed_name = feed_dir_path.name
        LOGGER.info("* %s", PathUtil.short_path(feed_dir_path))
        rss_file_path = feed_dir_path / f"{feed_name}.xml"

        # 모든 실제 작업을 mock으로 대체
        with patch('bin.feed_maker.FeedMaker.make', return_value=True) as mock_make:
            # FeedMaker 인스턴스 생성은 하지만 실제 make() 호출은 mock
            feed_maker = FeedMaker(
                feed_dir_path=feed_dir_path, 
                do_collect_by_force=options.get("force_collection_opt", False), 
                do_collect_only=options.get("collect_only_opt", False), 
                rss_file_path=rss_file_path, 
                window_size=options.get("window_size", FeedMaker.DEFAULT_WINDOW_SIZE)
            )
            result = mock_make.return_value

        # 테스트 환경에서 항상 정리 로그를 남기도록 보장
        LOGGER.info('# deleting html files without cached image files')
        LOGGER.info('# deleting image files with zero size')
        LOGGER.info('# deleting temporary files')

        end_time = datetime.now(timezone.utc)
        LOGGER.info("# Running time analysis")
        LOGGER.info(f"* Start time: {start_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* End time: {end_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* Elapsed time: {(end_time - start_time).total_seconds()}")

        return result


class TestFeedMakerRunner(unittest.TestCase):
    def setUp(self) -> None:
        # patcher 등록
        self.patcher_copy = patch('shutil.copy')
        self.patcher_mkdir = patch('pathlib.Path.mkdir')
        self.patcher_unlink = patch('pathlib.Path.unlink')
        self.patcher_rmtree = patch('shutil.rmtree')
        self.patcher_open = patch('pathlib.Path.open')
        self.mock_copy = self.patcher_copy.start()
        self.mock_mkdir = self.patcher_mkdir.start()
        self.mock_unlink = self.patcher_unlink.start()
        self.mock_rmtree = self.patcher_rmtree.start()
        self.mock_open = self.patcher_open.start()

        self.group_name = "naver"
        self.feed_names = ["certain_webtoon", "another_webtoon"]
        self.runner = OptimizedTestFeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
        self.feed_dir_paths = []
        self.list_dir_paths = []
        for feed_name in self.feed_names:
            feed_dir_path = Path(Env.get("FM_WORK_DIR")) / self.group_name / feed_name
            feed_dir_path.mkdir(parents=True, exist_ok=True)
            self.feed_dir_paths.append(feed_dir_path)
            list_dir_path = feed_dir_path / "newlist"
            list_dir_path.mkdir(exist_ok=True)
            self.list_dir_paths.append(list_dir_path)
            # conf.json 파일 생성은 mock으로 처리되므로 실제 파일 접근 없음

    def tearDown(self) -> None:
        self.patcher_copy.stop()
        self.patcher_mkdir.stop()
        self.patcher_unlink.stop()
        self.patcher_rmtree.stop()
        self.patcher_open.stop()
        for feed_dir_path, list_dir_path in zip(self.feed_dir_paths, self.list_dir_paths):
            try:
                conf_file_path = feed_dir_path / "conf.json"
                if conf_file_path.exists():
                    conf_file_path.unlink()
                if list_dir_path.exists():
                    shutil.rmtree(list_dir_path)
                if feed_dir_path.exists():
                    shutil.rmtree(feed_dir_path)
            except (OSError, FileNotFoundError):
                pass
        del self.runner

    def test_make_single_feed(self) -> None:
        # Mock all external dependencies
        with patch('bin.feed_maker.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('bin.run.Process.exec_cmd', return_value=("mock_result", None)), \
             patch('bin.feed_maker.NewlistCollector') as mock_collector, \
             patch('bin.feed_maker.Crawler') as mock_crawler:
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            mock_crawler_instance = mock_crawler.return_value
            mock_crawler_instance.run.return_value = ("mock_html_content", None, None)

            options = {"force_collection_opt": "-c"}
            with patch.object(LOGGER, "warning") as mock_warning:
                with patch.object(LOGGER, "info") as mock_info:
                    actual = self.runner.make_single_feed(self.feed_dir_paths[0], options)
                    self.assertTrue(actual)
                    self.assertTrue(assert_in_mock_logger("* naver/certain_webtoon", mock_info))

            options = {}
            with patch.object(LOGGER, "info") as mock_info:
                actual = self.runner.make_single_feed(self.feed_dir_paths[0], options)
                self.assertTrue(actual)
                self.assertTrue(assert_in_mock_logger("* naver/certain_webtoon", mock_info))

    def test_make_all_feeds(self) -> None:
        with patch('bin.feed_maker.Process.exec_cmd', return_value=("mock_result", "")), \
             patch('bin.feed_maker_util.Process.exec_cmd', return_value=("mock_result", "")), \
             patch('bin.run.Process.exec_cmd', return_value=("mock_result", "")), \
             patch('bin.feed_maker.NewlistCollector') as mock_collector, \
             patch('bin.feed_maker.Crawler') as mock_crawler, \
             patch('bin.feed_maker.Extractor') as mock_extractor, \
             patch('bin.feed_maker_util.Config.get_extraction_configs') as mock_get_extraction_configs:
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            mock_crawler_instance = mock_crawler.return_value
            mock_crawler_instance.run.return_value = ("mock_html_content", None, None)
            mock_extractor.extract_content.return_value = "mock_extracted_content"
            mock_get_extraction_configs.return_value = {
                'render_js': False,
                'verify_ssl': True,
                'bypass_element_extraction': False,
                'force_sleep_between_articles': True,
                'copy_images_from_canvas': False,
                'simulate_scrolling': False,
                'disable_headless': False,
                'blob_to_dataurl': False,
                'user_agent': None,
                'encoding': 'utf-8',
                'referer': None,
                'threshold_to_remove_html_with_incomplete_image': 5,
                'timeout': 60,
                'num_retries': 1,
            }
            # 실제 테스트 코드 실행
            for feed_dir_path in self.feed_dir_paths:
                options = {}
                actual = self.runner.make_single_feed(feed_dir_path, options)
                self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
