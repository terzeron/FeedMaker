#!/usr/bin/env python
# -*- coding: utf-8 -*-


import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch  # noqa: F401

import utils.aggregate_titles


class TestAggregateTitles(unittest.TestCase):
    def test_awk_replacement_logic(self) -> None:
        """awk 로직이 Python으로 정확히 대체되었는지 검증"""
        # awk -F'\t' '$2 >= 3 { for (i = 3; i < NF; i += 2) { print $(i) FS $(i + 1) } }'
        # 2번째 필드 >= 3인 행에서, 3번째부터 짝수 쌍을 탭 구분으로 출력
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output = Path(tmpdir) / "test.temp"
            # 형식: cluster_id \t count \t line_num \t title \t line_num \t title ...
            temp_output.write_text("1\t3\t1\ttitle_a\t2\ttitle_b\t3\ttitle_c\n2\t2\t4\ttitle_d\t5\ttitle_e\n3\t4\t6\ttitle_f\t7\ttitle_g\t8\ttitle_h\t9\ttitle_i\n", encoding="utf-8")
            result = utils.aggregate_titles._extract_clustered_lines(temp_output)
            # cluster 1 (count=3 >= 3): (1, title_a), (2, title_b), (3, title_c)
            # cluster 2 (count=2 < 3): 스킵
            # cluster 3 (count=4 >= 3): (6, title_f), (7, title_g), (8, title_h), (9, title_i)
            expected = [("1", "title_a"), ("2", "title_b"), ("3", "title_c"), ("6", "title_f"), ("7", "title_g"), ("8", "title_h"), ("9", "title_i")]
            self.assertEqual(result, expected)

    def test_extract_clustered_lines_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output = Path(tmpdir) / "test.temp"
            temp_output.write_text("", encoding="utf-8")
            result = utils.aggregate_titles._extract_clustered_lines(temp_output)
            self.assertEqual(result, [])

    def test_extract_clustered_lines_all_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output = Path(tmpdir) / "test.temp"
            temp_output.write_text("1\t1\t1\ttitle_a\n2\t2\t2\ttitle_b\t3\ttitle_c\n", encoding="utf-8")
            result = utils.aggregate_titles._extract_clustered_lines(temp_output)
            self.assertEqual(result, [])

    def test_no_shell_true_in_module(self) -> None:
        """subprocess.Popen(shell=True)가 모듈에 존재하지 않는지 확인"""
        import inspect

        source = inspect.getsource(utils.aggregate_titles)
        self.assertNotIn("shell=True", source)


# ────────────────────────────────────────────────────────
# From test_aggregate_titles_main.py
# ────────────────────────────────────────────────────────
class TestAggregateTitlesMain(unittest.TestCase):
    """utils/aggregate_titles.py main() 함수 테스트"""

    def test_main_no_args(self) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        with patch.object(_sys, "argv", ["aggregate_titles.py"]):
            result = main()
        self.assertEqual(result, -1)

    def test_main_with_t_option_no_args(self) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        with patch.object(_sys, "argv", ["aggregate_titles.py", "-t", "0.5"]):
            result = main()
        self.assertEqual(result, -1)

    def test_main_with_multiple_options_no_args(self) -> None:
        """여러 옵션을 전달하여 optlist 루프 반복 분기(46->45) 커버"""
        import sys as _sys
        from utils.aggregate_titles import main

        with patch.object(_sys, "argv", ["aggregate_titles.py", "-f", "dummy", "-t", "0.5"]):
            result = main()
        self.assertEqual(result, -1)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_with_stdin_data(self, mock_stdin, mock_exec_cmd, mock_logger) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle Two\textra2", "http://link3.com\tTitle Three\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(_sys, "argv", ["aggregate_titles.py", file_prefix]):
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
    def test_main_comment_lines_skipped(self, mock_stdin, mock_exec_cmd, mock_logger) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["# this is a comment", "http://link1.com\tTitle One\textra1", "# another comment", "http://link2.com\tTitle Two\textra2"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(_sys, "argv", ["aggregate_titles.py", file_prefix]):
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
    def test_main_title_deduplication(self, mock_stdin, mock_exec_cmd, mock_logger) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle One\textra2", "http://link3.com\tTitle Two\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(_sys, "argv", ["aggregate_titles.py", file_prefix]):
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
    def test_main_with_t_option_and_data(self, mock_stdin, mock_exec_cmd, mock_logger) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            with patch.object(_sys, "argv", ["aggregate_titles.py", "-t", "0.7", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            # hcluster command should include threshold
            cmd_arg = mock_exec_cmd.call_args[0][0]
            self.assertIn("-t '0.7'", cmd_arg)

    @patch("utils.aggregate_titles.LOGGER")
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_main_output_file_written(self, mock_stdin, mock_exec_cmd, mock_logger) -> None:
        import sys as _sys
        from utils.aggregate_titles import main

        mock_stdin.return_value = ["http://link1.com\tTitle One\textra1", "http://link2.com\tTitle Two\textra2", "http://link3.com\tTitle Three\textra3"]
        mock_exec_cmd.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            file_prefix = str(Path(tmpdir) / "test_output")
            # Create a temp_output file that _extract_clustered_lines will read
            temp_output = Path(file_prefix + ".temp")
            temp_output.write_text("1\t3\t1\tTitle One\t2\tTitle Two\t3\tTitle Three\n", encoding="utf-8")

            with patch.object(_sys, "argv", ["aggregate_titles.py", file_prefix]):
                result = main()

            self.assertEqual(result, 0)
            output = Path(file_prefix + ".output")
            self.assertTrue(output.exists())
            content = output.read_text(encoding="utf-8")
            self.assertIn("http://link1.com", content)


# ────────────────────────────────────────────────────────
# From test_aggregate_titles_main.py: defect fixes
# ────────────────────────────────────────────────────────
class TestDefect4LoggerFormatString(unittest.TestCase):
    """result에 %가 포함되어도 LOGGER.debug가 TypeError를 발생시키지 않아야 한다."""

    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_percent_in_result_no_error(self, mock_stdin, mock_exec):
        """result에 URL 인코딩(%20 등)이 포함되어도 로깅이 안전해야 한다."""
        mock_stdin.return_value = ["http://example.com\ttitle1\textra\n"]
        mock_exec.return_value = ("https://example.com/%20encoded%2Fpath", "")

        with tempfile.TemporaryDirectory() as tmp:
            intermediate = Path(tmp) / "test.intermediate"
            temp_output = Path(tmp) / "test.temp"
            output_file = Path(tmp) / "test.output"
            temp_output.touch()

            with patch("sys.argv", ["prog", "-t", "0.5", str(Path(tmp) / "test")]):
                from utils.aggregate_titles import main

                main()


class TestDefect4LoggerEdgeCases(unittest.TestCase):
    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_multiple_percent_signs_in_result(self, mock_stdin, mock_exec):
        """result에 여러 % 문자가 포함되어도 안전해야 한다."""
        mock_stdin.return_value = ["http://a.com\ttitle1\tx\n"]
        mock_exec.return_value = ("100% done %s %d %%", "some error %20")

        with tempfile.TemporaryDirectory() as tmp:
            temp_output = Path(tmp) / "test.temp"
            temp_output.touch()
            with patch("sys.argv", ["prog", str(Path(tmp) / "test")]):
                from utils.aggregate_titles import main

                main()

    @patch("utils.aggregate_titles.Process.exec_cmd")
    @patch("utils.aggregate_titles.IO.read_stdin_as_line_list")
    def test_empty_result_and_error(self, mock_stdin, mock_exec):
        """빈 result와 error에서도 안전해야 한다."""
        mock_stdin.return_value = ["http://a.com\ttitle1\tx\n"]
        mock_exec.return_value = ("", "")

        with tempfile.TemporaryDirectory() as tmp:
            temp_output = Path(tmp) / "test.temp"
            temp_output.touch()
            with patch("sys.argv", ["prog", str(Path(tmp) / "test")]):
                from utils.aggregate_titles import main

                main()


class TestExtractClusteredLinesEmptyLines(unittest.TestCase):
    """빈 줄이 섞인 TSV 입력에서 빈 줄을 건너뛰는지 검증 (branch 28->29)"""

    def test_empty_lines_mixed_with_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_output = Path(tmpdir) / "test.temp"
            temp_output.write_text("1\t3\t1\ttitle_a\t2\ttitle_b\t3\ttitle_c\n\n\n2\t3\t4\ttitle_d\t5\ttitle_e\t6\ttitle_f\n", encoding="utf-8")
            result = utils.aggregate_titles._extract_clustered_lines(temp_output)
            expected = [("1", "title_a"), ("2", "title_b"), ("3", "title_c"), ("4", "title_d"), ("5", "title_e"), ("6", "title_f")]
            self.assertEqual(result, expected)


class TestMainBlock(unittest.TestCase):
    """if __name__ == '__main__' 블록 커버리지 (branch 95->96)"""

    def test_main_block_execution(self) -> None:
        """__main__ 블록이 sys.exit(main())을 호출하는지 검증"""
        import types

        mod_file = utils.aggregate_titles.__file__
        src = Path(mod_file).read_text(encoding="utf-8")
        code = compile(src, mod_file, "exec")  # noqa: S102
        mod = types.ModuleType("__main__")
        mod.__name__ = "__main__"
        mod.__file__ = mod_file
        with patch("sys.argv", ["aggregate_titles.py"]):
            with self.assertRaises(SystemExit) as cm:
                eval(code, mod.__dict__)  # noqa: S307 - test code evaluating module source
        self.assertEqual(cm.exception.code, -1)


if __name__ == "__main__":
    unittest.main()
