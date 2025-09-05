#!/usr/bin/env python
# -*- coding: utf-8 -*-

import getopt
import logging.config
import os
import re
import sys
from pathlib import Path
from typing import Optional, Any, List, Tuple
from PIL import Image

from bin.crawler import Crawler
from bin.feed_maker_util import Config, Env, PathUtil, Process, URL, IO, FileManager
from utils.image_downloader import ImageDownloader

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

# JPEG size limit constant (increased from WebP limit)
JPEG_SIZE_LIMIT = 32767


def download_image_and_read_metadata(feed_dir_path: Path, crawler: Crawler, feed_img_dir_path: Path, page_url: str, quality: int = 75) -> tuple[list[Path], list[str], list[str], list[str]]:
    LOGGER.debug("# download_image_and_read_metadata(feed_dir_path=%r, crawler=%r, feed_img_dir_path=%r, page_url='%s')", PathUtil.short_path(feed_dir_path), crawler, PathUtil.short_path(feed_img_dir_path), page_url)
    img_file_list: list[Path] = []
    img_url_list: list[str] = []
    img_width_list: list[str] = []
    feed_name = feed_dir_path.name

    image_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX")
    feed_img_url_prefix = f"{image_url_prefix}/{feed_name}"

    normal_html_lines = []
    line_list: list[str] = IO.read_stdin_as_line_list()
    for line in line_list:
        line = line.rstrip()
        m = re.search(r'''
                       (?P<pre_text>.*)
                       <img
                       [^>]*
                       src=
                       [\"\']
                       (?P<img_url>[^\"\']+)
                       [\"\']
                       (?P<width_attr>\s*width=[\"\']\d+%?[\"\'])?
                       [^>]*
                       /?>
                       (?P<post_text>.*)
                       ''', line, re.VERBOSE)
        if m:
            pre_text = m.group("pre_text")
            img_url = m.group("img_url")
            width_attr = m.group("width_attr") or ""
            if not img_url.startswith("http"):
                img_url = URL.concatenate_url(page_url, img_url)
            img_url_short = img_url[:30] if img_url.startswith("data:image") else img_url
            LOGGER.debug(f"img_url={img_url_short}")
            post_text = m.group("post_text")

            # pre_text
            m = re.search(r'^\s*$', pre_text)
            if not m:
                print(pre_text)

            # download images and save their metadata
            new_cache_file_path, _ = ImageDownloader.download_image(crawler, feed_img_dir_path, img_url, quality=quality)

            if new_cache_file_path and new_cache_file_path.is_file():
                suffix = new_cache_file_path.suffix
                cache_url = FileManager.get_cache_url(feed_img_url_prefix, img_url, "")
                img_file_list.append(new_cache_file_path)
                img_url_list.append(img_url)
                img_width_list.append(width_attr.strip())
                LOGGER.debug("%s -> %s / %s%s", img_url_short, PathUtil.short_path(new_cache_file_path), cache_url, suffix)

            else:
                if not img_url.startswith("data:image/svg+xml;base64"):
                    LOGGER.error(f"<!-- can't download the image from '{img_url_short}' -->")
                    print(f"<img src='{img_url}' alt='original image'/>")
                else:
                    print(f"<img src='{img_url}' alt='svg image'/>")

            # post_text
            m = re.search(r'^\s*$', post_text)
            if not m:
                print(post_text)
        else:
            # general html elements
            m = re.search(r'^</?br>$', line)
            if not m:
                normal_html_lines.append(line.rstrip())

    return img_file_list, img_url_list, normal_html_lines, img_width_list


def get_image_dimensions(img_file_path: Path) -> Tuple[int, int]:
    """Get image dimensions"""
    try:
        with Image.open(img_file_path) as img:
            return img.size
    except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
        LOGGER.error(f"Error reading image dimensions for {img_file_path}: {e}")
        return (0, 0)


def crop_image_file(feed_dir_path: Path, img_file_path: Path) -> None:
    LOGGER.debug("# crop_image_file(feed_dir_path=%r, img_file_path=%r)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(img_file_path))
    temp_img_file_path = img_file_path.with_suffix(img_file_path.suffix + ".temp")
    cmd = f"innercrop -f 4 -m crop '{img_file_path}' '{temp_img_file_path}' && mv -f '{temp_img_file_path}' '{img_file_path}'"
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    if error:
        LOGGER.error("<!-- can't crop the image file '%s', cmd='%s', %r -->", PathUtil.short_path(img_file_path), cmd, error)
        # sys.exit(-1)


def crop_image_files(feed_dir_path: Path, num_units: int, feed_img_dir_path: Path, img_url: str) -> None:
    LOGGER.debug("# crop_image_files(feed_dir_path=%r, num_units=%d, feed_img_dir_path=%r, img_url='%s')", PathUtil.short_path(feed_dir_path), num_units, PathUtil.short_path(feed_img_dir_path), img_url)
    # crop some image files
    for i in range(num_units):
        img_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url, index=i + 1)
        LOGGER.debug("img_file='%s'", PathUtil.short_path(img_file_path))
        if img_file_path.is_file():
            crop_image_file(feed_dir_path, img_file_path)


def split_image_file(*, feed_dir_path: Path, img_file_path: Path, bandwidth: int, diff_threshold: float, size_threshold: float, acceptable_diff_of_color_value: int, num_units: int, bgcolor_option: str, orientation_option: str, wider_scan_option: str) -> bool:
    LOGGER.debug("# split_image_file(feed_dir_path=%r, img_file_path=%r, bandwidth=%d, diff_threshold=%f, size_threshold=%f, acceptable_diff_of_color_value=%d, num_units=%d, bgcolor_option=%s, orientation_option=%s, wider_scan_option=%s)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(img_file_path), bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, num_units, bgcolor_option, orientation_option, wider_scan_option)
    # split the image
    cmd = f"split.py -b {bandwidth} -t {diff_threshold} -s {size_threshold} -a {acceptable_diff_of_color_value} -n {num_units} {bgcolor_option} {orientation_option} {wider_scan_option} {img_file_path}"
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    if error:
        LOGGER.error("<!-- can't split the image file, cmd='%s', %r -->", cmd, error)
        return False
    return True


def progressive_merge_and_split(*, feed_dir_path: Path, img_file_list: list[Path], page_url: str,
                               feed_img_dir_path: Path, img_url_prefix: str,
                               bandwidth: int, diff_threshold: float, size_threshold: float,
                               acceptable_diff_of_color_value: int, num_units: int,
                               bgcolor_option: str, orientation_option: str, wider_scan_option: str,
                               do_innercrop: bool, do_only_merge: bool,
                               img_width_list: Optional[list[str]] = None) -> None:
    """
    Optimized progressive merge and split with single-pass processing
    """
    LOGGER.debug("# progressive_merge_and_split: processing %d images", len(img_file_list))

    if not img_file_list:
        return

    # First, run the normal merge/split process to create initial split files
    _run_normal_merge_split_process(
        img_file_list, page_url, feed_dir_path, feed_img_dir_path, img_url_prefix,
        bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value,
        num_units, bgcolor_option, orientation_option, wider_scan_option,
        do_innercrop, do_only_merge, img_width_list
    )

    if not do_only_merge:
        # Then fix cross-batch boundaries
        _fix_cross_batch_boundaries(feed_img_dir_path, page_url, img_url_prefix)

        # Finally, output all remaining split files
        _output_all_final_split_files(feed_img_dir_path, page_url, img_url_prefix)


def _run_normal_merge_split_process(img_file_list: list[Path], page_url: str,
                                   feed_dir_path: Path, feed_img_dir_path: Path, img_url_prefix: str,
                                   bandwidth: int, diff_threshold: float, size_threshold: float,
                                   acceptable_diff_of_color_value: int, num_units: int,
                                   bgcolor_option: str, orientation_option: str, wider_scan_option: str,
                                   do_innercrop: bool, do_only_merge: bool,
                                   img_width_list: Optional[list[str]] = None) -> None:
    """Run the original merge/split process to create initial split files"""

    # Create merged chunks respecting WebP size limits
    merged_chunks = create_merged_chunks(img_file_list, feed_img_dir_path, page_url, img_width_list)
    LOGGER.debug(f"Created {len(merged_chunks)} merged chunks")

    # Process each chunk normally
    for chunk_idx, (chunk_file_path, width_attr) in enumerate(merged_chunks):
        unit_num = chunk_idx + 1
        LOGGER.debug(f"Processing chunk {chunk_idx + 1}/{len(merged_chunks)}: {chunk_file_path}")

        if do_innercrop:
            crop_image_file(feed_dir_path, chunk_file_path)

        if do_only_merge:
            # Generate cache URL for the chunk
            chunk_url = FileManager.get_cache_url(img_url_prefix, page_url, postfix=str(unit_num))
            # Print with width attribute if available
            if width_attr:
                print(f"<img src='{chunk_url}.jpeg' {width_attr}/>")
            else:
                print(f"<img src='{chunk_url}.jpeg'/>")
        else:
            # Split the merged chunk
            if split_image_file(feed_dir_path=feed_dir_path, img_file_path=chunk_file_path,
                               bandwidth=bandwidth, diff_threshold=diff_threshold,
                               size_threshold=size_threshold,
                               acceptable_diff_of_color_value=acceptable_diff_of_color_value,
                               num_units=num_units, bgcolor_option=bgcolor_option,
                               orientation_option=orientation_option, wider_scan_option=wider_scan_option):

                # Split files will be output later by _output_all_final_split_files
                pass

        # Clean up temporary chunk file
        if chunk_file_path.exists():
            chunk_file_path.unlink()


def _convert_jpeg_to_webp(src_path: Path, quality: int = 75) -> Optional[Path]:
    """Convert a JPEG file to WEBP format and remove the original JPEG.

    Returns the path to the WEBP file if successful, otherwise None.
    """
    try:
        if not src_path.exists() or src_path.suffix.lower() not in [".jpg", ".jpeg"]:
            return None
        target_path = src_path.with_suffix(".webp")
        with Image.open(src_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(target_path, format="WEBP", quality=quality)
        try:
            src_path.unlink()
        except Exception:
            pass
        return target_path
    except Exception as e:
        LOGGER.warning(f"Failed to convert to WEBP: {src_path}, {e}")
        return None


def _fix_cross_batch_boundaries(feed_img_dir_path: Path, page_url: str, img_url_prefix: str) -> None:
    """Fix cross-batch boundaries by merging last split of previous batch with first split of next batch"""

    # Find all batch files
    batch_files = {}

    # Generate the hash prefix for this page URL
    from bin.feed_maker_util import URL
    hash_prefix = URL.get_short_md5_name(page_url)

    for jpeg_file in feed_img_dir_path.glob(f"{hash_prefix}_*.jpeg"):
        # Parse filename like f7d4736_1.14.jpeg to extract batch and split number
        stem = jpeg_file.stem  # f7d4736_1.14
        parts = stem.split('_')[1].split('.')  # ['1', '14']
        if len(parts) == 2:
            batch_num = int(parts[0])
            split_num = int(parts[1])

            if batch_num not in batch_files:
                batch_files[batch_num] = []
            batch_files[batch_num].append((split_num, jpeg_file))

    # Sort each batch by split number
    for batch_num in batch_files:
        batch_files[batch_num].sort(key=lambda x: x[0])


    # Process cross-batch boundaries
    batch_nums = sorted(batch_files.keys())
    for i in range(len(batch_nums) - 1):
        current_batch = batch_nums[i]
        next_batch = batch_nums[i + 1]

        # Get last split of current batch and first split of next batch
        last_split_current = batch_files[current_batch][-1][1]  # (split_num, file_path)
        first_split_next = batch_files[next_batch][0][1]


        try:
            # Load both images to check dimensions first
            with Image.open(last_split_current) as img1:
                width1, height1 = img1.size

            with Image.open(first_split_next) as img2:
                width2, height2 = img2.size

            # Check if merged image size would exceed JPEG limits
            new_height = height1 + height2
            if new_height > JPEG_SIZE_LIMIT:
                LOGGER.debug(f"Skipping cross-batch boundary merge: merged height {new_height} would exceed JPEG limit {JPEG_SIZE_LIMIT}, keeping original files")
                continue

            # If size is OK, proceed with the merge
            with Image.open(last_split_current) as img1:
                if img1.mode != 'RGB':
                    img1 = img1.convert('RGB')
                img1_copy = img1.copy()

            with Image.open(first_split_next) as img2:
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')
                img2_copy = img2.copy()

            # Create merged image
            new_width = max(width1, width2)

            merged_image = Image.new("RGB", (new_width, new_height), "white")
            merged_image.paste(img1_copy, (0, 0))
            merged_image.paste(img2_copy, (0, height1))

            # Save merged image as the first split of next batch
            merged_image.save(first_split_next, format='JPEG', quality=75)

            # Remove the last split of current batch only after successful save
            last_split_current.unlink()

        except (OSError, IOError, ValueError, TypeError) as e:
            LOGGER.warning(f"Failed to merge cross-batch boundary between batch {current_batch} and {next_batch}: {e}")
            # 원본 파일들은 그대로 유지됨 (삭제하지 않음)


def _output_all_final_split_files(feed_img_dir_path: Path, page_url: str, img_url_prefix: str) -> None:
    """Output img tags for all final split files after cross-batch boundary fixing"""
    # Find all split files and sort them properly
    all_split_files = []

    # Generate the hash prefix for this page URL
    from bin.feed_maker_util import URL
    hash_prefix = URL.get_short_md5_name(page_url)

    for jpeg_file in feed_img_dir_path.glob(f"{hash_prefix}_*.jpeg"):
        # Parse filename like f7d4736_1.14.jpeg to extract batch and split number
        stem = jpeg_file.stem  # f7d4736_1.14
        parts = stem.split('_')[1].split('.')  # ['1', '14']
        if len(parts) == 2:
            batch_num = int(parts[0])
            split_num = int(parts[1])
            all_split_files.append((batch_num, split_num, jpeg_file))

    # Sort by batch number, then by split number
    all_split_files.sort(key=lambda x: (x[0], x[1]))

    # Convert JPEG to WEBP and output img tags for all files
    for batch_num, split_num, jpeg_file in all_split_files:
        webp_path = _convert_jpeg_to_webp(jpeg_file, quality=75)
        split_img_url = FileManager.get_cache_url(img_url_prefix, page_url, postfix=f"{batch_num}.{split_num}")

        if webp_path and webp_path.exists():
            # 변환 성공: WEBP 사용
            print(f"<img src='{split_img_url}.webp'/>")
        else:
            # 변환 실패: 원본 JPEG 사용
            print(f"<img src='{split_img_url}.jpeg'/>")


def create_merged_chunks(img_file_list: list[Path], feed_img_dir_path: Path, page_url: str, img_width_list: Optional[list[str]] = None) -> list[tuple[Path, str]]:
    """Create merged image chunks respecting JPEG size limits"""
    if img_width_list is None:
        img_width_list = [""] * len(img_file_list)

    merged_chunks: list[tuple[Path, str]] = []
    current_merged_image: Optional[Image.Image] = None
    current_height = 0
    current_width = 0
    chunk_index = 1
    current_chunk_width_attr = ""

    for i, img_file in enumerate(img_file_list):
        try:
            with Image.open(img_file) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img_copy = img.copy()

                # Safely extract image dimensions
                size = getattr(img, 'size', None)
                if not size or len(size) != 2:
                    LOGGER.warning(f"Invalid or missing image size for {img_file}: {size}, skipping")
                    continue

                width, height = size

                # Check if size is valid
                if width <= 0 or height <= 0:
                    LOGGER.warning(f"Invalid image dimensions for {img_file}: {width}x{height}, skipping")
                    continue

                LOGGER.debug(f"Adding to chunk: {img_file.name} ({width}x{height})")

                # Get width attribute for this image
                width_attr = img_width_list[i] if i < len(img_width_list) else ""

                if current_merged_image is None:
                    # First image
                    current_merged_image = img_copy
                    current_height = height
                    current_width = width
                    current_chunk_width_attr = width_attr
                else:
                    # Check if adding this image would exceed JPEG limits
                    new_height = current_height + height
                    new_width = max(current_width, width)

                    if new_height > JPEG_SIZE_LIMIT:
                        # Save current chunk and start new one
                        chunk_path = _save_merged_chunk(current_merged_image, feed_img_dir_path, page_url, chunk_index)
                        merged_chunks.append((chunk_path, current_chunk_width_attr))
                        LOGGER.debug(f"Saved chunk {chunk_index}: {current_width}x{current_height}")
                        chunk_index += 1

                        # Start new chunk with current image
                        current_merged_image = img_copy
                        current_height = height
                        current_width = width
                        current_chunk_width_attr = width_attr
                    else:
                        # Extend current merged image
                        new_merged = Image.new("RGB", (new_width, new_height), "white")
                        new_merged.paste(current_merged_image, (0, 0))
                        new_merged.paste(img_copy, (0, current_height))

                        current_merged_image = new_merged
                        current_height = new_height
                        current_width = new_width
                        # Keep the first width attribute for the chunk
                        if not current_chunk_width_attr and width_attr:
                            current_chunk_width_attr = width_attr
        except (OSError, IOError, TypeError, ValueError, RuntimeError, AttributeError, MemoryError) as e:
            LOGGER.error(f"Error processing image {img_file}: {e}, skipping")
            continue
        except Exception as e:
            # Catch PIL-specific exceptions like UnidentifiedImageError, DecompressionBombError
            LOGGER.error(f"Unexpected error processing image {img_file}: {e}, skipping")
            continue

    # Save the final chunk
    if current_merged_image is not None:
        chunk_path = _save_merged_chunk(current_merged_image, feed_img_dir_path, page_url, chunk_index)
        merged_chunks.append((chunk_path, current_chunk_width_attr))
        LOGGER.debug(f"Saved final chunk {chunk_index}: {current_width}x{current_height}")

    return merged_chunks


def _save_merged_chunk(merged_image: Image.Image, feed_img_dir_path: Path, page_url: str, chunk_index: int) -> Path:
    """Save a merged chunk using proper FileManager naming"""
    # Use FileManager to get proper file path with correct naming pattern
    chunk_file_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=str(chunk_index), suffix=".jpeg")
    try:
        merged_image.save(chunk_file_path, format='JPEG', quality=75)
        LOGGER.debug(f"Saved merged chunk to: {chunk_file_path}")
        return chunk_file_path
    except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
        LOGGER.error(f"Failed to save merged chunk: {e}")
        raise


def print_image_files(*, num_units: int, feed_img_dir_path: Path, img_url_prefix: str, img_url: str, img_file_path: Optional[Path], postfix: Optional[str], do_flip_right_to_left: bool) -> None:
    img_url_str = img_url if not img_url.startswith("data:image") else img_url[:30]
    LOGGER.debug("# print_image_files(num_units=%d, feed_img_dir_path=%r, img_url_prefix='%s', img_url='%s', img_file_path=%r, postfix='%s', do_flip_right_to_left=%r)", num_units, PathUtil.short_path(feed_img_dir_path), img_url_prefix, img_url_str, PathUtil.short_path(img_file_path), postfix, do_flip_right_to_left)
    # print some split images
    if not do_flip_right_to_left:
        custom_range = list(range(num_units))
    else:
        custom_range = list(reversed(range(num_units)))
    for i in custom_range:
        if img_file_path:
            split_img_path = img_file_path.with_stem(img_file_path.stem + "." + str(i + 1))
            suffix = img_file_path.suffix
        else:
            split_img_path = FileManager.get_cache_file_path(path_prefix=feed_img_dir_path, img_url_for_hashing=img_url, postfix=postfix, index=i + 1)
            suffix = ""
        LOGGER.debug(f"{split_img_path=}, {suffix=}")
        if split_img_path.is_file():
            split_img_url = FileManager.get_cache_url(img_url_prefix, img_url, postfix=postfix, index=i + 1)
            print(f"<img src='{split_img_url}{suffix}'/>")


def print_cached_image_file(feed_img_dir_path: Path, img_url_prefix: str, img_url: str, unit_num: Optional[int] = None) -> None:
    img_url_str = img_url if not img_url.startswith("data:image") else img_url[:30]
    LOGGER.debug("# print_cached_image_file(feed_img_dir_path=%r, img_url_prefix='%s', img_url='%s', unit_num=%d)", PathUtil.short_path(feed_img_dir_path), img_url_prefix, img_url_str, unit_num)
    img_file_path = FileManager.get_cache_file_path(path_prefix=feed_img_dir_path, img_url_for_hashing=img_url, postfix=unit_num)
    LOGGER.debug("img_file='%s'", PathUtil.short_path(img_file_path))
    if img_file_path.is_file():
        suffix = img_file_path.suffix
        img_url = FileManager.get_cache_url(url_prefix=img_url_prefix, img_url_for_hashing=img_url, postfix=unit_num, suffix=suffix)
        print(f"<img src='{img_url}'/>")


def print_statistics(original_images: list[Path], output_images: list[Path], page_url: str, feed_img_dir_path: Path) -> None:
    """Print statistics about original vs processed images as HTML comments"""
    # Calculate original image statistics
    original_total_area = 0
    original_total_height = 0
    original_max_width = 0
    original_widths = []

    for img_file in original_images:
        if img_file.exists():
            width, height = get_image_dimensions(img_file)
            original_total_area += width * height
            original_total_height += height
            original_max_width = max(original_max_width, width)
            original_widths.append(width)

    # Calculate processed image statistics
    processed_total_area = 0
    processed_total_height = 0
    processed_max_width = 0
    processed_count = 0
    processed_widths = []

    # Find all split files for this page (prefer WEBP over JPEG for the same stem)
    from bin.feed_maker_util import URL
    hash_prefix = URL.get_short_md5_name(page_url)

    candidate_webp = list(feed_img_dir_path.glob(f"{hash_prefix}_*.webp"))
    candidate_jpeg = list(feed_img_dir_path.glob(f"{hash_prefix}_*.jpeg"))

    stems_to_paths: dict[str, list[Path]] = {}
    for p in candidate_webp + candidate_jpeg:
        stems_to_paths.setdefault(p.stem, []).append(p)

    # Choose WEBP if present for a stem; otherwise choose any path for that stem
    chosen_files: list[Path] = []
    for stem, paths in stems_to_paths.items():
        webp_path = next((pp for pp in paths if pp.suffix.lower() == ".webp"), None)
        chosen_files.append(webp_path or paths[0])

    for f in chosen_files:
        if f.exists():
            width, height = get_image_dimensions(f)
            processed_total_area += width * height
            processed_total_height += height
            processed_max_width = max(processed_max_width, width)
            processed_widths.append(width)
            processed_count += 1

    # Calculate average widths for meaningful comparison
    original_avg_width = sum(original_widths) / len(original_widths) if original_widths else 0
    processed_avg_width = sum(processed_widths) / len(processed_widths) if processed_widths else 0

    # Output statistics as HTML comments only if enabled
    print(f"<!-- Image Processing Statistics -->")
    print(f"<!-- Original Images: {len(original_images)} files -->")
    print(f"<!-- Original Total Area: {original_total_area:,}px², Total Height: {original_total_height}px -->")
    print(f"<!-- Original Max Width: {original_max_width}px, Avg Width: {original_avg_width:.0f}px -->")
    print(f"<!-- Processed Images: {processed_count} files -->")
    print(f"<!-- Processed Total Area: {processed_total_area:,}px², Total Height: {processed_total_height}px -->")
    print(f"<!-- Processed Max Width: {processed_max_width}px, Avg Width: {processed_avg_width:.0f}px -->")
    if original_total_area > 0:
        area_change = ((processed_total_area - original_total_area) / original_total_area) * 100
        height_change = ((processed_total_height - original_total_height) / original_total_height) * 100
        print(f"<!-- Area Change: {area_change:+.1f}%, Height Change: {height_change:+.1f}% -->")
    print(f"<!-- Note: Height/Area increase is expected due to cross-batch boundary merging for seamless transitions -->")


def print_usage(program_name: str) -> None:
    print(f"Usage: {program_name} [-c <fuzzy>] [-m] [-i] [-l] [-v] [-b <bandwidth>] <page_url>")
    print("\t\t-c <color>: specify background color")
    print("\t\t\t\t(ex. 'white' or 'blackorwhite', 'dominant', 'fuzzy', '#135fd8')")
    print("\t\t-m: merge")
    print("\t\t-i: innercrop")
    print("\t\t-l: flip right to left (determine image order)")
    print("\t\t-v: split vertically")
    print("\t\t-b <bandwidth>")
    print("\t\t-n <num units>")
    print("\t\t-t <diff threshold>")
    print("\t\t-s <size threshold>")
    print("\t\t-q <quality>: JPEG quality (1-100, default: 75)")
    print("\t\t-d: debug mode")
    print()
    sys.exit(0)


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path = Path.cwd()

    num_units = 25
    diff_threshold = 0.05
    size_threshold = 0
    acceptable_diff_of_color_value = 1
    bandwidth = 10
    quality = 75  # default quality

    # options
    bgcolor_option: str = ""
    do_merge = False
    do_innercrop = False
    orientation_option: str = ""
    wider_scan_option: str = ""
    do_flip_right_to_left = False
    do_only_merge = False
    optlist, args = getopt.getopt(sys.argv[1:], "milvwf:c:b:t:n:s:a:q:h", ["only-merge="])
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)
        elif o == "-c":
            bgcolor_option = "-c " + a
        elif o == "-m":
            do_merge = True
        elif o == "-i":
            do_innercrop = True
        elif o == "-l":
            do_flip_right_to_left = True
        elif o == "-v":
            orientation_option = "-v"
        elif o == "-w":
            wider_scan_option = "-w"
        elif o == "-b":
            bandwidth = int(a)
        elif o == "-t":
            diff_threshold = float(a)
        elif o == "-s":
            size_threshold = int(a)
        elif o == "-a":
            acceptable_diff_of_color_value = int(a)
        elif o == "-n":
            num_units = int(a)
        elif o == "-q":
            quality = int(a)
        elif o == "-h":
            print_usage(sys.argv[0])
        elif o == "--only-merge":
            do_only_merge = a == "true"

    if len(args) < 1:
        print_usage(sys.argv[0])

    if not feed_dir_path or not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url = args[0]
    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_name
    LOGGER.debug("feed_name=%s", feed_name)
    LOGGER.debug("feed_img_dir_path=%r", feed_img_dir_path)

    config = Config(feed_dir_path=feed_dir_path)
    extraction_conf = config.get_extraction_configs()

    headers: dict[str, Any] = {
        "User-Agent": extraction_conf.get("user_agent", ""),
        "Referer": URL.encode_suffix(page_url)
    }

    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    img_file_list, img_url_list, normal_html_lines, img_width_list = download_image_and_read_metadata(feed_dir_path, crawler, feed_img_dir_path, page_url, quality)
    for line in normal_html_lines:
        print(line)
    LOGGER.debug(f"img_file_list={img_file_list}")
    LOGGER.debug(f"img_width_list={img_width_list}")
    if len(img_file_list) == 0:
        return 0

    if do_merge:
        # Progressive merge-split mode with intelligent batching
        progressive_merge_and_split(
            feed_dir_path=feed_dir_path,
            img_file_list=img_file_list,
            page_url=page_url,
            feed_img_dir_path=feed_img_dir_path,
            img_url_prefix=img_url_prefix,
            bandwidth=bandwidth,
            diff_threshold=diff_threshold,
            size_threshold=size_threshold,
            acceptable_diff_of_color_value=acceptable_diff_of_color_value,
            num_units=num_units,
            bgcolor_option=bgcolor_option,
            orientation_option=orientation_option,
            wider_scan_option=wider_scan_option,
            do_innercrop=do_innercrop,
            do_only_merge=do_only_merge,
            img_width_list=img_width_list
        )
    else:
        # only split mode
        for img_file, img_url in zip(img_file_list, img_url_list):
            LOGGER.debug(f"img_file={img_file}", )
            img_url_short = img_url if not img_url.startswith("data:image") else img_url[:30]
            LOGGER.debug(f"img_url={img_url_short}")
            if split_image_file(feed_dir_path=feed_dir_path, img_file_path=img_file, bandwidth=bandwidth, diff_threshold=diff_threshold, size_threshold=size_threshold, acceptable_diff_of_color_value=acceptable_diff_of_color_value, num_units=num_units, bgcolor_option=bgcolor_option, orientation_option=orientation_option, wider_scan_option=wider_scan_option):
                if do_innercrop:
                    crop_image_files(feed_dir_path, num_units, feed_img_dir_path, img_url)
                print_image_files(num_units=num_units, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=img_url, img_file_path=img_file, postfix=None, do_flip_right_to_left=do_flip_right_to_left)
            else:
                print_cached_image_file(feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=img_url)

    # Print statistics after all processing is complete (enabled by default)
    print_statistics(img_file_list, [], page_url, feed_img_dir_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
