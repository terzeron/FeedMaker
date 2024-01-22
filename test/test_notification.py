#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
import shutil
from bin.notification import Notification

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class NotificationTest(unittest.TestCase):
    def test_send_msg(self):
        msg = "This is a message from python unittest"
        subject = "Notification test"
        notification = Notification()
        actual = notification.send_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_line_msg(self):
        notification = Notification()

        msg = "This is a line message from python unittest"
        subject = "Line messenger notification test"
        actual = notification._send_line_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_naver_cloud(self):
        notification = Notification()

        msg = "This is a mail by naver cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_naver_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_nhn_cloud(self):
        notification = Notification()

        msg = "This is a mail by nhn cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_nhn_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_smtp(self):
        notification = Notification()

        msg = "This is a mail by nhn cloud from python unittest"
        subject = "Email notification test"
        actual = notification._send_email_by_smtp(msg, subject)
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
