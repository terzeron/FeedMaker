#!/usr/bin/env python


import re
import time
import logging
from pathlib import Path
from base64 import b64decode
from typing import Optional
import cairosvg # type: ignore[import]
import pyheif # type: ignore[import]
from PIL import Image, UnidentifiedImageError
from bin.feed_maker_util import FileManager, PathUtil, Env
from bin.crawler import Crawler


LOGGER = logging.getLogger(__name__)


class ImageDownloader:
    @staticmethod
    def download_image(crawler: Crawler, feed_img_dir_path: Path, img_url: str, quality: int = 75) -> tuple[Optional[Path], Optional[str]]:
        LOGGER.debug(f"Downloading image: {img_url[:30]}")

        cache_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url)
        if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
            return cache_file_path, FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=cache_file_path.suffix)

        # 데이터 URI (base64) 처리
        m = re.search(r'^data:image/(?P<ext>png|jpeg|jpg);base64,(?P<data>.+)', img_url)
        if m:
            img_data, suffix = m.group("data"), f".{m.group('ext')}"
            img_file_path = cache_file_path.with_suffix(suffix)
            with open(img_file_path, "wb") as outfile:
                outfile.write(b64decode(img_data))
            return img_file_path, FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=suffix)

        # HTTP 다운로드 처리
        if img_url.startswith("http"):
            result, _, _ = crawler.run(img_url, download_file=cache_file_path)
            if not result:
                time.sleep(5)
                result, _, _ = crawler.run(img_url, download_file=cache_file_path)
                if not result:
                    return None, None

            # 파일 포맷 확인 및 변환
            new_cache_file_path = ImageDownloader.convert_image_format(cache_file_path, quality=quality)
            if new_cache_file_path and new_cache_file_path.is_file():
                suffix = new_cache_file_path.suffix
                cache_url = FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=suffix)
                url_img_short = img_url if not img_url.startswith("data:image") else img_url[:30]
                LOGGER.debug("%s -> %s / %s", url_img_short, PathUtil.short_path(new_cache_file_path), cache_url)
                return new_cache_file_path, cache_url

        return None, None


    @staticmethod
    def optimize_for_webtoon(img: Image.Image, max_width: int = 1600) -> Image.Image:
        """웹툰용 이미지 최적화"""
        # 너비 제한 (iPad Pro 12.9" 세로 모드 최적화 - 2048px 너비)
        # 실제로는 1600px 정도면 충분히 선명하면서도 용량 절약
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)
        
        return img

    @staticmethod
    def convert_image_format(cache_file_path: Path, quality: int = 75) -> Optional[Path]:
        with cache_file_path.open("rb") as infile:
            header = infile.read(1024)

        if header.startswith(b"<svg"):
            new_cache_file_path = cache_file_path.with_suffix(".webp")
            cairosvg.svg2png(url=str(cache_file_path), write_to=str(new_cache_file_path.with_suffix(".png")))
            # PNG를 WebP로 최적화
            with Image.open(new_cache_file_path.with_suffix(".png")) as img:
                optimized_img = ImageDownloader.optimize_for_webtoon(img)
                optimized_img.save(new_cache_file_path, "WEBP", quality=quality, optimize=True)
            cache_file_path.unlink(missing_ok=True)
            new_cache_file_path.with_suffix(".png").unlink(missing_ok=True)
            return new_cache_file_path

        if any(ftyp in header for ftyp in [b"ftypheic", b"ftypheix", b"ftyphevc", b"ftyphevx"]):
            heif_file = pyheif.read(str(cache_file_path))
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
            optimized_img = ImageDownloader.optimize_for_webtoon(img)
            new_cache_file_path = cache_file_path.with_suffix(".webp")
            optimized_img.save(new_cache_file_path, "WEBP", quality=quality, optimize=True)
            return new_cache_file_path

        try:
            with Image.open(cache_file_path) as img:
                optimized_img = ImageDownloader.optimize_for_webtoon(img)
                
                # 모든 포맷을 WebP로 변환 (iOS 14+ 최적화)
                new_cache_file_path = cache_file_path.with_suffix(".webp")
                
                # WebP 저장 시도
                try:
                    optimized_img.save(new_cache_file_path, "WEBP", quality=quality, optimize=True)
                    if cache_file_path != new_cache_file_path:
                        cache_file_path.unlink(missing_ok=True)
                    return new_cache_file_path
                except Exception as e:
                    LOGGER.warning(f"WebP 저장 실패, JPEG로 폴백: {e}")
                    # WebP 실패 시 JPEG로 폴백
                    fallback_path = cache_file_path.with_suffix(".jpg")
                    optimized_img.convert("RGB").save(fallback_path, "JPEG", quality=quality, optimize=True)
                    if cache_file_path != fallback_path:
                        cache_file_path.unlink(missing_ok=True)
                    return fallback_path
        except UnidentifiedImageError:
            LOGGER.warning(f"Cannot identify image format: {cache_file_path}")

        return None
