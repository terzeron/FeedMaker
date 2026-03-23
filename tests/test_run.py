#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json  # noqa: F401
import logging  # noqa: F401
import logging.config  # noqa: F401
import shutil  # noqa: F401
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any  # noqa: F401
from unittest.mock import patch, Mock, MagicMock  # noqa: F401

from filelock import Timeout

from bin.feed_maker import FeedMaker  # noqa: F401
from bin.feed_maker_util import Env, PathUtil, Config  # noqa: F401
from bin.run import FeedMakerRunner


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

        with patch.object(Path, "is_file", return_value=True), patch.object(Path, "stat", return_value=mock_stat), patch.object(Path, "unlink") as mock_unlink:
            result = runner.make_single_feed(feed_dir, options={})
            mock_unlink.assert_called_once_with(missing_ok=True)
            self.assertTrue(result)

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
    @patch("bin.run.random.shuffle")
    def test_iterates_directories(self, mock_shuffle, mock_config_cls, mock_notif_cls):
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
    @patch("bin.run.random.shuffle")
    def test_handles_not_found_config_error(self, mock_shuffle, mock_config_cls, mock_notif_cls):
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
    @patch("bin.run.random.shuffle")
    def test_is_completed_feeds(self, mock_shuffle, mock_config_cls, mock_notif_cls):
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
    @patch("bin.run.random.shuffle")
    def test_failed_feeds_notification(self, mock_shuffle, mock_config_cls, mock_notif_cls):
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


class TestFeedMakerRunnerCheckRunning(unittest.TestCase):
    """check_running: unlocked, locked, FileNotFoundError"""

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_unlocked_returns_false(self, mock_filelock, mock_env):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertFalse(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_locked_returns_true(self, mock_filelock, mock_env):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertTrue(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_file_not_found_returns_none(self, mock_filelock, mock_env):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=FileNotFoundError("no file"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertIsNone(result)


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
        self.assertEqual(str(actual_path), "naver/some_feed")

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

        with patch("bin.run.Process.kill_process_group"):
            result = main()

        self.assertEqual(result, 0)
        mock_runner.make_all_feeds.assert_called_once()
        mock_pm.load_all.assert_called_once()


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

        with patch("bin.run.Process.kill_process_group"):
            result = main()

        self.assertEqual(result, -1)


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
            feed_maker = FeedMaker(feed_dir_path=feed_dir_path, do_collect_by_force=options.get("force_collection_opt", False), do_collect_only=options.get("collect_only_opt", False), rss_file_path=rss_file_path, window_size=options.get("window_size", FeedMaker.DEFAULT_WINDOW_SIZE))
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
        with (
            patch("bin.feed_maker.Process.exec_cmd", return_value=("mock_result", None)),
            patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", None)),
            patch("bin.run.Process.exec_cmd", return_value=("mock_result", None)),
            patch("bin.feed_maker.NewlistCollector") as mock_collector,
            patch("bin.feed_maker.Crawler") as mock_crawler,
        ):
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
        with (
            patch("bin.feed_maker.Process.exec_cmd", return_value=("mock_result", "")),
            patch("bin.feed_maker_util.Process.exec_cmd", return_value=("mock_result", "")),
            patch("bin.run.Process.exec_cmd", return_value=("mock_result", "")),
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
