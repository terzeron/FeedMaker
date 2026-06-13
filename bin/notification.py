#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import smtplib
import logging.config
from pathlib import Path
from typing import Callable
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from bin.feed_maker_util import Env

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Notification:
    def __init__(self) -> None:
        # email sender & recipient
        self.email_sender_address: str = Env.get("MSG_EMAIL_SENDER_ADDR")
        self.email_sender_name: str = Env.get("MSG_EMAIL_SENDER_NAME")
        self.email_recipient_list: list[tuple[str, str]] = []
        recipient = Env.get("MSG_EMAIL_RECIPIENT_LIST")
        recipients = re.split(r"\s*,\s*", recipient)
        for i in range(0, len(recipients), 2):
            name = recipients[i]
            addr = recipients[i + 1]
            self.email_recipient_list.append((addr, name))

        # smtp relay: unauthenticated by default; logs in over STARTTLS only when
        # both id and password are provided (e.g. relaying through a trusted local
        # MTA needs no auth, an external submission server does).
        self.smtp_host: str = Env.get("MSG_SMTP_SERVER")
        self.smtp_port: int = int(Env.get("MSG_SMTP_PORT", "25"))
        self.smtp_login_id: str = Env.get("MSG_SMTP_LOGIN_ID", "")
        self.smtp_login_password: str = Env.get("MSG_SMTP_LOGIN_PASSWORD", "")

        self.send_msg: Callable[[str, str], bool] = self._send_email_by_smtp

    def _build_message(self, msg: str, subject: str) -> EmailMessage:
        email_msg = EmailMessage()
        email_msg["Subject"] = subject
        email_msg["From"] = f"{self.email_sender_name} <{self.email_sender_address}>"
        email_msg["To"] = ", ".join(f"{name} <{address}>" for address, name in self.email_recipient_list)
        email_msg["Date"] = formatdate(localtime=False)
        email_msg["Message-ID"] = make_msgid(domain=self.email_sender_address.rsplit("@", 1)[-1])
        email_msg.set_content(msg)
        return email_msg

    def _send_email_by_smtp(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_smtp('{msg}', '{subject}')")
        if not msg:
            return False
        if not self.email_recipient_list:
            LOGGER.error("can't send email by smtp, no recipients configured")
            return False
        if not self.smtp_host:
            LOGGER.error("can't send email by smtp, no smtp server configured (MSG_SMTP_SERVER)")
            return False
        email_msg = self._build_message(msg, subject)
        recipient_addresses = [address for address, _ in self.email_recipient_list]
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
                if self.smtp_login_id and self.smtp_login_password:
                    smtp.starttls()
                    smtp.login(self.smtp_login_id, self.smtp_login_password)
                smtp.send_message(email_msg, from_addr=self.email_sender_address, to_addrs=recipient_addresses)
        except (OSError, smtplib.SMTPException) as e:
            LOGGER.error(f"can't send email by smtp, {e}")
            return False
        return True
