#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import unittest
import feed_maker_util


class RemoveDuplicatesTest(unittest.TestCase):
    def test_remove_duplicates(self):
        input = ["3", "a", "b", "1", "d", "d", "b", "c", "3", "2", "1"]
        expected = ["3", "a", "b", "1", "d", "c", "2"]
        result = feed_maker_util.remove_duplicates(input)
        self.assertEqual(expected, result)


if __name__ == "__main__":
    unittest.main()
