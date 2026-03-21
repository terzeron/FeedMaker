#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
from unittest.mock import patch, MagicMock


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


if __name__ == "__main__":
    unittest.main()
