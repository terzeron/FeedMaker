#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest.mock import patch, MagicMock

import pytest

from backend.auth import verify_facebook_token


class TestVerifyFacebookToken:
    def test_valid_token(self):
        """유효한 토큰과 일치하는 이메일이면 True"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "user@example.com"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("valid_token", "user@example.com") is True

    def test_email_mismatch(self):
        """토큰의 이메일과 요청 이메일이 다르면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "real@example.com"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("valid_token", "fake@example.com") is False

    def test_invalid_token(self):
        """Facebook API가 오류 응답을 반환하면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 400

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("invalid_token", "user@example.com") is False

    def test_network_error(self):
        """네트워크 오류 시 False"""
        import requests
        with patch("backend.auth.http_requests.get", side_effect=requests.RequestException("timeout")):
            assert verify_facebook_token("token", "user@example.com") is False

    def test_no_email_in_response(self):
        """Facebook 응답에 email 필드가 없으면 False"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "User"}

        with patch("backend.auth.http_requests.get", return_value=mock_response):
            assert verify_facebook_token("token", "user@example.com") is False
