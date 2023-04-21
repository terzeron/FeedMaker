#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import unittest
import logging.config
from pathlib import Path
import shutil
from notification import Notification

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class NotificationTest(unittest.TestCase):
    def setUp(self):
        self.source_conf_dir_path = Path(os.environ["FEED_MAKER_HOME_DIR"]) / "test"
        self.target_conf_file_path = Path(os.environ["FEED_MAKER_HOME_DIR"]) / "bin" / "global_config.json"

    def tearDown(self):
        example_conf_file_path = Path(os.environ["FEED_MAKER_HOME_DIR"]) / "test" / "global_config.json.example"
        shutil.copy(example_conf_file_path, self.target_conf_file_path)
        del self.source_conf_dir_path
        del self.target_conf_file_path

    def test_send_msg(self):
        msg = "This is a message from python unittest"
        subject = "Notification test"
        notification = Notification()
        actual = notification.send_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_line_msg(self):
        temp_conf_file_path = self.source_conf_dir_path / "global_config_line_messenger.json"
        shutil.copy(temp_conf_file_path, self.target_conf_file_path)
        notification = Notification()

        msg = "This is a line message from python unittest"
        subject = "Line messenger notification test"
        actual = notification._send_line_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_naver_cloud(self):
        temp_conf_file_path = self.source_conf_dir_path / "global_config_naver_email.json"
        shutil.copy(temp_conf_file_path, self.target_conf_file_path)
        notification = Notification()

        msg = "This is a mail by naver cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_naver_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_nhn_cloud(self):
        temp_conf_file_path = self.source_conf_dir_path / "global_config_nhn_email.json"
        shutil.copy(temp_conf_file_path, self.target_conf_file_path)
        notification = Notification()

        msg = "This is a mail by nhn cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_nhn_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_smtp(self):
        temp_conf_file_path = self.source_conf_dir_path / "global_config_nhn_smtp.json"
        shutil.copy(temp_conf_file_path, self.target_conf_file_path)
        notification = Notification()

        msg = "This is a mail by nhn cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_smtp(msg, subject)
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
