#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from dotenv import load_dotenv
from bin.notification import Notification

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class NotificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv(".env.test.notification", override=True)

    def test_send_msg(self):
        msg = "This is a message from python unittest"
        subject = "Notification test"
        notification = Notification()
        actual = notification.send_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_naver_cloud(self):
        notification = Notification()

        msg = "This is a mail by NAVER Cloud from python unittest"
        subject = "Email notification test (by NAVER Cloud Email)"
        actual = notification._send_email_by_naver_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_nhn_cloud(self):
        notification = Notification()

        msg = "This is a mail by NHN Cloud from python unittest"
        subject = "Email notification test (by NHN Cloud Email)"
        actual = notification._send_email_by_nhn_cloud(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_smtp(self):
        notification = Notification()

        msg = "This is a mail by SMTP of NHN Cloud from python unittest"
        subject = "Email notification test (by NHN Cloud SMTP)"
        actual = notification._send_email_by_smtp(msg, subject)
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
