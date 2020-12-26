#!/usr/bin/env python


import os
import sys
import re
import getopt
import logging
import logging.config
from typing import List, Tuple, Optional, Dict, Any
from crawler import Crawler
from feed_maker_util import Config, Cache, IO, exec_cmd, make_path
from download_image import download_image


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
IMAGE_NOT_FOUND_IMAGE_URL = "https://terzeron.com/image-not-found.png"


def download_image_and_read_metadata(crawler: Crawler, path_prefix: str, page_url: str) -> Tuple[List[str], List[str], List[str]]:
    LOGGER.debug("# download_image_and_read_metadata(crawler=%r, path_prefix=%r, page_url=%r)", crawler, path_prefix, page_url)
    #
    # read input and collect image files into the list
    # (file name, url and dimension)
    #
    img_file_list: List[str] = []
    img_url_list: List[str] = []

    crawler = Crawler(headers={"Referer": page_url}, num_retries=2)

    normal_html_lines = []
    line_list: List[str] = IO.read_stdin_as_line_list()
    for line in line_list:
        line = line.rstrip()
        m = re.search(r"<img src=(?:[\"'])(?P<img_url>[^\"']+)(?:[\"'])( width='\d+%?')?/?>", line)
        if m:
            img_url = m.group("img_url")
            LOGGER.debug("img_url=%s", img_url if not img_url.startswith("data:image") else img_url[:30])
            # download
            cache_file = download_image(crawler, path_prefix, img_url)
            if not cache_file:
                LOGGER.error("<!-- can't download the image from '%s' -->", img_url)
                print("<img src='%s' alt='not exist or size 0'/>" % IMAGE_NOT_FOUND_IMAGE_URL)
                continue
            img_file_list.append(cache_file)
            img_url_list.append(img_url)
            LOGGER.debug("<!-- %s -> %s -->", img_url if not img_url.startswith("data:image") else img_url[:30], cache_file)
        else:
            m = re.search(r'^</?br>$', line)
            if not m:
                normal_html_lines.append(line.rstrip())

    return img_file_list, img_url_list, normal_html_lines


def split_image_list(img_file_list: List[str]) -> List[List[str]]:
    LOGGER.debug("# split_image_list(img_file_list=%r)", img_file_list)
    #
    # split array into 4 sub-array
    #
    img_file_partition_list: List[List[str]] = []
    partition_size = int((len(img_file_list) + 3) / 4)
    LOGGER.debug("<!-- length=%d, partition_size=%d -->", len(img_file_list), partition_size)
    for i in range(int((len(img_file_list) + partition_size - 1) / partition_size)):
        img_file_partition_list.append(img_file_list[i * partition_size: (i + 1) * partition_size])
    #LOGGER.debug(pprint.pformat(img_file_partition_list))
    return img_file_partition_list


def merge_image_files(img_file_list: List[str], path_prefix: str, img_url: str, unit_num: int) -> str:
    LOGGER.debug("# merge_image_files(img_file_list=%r, path_prefix=%s, img_url=%s, unit_num=%d)", img_file_list, path_prefix, img_url, unit_num)
    #
    # merge mode
    #
    merged_img_file = Cache.get_cache_file_name(path_prefix, img_url, postfix=str(unit_num))
    cmd = "merge.py " + merged_img_file + " "
    for cache_file in img_file_list:
        cmd = cmd + cache_file + " "
    LOGGER.debug(cmd)
    result, error = exec_cmd(cmd)
    LOGGER.debug(result)
    if not result:
        LOGGER.error("<!-- can't merge the image files, cmd='%s', %s -->", cmd, error)
        sys.exit(-1)
    return merged_img_file


def crop_image_file(img_file: str) -> None:
    LOGGER.debug("# crop_image_file(img_file=%s)", img_file)
    #
    # crop mode (optional)
    #
    cmd = "innercrop -f 4 -m crop \"%s\" \"%s.temp\" && mv -f \"%s.temp\" \"%s\"" % (img_file, img_file, img_file, img_file)
    LOGGER.debug(cmd)
    _, error = exec_cmd(cmd)
    if error:
        LOGGER.error("<!-- can't crop the image file '%s', cmd='%s', %s -->", img_file, cmd, error)
        # sys.exit(-1)
        return


def crop_image_files(num_units: int, path_prefix: str, img_url: str) -> None:
    LOGGER.debug("# crop_image_files(num_units=%d, path_prefix=%s, img_url=%s)", num_units, path_prefix, img_url)
    # crop some image files
    for i in range(num_units):
        img_file = Cache.get_cache_file_name(path_prefix, img_url, index=(i + 1))
        LOGGER.debug("img_file=%s", img_file)
        if os.path.exists(img_file):
            crop_image_file(img_file)


def remove_image_files(img_file_list: List[str]) -> bool:
    LOGGER.debug("# remove_image_files(img_file_list=%r)", img_file_list)
    # remove the original image
    cmd = "rm -f "
    for cache_file in img_file_list:
        cmd = cmd + "'" + cache_file + "' "
    LOGGER.debug(cmd)
    _, error = exec_cmd(cmd)
    if error:
        LOGGER.error("<!-- can't remove files '%s', %s, %s -->", img_file_list, cmd, error)
        return False
    return True


def split_image_file(img_file: str, bandwidth: int, diff_threshold: float, size_threshold: float, num_units: int, bgcolor_option: str, orientation_option: str) -> bool:
    LOGGER.debug("# split_image_file(img_file=%s, bandwidth=%d, diff_threshold=%f, size_threshold=%f, num_units=%d, bgcolor_option=%s, orientation_option=%s)", img_file, num_units, diff_threshold, size_threshold, num_units, bgcolor_option, orientation_option)
    # split the image
    cmd = "split.py -b %d -t %f -s %d -n %d %s %s %s" % (bandwidth, diff_threshold, size_threshold, num_units, orientation_option, bgcolor_option, img_file)
    LOGGER.debug(cmd)
    _, error = exec_cmd(cmd)
    if error:
        LOGGER.error("<!-- can't split the image file, %s, %s -->", cmd, error)
        return False
    return True


def print_image_files(num_units: int, path_prefix: str, img_url_prefix: str, img_url: str, img_file: Optional[str], postfix: Optional[str], do_flip_right_to_left: bool) -> None:
    LOGGER.debug("# print_image_files(num_units=%d, path_prefix=%s, img_url_prefix=%s, img_url=%s, img_file=%r, postfix=%r, do_flip_right_to_left=%s)", num_units, path_prefix, img_url_prefix, img_url if not img_url.startswith("data:image") else img_url[:30], img_file, postfix, do_flip_right_to_left)
    # print some split images
    if not do_flip_right_to_left:
        custom_range = list(range(num_units))
    else:
        custom_range = list(reversed(range(num_units)))
    for i in custom_range:
        if img_file:
            file, ext = os.path.splitext(img_file)
            split_img_file = file + "." + str(i+1) + ext
        else:
            split_img_file = Cache.get_cache_file_name(path_prefix, img_url, postfix=postfix, index=(i + 1))
            ext = ""
        LOGGER.debug("split_img_file=%s", split_img_file)
        if os.path.exists(split_img_file):
            split_img_url = Cache.get_cache_url(img_url_prefix, img_url, postfix=postfix, index=(i + 1))
            print("<img src='%s%s'/>" % (split_img_url, ext))


def print_cached_image_file(path_prefix: str, img_url_prefix: str, img_url: str, unit_num: Optional[int] = None) -> None:
    LOGGER.debug("# print_cached_image_file(path_prefix=%s, img_url_prefix=%s, img_url=%s, unit_num=%r)", path_prefix, img_url_prefix, img_url if not img_url.startswith("data:image") else img_url[:30], unit_num)
    img_file = Cache.get_cache_file_name(path_prefix, img_url, postfix=unit_num)
    LOGGER.debug("img_file=%s", img_file)
    if os.path.exists(img_file):
        img_url = Cache.get_cache_url(img_url_prefix, img_url, postfix=unit_num)
        print("<img src='%s'/>" % img_url)


def print_usage(program_name: str) -> None:
    print("Usage: %s [-c <fuzzy>] [-m] [-i] [-l] [-v] [-d] <page_url>" % program_name)
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
    cmd = "basename " + os.getcwd()
    LOGGER.debug(cmd)
    result, error = exec_cmd(cmd)
    if not result:
        LOGGER.error("<!-- can't identify current working directory, %s -->", error)
        return -1
    feed_name = result.rstrip()
    LOGGER.debug("<!-- feed_name=%s -->", feed_name)
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/" + feed_name
    LOGGER.debug("<!--- path_prefix=%s -->", path_prefix)

    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    num_units = 25
    diff_threshold = 0.05
    size_threshold = 0
    bandwidth = 10

    # options
    bgcolor_option = ""
    do_merge = False
    do_innercrop = False
    orientation_option = ""
    do_flip_right_to_left = False
    do_only_merge = False
    optlist, args = getopt.getopt(sys.argv[1:], "c:milvb:t:n:s:h", ["only-merge="])
    for o, a in optlist:
        if o == "-c":
            bgcolor_option = "-c " + a
        elif o == "-m":
            do_merge = True
        elif o == "-i":
            do_innercrop = True
        elif o == "-l":
            do_flip_right_to_left = True
        elif o == "-v":
            orientation_option = "-v"
        elif o == "-b":
            bandwidth = int(a)
        elif o == "-t":
            diff_threshold = float(a)
        elif o == "-s":
            size_threshold = int(a)
        elif o == "-n":
            num_units = int(a)
        elif o == "-h":
            print_usage(sys.argv[0])
        elif o == "--only-merge":
            do_only_merge = (a == "true")

    if len(args) < 1:
        print_usage(sys.argv[0])

    page_url = args[0]

    make_path(path_prefix)

    config = Config()
    if not config:
        LOGGER.error("can't read configuration")
        return -1
    extraction_conf = config.get_extraction_configs()

    headers: Dict[str, Any] = {}
    if "user_agent" in extraction_conf:
        headers["User-Agent"] = extraction_conf["user_agent"]
    headers["Referer"] = page_url
    crawler = Crawler(headers=headers, num_retries=2)

    img_file_list, img_url_list, normal_html_lines = download_image_and_read_metadata(crawler, path_prefix, page_url)
    for line in normal_html_lines:
        print(line)
    LOGGER.debug("img_file_list=%r", img_file_list)
    if len(img_file_list) == 0:
        return 0

    if do_merge:
        # merge-split mode
        img_file_partition_list: List[List[str]] = split_image_list(img_file_list)
        LOGGER.debug("img_file_partition_list=%r", img_file_partition_list)

        unit_num = 1
        for img_file_partition in img_file_partition_list:
            if len(img_file_partition) == 0:
                continue

            merged_img_file = merge_image_files(img_file_partition, path_prefix, page_url, unit_num)

            if do_innercrop:
                crop_image_file(merged_img_file)

            if do_only_merge:
                print_cached_image_file(path_prefix, img_url_prefix, page_url, unit_num)
            else:
                #remove_image_files(img_file_partition)
                if split_image_file(merged_img_file, bandwidth, diff_threshold, size_threshold, num_units, bgcolor_option, orientation_option):
                    #remove_image_files([merged_img_file])
                    print_image_files(num_units, path_prefix, img_url_prefix, page_url, None, str(unit_num), do_flip_right_to_left)

            unit_num = unit_num + 1
    else:
        # only split mode
        for img_file, img_url in zip(img_file_list, img_url_list):
            LOGGER.debug("img_file=%s", img_file)
            LOGGER.debug("img_url=%s", img_url if not img_url.startswith("data:image") else img_url[:30])
            if split_image_file(img_file, bandwidth, diff_threshold, size_threshold, num_units, bgcolor_option, orientation_option):
                if do_innercrop:
                    crop_image_files(num_units, path_prefix, img_url)
                print_image_files(num_units, path_prefix, img_url_prefix, img_url, img_file, None, do_flip_right_to_left)
            else:
                print_cached_image_file(path_prefix, img_url_prefix, img_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
