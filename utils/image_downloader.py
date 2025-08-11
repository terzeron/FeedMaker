#!/usr/bin/env python


import re
import time
import logging
from pathlib import Path
from base64 import b64decode
from typing import Optional
import cairosvg
import pyheif
from PIL import Image, ImageOps, UnidentifiedImageError
from bin.feed_maker_util import FileManager, PathUtil, Env
from bin.crawler import Crawler


LOGGER = logging.getLogger(__name__)


class ImageDownloader:
    BLOCKED_DOMAINS = ["egloos.com", "hanafos.com"]
    
    @staticmethod
    def download_image(crawler: Crawler, feed_img_dir_path: Path, img_url: str, quality: int = 75) -> tuple[Optional[Path], Optional[str]]:
        LOGGER.debug(f"Downloading image: {img_url[:30]}")

        # Check for blocked domains
        if any(domain in img_url for domain in ImageDownloader.BLOCKED_DOMAINS):
            LOGGER.warning(f"Skipping download from blocked domain: {img_url}")
            return None, None

        cache_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url)
        if cache_file_path.is_file() and cache_file_path.stat().st_size > 0:
            return cache_file_path, FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=cache_file_path.suffix)

        # 데이터 URI (base64) 처리
        m = re.search(r'^data:image/(?P<ext>png|jpeg|jpg|webp);base64,(?P<data>.+)', img_url)
        if m:
            img_data = m.group("data")
            ext = m.group('ext')
            suffix = f".{ext}"
            temp_img_file_path = cache_file_path.with_suffix(suffix)
            with open(temp_img_file_path, "wb") as outfile:
                outfile.write(b64decode(img_data))

            # If already WebP, don't re-encode; just use as-is
            if ext.lower() == 'webp':
                return temp_img_file_path, FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=temp_img_file_path.suffix)

            # Otherwise, convert to WebP for consistency
            new_cache_file_path = ImageDownloader.convert_image_format(temp_img_file_path, quality=quality)
            if new_cache_file_path and new_cache_file_path.is_file():
                return new_cache_file_path, FileManager.get_cache_url(Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_img_dir_path.name, img_url, suffix=new_cache_file_path.suffix)
            return None, None

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
        oriented_img = ImageOps.exif_transpose(img)
        if oriented_img:
            img = oriented_img

        # 너비 제한 (iPad Pro 12.9" 세로 모드 최적화 - 2048px 너비)
        # 실제로는 1600px 정도면 충분히 선명하면서도 용량 절약
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
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
                optimized_img.convert("RGB").save(new_cache_file_path, "WEBP", quality=quality)
            cache_file_path.unlink(missing_ok=True)
            new_cache_file_path.with_suffix(".png").unlink(missing_ok=True)
            return new_cache_file_path

        if any(ftyp in header for ftyp in [b"ftypheic", b"ftypheix", b"ftyphevc", b"ftyphevx"]):
            heif_file = pyheif.read(str(cache_file_path))
            img = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data)
            optimized_img = ImageDownloader.optimize_for_webtoon(img)
            new_cache_file_path = cache_file_path.with_suffix(".webp")
            optimized_img.convert("RGB").save(new_cache_file_path, "WEBP", quality=quality)
            return new_cache_file_path

        try:
            with Image.open(cache_file_path) as img:
                # If already WEBP, avoid recompressing unless resizing is needed or naming needs suffix
                if getattr(img, 'format', '').upper() == 'WEBP':
                    optimized_img = ImageDownloader.optimize_for_webtoon(img)
                    target_path = cache_file_path.with_suffix('.webp')
                    try:
                        # If no resize needed and suffix already .webp, reuse file
                        if optimized_img.size == img.size and cache_file_path.suffix == '.webp':
                            return cache_file_path
                        # If no resize needed but suffix missing, just rename
                        if optimized_img.size == img.size and cache_file_path.suffix != '.webp':
                            if not target_path.exists():
                                cache_file_path.rename(target_path)
                            else:
                                # fallback to save if target exists
                                optimized_img.convert('RGB').save(target_path, 'WEBP', quality=quality)
                                if cache_file_path != target_path:
                                    cache_file_path.unlink(missing_ok=True)
                            return target_path
                        # Resize or orientation fix needed → save as WEBP
                        optimized_img.convert('RGB').save(target_path, 'WEBP', quality=quality)
                        if cache_file_path != target_path:
                            cache_file_path.unlink(missing_ok=True)
                        return target_path
                    except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
                        LOGGER.warning(f"WEBP 처리 실패: {e}")
                        return None

                # Non-WEBP → convert to WEBP
                optimized_img = ImageDownloader.optimize_for_webtoon(img)
                new_cache_file_path = cache_file_path.with_suffix('.webp')
                try:
                    optimized_img.convert('RGB').save(new_cache_file_path, 'WEBP', quality=quality)
                    if cache_file_path != new_cache_file_path:
                        cache_file_path.unlink(missing_ok=True)
                    return new_cache_file_path
                except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
                    LOGGER.warning(f"WEBP 저장 실패: {e}")
                    return None
        except UnidentifiedImageError:
            LOGGER.warning(f"Cannot identify image format: {cache_file_path}")

        return None
