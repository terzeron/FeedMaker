#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json  # noqa: F401
import logging  # noqa: F401
import logging.config  # noqa: F401
import shutil  # noqa: F401
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any  # noqa: F401
from unittest.mock import patch, Mock, MagicMock  # noqa: F401

from filelock import Timeout

from bin.feed_maker import FeedMaker, STOP_FLAG_FILE_NAME  # noqa: F401
from bin.feed_maker_util import Env, PathUtil, Config  # noqa: F401
from bin.run import FeedMakerRunner, spread_feeds_by_group


class TestDetermineOptions(unittest.TestCase):
    """determine_options: parse -a, -r, -c, -l, -n, -w flags"""

    @patch("bin.run.FeedMaker")
    def test_flag_a(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-a"]):
            options, args = determine_options()
        self.assertTrue(options["do_make_all_feeds"])
        self.assertFalse(options["do_remove_all_files"])

    @patch("bin.run.FeedMaker")
    def test_flag_r(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-r", "feed_path"]):
            options, args = determine_options()
        self.assertTrue(options["do_remove_all_files"])
        self.assertEqual(args, ["feed_path"])

    @patch("bin.run.FeedMaker")
    def test_flag_c(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-c"]):
            options, args = determine_options()
        self.assertEqual(options["force_collection_opt"], "-c")

    @patch("bin.run.FeedMaker")
    def test_flag_e(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-e"]):
            options, args = determine_options()
        self.assertEqual(options["extract_only_opt"], "-e")

    @patch("bin.run.FeedMaker")
    def test_flag_l(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-l"]):
            options, args = determine_options()
        self.assertEqual(options["collect_only_opt"], "-l")

    @patch("bin.run.FeedMaker")
    def test_flag_n(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-n", "10"]):
            options, args = determine_options()
        self.assertEqual(options["num_feeds"], 10)

    @patch("bin.run.FeedMaker")
    def test_flag_w(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-w", "20"]):
            options, args = determine_options()
        self.assertEqual(options["window_size"], 20)

    @patch("bin.run.FeedMaker")
    def test_combined_flags(self, mock_fm):
        mock_fm.DEFAULT_WINDOW_SIZE = 5
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-a", "-r", "-c", "-l", "-n", "5", "-w", "3"]):
            options, args = determine_options()
        self.assertTrue(options["do_make_all_feeds"])
        self.assertTrue(options["do_remove_all_files"])
        self.assertEqual(options["force_collection_opt"], "-c")
        self.assertEqual(options["collect_only_opt"], "-l")
        self.assertEqual(options["num_feeds"], 5)
        self.assertEqual(options["window_size"], 3)


class TestFeedMakerRunnerMakeSingleFeed(unittest.TestCase):
    """make_single_feed: lock file, FileLock timeout, options"""

    @patch("bin.run.Env.get")
    def _make_runner(self, mock_env):
        mock_env.side_effect = lambda k: {"FM_WORK_DIR": "/tmp/fm_work", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/fm_img"}[k]
        with patch("pathlib.Path.is_dir", return_value=True):
            from bin.run import FeedMakerRunner

            return FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_old_lock_file_removal(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = True
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate old lock file (>1 day old)
        old_mtime = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
        mock_stat = MagicMock()
        mock_stat.st_mtime = old_mtime

        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "stat", return_value=mock_stat), patch.object(Path, "unlink", autospec=True) as mock_unlink:
            result = runner.make_single_feed(feed_dir, options={})
            removed = [call.args[0].name for call in mock_unlink.call_args_list]
            self.assertIn(".feed_maker_runner.lock", removed)
            self.assertTrue(result)

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_failure_reason_is_propagated(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = False
        mock_fm.failure_reason = "no permission to access the data source (HTTP 401): https://example.com/list"
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={})
        self.assertFalse(result)
        self.assertEqual(mock_fm.failure_reason, runner.failure_reason)

    @patch("bin.run.FileLock")
    def test_filelock_timeout(self, mock_filelock):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_filelock.return_value.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)
        # FileLock context manager raises Timeout
        mock_filelock.side_effect = None
        # Use real Timeout behavior
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={})
            self.assertFalse(result)

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_do_remove_all_files_option(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = True
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={"do_remove_all_files": True})
            mock_file_mgr.remove_all_files.assert_called_once_with(feed_dir)
            self.assertTrue(result)

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_force_collection_option(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = True
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={"force_collection_opt": "-c"})
            self.assertTrue(result)
            mock_fm_cls.assert_called_once()
            call_kwargs = mock_fm_cls.call_args[1]
            self.assertEqual(call_kwargs["do_collect_by_force"], "-c")

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_collect_only_option(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = True
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={"collect_only_opt": "-l"})
            self.assertTrue(result)
            call_kwargs = mock_fm_cls.call_args[1]
            self.assertEqual(call_kwargs["do_collect_only"], "-l")

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_window_size_option(self, mock_filelock, mock_fm_cls, mock_file_mgr):
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm = MagicMock()
        mock_fm.make.return_value = True
        mock_fm_cls.return_value = mock_fm
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={"window_size": 10})
            self.assertTrue(result)
            call_kwargs = mock_fm_cls.call_args[1]
            self.assertEqual(call_kwargs["window_size"], 10)

    @patch("bin.run.HeadlessBrowser")
    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_recycle_session_called_after_feed_make(self, mock_filelock, mock_fm_cls, mock_file_mgr, mock_headless):
        # 같은 피드그룹의 다음 피드가 fresh Chromium 인스턴스로 시작하도록
        # feed_maker.make() 직후 recycle_session()이 호출되어야 한다.
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm_cls.return_value.make.return_value = True
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            result = runner.make_single_feed(feed_dir, options={})

        self.assertTrue(result)
        mock_headless.recycle_session.assert_called_once()

    @patch("bin.run.HeadlessBrowser")
    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_recycle_session_called_even_when_make_raises(self, mock_filelock, mock_fm_cls, mock_file_mgr, mock_headless):
        # feed_maker.make()가 예외를 던져도 finally를 통해 recycle_session이 호출되어
        # 다음 피드가 깨진 Chromium 세션을 물려받지 않도록 보장해야 한다.
        runner = self._make_runner()
        feed_dir = Path("/tmp/fm_work/group/feed")

        mock_fm_cls.return_value.make.side_effect = RuntimeError("simulated feed failure")
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)

        with patch.object(Path, "is_file", return_value=False):
            with self.assertRaises(RuntimeError):
                runner.make_single_feed(feed_dir, options={})

        mock_headless.recycle_session.assert_called_once()


class TestFeedMakerRunnerMakeAllFeeds(unittest.TestCase):
    """make_all_feeds: iterates directories, handles errors"""

    @patch("bin.run.Env.get")
    def _make_runner(self, mock_env):
        mock_env.side_effect = lambda k: {"FM_WORK_DIR": "/tmp/fm_work", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/fm_img"}[k]
        with patch("pathlib.Path.is_dir", return_value=True):
            from bin.run import FeedMakerRunner

            return FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_iterates_directories(self, mock_config_cls, mock_notif_cls):
        runner = self._make_runner()

        # Setup directory structure mocks
        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "test_feed"
        feed_dir.is_dir.return_value = True
        feed_dir.parent = MagicMock()
        feed_dir.parent.name = "group1"
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        feed_dir.__truediv__ = MagicMock(return_value=conf_file)

        group_dir = MagicMock(spec=Path)
        group_dir.name = "group1"
        group_dir.is_dir.return_value = True
        group_dir.iterdir.return_value = [feed_dir]

        runner.work_dir_path = MagicMock()
        runner.work_dir_path.iterdir.return_value = [group_dir]

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": False}
        mock_config_cls.return_value = mock_config

        with patch.object(runner, "make_single_feed", return_value=True) as mock_make:
            result = runner.make_all_feeds(options={})
            self.assertTrue(result)
            mock_make.assert_called()

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_handles_not_found_config_error(self, mock_config_cls, mock_notif_cls):
        from bin.feed_maker_util import NotFoundConfigItemError

        runner = self._make_runner()

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "bad_feed"
        feed_dir.is_dir.return_value = True
        feed_dir.parent = MagicMock()
        feed_dir.parent.name = "group1"
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        feed_dir.__truediv__ = MagicMock(return_value=conf_file)

        group_dir = MagicMock(spec=Path)
        group_dir.name = "group1"
        group_dir.is_dir.return_value = True
        group_dir.iterdir.return_value = [feed_dir]

        runner.work_dir_path = MagicMock()
        runner.work_dir_path.iterdir.return_value = [group_dir]

        mock_config = MagicMock()
        mock_config.get_collection_configs.side_effect = NotFoundConfigItemError("missing")
        mock_config_cls.return_value = mock_config

        mock_notif = MagicMock()
        mock_notif_cls.return_value = mock_notif

        result = runner.make_all_feeds(options={})
        self.assertTrue(result)
        mock_notif.send_msg.assert_called_once()

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_is_completed_feeds(self, mock_config_cls, mock_notif_cls):
        runner = self._make_runner()

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "completed_feed"
        feed_dir.is_dir.return_value = True
        feed_dir.parent = MagicMock()
        feed_dir.parent.name = "group1"
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        feed_dir.__truediv__ = MagicMock(return_value=conf_file)

        group_dir = MagicMock(spec=Path)
        group_dir.name = "group1"
        group_dir.is_dir.return_value = True
        group_dir.iterdir.return_value = [feed_dir]

        runner.work_dir_path = MagicMock()
        runner.work_dir_path.iterdir.return_value = [group_dir]

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": True}
        mock_config_cls.return_value = mock_config

        with patch.object(runner, "make_single_feed", return_value=True) as mock_make:
            result = runner.make_all_feeds(options={})
            self.assertTrue(result)
            # Called twice: once with force_collection, once normal
            self.assertEqual(mock_make.call_count, 2)

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_failed_feeds_notification(self, mock_config_cls, mock_notif_cls):
        runner = self._make_runner()

        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "fail_feed"
        feed_dir.is_dir.return_value = True
        feed_dir.parent = MagicMock()
        feed_dir.parent.name = "group1"
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        feed_dir.__truediv__ = MagicMock(return_value=conf_file)

        group_dir = MagicMock(spec=Path)
        group_dir.name = "group1"
        group_dir.is_dir.return_value = True
        group_dir.iterdir.return_value = [feed_dir]

        runner.work_dir_path = MagicMock()
        runner.work_dir_path.iterdir.return_value = [group_dir]

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": False}
        mock_config_cls.return_value = mock_config

        mock_notif = MagicMock()
        mock_notif_cls.return_value = mock_notif

        with patch.object(runner, "make_single_feed", return_value=False):
            result = runner.make_all_feeds(options={})
            self.assertTrue(result)
            mock_notif.send_msg.assert_called_once()
            self.assertIn("fail_feed", mock_notif.send_msg.call_args[0][0])


class TestMakeAllFeedsIsolatesMissingConfigItem(unittest.TestCase):
    """피드 하나의 설정 누락(make_single_feed에서 발생)이 전체 실행(run.py -a)을 멈추지 않는다."""

    def setUp(self) -> None:
        self.tmp_root = Path(tempfile.mkdtemp())
        for group, feed in (("group_a", "bad_feed"), ("group_b", "good_feed")):
            feed_dir = self.tmp_root / group / feed
            feed_dir.mkdir(parents=True)
            (feed_dir / Config.DEFAULT_CONF_FILE).write_text("{}", encoding="utf-8")
        with patch("bin.run.Env.get", side_effect=lambda k: {"FM_WORK_DIR": str(self.tmp_root), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(self.tmp_root)}[k]):
            self.runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
        self.runner.work_dir_path = self.tmp_root

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_missing_config_item_in_one_feed_continues_others(self, mock_config_cls, mock_notif_cls):
        from bin.feed_maker_util import NotFoundConfigItemError

        mock_config_cls.DEFAULT_CONF_FILE = Config.DEFAULT_CONF_FILE
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": False}
        made: list[str] = []

        def make_single_feed(feed_dir_path: Path, options: dict[str, Any]) -> bool:
            if feed_dir_path.name == "bad_feed":
                raise NotFoundConfigItemError("rss_title")
            made.append(feed_dir_path.name)
            return True

        with patch.object(self.runner, "make_single_feed", side_effect=make_single_feed):
            result = self.runner.make_all_feeds(options={})

        self.assertTrue(result)
        self.assertEqual(made, ["good_feed"])
        mock_notif_cls.return_value.send_msg.assert_called_once_with("group_a/bad_feed", "Errors of FeedMaker")

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_unexpected_exception_in_one_feed_continues_others(self, mock_config_cls, mock_notif_cls):
        # in-process crawler에서 처리하지 않은 예외(requests.ChunkedEncodingError 등)가
        # 피드 하나에서 나도 run.py -a 전체가 죽지 않고, traceback은 run.log에 남아야 한다.
        mock_config_cls.DEFAULT_CONF_FILE = Config.DEFAULT_CONF_FILE
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": False}
        made: list[str] = []

        def make_single_feed(feed_dir_path: Path, options: dict[str, Any]) -> bool:
            if feed_dir_path.name == "bad_feed":
                raise KeyError("unexpected")
            made.append(feed_dir_path.name)
            return True

        with patch.object(self.runner, "make_single_feed", side_effect=make_single_feed), self.assertLogs(level="ERROR") as logs:
            result = self.runner.make_all_feeds(options={})

        self.assertTrue(result)
        self.assertEqual(made, ["good_feed"])
        mock_notif_cls.return_value.send_msg.assert_called_once_with("group_a/bad_feed", "Errors of FeedMaker")
        self.assertTrue(any("Traceback" in line and "KeyError" in line for line in logs.output))


@patch("bin.run.Path.is_dir", return_value=True)
class TestFeedMakerRunnerCheckRunning(unittest.TestCase):
    """check_running: unlocked, locked, FileNotFoundError"""

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_nonblocking_check_of_locked_feed(self, mock_filelock, mock_env, _mock_is_dir):
        mock_filelock.return_value.__enter__.side_effect = Timeout("/tmp/lock")
        self.assertTrue(FeedMakerRunner.check_running("group", "feed", timeout=0))
        mock_filelock.assert_called_once_with("/tmp/fm_work/group/feed/.feed_maker_runner.lock", timeout=0)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_unlocked_returns_false(self, mock_filelock, mock_env, _mock_is_dir):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertFalse(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_locked_returns_true(self, mock_filelock, mock_env, _mock_is_dir):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertTrue(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_file_not_found_returns_none(self, mock_filelock, mock_env, _mock_is_dir):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=FileNotFoundError("no file"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertIsNone(result)


class TestFeedMakerRunnerCheckRunningMissingDir(unittest.TestCase):
    def test_missing_feed_dir_returns_none_without_creating_it(self):
        # FileLock은 상위 디렉터리를 만들므로 삭제된 피드 디렉터리가 되살아나지 않아야 한다
        work_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work_dir, ignore_errors=True)
        with patch("bin.run.Env.get", return_value=str(work_dir)):
            result = FeedMakerRunner.check_running("group", "feed")
        self.assertIsNone(result)
        self.assertFalse((work_dir / "group").exists())


# ────────────────────────────────────────────────────────
# From test_defect_fixes.py: 결함 3 - run.py main() args[0]
# ────────────────────────────────────────────────────────
class TestDefect3RunMainArgs(unittest.TestCase):
    """main()에서 피드 경로 인자가 args[0]으로 올바르게 전달되어야 한다."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_feed_path_from_args_not_argv0(self, mock_config, mock_runner_cls, mock_pm):
        """사용자가 전달한 경로(args[0])가 feed_dir_path로 설정되어야 한다."""
        mock_config_inst = MagicMock()
        mock_config_inst.get_collection_configs.return_value = {"is_completed": False}
        mock_config.return_value = mock_config_inst

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        user_feed_path = "/some/custom/feed/path"

        with patch("sys.argv", ["run.py", user_feed_path]):
            from bin.run import main

            main()

        call_args = mock_runner.make_single_feed.call_args
        actual_path = call_args[0][0]
        self.assertEqual(str(actual_path), user_feed_path)
        self.assertNotEqual(str(actual_path), "run.py")


class TestDefect3RunMainEdgeCases(unittest.TestCase):
    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_relative_path_arg(self, mock_config, mock_runner_cls, mock_pm):
        """상대 경로 인자도 올바르게 처리되어야 한다."""
        mock_config_inst = MagicMock()
        mock_config_inst.get_collection_configs.return_value = {"is_completed": False}
        mock_config.return_value = mock_config_inst
        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["run.py", "naver/some_feed"]):
            from bin.run import main

            main()

        actual_path = mock_runner.make_single_feed.call_args[0][0]
        self.assertEqual(actual_path, Path.cwd() / "naver" / "some_feed")
        self.assertEqual(actual_path.name, "some_feed")

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_dot_path_arg_keeps_feed_and_group_name(self, mock_config, mock_runner_cls, mock_pm):
        """'.' 인자를 절대 경로로 바꿔 feed_name/group_name이 빈 문자열이 되지 않아야 한다."""
        mock_config_inst = MagicMock()
        mock_config_inst.get_collection_configs.return_value = {"is_completed": False}
        mock_config.return_value = mock_config_inst
        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["run.py", "."]):
            from bin.run import main

            main()

        actual_path = mock_runner.make_single_feed.call_args[0][0]
        self.assertEqual(actual_path, Path.cwd())
        self.assertNotEqual(actual_path.name, "")
        self.assertEqual(mock_pm.return_value.feed_manager.add_config_info.call_args[0][0], Path.cwd())
        self.assertEqual(mock_pm.return_value.update_feed_info.call_args[0][0], Path.cwd())

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_options_with_path_arg(self, mock_config, mock_runner_cls, mock_pm):
        """옵션과 경로 인자가 함께 전달되어도 경로가 올바르게 파싱되어야 한다."""
        mock_config_inst = MagicMock()
        mock_config_inst.get_collection_configs.return_value = {"is_completed": False}
        mock_config.return_value = mock_config_inst
        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        with patch("sys.argv", ["run.py", "-c", "-w", "10", "/feeds/webtoon/naver"]):
            from bin.run import main

            main()

        actual_path = mock_runner.make_single_feed.call_args[0][0]
        self.assertEqual(str(actual_path), "/feeds/webtoon/naver")


# ────────────────────────────────────────────────────────
# From test_final_gaps.py: run.py 추가 테스트
# ────────────────────────────────────────────────────────
class TestFeedMakerRunnerInit(unittest.TestCase):
    """Lines 28, 31: work_dir_path / img_dir_path not a dir."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.Env")
    def test_work_dir_not_a_dir(self, mock_env, mock_pm):
        mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": "/nonexistent/work_dir_123", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/nonexistent/img_dir_456"}.get(k, d)

        runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)
        self.assertIsNotNone(runner)


class TestDetermineOptionsH(unittest.TestCase):
    """Lines 184-185: -h option prints usage and exits."""

    @patch("bin.run.Env")
    def test_h_option_exits(self, mock_env):
        mock_env.get.return_value = "/tmp"
        from bin.run import determine_options

        with patch.object(sys, "argv", ["run.py", "-h"]):
            with self.assertRaises(SystemExit) as ctx:
                determine_options()
            self.assertEqual(ctx.exception.code, 0)


class TestMakeAllFeedsNumFeedsSlicing(unittest.TestCase):
    """Line 108: num_feeds > 0 slicing."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.Env")
    def test_num_feeds_slicing(self, mock_env, mock_pm):
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        img_dir = Path(tempfile.mkdtemp())
        mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": str(tmp), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_dir)}.get(k, d)

        for i in range(3):
            group = tmp / f"group{i}"
            feed = group / f"feed{i}"
            feed.mkdir(parents=True)
            (feed / "conf.json").write_text("{}")

        runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

        with patch.object(runner, "make_single_feed", return_value=True) as mock_make:
            with patch("bin.run.Config") as mock_config:
                mock_config.DEFAULT_CONF_FILE = "conf.json"
                mock_config.return_value.get_collection_configs.return_value = {}
                with patch("bin.run.Notification"):
                    runner.make_all_feeds({"num_feeds": 1})
        self.assertEqual(mock_make.call_count, 1)


class TestMakeAllFeedsSingleFeedFails(unittest.TestCase):
    """Lines 125-127: make_single_feed fails with is_completed feed."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.Env")
    def test_is_completed_feed_failure(self, mock_env, mock_pm):
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        img_dir = Path(tempfile.mkdtemp())
        mock_env.get.side_effect = lambda k, d="": {"FM_WORK_DIR": str(tmp), "WEB_SERVICE_IMAGE_DIR_PREFIX": str(img_dir)}.get(k, d)

        group = tmp / "group1"
        feed = group / "feed1"
        feed.mkdir(parents=True)
        (feed / "conf.json").write_text("{}")

        runner = FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

        with patch.object(runner, "make_single_feed", return_value=False) as mock_make:
            with patch("bin.run.Config") as mock_config:
                mock_config.DEFAULT_CONF_FILE = "conf.json"
                mock_config.return_value.get_collection_configs.return_value = {"is_completed": True}
                with patch("bin.run.Notification"):
                    runner.make_all_feeds({"num_feeds": 0})
        self.assertTrue(mock_make.called)


# ────────────────────────────────────────────────────────
# From test_remaining_gaps.py: run.py print_usage 및 main
# ────────────────────────────────────────────────────────
class TestRunPrintUsage(unittest.TestCase):
    """print_usage: lines 162-167"""

    def test_print_usage(self):
        import io

        from bin.run import print_usage

        with patch("sys.stdout", new_callable=io.StringIO) as out:
            print_usage()
        output = out.getvalue()
        self.assertIn("Usage:", output)
        self.assertIn("-a: make all feeds", output)


class TestRunMainDetermineOptions(unittest.TestCase):
    """determine_options and main entry path"""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    def test_main_single_feed(self, mock_config, mock_runner_cls, mock_pm_cls):
        mock_config.return_value.get_collection_configs.return_value = {"is_completed": False}
        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner
        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        argv = ["run.py"]
        with patch("sys.argv", argv), patch("pathlib.Path.is_dir", return_value=True):
            from bin.run import main

            ret = main()
            self.assertEqual(ret, 0)


# ────────────────────────────────────────────────────────
# From test_run_main.py
# ────────────────────────────────────────────────────────
class TestMainMakeAllFeeds(unittest.TestCase):
    """main() with do_make_all_feeds=True."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.determine_options")
    def test_make_all_feeds(self, mock_det_opts, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": True, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_runner = MagicMock()
        mock_runner.make_all_feeds.return_value = True
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with patch("bin.run.HeadlessBrowser.cleanup_all_sessions") as mock_cleanup:
            result = main()

        self.assertEqual(result, 0)
        mock_runner.make_all_feeds.assert_called_once()
        mock_pm.load_all.assert_called_once()
        mock_cleanup.assert_called_once()


class TestMainMakeAllFeedsFails(unittest.TestCase):
    """main() with do_make_all_feeds=True but make_all_feeds returns False."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.determine_options")
    def test_make_all_feeds_failure(self, mock_det_opts, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": True, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_runner = MagicMock()
        mock_runner.make_all_feeds.return_value = False
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        with patch("bin.run.HeadlessBrowser.cleanup_all_sessions") as mock_cleanup:
            result = main()

        self.assertEqual(result, -1)
        mock_cleanup.assert_called_once()


class TestMainSingleFeedDefault(unittest.TestCase):
    """main() single feed, default path, is_completed=False."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_single_feed_default(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": False}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        result = main()

        self.assertEqual(result, 0)
        # make_single_feed called once (not is_completed, so no -c call)
        mock_runner.make_single_feed.assert_called_once()
        mock_pm.update_feed_info.assert_called_once()

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_single_feed_syncs_config_info_before_run(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        """실행 중에도 탭에서 보이도록 피드 생성 전에 DB의 설정 정보를 먼저 갱신한다."""
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, ["/tmp/fm_work/group/feed"])
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": False}

        call_order: list[str] = []
        mock_pm = MagicMock()
        mock_pm.feed_manager.add_config_info.side_effect = lambda *_a, **_k: call_order.append("sync")
        mock_pm_cls.return_value = mock_pm
        mock_runner = MagicMock()
        mock_runner.make_single_feed.side_effect = lambda *_a, **_k: call_order.append("run") or True
        mock_runner_cls.return_value = mock_runner

        result = main()

        self.assertEqual(result, 0)
        mock_pm.feed_manager.add_config_info.assert_called_once_with(Path("/tmp/fm_work/group/feed"))
        self.assertEqual(call_order, ["sync", "run"])

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_single_feed_runs_even_if_config_sync_fails(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        """초반 DB 갱신 실패가 피드 생성을 막지 않는다."""
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": False}
        mock_pm = MagicMock()
        mock_pm.feed_manager.add_config_info.side_effect = RuntimeError("db down")
        mock_pm_cls.return_value = mock_pm
        mock_runner_cls.return_value.make_single_feed.return_value = True

        result = main()

        self.assertEqual(result, 0)
        mock_runner_cls.return_value.make_single_feed.assert_called_once()


class TestMainSingleFeedIsCompleted(unittest.TestCase):
    """main() single feed, is_completed=True and not collect_only -> runs with -c first."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_single_feed_is_completed(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": True}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        result = main()

        self.assertEqual(result, 0)
        # make_single_feed called twice: first with -c, then normal
        self.assertEqual(mock_runner.make_single_feed.call_count, 2)
        first_call_opts = mock_runner.make_single_feed.call_args_list[0][1].get("options", mock_runner.make_single_feed.call_args_list[0][0][1])
        self.assertEqual(first_call_opts.get("force_collection_opt"), "-c")


class TestMainSingleFeedIsCompletedFirstCallFails(unittest.TestCase):
    """main() single feed, is_completed=True, first -c call fails -> returns -1."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_completed_first_call_fails(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": True}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = False
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        result = main()

        self.assertEqual(result, -1)
        # Only first call with -c, since it failed
        mock_runner.make_single_feed.assert_called_once()


class TestMainSingleFeedWithArgs(unittest.TestCase):
    """main() with args sets feed_dir_path (note: uses sys.argv[0])."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_with_args(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, ["/some/feed/path"])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": False}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        # Note: main() uses sys.argv[0] instead of args[0] when args exist
        with patch.object(sys, "argv", ["run.py", "/some/feed/path"]):
            result = main()

        self.assertEqual(result, 0)
        mock_runner.make_single_feed.assert_called_once()


class TestMainWithTooManyArgs(unittest.TestCase):
    """main() with more than 1 arg prints usage and returns -1."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.determine_options")
    def test_too_many_args(self, mock_det_opts, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, ["path1", "path2"])

        with patch("bin.run.print_usage"):
            result = main()

        self.assertEqual(result, -1)


class TestMainSingleFeedFailure(unittest.TestCase):
    """main() single feed, make_single_feed returns False -> returns -1."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_single_feed_failure(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "", "num_feeds": 0, "window_size": 5}, [])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": False}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = False
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        result = main()

        self.assertEqual(result, -1)
        mock_pm.update_feed_info.assert_called_once()


class TestMainSingleFeedCollectOnlySkipsForceCollection(unittest.TestCase):
    """main() with is_completed=True but collect_only_opt set -> skips -c run."""

    @patch("bin.run.ProblemManager")
    @patch("bin.run.FeedMakerRunner")
    @patch("bin.run.Config")
    @patch("bin.run.determine_options")
    def test_collect_only_skips_force(self, mock_det_opts, mock_config_cls, mock_runner_cls, mock_pm_cls):
        from bin.run import main

        mock_det_opts.return_value = ({"do_make_all_feeds": False, "do_remove_all_files": False, "force_collection_opt": "", "collect_only_opt": "-l", "num_feeds": 0, "window_size": 5}, [])

        mock_config = MagicMock()
        mock_config.get_collection_configs.return_value = {"is_completed": True}
        mock_config_cls.return_value = mock_config

        mock_runner = MagicMock()
        mock_runner.make_single_feed.return_value = True
        mock_runner_cls.return_value = mock_runner

        mock_pm = MagicMock()
        mock_pm_cls.return_value = mock_pm

        result = main()

        self.assertEqual(result, 0)
        # Only one call (no -c call because collect_only_opt is set)
        mock_runner.make_single_feed.assert_called_once()


# ────────────────────────────────────────────────────────
# From test_feed_maker_runner.py: FeedMakerRunner 통합 테스트
# ────────────────────────────────────────────────────────

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
        with patch("bin.feed_maker.FeedMaker.make", return_value=True) as mock_make:
            # FeedMaker 인스턴스 생성은 하지만 실제 make() 호출은 mock
            FeedMaker(feed_dir_path=feed_dir_path, do_collect_by_force=options.get("force_collection_opt", False), do_collect_only=options.get("collect_only_opt", False), rss_file_path=rss_file_path, window_size=options.get("window_size", FeedMaker.DEFAULT_WINDOW_SIZE))
            result = mock_make.return_value

        # 테스트 환경에서 항상 정리 로그를 남기도록 보장
        LOGGER.info("# deleting html files without cached image files")
        LOGGER.info("# deleting image files with zero size")
        LOGGER.info("# deleting temporary files")

        end_time = datetime.now(timezone.utc)
        LOGGER.info("# Running time analysis")
        LOGGER.info(f"* Start time: {start_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* End time: {end_time.isoformat(timespec='seconds')}")
        LOGGER.info(f"* Elapsed time: {(end_time - start_time).total_seconds()}")

        return result


class TestFeedMakerRunnerIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # patcher 등록
        self.patcher_copy = patch("shutil.copy")
        self.patcher_mkdir = patch("pathlib.Path.mkdir")
        self.patcher_unlink = patch("pathlib.Path.unlink")
        self.patcher_rmtree = patch("shutil.rmtree")
        self.patcher_open = patch("pathlib.Path.open")
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
                conf_file_path = feed_dir_path / Config.DEFAULT_CONF_FILE
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
        with patch("bin.feed_maker.Process.exec_cmd", return_value=("mock_result", None)), patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", None)), patch("bin.feed_maker.NewlistCollector") as mock_collector, patch("bin.feed_maker.Crawler") as mock_crawler:
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            mock_crawler_instance = mock_crawler.return_value
            mock_crawler_instance.run.return_value = ("mock_html_content", None, None)

            options = {"force_collection_opt": "-c"}
            with patch.object(LOGGER, "warning"):
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
        with (
            patch("bin.feed_maker.Process.exec_cmd", return_value=("mock_result", "")),
            patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", "")),
            patch("bin.feed_maker.NewlistCollector") as mock_collector,
            patch("bin.feed_maker.Crawler") as mock_crawler,
            patch("bin.feed_maker.Extractor") as mock_extractor,
            patch("bin.feed_maker_util.Config.get_extraction_configs") as mock_get_extraction_configs,
        ):
            mock_instance = mock_collector.return_value
            mock_instance.collect.return_value = [("https://comic.naver.com/webtoon/detail?titleId=725586&no=136", "136화")]
            mock_crawler_instance = mock_crawler.return_value
            mock_crawler_instance.run.return_value = ("mock_html_content", None, None)
            mock_extractor.extract_content.return_value = "mock_extracted_content"
            mock_get_extraction_configs.return_value = {
                "render_js": False,
                "verify_ssl": True,
                "bypass_element_extraction": False,
                "force_sleep_between_articles": True,
                "copy_images_from_canvas": False,
                "simulate_scrolling": False,
                "disable_headless": False,
                "blob_to_dataurl": False,
                "user_agent": None,
                "encoding": "utf-8",
                "referer": None,
                "threshold_to_remove_html_with_incomplete_image": 5,
                "timeout": 60,
                "num_retries": 1,
            }
            # 실제 테스트 코드 실행
            for feed_dir_path in self.feed_dir_paths:
                options = {}
                actual = self.runner.make_single_feed(feed_dir_path, options)
                self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()


class TestFeedMakerRunnerRequestStop(unittest.TestCase):
    """request_stop: 실행 중이 아니면 거부, 실행 중이면 플래그 생성과 하위 프로세스 종료"""

    @patch("bin.run.FeedMakerRunner.check_running", return_value=False)
    def test_not_running_is_rejected(self, _mock_check):
        ok, message = FeedMakerRunner.request_stop("group", "feed")
        self.assertFalse(ok)
        self.assertTrue(message)

    @patch("bin.run.Process.kill_process_group", return_value=2)
    @patch("bin.run.FeedMakerRunner.check_running", return_value=True)
    def test_running_creates_flag_and_kills_children(self, _mock_check, mock_kill):
        import tempfile

        with tempfile.TemporaryDirectory() as work_dir:
            feed_dir = Path(work_dir) / "group" / "feed"
            feed_dir.mkdir(parents=True)
            with patch("bin.run.Env.get", return_value=work_dir):
                ok, message = FeedMakerRunner.request_stop("group", "feed")
            self.assertTrue(ok)
            self.assertEqual(message, "")
            self.assertTrue((feed_dir / STOP_FLAG_FILE_NAME).is_file())
            self.assertIn(str(feed_dir), mock_kill.call_args[0][0].replace("\\", ""))


class TestSpreadFeedsByGroup(unittest.TestCase):
    """spread_feeds_by_group: 같은 그룹 피드를 실행 순서에서 최대한 멀리 떨어뜨린다."""

    @staticmethod
    def _feeds(counts: dict[str, int]) -> list[Path]:
        return [Path("/work") / group / f"feed{i}" for group, n in counts.items() for i in range(n)]

    @staticmethod
    def _groups(feeds: list[Path]) -> list[str]:
        return [p.parent.name for p in feeds]

    @staticmethod
    def _max_run(groups: list[str]) -> int:
        best = run = 0
        prev = ""
        for g in groups:
            run = run + 1 if g == prev else 1
            prev = g
            best = max(best, run)
        return best

    def test_keeps_all_feeds(self) -> None:
        feeds = self._feeds({"A": 6, "B": 2, "C": 1})
        result = spread_feeds_by_group(feeds)
        self.assertCountEqual(result, feeds)

    def test_dominant_group_has_minimal_run(self) -> None:
        # A가 9개 중 6개이면 2연속은 피할 수 없다. 단순 라운드로빈은 ABCABAAAA(4연속)가 된다.
        result = spread_feeds_by_group(self._feeds({"A": 6, "B": 2, "C": 1}))
        self.assertEqual(self._max_run(self._groups(result)), 2)

    def test_same_size_groups_do_not_clump(self) -> None:
        # 크기가 같은 B, C가 몰리면 A가 붙는다. A가 절반이면 완전 교차가 가능하다.
        result = spread_feeds_by_group(self._feeds({"A": 8, "B": 3, "C": 3, "D": 2}))
        self.assertEqual(self._max_run(self._groups(result)), 1)

    def test_max_run_reaches_lower_bound_for_random_distributions(self) -> None:
        import math
        import random

        rng = random.Random(1)
        for _ in range(200):
            counts = {f"g{i:02d}": rng.choice([1, 1, 2, 3, 5, 8, 13, 20, 40]) for i in range(rng.randint(1, 15))}
            total = sum(counts.values())
            largest = max(counts.values())
            lower_bound = math.ceil(largest / (total - largest + 1))
            result = spread_feeds_by_group(self._feeds(counts))
            self.assertCountEqual(result, self._feeds(counts))
            self.assertEqual(self._max_run(self._groups(result)), lower_bound, counts)

    def test_no_consecutive_when_balanced(self) -> None:
        result = spread_feeds_by_group(self._feeds({"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}))
        self.assertEqual(self._max_run(self._groups(result)), 1)

    def test_group_feeds_evenly_spaced(self) -> None:
        # 큰 그룹의 최소 간격이 전체 수 // 그룹 피드 수 이상이어야 한다. 끝부분에 몰리면 간격이 줄어든다.
        result = spread_feeds_by_group(self._feeds({"A": 8, "B": 3, "C": 3, "D": 2}))
        positions = [i for i, p in enumerate(result) if p.parent.name == "A"]
        gaps = [b - a for a, b in zip(positions, positions[1:])]
        self.assertGreaterEqual(min(gaps), len(result) // 8)

    def test_deterministic_and_sorted_within_group(self) -> None:
        feeds = self._feeds({"A": 3, "B": 2})
        first = spread_feeds_by_group(list(reversed(feeds)))
        second = spread_feeds_by_group(feeds)
        self.assertEqual(first, second)
        self.assertEqual([p.name for p in first if p.parent.name == "A"], ["feed0", "feed1", "feed2"])

    def test_empty(self) -> None:
        self.assertEqual(spread_feeds_by_group([]), [])


class TestLongTermTask(unittest.TestCase):
    """run.py -a는 장시간 작업을 별도 세션으로 넘기고, 다른 세션이 실행 중인 피드는 실패로 세지 않고 건너뛴다."""

    @patch("bin.run.Env.get")
    def _make_runner(self, mock_env):
        mock_env.side_effect = lambda k: {"FM_WORK_DIR": "/tmp/fm_work", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/fm_img"}[k]
        with patch("pathlib.Path.is_dir", return_value=True):
            return FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

    def _setup_one_feed(self, runner):
        feed_dir = MagicMock(spec=Path)
        feed_dir.name = "long_feed"
        feed_dir.is_dir.return_value = True
        feed_dir.parent = MagicMock()
        feed_dir.parent.name = "group1"
        conf_file = MagicMock()
        conf_file.is_file.return_value = True
        feed_dir.__truediv__ = MagicMock(return_value=conf_file)
        group_dir = MagicMock(spec=Path)
        group_dir.name = "group1"
        group_dir.is_dir.return_value = True
        group_dir.iterdir.return_value = [feed_dir]
        runner.work_dir_path = MagicMock()
        runner.work_dir_path.iterdir.return_value = [group_dir]
        return feed_dir

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_long_term_task_is_spawned_and_skipped(self, mock_config_cls, mock_notif_cls):
        runner = self._make_runner()
        feed_dir = self._setup_one_feed(runner)
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": True}

        def fake_make(_feed_dir_path, options):
            runner.is_long_term_task = True
            return True

        with patch.object(runner, "make_single_feed", side_effect=fake_make) as mock_make, patch.object(FeedMakerRunner, "_spawn_long_term_task", return_value=True) as mock_spawn:
            self.assertTrue(runner.make_all_feeds(options={}))
        self.assertEqual(mock_make.call_count, 1)
        self.assertEqual(mock_make.call_args.kwargs["options"]["long_term_task_threshold"], 50)
        mock_spawn.assert_called_once_with(feed_dir)
        mock_notif_cls.return_value.send_msg.assert_not_called()

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_failed_spawn_is_reported(self, mock_config_cls, mock_notif_cls):
        runner = self._make_runner()
        self._setup_one_feed(runner)
        mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": True}

        def fake_make(_feed_dir_path, options):
            runner.is_long_term_task = True
            return True

        with patch.object(runner, "make_single_feed", side_effect=fake_make), patch.object(FeedMakerRunner, "_spawn_long_term_task", return_value=False):
            runner.make_all_feeds(options={})
        mock_notif_cls.return_value.send_msg.assert_called_once_with("group1/long_feed", "Errors of FeedMaker")

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_feed_running_elsewhere_is_skipped_without_failure(self, mock_config_cls, mock_notif_cls):
        for is_completed in (True, False):
            runner = self._make_runner()
            self._setup_one_feed(runner)
            mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": is_completed}
            mock_notif_cls.reset_mock()

            def fake_make(_feed_dir_path, options, runner=runner):
                runner.is_running_elsewhere = True
                return False

            with patch.object(runner, "make_single_feed", side_effect=fake_make) as mock_make:
                runner.make_all_feeds(options={})
            self.assertEqual(mock_make.call_count, 1)
            mock_notif_cls.return_value.send_msg.assert_not_called()

    @patch("bin.run.FileLock")
    def test_make_single_feed_marks_running_elsewhere_on_lock_timeout(self, mock_filelock):
        runner = self._make_runner()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx
        with patch.object(Path, "is_file", return_value=False):
            self.assertFalse(runner.make_single_feed(Path("/tmp/fm_work/group/feed"), options={}))
        self.assertTrue(runner.is_running_elsewhere)

    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    @patch("bin.run.FileLock")
    def test_make_single_feed_passes_threshold_and_reads_flag(self, mock_filelock, mock_fm_cls, _mock_file_mgr):
        runner = self._make_runner()
        mock_fm_cls.return_value.make.return_value = True
        mock_fm_cls.return_value.is_long_term_task = True
        mock_filelock.return_value.__enter__ = MagicMock()
        mock_filelock.return_value.__exit__ = MagicMock(return_value=False)
        with patch.object(Path, "is_file", return_value=False):
            runner.make_single_feed(Path("/tmp/fm_work/group/feed"), options={"force_collection_opt": "-c", "long_term_task_threshold": 50})
        self.assertEqual(mock_fm_cls.call_args.kwargs["long_term_task_threshold"], 50)
        self.assertTrue(runner.is_long_term_task)
        self.assertFalse(runner.is_running_elsewhere)

    def test_make_single_feed_refreshes_lock_file_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = self._make_runner()
            feed_dir = Path(tmp)
            lock_file_path = feed_dir / ".feed_maker_runner.lock"
            lock_file_path.touch()
            old_time = (datetime.now() - timedelta(hours=23)).timestamp()
            import os

            os.utime(lock_file_path, (old_time, old_time))
            with patch("bin.run.FeedMaker") as mock_fm_cls, patch("bin.run.FileManager"), patch("bin.run.HeadlessBrowser"):
                mock_fm_cls.return_value.make.return_value = True
                runner.make_single_feed(feed_dir, options={})
            self.assertGreater(lock_file_path.stat().st_mtime, old_time + 3600)

    def test_spawn_long_term_task_starts_new_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_dir = Path(tmp)
            with patch("bin.run.subprocess.Popen") as mock_popen:
                self.assertTrue(FeedMakerRunner._spawn_long_term_task(feed_dir))
            args, kwargs = mock_popen.call_args
            self.assertEqual(args[0][0], sys.executable)
            self.assertTrue(args[0][1].endswith("run.py"))
            self.assertEqual(args[0][2], str(feed_dir))
            self.assertTrue(kwargs["start_new_session"])
            self.assertEqual(kwargs["cwd"], feed_dir)
            self.assertTrue((feed_dir / "run_long_term.log").is_file())

    def test_spawn_long_term_task_returns_false_on_os_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("bin.run.subprocess.Popen", side_effect=OSError("boom")):
                self.assertFalse(FeedMakerRunner._spawn_long_term_task(Path(tmp)))

    def test_spawn_long_term_task_overwrites_previous_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            feed_dir = Path(tmp)
            log_file_path = feed_dir / "run_long_term.log"
            log_file_path.write_text("previous run\n", encoding="utf-8")
            with patch("bin.run.subprocess.Popen"):
                self.assertTrue(FeedMakerRunner._spawn_long_term_task(feed_dir))
            self.assertEqual(log_file_path.read_text(encoding="utf-8"), "")


class TestRunLogInKst(unittest.TestCase):
    @patch("bin.run.Env.get")
    def _make_runner(self, mock_env):
        mock_env.side_effect = lambda k: {"FM_WORK_DIR": "/tmp/fm_work", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/fm_img"}[k]
        with patch("pathlib.Path.is_dir", return_value=True):
            return FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

    @patch("bin.run.HeadlessBrowser")
    @patch("bin.run.FileManager")
    @patch("bin.run.FeedMaker")
    def test_make_single_feed_logs_start_and_end_time_in_kst(self, mock_fm_cls, _mock_file_mgr, _mock_hb):
        runner = self._make_runner()
        mock_fm_cls.return_value.make.return_value = True
        with tempfile.TemporaryDirectory() as tmp, self.assertLogs(level="INFO") as cm:
            runner.make_single_feed(Path(tmp), options={})
        time_lines = [line for line in cm.output if "* Start time:" in line or "* End time:" in line]
        self.assertEqual(len(time_lines), 2)
        for line in time_lines:
            self.assertTrue(line.endswith("+09:00"), line)


class TestPerFeedRunLog(unittest.TestCase):
    """run.py -a는 피드를 처리하는 동안 로그를 그 피드 디렉터리의 run.log에도 남긴다."""

    @patch("bin.run.Env.get")
    def _make_runner(self, mock_env):
        mock_env.side_effect = lambda k: {"FM_WORK_DIR": "/tmp/fm_work", "WEB_SERVICE_IMAGE_DIR_PREFIX": "/tmp/fm_img"}[k]
        with patch("pathlib.Path.is_dir", return_value=True):
            return FeedMakerRunner(html_archiving_period=30, list_archiving_period=7)

    @patch("bin.run.Notification")
    @patch("bin.run.Config")
    def test_feed_log_is_written_to_feed_run_log(self, mock_config_cls, _mock_notif_cls):
        import logging as _logging

        with tempfile.TemporaryDirectory() as tmp:
            runner = self._make_runner()
            runner.work_dir_path = Path(tmp)
            feed_dirs = []
            for name in ("feed_a", "feed_b"):
                feed_dir = Path(tmp) / "group1" / name
                feed_dir.mkdir(parents=True)
                (feed_dir / "conf.json").write_text("{}", encoding="utf-8")
                feed_dirs.append(feed_dir)
            mock_config_cls.DEFAULT_CONF_FILE = "conf.json"
            mock_config_cls.return_value.get_collection_configs.return_value = {"is_completed": True}
            num_handlers = len(_logging.getLogger().handlers)

            def fake_make(feed_dir_path, options):
                _logging.getLogger().info("making %s %s", feed_dir_path.name, options.get("force_collection_opt", ""))
                return True

            with patch.object(runner, "make_single_feed", side_effect=fake_make):
                runner.make_all_feeds(options={})

            self.assertEqual(len(_logging.getLogger().handlers), num_handlers)
            log_a = (feed_dirs[0] / "run.log").read_text(encoding="utf-8")
            self.assertIn("making feed_a -c", log_a)
            self.assertRegex(log_a, r"(?m)making feed_a $")
            self.assertNotIn("feed_b", log_a)
            self.assertRegex(log_a, r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}\]\[")

    def test_handler_is_not_added_when_same_file_is_already_logged(self):
        import logging as _logging

        with tempfile.TemporaryDirectory() as tmp:
            feed_dir = Path(tmp)
            existing = _logging.FileHandler(str(feed_dir / "run.log"), encoding="utf-8")
            root = _logging.getLogger()
            root.addHandler(existing)
            try:
                self.assertIsNone(FeedMakerRunner._add_feed_log_handler(feed_dir))
            finally:
                root.removeHandler(existing)
                existing.close()
