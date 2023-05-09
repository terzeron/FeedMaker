#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging.config
import base64
import hmac
import hashlib
import json
from typing import Any, Dict, Tuple, Callable, List
from datetime import datetime
import requests
import mail1
from feed_maker_util import Config

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class Notification:
    def __init__(self) -> None:
        self.line_receiver_id: str = ""
        self.line_access_token: str = ""
        self.mail_sender_address: str = ""
        self.mail_sender_name: str = ""
        self.mail_recipient_list: List[Tuple[str, str]] = []
        self.smtp_server: str = ""
        self.smtp_port: str = ""
        self.smtp_login_id: str = ""
        self.smtp_login_password: str = ""
        self.send_msg: Callable[[str, str], bool] = self._send_email_by_smtp

        # read global config
        global_config = Config.get_global_config()
        if "notification" in global_config and global_config["notification"]:
            notification_config = global_config["notification"]
            if "line_messenger" in notification_config and notification_config["line_messenger"]:
                line_config = notification_config["line_messenger"]
                if "line_receiver_id_list" in line_config and "line_access_token" in line_config:
                    self.line_receiver_id_list = line_config["line_receiver_id_list"]
                    self.line_access_token = line_config["line_access_token"]
                    self.send_msg = self._send_line_msg
                else:
                    LOGGER.error("can't find line_receiver_id_list or line_access_token in line_messenger from global configuration")
            if "email" in notification_config and notification_config["email"]:
                email_config = notification_config["email"]
                if "mail_sender_address" in email_config and "mail_sender_name" in email_config and "mail_recipient_list" in email_config:
                    self.mail_sender_address = email_config["mail_sender_address"]
                    self.mail_sender_name = email_config["mail_sender_name"]
                    for recipient in email_config["mail_recipient_list"]:
                        self.mail_recipient_list.append((recipient["mail_recipient_address"], recipient["mail_recipient_name"]))
                else:
                    LOGGER.error("can't find mail_sender_address or mail_recipient_list in email from global configuration")
                if "email_by_naver_cloud" in email_config and email_config["email_by_naver_cloud"]:
                    if "access_key" in email_config["email_by_naver_cloud"] and "secret_key" in email_config["email_by_naver_cloud"]:
                        self.naver_cloud_access_key = email_config["email_by_naver_cloud"]["access_key"]
                        self.naver_cloud_secret_key = email_config["email_by_naver_cloud"]["secret_key"]
                    self.send_msg = self._send_email_by_naver_cloud
                if "email_by_nhn_cloud" in email_config and email_config["email_by_nhn_cloud"]:
                    if "appkey" in email_config["email_by_nhn_cloud"] and "secretkey" in email_config["email_by_nhn_cloud"]:
                        self.nhn_cloud_appkey = email_config["email_by_nhn_cloud"]["appkey"]
                        self.nhn_cloud_secretkey = email_config["email_by_nhn_cloud"]["secretkey"]
                    self.send_msg = self._send_email_by_nhn_cloud
                if "smtp" in email_config and email_config["smtp"]:
                    smtp_config = email_config["smtp"]
                    if "smtp_server" in smtp_config and "smtp_port" in smtp_config and "smtp_login_id" in smtp_config and "smtp_login_password" in smtp_config:
                        self.smtp_server = smtp_config["smtp_server"]
                        self.smtp_port = smtp_config["smtp_port"]
                        self.smtp_login_id = smtp_config["smtp_login_id"]
                        self.smtp_login_password = smtp_config["smtp_login_password"]
                    self.send_msg = self._send_email_by_smtp
        else:
            LOGGER.error("can't find any notification configuration")

    def __del__(self) -> None:
        del self.line_receiver_id
        del self.line_access_token
        del self.mail_sender_address
        del self.mail_sender_name
        del self.mail_recipient_list
        del self.smtp_server
        del self.smtp_port
        del self.smtp_login_id
        del self.smtp_login_password

    def _send_line_msg(self, msg: str, subject: str = "") -> bool:
        LOGGER.debug(f"# _send_line_msg('{msg}', '{subject}')")
        LOGGER.debug("line_access_token: %s", self.line_access_token)
        LOGGER.debug("line_receiver_id_list: %r", self.line_receiver_id_list)
        if not msg:
            return False

        url = "https://api.line.me/v2/bot/message/multicast"
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.line_access_token}"
        }
        data: Dict[str, Any] = {
            "to": self.line_receiver_id_list,
            "messages": [
                {
                    "type": "text",
                    "text": msg[:1999]
                }
            ]
        }
        response = requests.post(url, json=data, headers=headers, timeout=60, verify=True)
        if response and response.status_code == 200:
            return True
        LOGGER.error(f"can't send message to line messenger, {response.status_code}")
        return False

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
