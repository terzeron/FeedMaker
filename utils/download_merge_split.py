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

# WebP size limit constant
WEBP_SIZE_LIMIT = 16383


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


def calculate_optimal_partition(img_file_list: list[Path], max_height: int = WEBP_SIZE_LIMIT) -> list[list[Path]]:
    """
    Calculate optimal partition of images considering WebP size limits
    and ensuring proper connection between consecutive image groups
    """
    LOGGER.debug(f"# calculate_optimal_partition(img_file_list={len(img_file_list)} images, max_height={max_height})")
    
    if not img_file_list:
        return []
    
    partitions: list[list[Path]] = []
    current_partition: list[Path] = []
    current_total_height = 0
    
    for i, img_file in enumerate(img_file_list):
        _, height = get_image_dimensions(img_file)
        
        # Check if adding this image would exceed the height limit
        if current_total_height + height > max_height and current_partition:
            # Save current partition and start a new one
            partitions.append(current_partition)
            current_partition = [img_file]
            current_total_height = height
        else:
            current_partition.append(img_file)
            current_total_height += height
    
    # Add the last partition if it has content
    if current_partition:
        partitions.append(current_partition)
    
    LOGGER.debug(f"Created {len(partitions)} partitions")
    for i, partition in enumerate(partitions):
        total_height = sum(get_image_dimensions(img)[1] for img in partition)
        LOGGER.debug(f"Partition {i+1}: {len(partition)} images, total height: {total_height}")
    
    return partitions


def merge_images_with_pil(img_file_list: list[Path], output_path: Path) -> bool:
    """
    Merge images using PIL instead of external merge.py script
    """
    LOGGER.debug(f"# merge_images_with_pil(img_file_list={len(img_file_list)} images, output_path={output_path})")
    
    if not img_file_list:
        LOGGER.error("No images to merge")
        return False
    
    try:
        images = []
        total_width = 0
        total_height = 0
        
        # Load all images and calculate dimensions
        for img_file in img_file_list:
            with Image.open(img_file) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img.copy())  # Create copy to avoid file handle issues
                width, height = img.size
                total_width = max(total_width, width)
                total_height += height
                LOGGER.debug(f"Image {img_file.name}: {width}x{height}")
        
        # Check WebP size limit
        if total_height > WEBP_SIZE_LIMIT:
            LOGGER.warning(f"Total height {total_height} exceeds WebP limit {WEBP_SIZE_LIMIT}")
            # Try to reduce quality or use different format
            output_format = 'JPEG'
        else:
            output_format = 'WEBP'
        
        # Create new image
        new_image = Image.new("RGB", (total_width, total_height), "white")
        
        # Paste images vertically
        y_offset = 0
        for img in images:
            new_image.paste(img, (0, y_offset))
            y_offset += img.size[1]
        
        # Save with appropriate format and quality
        if output_format == 'WEBP':
            new_image.save(output_path, format='WEBP', quality=95)
        else:
            new_image.save(output_path, format='JPEG', quality=95)
        
        LOGGER.debug(f"Successfully merged {len(images)} images to {output_path}")
        return True
        
    except (OSError, IOError, TypeError, ValueError, MemoryError, RuntimeError) as e:
        LOGGER.error(f"Error merging images: {e}")
        return False


def merge_image_files(feed_dir_path: Path, img_file_list: list[Path], feed_img_dir_path: Path, img_url: str, unit_num: int) -> Path:
    LOGGER.debug("# merge_image_files(feed_dir_path=%s, img_file_list=%r, feed_img_dir_path=%r, img_url='%s', unit_num=%d)", PathUtil.short_path(feed_dir_path), img_file_list, feed_img_dir_path, img_url, unit_num)
    
    suffix = img_file_list[0].suffix
    merged_img_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url, postfix=str(unit_num), suffix=suffix)
    
    # Use PIL-based merging instead of external script
    if merge_images_with_pil(img_file_list, merged_img_file_path):
        LOGGER.debug("merged_img_file_path=%r", merged_img_file_path)
        return merged_img_file_path

    # Fallback to original merge.py if PIL fails
    cmd = f"merge.py '{str(merged_img_file_path)}' "
    for cache_file in img_file_list:
        cmd += f" '{cache_file}'"
    LOGGER.debug(cmd)
    result, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    LOGGER.debug(result)
    if not result or error:
        LOGGER.error("<!-- can't merge the image files, cmd='%s', %r -->", cmd, error)
        sys.exit(-1)
    LOGGER.debug("merged_img_file_path=%r", merged_img_file_path)
    return merged_img_file_path


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


def remove_image_files(feed_dir_path: Path, img_file_list: list[str]) -> bool:
    LOGGER.debug("# remove_image_files(feed_dir_path=%r, img_file_list=%r)", PathUtil.short_path(feed_dir_path), img_file_list)
    # remove the original image
    cmd = "rm -f "
    for cache_file in img_file_list:
        cmd = cmd + "'" + cache_file + "' "
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    if error:
        LOGGER.error("<!-- can't remove files '%r', cmd='%s', %r -->", img_file_list, cmd, error)
        return False
    return True


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
                print(f"<img src='{chunk_url}.webp' {width_attr}/>")
            else:
                print(f"<img src='{chunk_url}.webp'/>")
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


def _optimized_progressive_process(img_file_list: list[Path], page_url: str, feed_dir_path: Path, 
                                  feed_img_dir_path: Path, img_url_prefix: str,
                                  bandwidth: int, diff_threshold: float, size_threshold: float, 
                                  acceptable_diff_of_color_value: int, num_units: int, 
                                  bgcolor_option: str, orientation_option: str, wider_scan_option: str,
                                  do_innercrop: bool, do_flip_right_to_left: bool, do_only_merge: bool) -> None:
    """
    Optimized single-pass progressive processing with intelligent cross-batch merging
    """
    LOGGER.debug("# _optimized_progressive_process: processing %d images", len(img_file_list))
    
    if not img_file_list:
        return
    
    current_batch_images = []
    current_batch_height = 0
    batch_num = 1
    previous_last_split = None
    
    # Process images in a streaming fashion
    for i, img_file in enumerate(img_file_list):
        # Load image efficiently
        with Image.open(img_file) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_copy = img.copy()
            width, height = img.size
            
            LOGGER.debug(f"Processing image {i+1}/{len(img_file_list)}: {img_file.name} ({width}x{height})")
            
            # Check if adding this image would exceed WebP limits
            if current_batch_height + height > WEBP_SIZE_LIMIT and current_batch_images:
                # Process current batch
                previous_last_split = _process_batch_optimized(
                    current_batch_images, batch_num, previous_last_split, 
                    feed_dir_path, feed_img_dir_path, page_url, img_url_prefix,
                    bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, 
                    num_units, bgcolor_option, orientation_option, wider_scan_option,
                    do_innercrop, do_flip_right_to_left, do_only_merge
                )
                
                # Reset for next batch
                current_batch_images = [img_copy]
                current_batch_height = height
                batch_num += 1
            else:
                # Add to current batch
                current_batch_images.append(img_copy)
                current_batch_height += height
    
    # Process final batch
    if current_batch_images:
        _process_batch_optimized(
            current_batch_images, batch_num, previous_last_split,
            feed_dir_path, feed_img_dir_path, page_url, img_url_prefix,
            bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, 
            num_units, bgcolor_option, orientation_option, wider_scan_option,
            do_innercrop, do_flip_right_to_left, do_only_merge
        )


def _process_batch_optimized(batch_images: list[Image.Image], batch_num: int, previous_last_split: Optional[Image.Image],
                           feed_dir_path: Path, feed_img_dir_path: Path, page_url: str, img_url_prefix: str,
                           bandwidth: int, diff_threshold: float, size_threshold: float, 
                           acceptable_diff_of_color_value: int, num_units: int, 
                           bgcolor_option: str, orientation_option: str, wider_scan_option: str,
                           do_innercrop: bool, do_flip_right_to_left: bool, do_only_merge: bool) -> Optional[Image.Image]:
    """
    Process a batch of images with optimized cross-batch merging
    Returns the last split image for potential merging with next batch
    """
    LOGGER.debug(f"Processing batch {batch_num} with {len(batch_images)} images")
    
    # Create merged image from batch
    if not batch_images:
        return None
    
    # Merge all images in batch efficiently
    total_width = max(img.size[0] for img in batch_images)
    total_height = sum(img.size[1] for img in batch_images)
    
    merged_image = Image.new("RGB", (total_width, total_height), "white")
    y_offset = 0
    for img in batch_images:
        merged_image.paste(img, (0, y_offset))
        y_offset += img.size[1]
    
    # Save merged chunk
    merged_file_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=str(batch_num), suffix=".webp")
    merged_image.save(merged_file_path, format='WEBP', quality=95)
    
    if do_innercrop:
        crop_image_file(feed_dir_path, merged_file_path)
    
    if do_only_merge:
        print_cached_image_file(feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, 
                               img_url=page_url, unit_num=batch_num)
        return None
    
    # Split the merged image
    if not split_image_file(feed_dir_path=feed_dir_path, img_file_path=merged_file_path, 
                           bandwidth=bandwidth, diff_threshold=diff_threshold, 
                           size_threshold=size_threshold, 
                           acceptable_diff_of_color_value=acceptable_diff_of_color_value, 
                           num_units=num_units, bgcolor_option=bgcolor_option, 
                           orientation_option=orientation_option, wider_scan_option=wider_scan_option):
        return None
    
    # Get split files
    split_files = _get_split_result_files_optimized(merged_file_path, batch_num)
    
    # Handle cross-batch merging on-the-fly
    if previous_last_split and split_files:
        first_split = split_files[0]
        LOGGER.debug(f"Merging previous last split with {first_split.name}")
        
        # Merge previous last split with current first split
        try:
            width1, height1 = previous_last_split.size
            with Image.open(first_split) as img2:
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')
                img2_copy = img2.copy()
                width2, height2 = img2.size
                
                new_width = max(width1, width2)
                new_height = height1 + height2
                
                merged = Image.new("RGB", (new_width, new_height), "white")
                merged.paste(previous_last_split, (0, 0))
                merged.paste(img2_copy, (0, height1))
                
                # Save as first split of current batch
                merged.save(first_split, format='WEBP', quality=95)
                LOGGER.debug(f"Successfully merged cross-batch boundary into {first_split.name}")
                
        except (OSError, IOError, ValueError, TypeError) as e:
            LOGGER.error(f"Failed to merge cross-batch boundary: {e}")
    
    # Output split files with proper naming
    for i, split_file in enumerate(split_files):
        if split_file.exists():
            # Generate proper filename using FileManager naming convention
            split_file_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=f"{batch_num}.{i+1}", suffix=".webp")
            
            # Copy the split file to the proper location with proper name
            try:
                import shutil
                shutil.copy2(split_file, split_file_path)
                LOGGER.debug(f"Copied {split_file} to {split_file_path}")
                
                # Generate URL for the properly named file
                split_img_url = FileManager.get_cache_url(img_url_prefix, page_url, postfix=f"{batch_num}.{i+1}")
                print(f"<img src='{split_img_url}.webp'/>")
                
            except (OSError, IOError, TypeError, ValueError, RuntimeError) as e:
                LOGGER.error(f"Failed to copy split file {split_file} to {split_file_path}: {e}")
    
    # Clean up original split files and merged file
    for split_file in split_files:
        if split_file.exists():
            split_file.unlink()
    
    if merged_file_path.exists():
        merged_file_path.unlink()
    
    # Return last split for next batch
    if split_files:
        last_split_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=f"{batch_num}.{len(split_files)}", suffix=".webp")
        if last_split_path.exists():
            with Image.open(last_split_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                return img.copy()
    
    return None


def _get_split_result_files_optimized(merged_file_path: Path, batch_num: int) -> list[Path]:
    """Optimized version of getting split result files"""
    split_files = []
    base_name = merged_file_path.stem
    parent_dir = merged_file_path.parent
    
    # Look for split files with pattern like merged_file.1, merged_file.2, etc.
    for i in range(1, 26):  # Assuming max 25 splits
        split_file = parent_dir / f"{base_name}.{i}{merged_file_path.suffix}"
        if split_file.exists():
            split_files.append(split_file)
        else:
            break
    
    LOGGER.debug(f"Found {len(split_files)} split files for batch {batch_num}")
    return split_files


def _fix_cross_batch_boundaries(feed_img_dir_path: Path, page_url: str, img_url_prefix: str) -> None:
    """Fix cross-batch boundaries by merging last split of previous batch with first split of next batch"""
    
    # Find all batch files
    batch_files = {}
    
    # Generate the hash prefix for this page URL
    from bin.feed_maker_util import URL
    hash_prefix = URL.get_short_md5_name(page_url)
    
    for webp_file in feed_img_dir_path.glob(f"{hash_prefix}_*.webp"):
        # Parse filename like f7d4736_1.14.webp to extract batch and split number
        stem = webp_file.stem  # f7d4736_1.14
        parts = stem.split('_')[1].split('.')  # ['1', '14']
        if len(parts) == 2:
            batch_num = int(parts[0])
            split_num = int(parts[1])
            
            if batch_num not in batch_files:
                batch_files[batch_num] = []
            batch_files[batch_num].append((split_num, webp_file))
    
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
            # Load both images
            with Image.open(last_split_current) as img1:
                if img1.mode != 'RGB':
                    img1 = img1.convert('RGB')
                img1_copy = img1.copy()
                
            with Image.open(first_split_next) as img2:
                if img2.mode != 'RGB':
                    img2 = img2.convert('RGB')
                img2_copy = img2.copy()
            
            # Create merged image
            width1, height1 = img1_copy.size
            width2, height2 = img2_copy.size
            new_width = max(width1, width2)
            new_height = height1 + height2
            
            merged_image = Image.new("RGB", (new_width, new_height), "white")
            merged_image.paste(img1_copy, (0, 0))
            merged_image.paste(img2_copy, (0, height1))
            
            # Save merged image as the first split of next batch
            merged_image.save(first_split_next, format='WEBP', quality=95)
            
            # Remove the last split of current batch
            last_split_current.unlink()
            
        except (OSError, IOError, ValueError, TypeError) as e:
            LOGGER.error(f"Failed to merge cross-batch boundary: {e}")


def _output_all_final_split_files(feed_img_dir_path: Path, page_url: str, img_url_prefix: str) -> None:
    """Output img tags for all final split files after cross-batch boundary fixing"""
    # Find all split files and sort them properly
    all_split_files = []
    
    # Generate the hash prefix for this page URL
    from bin.feed_maker_util import URL
    hash_prefix = URL.get_short_md5_name(page_url)
    
    for webp_file in feed_img_dir_path.glob(f"{hash_prefix}_*.webp"):
        # Parse filename like f7d4736_1.14.webp to extract batch and split number
        stem = webp_file.stem  # f7d4736_1.14
        parts = stem.split('_')[1].split('.')  # ['1', '14']
        if len(parts) == 2:
            batch_num = int(parts[0])
            split_num = int(parts[1])
            all_split_files.append((batch_num, split_num, webp_file))
    
    # Sort by batch number, then by split number
    all_split_files.sort(key=lambda x: (x[0], x[1]))
    
    # Output img tags for all files
    for batch_num, split_num, webp_file in all_split_files:
        split_img_url = FileManager.get_cache_url(img_url_prefix, page_url, postfix=f"{batch_num}.{split_num}")
        print(f"<img src='{split_img_url}.webp'/>")


def create_merged_chunks(img_file_list: list[Path], feed_img_dir_path: Path, page_url: str, img_width_list: Optional[list[str]] = None) -> list[tuple[Path, str]]:
    """Create merged image chunks respecting WebP size limits"""
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
                    # Check if adding this image would exceed WebP limits
                    new_height = current_height + height
                    new_width = max(current_width, width)
                    
                    if new_height > WEBP_SIZE_LIMIT:
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
    chunk_file_path = FileManager.get_cache_file_path(feed_img_dir_path, page_url, postfix=str(chunk_index), suffix=".webp")
    try:
        merged_image.save(chunk_file_path, format='WEBP', quality=95)
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

    return 0


if __name__ == "__main__":
    sys.exit(main())
