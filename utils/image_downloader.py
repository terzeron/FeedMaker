#!/usr/bin/env python


import re
import time
import logging
from pathlib import Path
from base64 import b64decode
from typing import Optional
import cairosvg
import pyheif
from PIL import Image, UnidentifiedImageError
from bin.feed_maker_util import FileManager
from bin.crawler import Crawler


LOGGER = logging.getLogger(__name__)


class ImageDownloader:
    @staticmethod
    def download_image(crawler: Crawler, feed_img_dir_path: Path, img_url: str) -> Optional[Path]:
        LOGGER.debug(f"Downloading image: {img_url[:30]}")

        cache_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url)
        if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
            return cache_file_path

        # 데이터 URI (base64) 처리
        m = re.search(r'^data:image/(?P<ext>png|jpeg|jpg);base64,(?P<data>.+)', img_url)
        if m:
            img_data, suffix = m.group("data"), f".{m.group('ext')}"
            img_file_path = cache_file_path.with_suffix(suffix)
            with open(img_file_path, "wb") as outfile:
                outfile.write(b64decode(img_data))
            return img_file_path

        # HTTP 다운로드 처리
        if img_url.startswith("http"):
            result, _, _ = crawler.run(img_url, download_file=cache_file_path)
            if not result:
                time.sleep(5)
                result, _, _ = crawler.run(img_url, download_file=cache_file_path)
                if not result:
                    return None

            # 파일 포맷 확인 및 변환
            return ImageDownloader.convert_image_format(cache_file_path)

        return None


    @staticmethod
    def convert_image_format(cache_file_path: Path) -> Optional[Path]:
        with cache_file_path.open("rb") as infile:
            header = infile.read(1024)

        if header.startswith(b"<svg"):
            new_cache_file_path = cache_file_path.with_suffix(".png")
            cairosvg.svg2png(url=str(cache_file_path), write_to=str(new_cache_file_path))
            cache_file_path.unlink(missing_ok=True)
            return new_cache_file_path

        if any(ftyp in header for ftyp in [b"ftypheic", b"ftypheix", b"ftyphevc", b"ftyphevx"]):
            heif_file = pyheif.read(str(cache_file_path))
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
            new_cache_file_path = cache_file_path.with_suffix(".png")
            img.save(new_cache_file_path, "PNG")
            return new_cache_file_path

        try:
            with Image.open(cache_file_path) as img:
                if img.format in ("JPEG", "PNG", "WEBP", "GIF"):
                    new_cache_file_path = cache_file_path.with_suffix("." + img.format.lower())
                    cache_file_path.rename(new_cache_file_path)
                    return new_cache_file_path

                new_cache_file_path = cache_file_path.with_suffix(".png")
                img.convert("RGB").save(new_cache_file_path, "PNG")
                cache_file_path.unlink(missing_ok=True)
                return new_cache_file_path
        except UnidentifiedImageError:
            LOGGER.warning(f"Cannot identify image format: {cache_file_path}")

        return None
