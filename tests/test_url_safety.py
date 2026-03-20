#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from bin.feed_maker_util import URLSafety


class URLSafetyTest(unittest.TestCase):
    def test_block_non_http_schemes(self) -> None:
        ok, _ = URLSafety.check_url("file:///etc/passwd", allow_private=False)
        self.assertFalse(ok)

    def test_block_localhost_ip(self) -> None:
        ok, _ = URLSafety.check_url("http://127.0.0.1/", allow_private=False)
        self.assertFalse(ok)

    def test_block_link_local_metadata(self) -> None:
        ok, _ = URLSafety.check_url("http://169.254.169.254/latest/meta-data/", allow_private=False)
        self.assertFalse(ok)

    def test_block_ipv6_loopback(self) -> None:
        ok, _ = URLSafety.check_url("http://[::1]/", allow_private=False)
        self.assertFalse(ok)

    def test_allow_public_ip(self) -> None:
        ok, _ = URLSafety.check_url("http://93.184.216.34/", allow_private=False)
        self.assertTrue(ok)

    def test_allow_private_when_flagged(self) -> None:
        ok, _ = URLSafety.check_url("http://127.0.0.1/", allow_private=True)
        self.assertTrue(ok)

    def test_allowlist_bypass(self) -> None:
        ok, _ = URLSafety.check_url("http://localhost/", allow_private=False, allowed_hosts_raw="localhost")
        self.assertTrue(ok)

    def test_allowlist_suffix(self) -> None:
        ok, _ = URLSafety.check_url("https://sub.example.com/path", allow_private=False, allowed_hosts_raw=".example.com")
        self.assertTrue(ok)

    def test_block_when_dns_resolution_fails(self) -> None:
        ok, _ = URLSafety.check_url("http://nonexistent.invalid/", allow_private=False)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
