#!/usr/bin/env python
# -*- coding: utf-8 -*-


import unittest
from unittest.mock import patch
from io import StringIO
import logging.config
from pathlib import Path
from bin.feed_maker_util import IO

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class IOTest(unittest.TestCase):
    def test_read_stdin(self):
        expected = "test data from stdin\nsecond line from stdin\n"
        with patch("sys.stdin", StringIO("test data from stdin\nsecond line from stdin\n")):
            actual = IO.read_stdin()
            self.assertEqual(expected, actual)

    def test_read_stdin_as_line_list(self):
        expected = ["test data from stdin\n", "second line from stdin\n"]
        with patch("sys.stdin", StringIO("test data from stdin\nsecond line from stdin\n")):
            actual = IO.read_stdin_as_line_list()
            self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
