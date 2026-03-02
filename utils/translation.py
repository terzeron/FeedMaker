#!/usr/bin/env python


import sys
import getopt
import json
import re
import uuid
import logging.config
import time
from pathlib import Path
from typing import Protocol
from enum import Enum

# 캐시 항목 TTL: 7일
_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# 번역 요청 간 sleep 시간(초)
_SLEEP_SECONDS: float = 1

# 내부 타임스탬프 캐시 타입: {"en": {"t": "ko", "ts": unix_epoch}}
_TimestampedCache = dict[str, dict]

from bin.feed_maker_util import Env
from bin.crawler import Crawler, Method


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

_STATUS_CODE_RE = re.compile(r"status code '(\d+)'")
_RATE_LIMIT_CODES = {"429", "456", "529"}
_AUTH_ERROR_CODES = {"401", "403"}
_UNRECOVERABLE_CODES = _RATE_LIMIT_CODES | _AUTH_ERROR_CODES


def _is_rate_limit_error(error_msg: str) -> bool:
    """Crawler error_msg에서 rate limit 관련 상태 코드(429/456/529)를 감지한다."""
    m = _STATUS_CODE_RE.search(error_msg)
    return m is not None and m.group(1) in _RATE_LIMIT_CODES


def _is_unrecoverable_error(error_msg: str) -> bool:
    """재시도해도 결과가 동일한 오류(인증 실패, rate limit 등)를 감지한다."""
    m = _STATUS_CODE_RE.search(error_msg)
    return m is not None and m.group(1) in _UNRECOVERABLE_CODES


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
                    LOGGER.debug(f"DeepL translation request failed: {error_msg}")
                    if _is_unrecoverable_error(error_msg):
                        break
                    continue
                time.sleep(_SLEEP_SECONDS)
                data = json.loads(response_text)
                if "translations" in data:
                    translations = data["translations"]
                    for en, translation in zip(batch, translations):
                        ko = translation.get("text", "")
                        result_map[en] = ko
            except Exception as e:
                LOGGER.debug(f"DeepL translation request failed: {e}")
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
                    LOGGER.debug(f"Azure translation request failed: {error_msg}")
                    if _is_unrecoverable_error(error_msg):
                        break
                    continue
                time.sleep(_SLEEP_SECONDS)
                data = json.loads(response_text)
                for payload_item, data_item in zip(payload, data):
                    en = payload_item["text"]
                    if "translations" in data_item:
                        translations = data_item.get("translations", [])
                        ko = translations[0].get("text", "")
                        result_map[en] = ko
            except Exception as e:
                LOGGER.debug(f"Azure translation request failed: {e}")
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
                    LOGGER.debug(f"Google translation request failed: {error_msg}")
                    if _is_unrecoverable_error(error_msg):
                        break
                    continue
                time.sleep(_SLEEP_SECONDS)
                data = json.loads(response_text)
                if "data" in data and "translations" in data["data"]:
                    translations = data["data"]["translations"]
                    for original_text, translation in zip(batch, translations):
                        translated_text = translation.get("translatedText", "")
                        result_map[original_text] = translated_text
            except Exception as e:
                LOGGER.debug(f"Google translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is GoogleTranslationService


class ClaudeTranslationService(TranslationService):
    MAX_ITEMS_PER_BATCH = 20
    SYSTEM_PROMPT = "Translate English to Korean. Return ONLY a JSON array of translated strings, same order."

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
        client = Crawler(method=Method.POST, headers=headers, timeout=60)

        batches = TranslationService.chunk_by_items(texts, self.MAX_ITEMS_PER_BATCH)
        for batch in batches:
            texts_json = json.dumps(batch, ensure_ascii=False)
            payload = json.dumps({
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": max(len(batch) * 100, 1024),
                "system": self.SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": texts_json},
                    {"role": "assistant", "content": "["}
                ]
            })

            try:
                response_text, error_msg, _ = client.run(self.endpoint, data=payload)
                if not response_text:
                    LOGGER.debug(f"Claude translation request failed: {error_msg}")
                    if _is_unrecoverable_error(error_msg):
                        break
                    continue
                time.sleep(_SLEEP_SECONDS)
                data = json.loads(response_text)
                # API 에러 응답 체크 (HTTP 200이지만 type=error)
                if data.get("type") == "error":
                    err = data.get("error", {})
                    LOGGER.warning(f"Claude API error: {err.get('type', 'unknown')} - {err.get('message', '')}")
                    break
                # stop_reason 체크: max_tokens이면 응답이 잘렸을 가능성
                stop_reason = data.get("stop_reason", "")
                if stop_reason == "max_tokens":
                    LOGGER.warning("Claude: 응답이 max_tokens로 잘림, 복구 시도")
                # Messages API 응답에서 텍스트 추출
                content_blocks = data.get("content", [])
                text_content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        text_content += block.get("text", "")
                # prefill한 "[" + 응답 텍스트로 JSON 배열 완성
                text_content = "[" + text_content.strip()
                # JSON 배열 파싱 — 잘린 응답 복구 시도
                try:
                    translations = json.loads(text_content)
                except json.JSONDecodeError:
                    # 잘린 JSON에서 마지막 완전한 항목까지 복구
                    last_comma = text_content.rfind('",')
                    if last_comma != -1:
                        text_content = text_content[:last_comma + 1] + "]"
                        translations = json.loads(text_content)
                    else:
                        raise
                if isinstance(translations, list):
                    if len(translations) < len(batch):
                        LOGGER.warning(f"Claude: {len(batch)}개 중 {len(translations)}개만 반환, 부분 매핑")
                    for en, ko in zip(batch, translations):
                        if isinstance(ko, str) and ko:
                            result_map[en] = ko
                else:
                    LOGGER.debug(f"Claude translation returned unexpected format: expected list, got {type(translations).__name__}")
            except (json.JSONDecodeError, KeyError) as e:
                LOGGER.debug(f"Claude translation response parsing failed: {e}")
                continue
            except Exception as e:
                LOGGER.debug(f"Claude translation request failed: {e}")
                continue

        return result_map

    def __eq__(self, other) -> bool:
        return other is ClaudeTranslationService


class TranslationServiceFactory:
    # 우선순위: Azure(2M) → DeepL(500K) → Google(500K) → Claude(유료)
    _PRIORITY: list[tuple[str, type]] = [
        ("AZURE_API_KEY", AzureTranslationService),
        ("DEEPL_API_KEY", DeepLTranslationService),
        ("GOOGLE_API_KEY", GoogleTranslationService),
        ("ANTHROPIC_API_KEY", ClaudeTranslationService),
    ]

    @staticmethod
    def create_services() -> list[TranslationService]:
        """사용 가능한 모든 번역 서비스를 우선순위 순으로 반환한다."""
        services: list[TranslationService] = []
        for env_key, cls in TranslationServiceFactory._PRIORITY:
            key = Env.get(env_key)
            if key:
                services.append(cls(key))
        return services

    @staticmethod
    def create_service() -> TranslationService | None:
        """하위 호환: 최우선 서비스 1개만 반환."""
        services = TranslationServiceFactory.create_services()
        return services[0] if services else None


class Translation:
    def __init__(self, provider: TranslationProvider | None = None):
        services = TranslationServiceFactory.create_services()
        if provider is not None:
            services = [s for s in services if s.provider == provider]
        self.services = services
        # 하위 호환
        self.service = self.services[0] if self.services else None
        if not self.services:
            LOGGER.error("어떤 번역 서비스 API 키도 설정되지 않음")

    @staticmethod
    def _load_translation_cache(file_path: Path) -> tuple[dict[str, str], _TimestampedCache]:
        """번역 캐시 파일을 로드하고, 만료 항목을 퍼지한다.

        Returns:
            (flat_map, ts_cache) — flat_map은 {en: ko}, ts_cache는 {en: {"t": ko, "ts": epoch}}
        """
        if not file_path.is_file():
            return {}, {}

        with file_path.open("r", encoding="utf-8") as infile:
            raw: dict = json.load(infile)

        now = int(time.time())

        if raw.get("_version") == 2:
            # v2 포맷: 만료 항목 퍼지
            ts_cache: _TimestampedCache = {}
            flat: dict[str, str] = {}
            for key, val in raw.items():
                if key == "_version":
                    continue
                if isinstance(val, dict) and now - val.get("ts", 0) < _CACHE_TTL_SECONDS:
                    ts_cache[key] = val
                    flat[key] = val.get("t", "")
            return flat, ts_cache
        else:
            # 구 포맷 마이그레이션: 모든 항목에 현재 ts 부여
            ts_cache = {}
            flat = {}
            for key, val in raw.items():
                if isinstance(val, str):
                    ts_cache[key] = {"t": val, "ts": now}
                    flat[key] = val
            return flat, ts_cache

    @staticmethod
    def _save_translation_cache(file_path: Path, ts_cache: _TimestampedCache) -> None:
        """번역 캐시를 v2 포맷으로 저장한다."""
        data: dict = {"_version": 2}
        data.update(ts_cache)
        with file_path.open("w", encoding="utf-8") as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)

    def _translate_with_fallback(self, texts: list[str]) -> dict[str, str]:
        """서비스 순회하며 미번역 항목을 다음 서비스로 넘기는 fallback chain."""
        result: dict[str, str] = {}
        remaining = list(texts)
        for svc in self.services:
            if not remaining:
                break
            LOGGER.debug(f"[fallback] {svc.provider.value}로 {len(remaining)}개 번역 시도")
            partial = svc.translate_batch(remaining)
            if partial:
                translated = dict(partial)
                result.update(translated)
                remaining = [t for t in remaining if t not in translated]
            if not remaining:
                break
        if remaining:
            LOGGER.warning(f"[fallback] {len(remaining)}개 텍스트가 모든 서비스에서 번역 실패")
        return result

    def translate(self, texts: list[tuple[str, str]], do_save: bool = True) -> list[tuple[str, str]]:
        translation_map_file_path = Path(Env.get("FM_WORK_DIR")) / "translation_map.json"

        # 기존 번역 캐시 로드 (만료 항목은 이미 퍼지됨)
        all_translation_map, ts_cache = Translation._load_translation_cache(translation_map_file_path)

        # 번역이 필요한 텍스트만 필터링
        fresh_translation_map: dict[str, str] = {}
        src_text_list: list[str] = [text for _, text in texts if text not in all_translation_map]

        # 번역 서비스 생성 및 사용
        if src_text_list:
            if not self.services:
                LOGGER.warning("번역 서비스가 없어 %d개 텍스트를 번역하지 못합니다", len(src_text_list))
            else:
                LOGGER.debug(f"캐시에 없는 {len(src_text_list)}개 텍스트를 번역합니다...")
                fresh_translation_map = self._translate_with_fallback(src_text_list)

            if fresh_translation_map:
                LOGGER.debug(f"번역 완료: {len(fresh_translation_map)}개")
                now = int(time.time())
                # 캐시 갱신
                for en, ko in fresh_translation_map.items():
                    all_translation_map[en] = ko
                    ts_cache[en] = {"t": ko, "ts": now}
            else:
                LOGGER.debug("번역 실패: 번역 서비스에서 결과를 받지 못했습니다")
        else:
            LOGGER.debug("모든 텍스트가 캐시에 있습니다")

        # 번역 결과 저장
        if do_save:
            Translation._save_translation_cache(translation_map_file_path, ts_cache)

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


def translate_html(html: str, provider: TranslationProvider | None = None) -> str:
    """HTML 문자열에서 사람이 읽을 수 있는 텍스트 노드를 추출하여 번역한 HTML을 반환한다."""
    from bs4 import BeautifulSoup, NavigableString

    soup = BeautifulSoup(html, "html.parser")

    # 번역 대상이 아닌 태그
    skip_tags = {"script", "style", "code", "pre", "textarea"}

    # 텍스트 노드 수집
    text_nodes: list[NavigableString] = []
    for node in soup.descendants:
        if not isinstance(node, NavigableString):
            continue
        if node.parent and node.parent.name in skip_tags:
            continue
        stripped = node.strip()
        if not stripped:
            continue
        text_nodes.append(node)

    if not text_nodes:
        return str(soup), 0

    # 고유 텍스트 목록 추출
    unique_texts = list(dict.fromkeys(node.strip() for node in text_nodes))

    # 번역 캐시 로드
    translation_map_file_path = Path(Env.get("FM_WORK_DIR")) / "translation_map.json"
    cached_map, ts_cache = Translation._load_translation_cache(translation_map_file_path)

    # 캐시에 없는 텍스트만 번역 대상으로 선별
    texts_to_translate = [t for t in unique_texts if t not in cached_map]

    translator = Translation(provider=provider)
    if texts_to_translate:
        LOGGER.debug(f"캐시에 없는 {len(texts_to_translate)}개 텍스트를 번역합니다...")
        fresh_map = translator._translate_with_fallback(texts_to_translate)
        # 새로 번역된 결과를 캐시에 반영 후 저장 (일부 실패해도 성공분은 보존)
        if fresh_map:
            now = int(time.time())
            for en, ko in fresh_map.items():
                cached_map[en] = ko
                ts_cache[en] = {"t": ko, "ts": now}
            Translation._save_translation_cache(translation_map_file_path, ts_cache)

    # 미번역 텍스트 수
    untranslated = sum(1 for t in unique_texts if t not in cached_map)

    # 텍스트 노드 치환
    for node in text_nodes:
        original = node.strip()
        translated = cached_map.get(original)
        if translated:
            # 원본 텍스트 앞뒤 공백 보존
            leading = node[: len(node) - len(node.lstrip())]
            trailing = node[len(node.rstrip()) :]
            node.replace_with(NavigableString(leading + translated + trailing))

    return str(soup), untranslated


def main():
    """표준입력으로 HTML을 받아 텍스트를 번역하여 출력한다."""
    _OPTION_MAP = {
        "-c": TranslationProvider.CLAUDE,
        "-g": TranslationProvider.GOOGLE,
        "-z": TranslationProvider.AZURE,
        "-d": TranslationProvider.DEEPL,
    }
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "cgzdf:t:")
    except getopt.GetoptError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Usage: translation.py [-c|-g|-z|-d] [-f <file>] [-t <seconds>]", file=sys.stderr)
        sys.exit(1)

    global _SLEEP_SECONDS
    provider: TranslationProvider | None = None
    for opt, val in opts:
        if opt in _OPTION_MAP:
            provider = _OPTION_MAP[opt]
        elif opt == "-t":
            _SLEEP_SECONDS = float(val)

    html = sys.stdin.read()
    if not html.strip():
        return
    result, untranslated = translate_html(html, provider=provider)
    if untranslated > 0:
        LOGGER.warning(f"{untranslated}개 텍스트 번역 실패")
        sys.exit(-1)
    print(result)


if __name__ == "__main__":
    main()
