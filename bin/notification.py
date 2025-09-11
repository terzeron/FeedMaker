#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import logging.config
import base64
import hmac
import hashlib
import json
from pathlib import Path
from typing import Callable, TypedDict
from datetime import datetime, timezone
import requests
import mail1
from bin.feed_maker_util import Env, NotFoundEnvError

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

class Recipient(TypedDict):
    address: str
    name: str
    type: str

class Receiver(TypedDict):
    receiveMailAddr: str
    receiveName: str
    receiveType: str

class Notification:
    def __init__(self) -> None:
        self.email_sender_address: str = ""
        self.email_sender_name: str = ""
        self.email_recipient_list: list[tuple[str, str]] = []
        self.smtp_server: str = ""
        self.smtp_port: str = ""
        self.smtp_login_id: str = ""
        self.smtp_login_password: str = ""
        self.send_msg: Callable[[str, str], bool] = self._send_email_by_smtp

        # email sender & recipient
        self.email_sender_address = Env.get("MSG_EMAIL_SENDER_ADDR")
        self.email_sender_name = Env.get("MSG_EMAIL_SENDER_NAME")
        recipient = Env.get("MSG_EMAIL_RECIPIENT_LIST")
        recipients = re.split(r"\s*,\s*", recipient)
        for i in range(0, len(recipients), 2):
            name = recipients[i]
            addr = recipients[i + 1]
            self.email_recipient_list.append((addr, name))

        # naver cloud email
        try:
            self.naver_cloud_access_key = Env.get("MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY")
            self.naver_cloud_secret_key = Env.get("MSG_EMAIL_NAVER_CLOUD_SECRET_KEY")
        except NotFoundEnvError as e:
            LOGGER.warning(f"MSG_EMAIL_NAVER_CLOUD_ACCESS_KEY or MSG_EMAIL_NAVER_CLOUD_SECRET_KEY not found, {e}")
            self.naver_cloud_access_key = ""
            self.naver_cloud_secret_key = ""

        # nhn cloud email
        try:
            self.nhn_cloud_appkey = Env.get("MSG_EMAIL_NHN_CLOUD_APPKEY")
            self.nhn_cloud_secretkey = Env.get("MSG_EMAIL_NHN_CLOUD_SECRETKEY")
            self.send_msg = self._send_email_by_nhn_cloud
        except NotFoundEnvError as e:
            LOGGER.warning(f"MSG_EMAIL_NHN_CLOUD_APPKEY or MSG_EMAIL_NHN_CLOUD_SECRETKEY not found, {e}")
            self.nhn_cloud_appkey = ""
            self.nhn_cloud_secretkey = ""

        # smtp
        #self.smtp_server = Env.get("MSG_SMTP_SERVER")
        #self.smtp_port = Env.get("MSG_SMTP_PORT")
        #self.smtp_login_id = Env.get("MSG_SMTP_LOGIN_ID")
        #self.smtp_login_password = Env.get("MSG_SMTP_LOGIN_PASSWORD")
        #self.send_msg = self._send_email_by_smtp

    def __del__(self) -> None:
        del self.email_sender_address
        del self.email_sender_name
        del self.email_recipient_list
        del self.smtp_server
        del self.smtp_port
        del self.smtp_login_id
        del self.smtp_login_password

    def _make_signature(self) -> tuple[str, int]:
        space = " "  # 공백
        new_line = "\n"  # 줄바꿈
        method = "POST"  # HTTP 메소드
        url = "/api/v1/mails"  # 도메인을 제외한 "/" 아래 전체 url (쿼리스트링 포함)
        timestamp = int(datetime.now(timezone.utc).timestamp()) * 1000
        message = f"{method}{space}{url}{new_line}{timestamp}{new_line}{self.naver_cloud_access_key}"
        signing_key = hmac.new(self.naver_cloud_secret_key.encode('UTF-8'), message.encode('UTF-8'), hashlib.sha256)
        raw_hmac = signing_key.digest()
        encode_base64_string = base64.b64encode(raw_hmac).decode('UTF-8')
        return encode_base64_string, timestamp

    def _send_email_by_naver_cloud(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_naver_cloud('{msg}', '{subject}')")
        LOGGER.debug("naver_cloud_access_key: %s", self.naver_cloud_access_key)
        LOGGER.debug("naver_cloud_secret_key: %s", self.naver_cloud_secret_key)
        LOGGER.debug("mail_sender_address: %s", self.email_sender_address)
        LOGGER.debug("mail_sender_name: %s", self.email_sender_name)
        LOGGER.debug("mail_recipient_list: %r", self.email_recipient_list)
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
        recipients: list[Recipient] = []
        for address, name in self.email_recipient_list:
            recipients.append({
                "address": address,
                "name": name,
                "type": "R"
            })
        payload = {
            "senderAddress": self.email_sender_address,
            "senderName": self.email_sender_name,
            "recipients": recipients,
            "individual": True,
            "advertising": False,
            "title": subject,
            "body": msg
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if response and response.status_code in [200, 201]:
            result = json.loads(response.content)
            if result.get("count", 0) > 0:
                return True
        LOGGER.error(f"can't send a mail by naver cloud, {response.status_code}")
        return False

    def _send_email_by_nhn_cloud(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_email_by_nhn_cloud('{msg}', '{subject}')")
        LOGGER.debug("nhn_cloud_appkey: %s", self.nhn_cloud_appkey)
        LOGGER.debug("nhn_cloud_secretkey: %s", self.nhn_cloud_secretkey)
        LOGGER.debug("mail_sender_address: %s", self.email_sender_address)
        LOGGER.debug("mail_sender_name: %s", self.email_sender_name)
        LOGGER.debug("mail_recipient_list: %r", self.email_recipient_list)
        if not msg:
            return False
        url = f"https://api-mail.cloud.toast.com/email/v2.0/appKeys/{self.nhn_cloud_appkey}/sender/mail"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Secret-Key": self.nhn_cloud_secretkey
        }
        receiver_list: list[Receiver] = []
        for address, name in self.email_recipient_list:
            receiver_list.append({
                "receiveMailAddr": address,
                "receiveName": name,
                "receiveType": "MRT0"
            })
        payload = {
            "senderAddress": self.email_sender_address,
            "senderName": self.email_sender_name,
            "title": subject,
            "body": msg,
            "receiverlist": receiver_list
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
        sender = self.email_sender_name + " <" + self.email_sender_address + ">"
        recipients: list[str] = []
        for address, name in self.email_recipient_list:
            recipients.append(name + " <" + address + ">")
        try:
            mail1.send(subject=subject, text=msg, sender=sender, recipients=recipients, smtp_host=self.smtp_server, smtp_port=self.smtp_port, username=self.smtp_login_id, password=self.smtp_login_password)
        except ConnectionRefusedError as e:
            LOGGER.error(f"can't send email by smtp, {e}")
            return False
        return True
