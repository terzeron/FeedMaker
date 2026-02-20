#!/usr/bin/env python


import json
import uuid
import logging.config
import time
from pathlib import Path
from typing import Protocol
from enum import Enum

from bin.feed_maker_util import Env
from bin.crawler import Crawler, Method


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


# 번역 서비스 제공자 구분을 위한 Enum 정의
class TranslationProvider(Enum):
    DEEPL = 'deepl'
    AZURE = 'azure'
    GOOGLE = 'google'
    CLAUDE = 'claude'


class TranslationService(Protocol):
    MAX_ITEMS_PER_BATCH = 20
    # 서비스 제공자를 나타내는 속성
    provider: TranslationProvider

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        ...

    @staticmethod
    def chunk_by_items(texts: list[str], max_items: int = MAX_ITEMS_PER_BATCH) -> list[list[str]]:
        batch = []
        out: list[list[str]] = []
        for text in texts:
            batch.append(text)
            if len(batch) >= max_items:
                out.append(batch)
                batch = []
        if batch:
            out.append(batch)
        return out


class DeepLTranslationService(TranslationService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api-free.deepl.com/v2/translate"
        # 서비스 제공자 설정
        self.provider = TranslationProvider.DEEPL

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        result_map: dict[str, str] = {}
        headers = {"Authorization": f"DeepL-Auth-Key {self.api_key}"}
        # Crawler 클라이언트 사용
        client = Crawler(method=Method.POST, headers=headers, timeout=10)

        batches = TranslationService.chunk_by_items(texts, TranslationService.MAX_ITEMS_PER_BATCH)
        for batch in batches:
            payload = {
                "text": batch,
                "target_lang": "KO",
                "preserve_formatting": 1,
                "split_sentences": "nonewlines"
            }

            try:
                # Crawler를 통해 요청
                response_text, error_msg, _ = client.run(self.endpoint, data=payload)
                if not response_text:
                    LOGGER.error(f"DeepL translation request failed: {error_msg}")
                    continue
                time.sleep(1)
                data = json.loads(response_text)
                if "translations" in data:
                    translations = data["translations"]
                    for en, translation in zip(batch, translations):
                        ko = translation.get("text", "")
                        result_map[en] = ko
            except Exception as e:
                LOGGER.error(f"DeepL translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is DeepLTranslationService


class AzureTranslationService(TranslationService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=ko"
        # 서비스 제공자 설정
        self.provider = TranslationProvider.AZURE

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        result_map: dict[str, str] = {}
        # Crawler 클라이언트 사용
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Ocp-Apim-Subscription-Region": "koreacentral",
            "Content-type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4())
        }
        client = Crawler(method=Method.POST, headers=headers, timeout=10)
        batches = TranslationService.chunk_by_items(texts, TranslationService.MAX_ITEMS_PER_BATCH)
        for batch in batches:
            payload = [{"text": t} for t in batch]

            try:
                response_text, error_msg, _ = client.run(self.endpoint, data=json.dumps(payload))
                if not response_text:
                    LOGGER.error(f"Azure translation request failed: {error_msg}")
                    continue
                time.sleep(1)
                data = json.loads(response_text)
                for payload_item, data_item in zip(payload, data):
                    en = payload_item["text"]
                    if "translations" in data_item:
                        translations = data_item.get("translations", [])
                        ko = translations[0].get("text", "")
                        result_map[en] = ko
            except Exception as e:
                LOGGER.error(f"Azure translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is AzureTranslationService


class GoogleTranslationService(TranslationService):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://translation.googleapis.com/language/translate/v2"
        # 서비스 제공자 설정
        self.provider = TranslationProvider.GOOGLE

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        result_map: dict[str, str] = {}
        # Crawler 클라이언트 사용
        client = Crawler(method=Method.POST, headers={'Content-Type': 'application/json'}, timeout=10)

        batches = TranslationService.chunk_by_items(texts, TranslationService.MAX_ITEMS_PER_BATCH)
        for batch in batches:
            payload = {
                'q': batch,
                'key': self.api_key,
            }

            try:
                response_text, error_msg, _ = client.run(self.endpoint, data=json.dumps(payload))
                if not response_text:
                    LOGGER.error(f"Google translation request failed: {error_msg}")
                    continue
                time.sleep(1)
                data = json.loads(response_text)
                if "data" in data and "translations" in data["data"]:
                    translations = data["data"]["translations"]
                    for original_text, translation in zip(batch, translations):
                        translated_text = translation.get("translatedText", "")
                        result_map[original_text] = translated_text
            except Exception as e:
                LOGGER.error(f"Google translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is GoogleTranslationService


class ClaudeTranslationService(TranslationService):
    MAX_ITEMS_PER_BATCH = 10

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://api.anthropic.com/v1/messages"
        self.provider = TranslationProvider.CLAUDE

    def translate_batch(self, texts: list[str]) -> dict[str, str]:
        result_map: dict[str, str] = {}
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        client = Crawler(method=Method.POST, headers=headers, timeout=30)

        batches = TranslationService.chunk_by_items(texts, self.MAX_ITEMS_PER_BATCH)
        for batch in batches:
            numbered_texts = "\n".join(f"{i+1}. {t}" for i, t in enumerate(batch))
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": f"Translate the following English texts to Korean. "
                                   f"Return ONLY a JSON array of translated strings in the same order, "
                                   f"with no additional text or explanation.\n\n{numbered_texts}"
                    }
                ]
            })

            try:
                response_text, error_msg, _ = client.run(self.endpoint, data=payload)
                if not response_text:
                    LOGGER.error(f"Claude translation request failed: {error_msg}")
                    continue
                time.sleep(1)
                data = json.loads(response_text)
                # Messages API 응답에서 텍스트 추출
                content_blocks = data.get("content", [])
                text_content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")
                # JSON 배열 파싱
                translations = json.loads(text_content)
                if isinstance(translations, list) and len(translations) == len(batch):
                    for en, ko in zip(batch, translations):
                        result_map[en] = ko
                else:
                    LOGGER.error(f"Claude translation returned unexpected format: expected {len(batch)} items, got {len(translations) if isinstance(translations, list) else 'non-list'}")
            except (json.JSONDecodeError, KeyError) as e:
                LOGGER.error(f"Claude translation response parsing failed: {e}")
                continue
            except Exception as e:
                LOGGER.error(f"Claude translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is ClaudeTranslationService


class TranslationServiceFactory:
    @staticmethod
    def create_service() -> TranslationService | None:
        if Env.get("DEEPL_API_KEY"):
            return DeepLTranslationService(Env.get("DEEPL_API_KEY"))
        if Env.get("AZURE_API_KEY"):
            return AzureTranslationService(Env.get("AZURE_API_KEY"))
        if Env.get("GOOGLE_API_KEY"):
            return GoogleTranslationService(Env.get("GOOGLE_API_KEY"))
        if Env.get("ANTHROPIC_API_KEY"):
            return ClaudeTranslationService(Env.get("ANTHROPIC_API_KEY"))
        return None


class Translation:
    def __init__(self):
        self.service = TranslationServiceFactory.create_service()
        if not self.service:
            LOGGER.error("어떤 번역 서비스 API 키도 설정되지 않음")

    @staticmethod
    def _load_translation_cache(file_path: Path) -> dict[str, str]:
        """번역 캐시 파일을 로드합니다."""
        if file_path.is_file():
            with file_path.open("r", encoding="utf-8") as infile:
                return json.load(infile)
        return {}

    @staticmethod
    def _save_translation_cache(file_path: Path, translation_map: dict[str, str]) -> None:
        """번역 캐시를 파일에 저장합니다."""
        with file_path.open("w", encoding="utf-8") as outfile:
            json.dump(translation_map, outfile, ensure_ascii=False, indent=4)

    def translate(self, texts: list[tuple[str, str]], do_save: bool = True) -> list[tuple[str, str]]:
        translation_map_file_path = Path(Env.get("FM_WORK_DIR")) / "translation_map.json"

        # 기존 번역 캐시 로드
        all_translation_map = Translation._load_translation_cache(translation_map_file_path)

        # 번역이 필요한 텍스트만 필터링
        fresh_translation_map: dict[str, str] = {}
        src_text_list: list[str] = [text for _, text in texts if text not in all_translation_map]

        # 번역 서비스 생성 및 사용
        if src_text_list:
            if not self.service:
                LOGGER.warning("번역 서비스가 없어 %d개 텍스트를 번역하지 못합니다", len(src_text_list))
            else:
                LOGGER.debug(f"캐시에 없는 {len(src_text_list)}개 텍스트를 번역합니다...")
                fresh_translation_map = self.service.translate_batch(src_text_list)

            if fresh_translation_map:
                LOGGER.debug(f"번역 완료: {len(fresh_translation_map)}개")
                # 캐시 갱신
                for en, ko in fresh_translation_map.items():
                    all_translation_map[en] = ko
            else:
                LOGGER.debug("번역 실패: 번역 서비스에서 결과를 받지 못했습니다")
        else:
            LOGGER.debug("모든 텍스트가 캐시에 있습니다")

        # 번역 결과 저장
        if do_save:
            Translation._save_translation_cache(translation_map_file_path, all_translation_map)

        # 링크-원문 매핑 순회하며 포맷된 결과 구성 및 캐시 갱신
        # 중복된 텍스트는 마지막 링크만 사용
        unique: dict[str, str] = {}
        for link, en in texts:
            unique[en] = link
        new_result_list: list[tuple[str, str]] = []
        for en, link in unique.items():
            ko = all_translation_map.get(en, en)
            new_result_list.append((link, f"{ko}({en})"))
        return new_result_list
