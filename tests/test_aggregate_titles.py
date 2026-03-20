#!/usr/bin/env python
# -*- coding: utf-8 -*-


import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
