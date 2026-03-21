#!/usr/bin/env python

import unittest
from unittest.mock import patch
from io import StringIO


class TestPostProcessOnlyForImages(unittest.TestCase):
    """post_process_only_for_images: print_usage (10-13), getopt error + exit (22-24)"""

    def test_print_usage(self) -> None:
        """print_usage outputs expected text -> line 10-13"""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            from utils.post_process_only_for_images import print_usage

            print_usage()
            output = mock_stdout.getvalue()
            self.assertIn("Usage", output)
            self.assertIn("-u", output)
            self.assertIn("-r", output)

    @patch("sys.argv", ["post_process_only_for_images.py", "--invalid-option"])
    def test_invalid_option_exits(self) -> None:
        """Invalid option triggers getopt error -> print_usage + sys.exit -> line 22-24"""
        with patch("sys.stdout", new_callable=StringIO):
            with self.assertRaises(SystemExit):
                from utils.post_process_only_for_images import main

                main()


if __name__ == "__main__":
    unittest.main()
