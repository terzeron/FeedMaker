#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import unittest
from unittest.mock import patch
from io import StringIO
from extract import extract_content
from feed_maker_util import IO, header_str


dummy_url = "https://test.com"


def wrap_header(string):
    return header_str + "\n" + string + "\n"

def mock_stdin_stdout(input_str):
    result = ""
    with patch.object(IO, "read_file", create=True, return_value=input_str):
        with patch('sys.stdout', new=StringIO()) as out:
            extract_content([dummy_url])
            result = out.getvalue()
    return result


class ExtractTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_extract_with_id(self):
        input_str = '''<html><body><div id="content">message</div></body></html>'''
        expected = wrap_header('''<div>\nmessage</div>''')
        result = mock_stdin_stdout(input_str)
        self.assertEqual(result, expected)

    @patch('sys.stdout', new=StringIO())
    def test_extract_with_class(self):
        input_str = '''<div class="content_view">message</div>'''
        expected = wrap_header('''<div>\nmessage</div>''')
        result = mock_stdin_stdout(input_str)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
