#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from filelock import Timeout


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
        from bin.run import FeedMakerRunner

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock()
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertFalse(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_locked_returns_true(self, mock_filelock, mock_env):
        from bin.run import FeedMakerRunner

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=Timeout("/tmp/lock"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertTrue(result)

    @patch("bin.run.Env.get", return_value="/tmp/fm_work")
    @patch("bin.run.FileLock")
    def test_file_not_found_returns_none(self, mock_filelock, mock_env):
        from bin.run import FeedMakerRunner

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(side_effect=FileNotFoundError("no file"))
        mock_ctx.__exit__ = MagicMock(return_value=True)
        mock_filelock.return_value = mock_ctx

        result = FeedMakerRunner.check_running("group", "feed")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
