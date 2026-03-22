#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
import logging.config
from pathlib import Path
from dotenv import load_dotenv

from bin.notification import Notification
from unittest.mock import patch, MagicMock
from bin.feed_maker_util import NotFoundEnvError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class NotificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv(".env.tests.notification", override=True)

    def test_send_msg(self) -> None:
        msg = "This is a message from python unittest"
        subject = "Notification test"
        notification = Notification()
        actual = notification.send_msg(msg, subject)
        self.assertTrue(actual)

    def test_send_email_by_nhn_cloud(self) -> None:
        notification = Notification()

        msg = "This is a mail by NHN Cloud from python unittest"
        subject = "Email notification test (by NHN Cloud Email)"
        actual = notification._send_email_by_nhn_cloud(msg, subject)
        self.assertTrue(actual)


def _make_env_side_effect(env_map: dict[str, str]):
    from bin.feed_maker_util import NotFoundEnvError

    def side_effect(var: str, default_value: str = "") -> str:
        if var in env_map:
            return env_map[var]
        if default_value:
            return default_value
        raise NotFoundEnvError(f"can't get environment variable '{var}'")

    return side_effect


ALL_ENV = {
    "MSG_EMAIL_SENDER_ADDR": "sender@example.com",
    "MSG_EMAIL_SENDER_NAME": "Test Sender",
    "MSG_EMAIL_RECIPIENT_LIST": "Recipient1, rcpt1@example.com, Recipient2, rcpt2@example.com",
    "MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY": "naver_access_key",
    "MSG_EMAIL_NAVER_CLOUD_SECRET_KEY": "naver_secret_key",
    "MSG_EMAIL_NHN_CLOUD_APPKEY": "nhn_appkey",
    "MSG_EMAIL_NHN_CLOUD_SECRETKEY": "nhn_secretkey",
}


class TestNotificationInit(unittest.TestCase):
    @patch("bin.notification.Env.get")
    def test_init_with_all_env_vars(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        from bin.notification import Notification

        n = Notification()
        self.assertEqual(n.email_sender_address, "sender@example.com")
        self.assertEqual(n.email_sender_name, "Test Sender")
        self.assertEqual(len(n.email_recipient_list), 2)
        self.assertEqual(n.email_recipient_list[0], ("rcpt1@example.com", "Recipient1"))
        self.assertEqual(n.naver_cloud_access_key, "naver_access_key")
        self.assertEqual(n.nhn_cloud_appkey, "nhn_appkey")
        # NHN cloud keys present -> send_msg should be _send_email_by_nhn_cloud
        self.assertEqual(n.send_msg, n._send_email_by_nhn_cloud)

    @patch("bin.notification.Env.get")
    def test_init_missing_naver_cloud_keys(self, mock_env_get: MagicMock) -> None:
        env_without_naver = {k: v for k, v in ALL_ENV.items() if "NAVER" not in k}
        mock_env_get.side_effect = _make_env_side_effect(env_without_naver)
        from bin.notification import Notification

        n = Notification()
        self.assertEqual(n.naver_cloud_access_key, "")
        self.assertEqual(n.naver_cloud_secret_key, "")

    @patch("bin.notification.Env.get")
    def test_init_missing_nhn_cloud_keys(self, mock_env_get: MagicMock) -> None:
        env_without_nhn = {k: v for k, v in ALL_ENV.items() if "NHN" not in k}
        mock_env_get.side_effect = _make_env_side_effect(env_without_nhn)
        from bin.notification import Notification

        n = Notification()
        self.assertEqual(n.nhn_cloud_appkey, "")
        self.assertEqual(n.nhn_cloud_secretkey, "")
        # Without NHN keys, send_msg stays as _send_email_by_smtp
        self.assertEqual(n.send_msg, n._send_email_by_smtp)


class TestMakeSignature(unittest.TestCase):
    @patch("bin.notification.Env.get")
    def test_make_signature_returns_str_and_int(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        from bin.notification import Notification

        n = Notification()
        signature, timestamp = n._make_signature()
        self.assertIsInstance(signature, str)
        self.assertIsInstance(timestamp, int)
        self.assertGreater(len(signature), 0)
        self.assertGreater(timestamp, 0)


class TestSendEmailByNaverCloud(unittest.TestCase):
    def _create_notification(self, mock_env_get: MagicMock):
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        from bin.notification import Notification

        return Notification()

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_success_200_with_count(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"count": 1}'
        mock_post.return_value = mock_response
        result = n._send_email_by_naver_cloud("test message", "subject")
        self.assertTrue(result)

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_success_201_with_count(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.content = b'{"count": 2}'
        mock_post.return_value = mock_response
        result = n._send_email_by_naver_cloud("test message", "subject")
        self.assertTrue(result)

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_failure_400(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        result = n._send_email_by_naver_cloud("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_success_200_with_zero_count(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"count": 0}'
        mock_post.return_value = mock_response
        result = n._send_email_by_naver_cloud("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.Env.get")
    def test_empty_msg(self, mock_env_get: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        result = n._send_email_by_naver_cloud("", "subject")
        self.assertFalse(result)


class TestSendEmailByNhnCloud(unittest.TestCase):
    def _create_notification(self, mock_env_get: MagicMock):
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        from bin.notification import Notification

        return Notification()

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_success_200(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        result = n._send_email_by_nhn_cloud("test message", "subject")
        self.assertTrue(result)

    @patch("bin.notification.requests.post")
    @patch("bin.notification.Env.get")
    def test_failure_500(self, mock_env_get: MagicMock, mock_post: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        result = n._send_email_by_nhn_cloud("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.Env.get")
    def test_empty_msg(self, mock_env_get: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        result = n._send_email_by_nhn_cloud("", "subject")
        self.assertFalse(result)


class TestSendEmailBySmtp(unittest.TestCase):
    def _create_notification(self, mock_env_get: MagicMock):
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        from bin.notification import Notification

        return Notification()

    @patch("bin.notification.mail1.send")
    @patch("bin.notification.Env.get")
    def test_success(self, mock_env_get: MagicMock, mock_send: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_send.return_value = None
        result = n._send_email_by_smtp("test message", "subject")
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch("bin.notification.mail1.send")
    @patch("bin.notification.Env.get")
    def test_connection_refused(self, mock_env_get: MagicMock, mock_send: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_send.side_effect = ConnectionRefusedError("Connection refused")
        result = n._send_email_by_smtp("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.Env.get")
    def test_empty_msg(self, mock_env_get: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        result = n._send_email_by_smtp("", "subject")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
