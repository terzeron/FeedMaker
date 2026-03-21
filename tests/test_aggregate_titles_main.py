#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestAggregateTitlesMain(unittest.TestCase):
    """utils/aggregate_titles.py main() 함수 테스트"""

    def test_main_no_args(self) -> None:
        from utils.aggregate_titles import main

        with patch.object(sys, "argv", ["aggregate_titles.py"]):
            result = main()
        self.assertEqual(result, -1)

    def test_main_with_t_option_no_args(self) -> None:
        from utils.aggregate_titles import main

        with patch.object(sys, "argv", ["aggregate_titles.py", "-t", "0.5"]):
            result = main()
        self.assertEqual(result, -1)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_with_stdin_data(self, mock_stdin: MagicMock, mock_exec_cmd: MagicMock, mock_logger: MagicMock) -> None:
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle Two\textra2", "http://link3.com\tTitle Three\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(sys, "argv", ["aggregate_titles.py", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            # intermediate file should have been created with titles
            intermediate = Path(file_prefix + ".intermediate")
            self.assertTrue(intermediate.exists())
            content = intermediate.read_text(encoding="utf-8")
            self.assertIn("Title One", content)
            self.assertIn("Title Two", content)
            self.assertIn("Title Three", content)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_comment_lines_skipped(self, mock_stdin: MagicMock, mock_exec_cmd: MagicMock, mock_logger: MagicMock) -> None:
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["# this is a comment", "http://link1.com\tTitle One\textra1", "# another comment", "http://link2.com\tTitle Two\textra2"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(sys, "argv", ["aggregate_titles.py", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            intermediate = Path(file_prefix + ".intermediate")
            content = intermediate.read_text(encoding="utf-8")
            self.assertNotIn("comment", content)
            self.assertIn("Title One", content)
            self.assertIn("Title Two", content)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_title_deduplication(self, mock_stdin: MagicMock, mock_exec_cmd: MagicMock, mock_logger: MagicMock) -> None:
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle One\textra2", "http://link3.com\tTitle Two\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(sys, "argv", ["aggregate_titles.py", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            intermediate = Path(file_prefix + ".intermediate")
            content = intermediate.read_text(encoding="utf-8")
            lines = [l for l in content.strip().split("\n") if l]
            # "Title One" appears twice but should be deduplicated
            self.assertEqual(len(lines), 2)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_with_t_option_and_data(self, mock_stdin: MagicMock, mock_exec_cmd: MagicMock, mock_logger: MagicMock) -> None:
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(sys, "argv", ["aggregate_titles.py", "-t", "0.7", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            # hcluster command should include threshold
            cmd_arg = mock_exec_cmd.call_args[0][0]
            self.assertIn("-t '0.7'", cmd_arg)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_output_file_written(self, mock_stdin: MagicMock, mock_exec_cmd: MagicMock, mock_logger: MagicMock) -> None:
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle Two\textra2", "http://link3.com\tTitle Three\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            # Create a temp_output file that _extract_clustered_lines will read
            temp_output = Path(file_prefix + ".temp")
            temp_output.write_text("1\t3\t1\tTitle One\t2\tTitle Two\t3\tTitle Three\n", encoding="utf-8")

            with patch.object(sys, "argv", ["aggregate_titles.py", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            output = Path(file_prefix + ".output")
            self.assertTrue(output.exists())
            content = output.read_text(encoding="utf-8")
            self.assertIn("http://link1.com", content)


if __name__ == "__main__":
    unittest.main()
