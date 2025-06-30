#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import unittest
import logging.config
from datetime import datetime, timezone
from pathlib import Path

from bin.feed_maker_util import Datetime

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class DatetimeTest(unittest.TestCase):
    def test_get_current_time(self) -> None:
        # All three datetime functions may be completed in 1 seconds
        expected1 = str(datetime.now(timezone.utc))
        actual = str(Datetime.get_current_time())
        expected2 = str(datetime.now(timezone.utc))

        # YYYY-MM-DD HH:MI:SS
        e1 = expected1[:19]
        e2 = expected2[:19]
        a = actual[:19]
        self.assertIn(a, [e1, e2])

        # timezone
        expected = expected1[-6:]
        actual = actual[-6:]
        self.assertEqual(expected, actual)

    def test_get_time_str(self) -> None:
        expected = "2021-10-22T14:59:17"
        dt = datetime(2021, 10, 22, 14, 59, 17)
        actual = Datetime._get_time_str(dt)
        self.assertEqual(expected, actual)

    def test_get_current_time_str(self) -> None:
        actual = Datetime.get_current_time_str()
        m = re.search(r"^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\+\d\d:\d\d$", actual)
        self.assertTrue(m)

    def test_get_rss_date_str(self) -> None:
        actual = Datetime.get_rss_date_str()
        m = re.search(r"^(Sun|Mon|Tue|Wed|Thu|Fri|Sat), \d+ (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d\d\d\d \d\d:\d\d:\d\d \+\d\d\d\d$", actual)
        self.assertTrue(m)

    def test_get_short_date_str(self) -> None:
        expected = datetime.now(timezone.utc).strftime("%Y%m%d")
        actual = Datetime.get_short_date_str()
        self.assertEqual(expected, actual)

        expected = "20211022"
        dt = datetime(2021, 10, 22, 14, 59, 17)
        actual = Datetime.get_short_date_str(dt)
        self.assertEqual(expected, actual)

    def test_convert_datetime_to_str(self) -> None:
        d = "2022-01-01"
        self.assertEqual("2022-01-01", Datetime.convert_datetime_to_str(d))

        d = "2022-12-30 12:12:12"
        self.assertEqual("2022-12-30 12:12:12", Datetime.convert_datetime_to_str(d))

        d = "2018-01-31"
        self.assertEqual("2018-01-31", Datetime.convert_datetime_to_str(d))

        d = "01-31"
        self.assertEqual("01-31", Datetime.convert_datetime_to_str(d))

        dt = datetime.strptime("2018-01-13", "%Y-%m-%d")
        self.assertEqual("2018-01-13 00:00:00", Datetime.convert_datetime_to_str(dt))

        dt = datetime.strptime("2018-01-31 17:04:11", "%Y-%m-%d %H:%M:%S")
        self.assertEqual("2018-01-31 17:04:11", Datetime.convert_datetime_to_str(dt))


if __name__ == "__main__":
    unittest.main()
