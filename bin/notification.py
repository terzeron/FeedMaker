#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import re
import logging.config
import base64
import hmac
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Callable, List
from datetime import datetime
import requests
import mail1
from bin.feed_maker_util import Config

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Notification:
    def __init__(self) -> None:
        self.mail_sender_address: str = ""
        self.mail_sender_name: str = ""
        self.mail_recipient_list: List[Tuple[str, str]] = []
        self.smtp_server: str = ""
        self.smtp_port: str = ""
        self.smtp_login_id: str = ""
        self.smtp_login_password: str = ""
        self.send_msg: Callable[[str, str], bool] = self._send_email_by_smtp

        if "MSG_EMAIL_SENDER_ADDR" in os.environ and os.environ["MSG_EMAIL_SENDER_ADDR"] and "MSG_EMAIL_SENDER_NAME" in os.environ and os.environ["MSG_EMAIL_SENDER_NAME"] and "MSG_EMAIL_RECIPIENT_LIST" in os.environ and os.environ["MSG_EMAIL_RECIPIENT_LIST"]:
            self.mail_sender_address = os.environ["MSG_EMAIL_SENDER_ADDR"]
            self.mail_sender_name = os.environ["MSG_EMAIL_SENDER_NAME"]
            recipients = re.split(r"\s*,\s*", os.environ["MSG_EMAIL_RECIPIENT_LIST"])
            for i in range(0, len(recipients), 2):
                name = recipients[i]
                addr = recipients[i + 1]
                self.mail_recipient_list.append((addr, name))
        else:
            LOGGER.error("can't find 'MSG_EMAIL_SENDER_ADDR', 'MSG_EMAIL_SENDER_NAME' or 'MSG_EMAIL_RECIPIENT_LIST' from environment variables")
        if "MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY" in os.environ and os.environ["MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY"] and "MSG_EMAIL_NAVER_CLOUD_SECRET_KEY" in os.environ and os.environ["MSG_EMAIL_NAVER_CLOUD_SECRET_KEY"]:
            self.naver_cloud_access_key = os.environ["MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY"]
            self.naver_cloud_secret_key = os.environ["MSG_EMAIL_NAVER_CLOUD_SECRET_KEY"]
            self.send_msg = self._send_email_by_naver_cloud
        else:
            LOGGER.error("can't find 'MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY' or 'MSG_EMAIL_NAVER_CLOUD_SECRET_KEY' from environment variables")
        if "MSG_EMAIL_NHN_CLOUD_APPKEY" in os.environ and os.environ["MSG_EMAIL_NHN_CLOUD_APPKEY"] and "MSG_EMAIL_NHN_CLOUD_SECRETKEY" in os.environ and os.environ["MSG_EMAIL_NHN_CLOUD_SECRETKEY"]:
            self.nhn_cloud_appkey = os.environ["MSG_EMAIL_NHN_CLOUD_APPKEY"]
            self.nhn_cloud_secretkey = os.environ["MSG_EMAIL_NHN_CLOUD_SECRETKEY"]
            self.send_msg = self._send_email_by_nhn_cloud
        else:
            LOGGER.error("can't find 'MSG_EMAIL_NHN_CLOUD_APPKEY' or 'MSG_EMAIL_NHN_CLOUD_SECRETKEY' from environment variables")

        if "MSG_SMTP_SERVER" in os.environ and os.environ["MSG_SMTP_SERVER"] and "MSG_SMTP_PORT" in os.environ and os.environ["MSG_SMTP_PORT"] and "MSG_SMTP_LOGIN_ID" in os.environ and os.environ["MSG_SMTP_LOGIN_ID"] and "MSG_SMTP_LOGIN_PASSWORD" in os.environ and os.environ["MSG_SMTP_LOGIN_PASSWORD"]:
            self.smtp_server = os.environ["MSG_SMTP_SERVER"]
            self.smtp_port = os.environ["MSG_SMTP_PORT"]
            self.smtp_login_id = os.environ["MSG_SMTP_LOGIN_ID"]
            self.smtp_login_password = os.environ["MSG_SMTP_LOGIN_PASSWORD"]
            self.send_msg = self._send_email_by_smtp
        else:
            LOGGER.error("can't find 'MSG_SMTP_SERVER', 'MSG_SMTP_PORT', 'MSG_SMTP_LOGIN_ID' or 'MSG_SMTP_LOGIN_PASSWORD' from environment variables")

    def __del__(self) -> None:
        del self.mail_sender_address
        del self.mail_sender_name
        del self.mail_recipient_list
        del self.smtp_server
        del self.smtp_port
        del self.smtp_login_id
        del self.smtp_login_password

    def _make_signature(self) -> Tuple[str, int]:
        space = " "  # 공백
        new_line = "\n"  # 줄바꿈
        method = "POST"  # HTTP 메소드
        url = "/api/v1/mails"  # 도메인을 제외한 "/" 아래 전체 url (쿼리스트링 포함)
        timestamp = int(datetime.now().timestamp()) * 1000
        message = f"{method}{space}{url}{new_line}{timestamp}{new_line}{self.naver_cloud_access_key}"
        signing_key = hmac.new(self.naver_cloud_secret_key.encode('UTF-8'), message.encode('UTF-8'), hashlib.sha256)
        raw_hmac = signing_key.digest()
        encode_base64_string = base64.b64encode(raw_hmac).decode('UTF-8')
        return encode_base64_string, timestamp

    def _send_email_by_naver_cloud(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_naver_cloud('{msg}', '{subject}')")
        LOGGER.debug("naver_cloud_access_key: %s", self.naver_cloud_access_key)
        LOGGER.debug("naver_cloud_secret_key: %s", self.naver_cloud_secret_key)
        LOGGER.debug("mail_sender_address: %s", self.mail_sender_address)
        LOGGER.debug("mail_sender_name: %s", self.mail_sender_name)
        LOGGER.debug("mail_recipient_list: %r", self.mail_recipient_list)
        if not msg:
            return False
        signature, timestamp = self._make_signature()
        url = "https://mail.apigw.ntruss.com/api/v1/mails"
        headers = {
            "Content-Type": "application/json",
            "x-ncp-apigw-timestamp": str(timestamp),
            "x-ncp-iam-access-key": self.naver_cloud_access_key,
            "x-ncp-apigw-signature-v2": signature
        }
        recipients = []
        for address, name in self.mail_recipient_list:
            recipients.append({
                "address": address,
                "name": name,
                "type": "R"
            })
        payload = {
            "senderAddress": self.mail_sender_address,
            "senderName": self.mail_sender_name,
            "recipients": recipients,
            "individual": True,
            "advertising": False,
            "title": subject,
            "body": msg
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response and response.status_code in [200, 201]:
            result = json.loads(response.content)
            if "count" in result and result["count"] > 0:
                return True
        LOGGER.error(f"can't send a mail by naver cloud, {response.status_code}")
        return False

    def _send_email_by_nhn_cloud(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_nhn_cloud('{msg}', '{subject}')")
        LOGGER.debug("nhn_cloud_appkey: %s", self.nhn_cloud_appkey)
        LOGGER.debug("nhn_cloud_secretkey: %s", self.nhn_cloud_secretkey)
        LOGGER.debug("mail_sender_address: %s", self.mail_sender_address)
        LOGGER.debug("mail_sender_name: %s", self.mail_sender_name)
        LOGGER.debug("mail_recipient_list: %r", self.mail_recipient_list)
        if not msg:
            return False
        url = f"https://api-mail.cloud.toast.com/email/v2.0/appKeys/{self.nhn_cloud_appkey}/sender/mail"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Secret-Key": self.nhn_cloud_secretkey
        }
        receiver_list = []
        for address, name in self.mail_recipient_list:
            receiver_list.append({
                "receiveMailAddr": address,
                "receiveName": name,
                "receiveType": "MRT0"
            })
        payload = {
            "senderAddress": self.mail_sender_address,
            "senderName": self.mail_sender_name,
            "title": subject,
            "body": msg,
            "receiverList": receiver_list
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response and response.status_code == 200:
            return True
        LOGGER.error(f"can't send email by nhn cloud, {response.status_code}")
        return False

    def _send_email_by_smtp(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_smtp('{msg}', '{subject}')")
        if not msg:
            return False
        sender = self.mail_sender_name + " <" + self.mail_sender_address + ">"
        recipients = []
        for address, name in self.mail_recipient_list:
            recipients.append(name + " <" + address + ">")
        try:
            mail1.send(subject=subject, text=msg, sender=sender, recipients=recipients, smtp_host=self.smtp_server, smtp_port=self.smtp_port, username=self.smtp_login_id, password=self.smtp_login_password)
        except ConnectionRefusedError as e:
            LOGGER.error(f"can't send email by smtp, {e}")
            return False
        return True
