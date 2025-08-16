#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import json
import unittest
import logging.config
from pathlib import Path

from bin.feed_maker_util import Env


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class TranslationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_cwd = Path.cwd()
        self.work_dir = Path(Env.get("FM_WORK_DIR")) / "translation_test"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        os.chdir(self.work_dir)
        self.translation_map_path = self.work_dir / "translation_map.json"
        if self.translation_map_path.is_file():
            self.translation_map_path.unlink(missing_ok=True)

    def tearDown(self) -> None:
        if self.translation_map_path.is_file():
            self.translation_map_path.unlink(missing_ok=True)
        os.chdir(self._old_cwd)

    def test_chunk_by_items_unit(self) -> None:
        from utils.translation import Translation

        items = ["a", "b", "c", "d", "e"]
        chunks = Translation._chunk_by_items(items, max_items=2)
        self.assertEqual([["a", "b"], ["c", "d"], ["e"]], chunks)

    def test_translate_uses_cache_without_api(self) -> None:
        # 캐시 파일 준비
        cache = {
            "Global warming": "지구 온난화",
            "Speed of light": "빛의 속도",
        }
        self.translation_map_path.write_text(json.dumps(cache, ensure_ascii=False, indent=4), encoding="utf-8")

        from utils.translation import Translation

        result = Translation.translate([
            ("/a", "Global warming"),
            ("/b", "Speed of light"),
        ])

        self.assertIn(("/a", "지구 온난화(Global warming)"), result)
        self.assertIn(("/b", "빛의 속도(Speed of light)"), result)

    @unittest.skipIf(os.getenv("DEEPL_API_KEY", "") == "", "DEEPL_API_KEY not set")
    def test_translate_mixed_cached_and_new_two_lines_each(self) -> None:
        # 캐시에 2건 저장 (이미 번역된 텍스트)
        cache = {
            "Global warming": "지구 온난화",
            "Speed of light": "빛의 속도",
        }
        self.translation_map_path.write_text(json.dumps(cache, ensure_ascii=False, indent=4), encoding="utf-8")

        # 테스트 데이터: 캐시 2건 + 신규 2건 (형용사 명사, 명사 of 명사)
        inputs = [
            ("/a", "Global warming"),           # 캐시
            ("/b", "Speed of light"),           # 캐시
            ("/c", "Artificial intelligence"),  # 신규: 형용사 명사
            ("/d", "Law of gravity"),           # 신규: 명사 of 명사
        ]

        from utils.translation import Translation

        result = Translation.translate(inputs)

        # 캐시 2건은 지정된 한국어로 그대로 반환
        self.assertIn(("/a", "지구 온난화(Global warming)"), result)
        self.assertIn(("/b", "빛의 속도(Speed of light)"), result)

        # 신규 2건은 번역 + 원문 보존
        self.assertTrue(any(link == "/c" and text.endswith("(Artificial intelligence)") for link, text in result))
        self.assertTrue(any(link == "/d" and text.endswith("(Law of gravity)") for link, text in result))

        # 신규 번역의 한국어 핵심어 검증
        def get_ko(part: str) -> str:
            return part.split("(")[0]

        ko_map = {link: get_ko(text) for link, text in result}

        # Artificial intelligence -> '인공'과 '지능' 포함(띄어쓰기 허용)
        self.assertIn("/c", ko_map)
        self.assertRegex(ko_map["/c"], r"인공")
        self.assertRegex(ko_map["/c"], r"지능")

        # Law of gravity -> '법칙' 포함 + '중력' 또는 '만유인력' 포함
        self.assertIn("/d", ko_map)
        self.assertRegex(ko_map["/d"], r"법칙")
        self.assertRegex(ko_map["/d"], r"(중력|만유인력)")

        # 캐시 파일에 4건 모두 저장되었는지 확인
        self.assertTrue(self.translation_map_path.is_file())
        saved = json.loads(self.translation_map_path.read_text(encoding="utf-8"))
        self.assertIn("Global warming", saved)
        self.assertIn("Speed of light", saved)
        self.assertIn("Artificial intelligence", saved)
        self.assertIn("Law of gravity", saved)


if __name__ == "__main__":
    unittest.main()
