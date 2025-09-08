#!/usr/bin/env python


import json
import uuid
import logging.config
from pathlib import Path
from typing import List, Tuple, Dict

from bin.feed_maker_util import Env
from bin.crawler import Crawler, Method


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

MAX_ITEMS_PER_BATCH = 50


class Translation:
    @staticmethod
    def _chunk_by_items(texts: List[str], max_items: int = MAX_ITEMS_PER_BATCH) -> List[List[str]]:
        batch = []
        out: List[List[str]] = []
        for t in texts:
            t = "" if t is None else str(t)
            batch.append(t)
            if len(batch) >= max_items:
                out.append(batch)
                batch = []
        if batch:
            out.append(batch)
        return out


    @staticmethod
    def _translate_by_deepl(crawler: Crawler, texts: List[str]) -> Dict[str, str]:
        DEEPL_FREE_ENDPOINT = "https://api-free.deepl.com/v2/translate"
    
        translated_list: List[str] = []
        result_map: Dict[str, str] = {}
    
        batches = Translation._chunk_by_items(texts, MAX_ITEMS_PER_BATCH)
        for batch in batches:
            payload = {
                "text": batch,            # 리스트 그대로
                "target_lang": "KO",
                "preserve_formatting": 1,       # 공백/줄바꿈 보존
                "split_sentences": "nonewlines" # 줄바꿈 기준 유지
            }
    
            result, error, _ = crawler.run(url=DEEPL_FREE_ENDPOINT, data=payload)
            if not result or error:
                continue
            data = json.loads(result)
            translated_list = []
            if "translations" in data:
                translations = data["translations"]
                for item in translations:
                    for line in item["text"].split("\n"):
                        translated_list.append(line)
    
            #print(f"{len(batch)=}, {len(translated_list)=}")
            for i in range(len(batch)):
                en = batch[i]
                ko = translated_list[i]
                result_map[en] = ko
    
        return result_map

    @staticmethod
    def _translate_by_azure(crawler: Crawler, texts: List[str]) -> Dict[str, str]:
        AZURE_FREE_ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&to=ko"

        translated_list: List[str]= []
        result_map: Dict[str, str] = {}

        batches = Translation._chunk_by_items(texts, MAX_ITEMS_PER_BATCH)
        for batch in batches:
            payload = [ { "text": t } for t in batch ]
            #print(f"{payload=}")

            result, error, h = crawler.run(url=AZURE_FREE_ENDPOINT, data=json.dumps(payload))
            #print(f"{result=}, {error=}, {h=}")
            if not result or error:
                continue
            data = json.loads(result)
            translated_list = []
            for data_chunk in data:
                if "translations" in data_chunk:
                    translations = data_chunk["translations"]
                    for item in translations:
                        translated_list.append(item["text"])

            #print(f"{len(batch)=}, {len(translated_list)=}")
            for i in range(len(batch)):
                en = batch[i]
                ko = translated_list[i]
                result_map[en] = ko

        return result_map
        
    @staticmethod
    def translate(result_list: List[Tuple[str, str]], do_save=True, do_show_translated_only=False) -> List[Tuple[str, str]]:
        translation_map_file_path = Path(Env.get("FM_WORK_DIR")) / "translation_map.json"
        if translation_map_file_path.is_file():
            with translation_map_file_path.open("r", encoding="utf-8") as infile:
                translation_map = json.load(infile)
        else:
            translation_map = {}
            
        new_result_list: List[Tuple[str, str]] = []
        translation_req_list: List[str] = []
        untranslated_title_link_map: Dict[str, str] = {}
        for (link, en) in result_list:
            #print(f"{link=}, {en=}")
            if en in translation_map:
                # 기존 번역 매핑 활용
                ko = translation_map[en]
                new_result_list.append((link, f"{ko}({en})"))
            else:
                # 신규 번역 필요한 텍스트 수집
                #new_result_list.append((link, title))
                translation_req_list.append(en)
                untranslated_title_link_map[en] = link

        #print(f"{translation_req_list=}")
        deepl_api_key = Env.get("DEEPL_API_KEY")
        deepl_crawler = Crawler(render_js=False, method=Method.POST, headers={"Authorization": f"DeepL-Auth-Key {deepl_api_key}"})
        en_ko_map = Translation._translate_by_deepl(deepl_crawler, translation_req_list)
        if not en_ko_map:
            azure_api_key = Env.get("AZURE_API_KEY")
            azure_crawler = Crawler(render_js=False, method=Method.POST, headers={
                "Ocp-Apim-Subscription-Key": azure_api_key,
                "Ocp-Apim-Subscription-Region": "eastasia",
                "Content-type": "application/json",
                "X-ClientTraceId": str(uuid.uuid4())
            })
            en_ko_map = Translation._translate_by_azure(azure_crawler, translation_req_list)

        for en, link in untranslated_title_link_map.items():
            if en in en_ko_map:
                ko = en_ko_map[en]
                # 결과에 추가
                if do_show_translated_only:
                    new_result_list.append((link, f"{ko}"))
                else:
                    new_result_list.append((link, f"{ko}({en})"))

                # 기존 번역 매핑 업데이트
                translation_map[en] = ko
            else:
                new_result_list.append((link, f"{en}"))

        if do_save:
            with translation_map_file_path.open("w", encoding="utf-8") as outfile:
                json.dump(translation_map, outfile, ensure_ascii=False, indent=4)
    
        return new_result_list
