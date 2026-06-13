#!/usr/bin/env python
# -*- coding: utf-8 -*-


import smtplib
import unittest
import logging.config
from pathlib import Path
from dotenv import load_dotenv

from unittest.mock import patch, MagicMock
from bin.notification import Notification

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

_NOTIFICATION_ENV_FILE = ".env.tests.notification"


def _make_env_side_effect(env_map: dict[str, str]):
    # Mirror Env.get: return the mapped value, otherwise the supplied default
    # (Env.get wraps os.getenv(var, default_value), so a missing var with the
    # default "" yields "" rather than raising).
    def side_effect(var: str, default_value: str = "") -> str:
        return env_map.get(var, default_value)

    return side_effect


ALL_ENV = {"MSG_EMAIL_SENDER_ADDR": "sender@example.com", "MSG_EMAIL_SENDER_NAME": "Test Sender", "MSG_EMAIL_RECIPIENT_LIST": "Recipient1, rcpt1@example.com, Recipient2, rcpt2@example.com", "MSG_SMTP_SERVER": "smtp.example.com", "MSG_SMTP_PORT": "25"}

ENV_WITH_LOGIN = {**ALL_ENV, "MSG_SMTP_LOGIN_ID": "smtp_user", "MSG_SMTP_LOGIN_PASSWORD": "smtp_pass"}


class TestNotificationInit(unittest.TestCase):
    @patch("bin.notification.Env.get")
    def test_init_with_all_env_vars(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = _make_env_side_effect(ALL_ENV)
        n = Notification()
        self.assertEqual(n.email_sender_address, "sender@example.com")
        self.assertEqual(n.email_sender_name, "Test Sender")
        self.assertEqual(len(n.email_recipient_list), 2)
        self.assertEqual(n.email_recipient_list[0], ("rcpt1@example.com", "Recipient1"))
        self.assertEqual(n.email_recipient_list[1], ("rcpt2@example.com", "Recipient2"))
        self.assertEqual(n.smtp_host, "smtp.example.com")
        self.assertEqual(n.smtp_port, 25)
        self.assertIsInstance(n.smtp_port, int)
        # no auth configured by default
        self.assertEqual(n.smtp_login_id, "")
        self.assertEqual(n.smtp_login_password, "")
        # smtp is the only send path
        self.assertEqual(n.send_msg, n._send_email_by_smtp)

    @patch("bin.notification.Env.get")
    def test_init_port_defaults_to_25(self, mock_env_get: MagicMock) -> None:
        env_without_port = {k: v for k, v in ALL_ENV.items() if k != "MSG_SMTP_PORT"}
        mock_env_get.side_effect = _make_env_side_effect(env_without_port)
        n = Notification()
        self.assertEqual(n.smtp_port, 25)

    @patch("bin.notification.Env.get")
    def test_init_with_login_credentials(self, mock_env_get: MagicMock) -> None:
        mock_env_get.side_effect = _make_env_side_effect(ENV_WITH_LOGIN)
        n = Notification()
        self.assertEqual(n.smtp_login_id, "smtp_user")
        self.assertEqual(n.smtp_login_password, "smtp_pass")

    @patch("bin.notification.Env.get")
    def test_init_missing_smtp_server_is_empty(self, mock_env_get: MagicMock) -> None:
        env_without_server = {k: v for k, v in ALL_ENV.items() if k != "MSG_SMTP_SERVER"}
        mock_env_get.side_effect = _make_env_side_effect(env_without_server)
        n = Notification()
        self.assertEqual(n.smtp_host, "")


class TestSendEmailBySmtp(unittest.TestCase):
    def _create_notification(self, mock_env_get: MagicMock, env: dict[str, str] = ALL_ENV) -> Notification:
        mock_env_get.side_effect = _make_env_side_effect(env)
        return Notification()

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_success_no_auth(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        smtp = mock_smtp_cls.return_value.__enter__.return_value
        result = n._send_email_by_smtp("test message", "subject")
        self.assertTrue(result)
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 25, timeout=30)
        smtp.send_message.assert_called_once()
        # unauthenticated relay: no STARTTLS / login
        smtp.starttls.assert_not_called()
        smtp.login.assert_not_called()
        # envelope sender and recipients passed explicitly
        _, kwargs = smtp.send_message.call_args
        self.assertEqual(kwargs["from_addr"], "sender@example.com")
        self.assertEqual(kwargs["to_addrs"], ["rcpt1@example.com", "rcpt2@example.com"])

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_success_with_auth(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get, ENV_WITH_LOGIN)
        smtp = mock_smtp_cls.return_value.__enter__.return_value
        result = n._send_email_by_smtp("test message", "subject")
        self.assertTrue(result)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("smtp_user", "smtp_pass")
        smtp.send_message.assert_called_once()

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_message_headers(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        smtp = mock_smtp_cls.return_value.__enter__.return_value
        n._send_email_by_smtp("body text", "the subject")
        sent_msg = smtp.send_message.call_args.args[0]
        self.assertEqual(sent_msg["Subject"], "the subject")
        self.assertEqual(sent_msg["From"], "Test Sender <sender@example.com>")
        self.assertIn("rcpt1@example.com", sent_msg["To"])
        self.assertEqual(sent_msg.get_content().strip(), "body text")

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_connection_refused(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        mock_smtp_cls.side_effect = ConnectionRefusedError("Connection refused")
        result = n._send_email_by_smtp("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_smtp_exception(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        smtp = mock_smtp_cls.return_value.__enter__.return_value
        smtp.send_message.side_effect = smtplib.SMTPException("relay denied")
        result = n._send_email_by_smtp("test message", "subject")
        self.assertFalse(result)

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_empty_msg(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        n = self._create_notification(mock_env_get)
        result = n._send_email_by_smtp("", "subject")
        self.assertFalse(result)
        mock_smtp_cls.assert_not_called()

    @patch("bin.notification.smtplib.SMTP")
    @patch("bin.notification.Env.get")
    def test_missing_smtp_server_fails_cleanly(self, mock_env_get: MagicMock, mock_smtp_cls: MagicMock) -> None:
        # Regression: when MSG_SMTP_SERVER is absent (smtp_host == "") the send must
        # fail cleanly without ever constructing an SMTP connection. Previously this
        # reached smtplib and surfaced the cryptic "please run connect() first".
        env_without_server = {k: v for k, v in ALL_ENV.items() if k != "MSG_SMTP_SERVER"}
        n = self._create_notification(mock_env_get, env_without_server)
        self.assertEqual(n.smtp_host, "")
        result = n._send_email_by_smtp("test message", "subject")
        self.assertFalse(result)
        mock_smtp_cls.assert_not_called()


@unittest.skipUnless(Path(_NOTIFICATION_ENV_FILE).is_file(), f"{_NOTIFICATION_ENV_FILE} not present")
class TestSendMsgIntegration(unittest.TestCase):
    """Real end-to-end send; runs only when an env file with live SMTP config exists."""

    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv(_NOTIFICATION_ENV_FILE, override=True)

    def test_send_msg(self) -> None:
        notification = Notification()
        actual = notification.send_msg("This is a message from python unittest", "Notification test")
        self.assertTrue(actual)


if __name__ == "__main__":
    unittest.main()
