#!/usr/bin/env python


import os
import sys
import re
import getopt
import logging.config
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from utils.download_image import download_image
from bin.crawler import Crawler
from bin.feed_maker_util import Config, FileManager, IO, Process, PathUtil, URL

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def download_image_and_read_metadata(feed_dir_path: Path, crawler: Crawler, feed_img_dir_path: Path, page_url: str) -> Tuple[List[Path], List[str], List[str]]:
    LOGGER.debug("# download_image_and_read_metadata(feed_dir_path=%r, crawler=%r, feed_img_dir_path=%r, page_url='%s')", PathUtil.short_path(feed_dir_path), crawler, PathUtil.short_path(feed_img_dir_path), page_url)
    #
    # read input and collect image files into the list
    # (file name, url and dimension)
    #
    img_file_list: List[Path] = []
    img_url_list: List[str] = []

    #crawler = Crawler(dir_path=feed_dir_path, headers={"Referer": page_url}, num_retries=2)

    normal_html_lines = []
    line_list: List[str] = IO.read_stdin_as_line_list()
    for line in line_list:
        line = line.rstrip()
        m = re.search(r"<img src=[\"'](?P<img_url>[^\"']+)[\"']( width='\d+%?')?/?>", line)
        if m:
            img_url = m.group("img_url")
            img_url_short = img_url if not img_url.startswith("data:image") else img_url[:30]
            LOGGER.debug(f"img_url={img_url_short}")
            # download
            cache_file_path = download_image(crawler, feed_img_dir_path, img_url)
            if not cache_file_path:
                if not img_url.startswith("data:image/svg+xml;base64"):
                    LOGGER.error(f"<!-- can't download the image from '{img_url}' -->")
                    print(f"<img src='{FileManager.IMAGE_NOT_FOUND_IMAGE_URL}' alt='not exist or size 0'/>")
                continue
            img_file_list.append(cache_file_path)
            img_url_list.append(img_url)
            img_url_str = img_url if not img_url.startswith("data:image") else img_url[:30]
            LOGGER.debug("%s -> %s", img_url_str, PathUtil.short_path(cache_file_path))
        else:
            m = re.search(r'^</?br>$', line)
            if not m:
                normal_html_lines.append(line.rstrip())

    return img_file_list, img_url_list, normal_html_lines


def split_image_list(img_file_list: List[Path]) -> List[List[Path]]:
    LOGGER.debug(f"# split_image_list(img_file_list={img_file_list})")
    #
    # split array into 8 sub-array
    #
    img_file_partition_list: List[List[Path]] = []
    partition_size = int((len(img_file_list) + 7) / 8)
    LOGGER.debug(f"length={len(img_file_list)}, partition_size={partition_size}")
    for i in range(int((len(img_file_list) + partition_size - 1) / partition_size)):
        img_file_partition_list.append(img_file_list[i * partition_size: (i + 1) * partition_size])
    # LOGGER.debug(pprint.pformat(img_file_partition_list))
    return img_file_partition_list


def merge_image_files(feed_dir_path: Path, img_file_list: List[Path], feed_img_dir_path: Path, img_url: str, unit_num: int) -> Path:
    LOGGER.debug("# merge_image_files(feed_dir_path=%s, img_file_list=%r, feed_img_dir_path=%r, img_url='%s', unit_num=%d)", PathUtil.short_path(feed_dir_path), img_file_list, feed_img_dir_path, img_url, unit_num)
    suffix = img_file_list[0].suffix
    merged_img_file_path = FileManager.get_cache_file_path(feed_img_dir_path, img_url, postfix=str(unit_num), suffix=suffix)
    cmd = f"merge.py '{str(merged_img_file_path)}' "
    for cache_file in img_file_list:
        cmd += f" '{cache_file}'"
    LOGGER.debug(cmd)
    result, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    LOGGER.debug(result)
    if not result:
        LOGGER.error(f"<!-- can't merge the image files, cmd='{cmd}', {error} -->")
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


def remove_image_files(feed_dir_path: Path, img_file_list: List[str]) -> bool:
    LOGGER.debug("# remove_image_files(feed_dir_path=%r, img_file_list=%r)", PathUtil.short_path(feed_dir_path), img_file_list)
    # remove the original image
    cmd = "rm -f "
    for cache_file in img_file_list:
        cmd = cmd + "'" + cache_file + "' "
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    if error:
        LOGGER.error(f"<!-- can't remove files '{img_file_list}', {cmd}, {error} -->")
        return False
    return True


def split_image_file(feed_dir_path: Path, img_file_path: Path, bandwidth: int, diff_threshold: float, size_threshold: float, acceptable_diff_of_color_value: int, num_units: int, bgcolor_option: str, orientation_option: str, wider_scan_option: str) -> bool:
    LOGGER.debug("# split_image_file(feed_dir_path=%r, img_file_path=%r, bandwidth=%d, diff_threshold=%f, size_threshold=%f, acceptable_diff_of_color_value=%d, num_units=%d, bgcolor_option=%s, orientation_option=%s, wider_scan_option=%s)", PathUtil.short_path(feed_dir_path), PathUtil.short_path(img_file_path), bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, num_units, bgcolor_option, orientation_option, wider_scan_option)
    # split the image
    cmd = f"split.py -b {bandwidth} -t {diff_threshold} -s {size_threshold} -a {acceptable_diff_of_color_value} -n {num_units} {bgcolor_option} {orientation_option} {wider_scan_option} {img_file_path}"
    LOGGER.debug(cmd)
    _, error = Process.exec_cmd(cmd, dir_path=feed_dir_path)
    if error:
        LOGGER.error(f"<!-- can't split the image file, {cmd}, {error} -->")
        return False
    return True


def print_image_files(num_units: int, feed_img_dir_path: Path, img_url_prefix: str, img_url: str, img_file_path: Optional[Path], postfix: Optional[str], do_flip_right_to_left: bool) -> None:
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
            split_img_path = FileManager.get_cache_file_path(path_prefix=feed_img_dir_path, img_url=img_url, postfix=postfix, index=i + 1)
            suffix = ""
        LOGGER.debug(f"{split_img_path=}, {suffix=}")
        if split_img_path.is_file():
            split_img_url = FileManager.get_cache_url(img_url_prefix, img_url, postfix=postfix, index=i + 1)
            print(f"<img src='{split_img_url}{suffix}'/>")


def print_cached_image_file(feed_img_dir_path: Path, img_url_prefix: str, img_url: str, unit_num: Optional[int] = None) -> None:
    img_url_str = img_url if not img_url.startswith("data:image") else img_url[:30]
    LOGGER.debug("# print_cached_image_file(feed_img_dir_path=%r, img_url_prefix='%s', img_url='%s', unit_num=%d)", PathUtil.short_path(feed_img_dir_path), img_url_prefix, img_url_str, unit_num)
    img_file_path = FileManager.get_cache_file_path(path_prefix=feed_img_dir_path, img_url=img_url, postfix=unit_num)
    LOGGER.debug("img_file='%s'", PathUtil.short_path(img_file_path))
    if img_file_path.is_file():
        suffix = img_file_path.suffix
        img_url = FileManager.get_cache_url(url_prefix=img_url_prefix, img_url=img_url, postfix=unit_num, suffix=suffix)
        print(f"<img src='{img_url}'/>")


def print_usage(program_name: str) -> None:
    print(f"Usage: {program_name} [-c <fuzzy>] [-m] [-i] [-l] [-v] [-d] <page_url>")
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

    # options
    bgcolor_option: str = ""
    do_merge = False
    do_innercrop = False
    orientation_option: str = ""
    wider_scan_option: str = ""
    do_flip_right_to_left = False
    do_only_merge = False
    optlist, args = getopt.getopt(sys.argv[1:], "f:c:milvwb:t:n:s:a:h", ["only-merge="])
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
    feed_img_dir_path = Path(os.environ["WEB_SERVICE_FEEDS_DIR"]) / "img" / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    LOGGER.debug("feed_name=%s", feed_name)
    LOGGER.debug("feed_img_dir_path=%r", feed_img_dir_path)

    config = Config(feed_dir_path=feed_dir_path)
    if not config:
        LOGGER.error("can't get configuration")
        return -1
    extraction_conf = config.get_extraction_configs()
    if not extraction_conf:
        LOGGER.error("can't get extraction configuration")
        return -1

    headers: Dict[str, Any] = {}
    if "user_agent" in extraction_conf:
        headers["User-Agent"] = extraction_conf["user_agent"]
    headers["Referer"] = URL.encode_suffix(page_url)

    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    img_file_list, img_url_list, normal_html_lines = download_image_and_read_metadata(feed_dir_path, crawler, feed_img_dir_path, page_url)
    for line in normal_html_lines:
        print(line)
    LOGGER.debug(f"img_file_list={img_file_list}")
    if len(img_file_list) == 0:
        return 0

    if do_merge:
        # merge-split mode
        img_file_partition_list: List[List[Path]] = split_image_list(img_file_list)
        LOGGER.debug(f"img_file_partition_list={img_file_partition_list}")

        unit_num = 1
        for img_file_partition in img_file_partition_list:
            if len(img_file_partition) == 0:
                continue

            merged_img_file_path = merge_image_files(feed_dir_path, img_file_partition, feed_img_dir_path, page_url, unit_num)

            if do_innercrop:
                crop_image_file(feed_dir_path, merged_img_file_path)

            if do_only_merge:
                print_cached_image_file(feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=page_url, unit_num=unit_num)
            else:
                # remove_image_files(feed_dir_path, img_file_partition)
                if split_image_file(feed_dir_path, merged_img_file_path, bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, num_units, bgcolor_option, orientation_option, wider_scan_option):
                    # remove_image_files([merged_img_file])
                    print_image_files(num_units=num_units, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=page_url, img_file_path=merged_img_file_path, postfix=str(unit_num), do_flip_right_to_left=do_flip_right_to_left)

            unit_num = unit_num + 1
    else:
        # only split mode
        for img_file, img_url in zip(img_file_list, img_url_list):
            LOGGER.debug(f"img_file={img_file}", )
            img_url_short = img_url if not img_url.startswith("data:image") else img_url[:30]
            LOGGER.debug(f"img_url={img_url_short}")
            if split_image_file(feed_dir_path, img_file, bandwidth, diff_threshold, size_threshold, acceptable_diff_of_color_value, num_units, bgcolor_option, orientation_option, wider_scan_option):
                if do_innercrop:
                    crop_image_files(feed_dir_path, num_units, feed_img_dir_path, img_url)
                print_image_files(num_units=num_units, feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=img_url, img_file_path=img_file, postfix=None, do_flip_right_to_left=do_flip_right_to_left)
            else:
                print_cached_image_file(feed_img_dir_path=feed_img_dir_path, img_url_prefix=img_url_prefix, img_url=img_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
