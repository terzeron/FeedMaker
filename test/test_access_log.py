#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
from datetime import datetime, timedelta
from bin.access_log import AccessLog


class AccessLogTest(unittest.TestCase):
    def test_loki_search(self):
        access_log = AccessLog()
        start = (datetime.now() + timedelta(days=-1)).strftime("%Y-%m-%dT00:00:00+09:00")
        end = datetime.now().strftime("%Y-%m-%dT00:00:00+09:00")
        params = {"query": '{namespace="feedmaker"}', "start": start, "end": end, "limit": 5000, "direction": "forward"}
        logs, stats = access_log.loki_search(params)
        self.assertTrue(logs)
        self.assertTrue(stats)

    def test_search(self):
        access_log = AccessLog()
        date_str = datetime.now().strftime("%Y-%m-%d")
        accessed_feed_list, viewed_feed_list = access_log.search(date_str)
        self.assertGreater(len(accessed_feed_list), 0)
        self.assertGreater(len(viewed_feed_list), 0)
