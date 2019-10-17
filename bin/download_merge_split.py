#!/usr/bin/env python


import os
import sys
import re
import getopt
import time
import pprint
import logging
import logging.config
import feed_maker_util
from feed_maker_util import Cache, IO, exec_cmd, make_path
from typing import List, Tuple, Optional


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


def download_image(path_prefix: str, img_url: str, img_ext: str, page_url: str) -> Optional[str]:
    logger.debug("# download_image(%s, %s, %s, %s)" % (path_prefix, img_url, img_ext, page_url))
    cache_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext)
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    cmd = 'crawler.py --retry 2 --download "%s" --referer "%s" "%s"' % (cache_file, page_url, img_url)
    logger.debug("<!-- cmd: %s -->" % cmd)
    (result, error) = exec_cmd(cmd)
    logger.debug("<!-- result: %s -->" % result)
    if error:
        time.sleep(5)
        (result, error) = exec_cmd(cmd)
        if error:
            return None
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return cache_file
    return None


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_total_height(img_size_list: List[str]) -> int:
    logger.debug("# get_total_height()")
    #
    # calculate the total height
    #
    total_height = 0
    for dimension in img_size_list:
        (width, height) = dimension.split("\t")
        total_height = total_height + int(height)
    logger.debug("<!-- total_height=%d -->" % total_height)
    return total_height


def download_image_and_read_metadata(path_prefix: str, img_ext: str, page_url: str) -> Tuple[List[str], List[str], List[str]]:
    logger.debug("# download_image_and_read_metadata(%s, %s, %s)" % (path_prefix, img_ext, page_url))
    #
    # read input and collect image files into the list
    # (file name, url and dimension)
    #
    img_file_list: List[str] = []
    img_url_list: List[str] = []
    img_size_list: List[str] = []
    line_list: List[str] = IO.read_stdin_as_line_list()
    for line in line_list:
        m1 = re.search(r"<img src=(?:[\"'])(?P<img_url>[^\"']+)(?:[\"'])( width='\d+%?')?/?>", line)
        if m1:
            img_url = m1.group("img_url")
            logger.debug(img_url)
            # download
            cache_file = download_image(path_prefix, img_url, img_ext, page_url)
            if not cache_file:
                logger.error("can't download the image from '%s'" % img_url)
                continue
            img_file_list.append(cache_file)
            img_url_list.append(img_url)
            logger.debug("<!-- %s -> %s -->" % (img_url, cache_file))
            cmd = "size.py " + cache_file
            logger.debug(cmd)
            (result, error) = exec_cmd(cmd)
            if error:
                logger.debug("can't get the size of image file '%s', cmd='%s'" % (cache_file, cmd))
                continue

            m2 = re.search(r"^(?P<width>\d+)\s+(?P<height>\d+)", result)
            if m2:
                width = int(m2.group("width"))
                height = int(m2.group("height"))
                img_size_list.append("%s\t%s" % (width, height))
                logger.debug("<!-- cache_file=cache_file, img_url=img_url, width=width, height=height -->")
        else:
            logger.debug(line)
    return img_file_list, img_url_list, img_size_list


def split_image_list(img_file_list: List[str]) -> List[List[str]]:
    logger.debug("# split_image_list()")
    #
    # split array into 4 sub-array
    #
    img_file_partition_list: List[List[str]] = []
    partition_size = int((len(img_file_list) + 3) / 4)
    logger.debug("<!-- length=%d, partition_size=%d -->" % (len(img_file_list), partition_size))
    for i in range(int(len(img_file_list) / partition_size)):
        img_file_partition_list.append(img_file_list[i * partition_size: (i + 1) * partition_size])
    logger.debug(pprint.pformat(img_file_partition_list))
    return img_file_partition_list


def merge_image_files(img_file_list: List[str], path_prefix: str, img_url: str, img_ext: str, unit_num: int) -> str:
    logger.debug("# merge_image_files()")
    #
    # merge mode
    #
    merged_img_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext, str(unit_num))
    cmd = "merge.py " + merged_img_file + " "
    for cache_file in img_file_list:
        cmd = cmd + cache_file + " "
    logger.debug(cmd)
    (result, error) = exec_cmd(cmd)
    logger.debug(result)
    if error:
        logger.error("can't merge the image files, cmd='%s'" % cmd)
        sys.exit(-1)
    return merged_img_file


def crop_image_file(img_file: str) -> None:
    logger.debug("# crop_image_file()")
    #
    # crop mode (optional)
    #
    cmd = "innercrop -f 4 -m crop \"%s\" \"%s.temp\" && mv -f \"%s.temp\" \"%s\"" % (img_file, img_file, img_file, img_file)
    logger.debug(cmd)
    (result, error) = exec_cmd(cmd)
    if error:
        # logger.error("can't crop the image file '%s', cmd='%s'" % (img_file, cmd))
        # sys.exit(-1)
        return


def crop_image_files(num_units: int, path_prefix: str, img_url: str, img_ext: str) -> None:
    logger.debug("# crop_image_files(%d, %s, %s, %s)" % (num_units, path_prefix, img_url, img_ext))
    # crop some image files
    for i in range(num_units):
        img_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext, None, i + 1)
        logger.debug("img_file=" + img_file)
        if os.path.exists(img_file):
            crop_image_file(img_file)


def remove_image_files(img_file_list: List[str]) -> bool:
    logger.debug("# remove_image_files()")
    # remove the original image
    cmd = "rm -f "
    for cache_file in img_file_list:
        cmd = cmd + "'" + cache_file + "' "
    logger.debug(cmd)
    (result, error) = exec_cmd(cmd)
    logger.debug(result)
    if error:
        return False
    return True


def split_image_file(img_file: str, bandwidth: int, diff_threshold: float, size_threshold: float, num_units: int, bgcolor_option: str, orientation_option: str) -> bool:
    logger.debug("# split_image_file(%s, %d, %s, %s)" % (img_file, num_units, bgcolor_option, orientation_option))
    # split the image
    cmd = "split.py -b %d -t %f -s %d -n %d %s %s %s" % (bandwidth, diff_threshold, size_threshold, num_units, orientation_option, bgcolor_option, img_file)
    logger.debug(cmd)
    (result, error) = exec_cmd(cmd)
    logger.debug(result)
    if error:
        logger.debug("can't split the image file, cmd='%s'" % cmd)
        return False
    return True


def print_image_files(num_units: int, path_prefix: str, img_url_prefix: str, img_url: str, img_ext: str, postfix: int, do_flip_right_to_left: bool) -> None:
    logger.debug("# print_image_files(%d, %s, %s, %s, %s, %s, %s)" % (num_units, path_prefix, img_url_prefix, img_url, img_ext, postfix if postfix else "", do_flip_right_to_left))
    # print some split images
    if not do_flip_right_to_left:
        custom_range = list(range(num_units))
    else:
        custom_range = list(reversed(range(num_units)))
    for i in custom_range:
        split_img_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext, postfix, i + 1)
        logger.debug("split_img_file=" + split_img_file)
        if os.path.exists(split_img_file):
            split_img_url = Cache.get_cache_url(img_url_prefix, img_url, img_ext, postfix, i + 1)
            print("<img src='%s'/>" % split_img_url)


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
    cmd = "basename " + os.getcwd()
    logger.debug(cmd)
    (result, error) = exec_cmd(cmd)
    feed_name = result.rstrip()
    logger.debug("<!-- feed_name=%s -->" % feed_name)
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/" + feed_name
    logger.debug("<!--- path_prefix=%s -->" % path_prefix)
    make_path(path_prefix)

    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    img_ext = "jpg"
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
    optlist, args = getopt.getopt(sys.argv[1:], "c:milvb:t:n:s:h")
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

    if len(args) < 1:
        print_usage(sys.argv[0])
        
    page_url = args[0]
    (img_file_list, img_url_list, img_size_list) = download_image_and_read_metadata(path_prefix, img_ext, page_url)
    logger.debug(pprint.pformat(img_file_list))
    if len(img_file_list) == 0:
        return 0

    if do_merge:
        # merge-split mode
        img_file_partition_list: List[List[str]] = split_image_list(img_file_list)

        unit_num = 1
        for img_file_list in img_file_partition_list:
            if len(img_file_list) == 0:
                continue

            merged_img_file = merge_image_files(img_file_list, path_prefix, page_url, img_ext, unit_num)

            if do_innercrop:
                crop_image_file(merged_img_file)

            remove_image_files(img_file_list)
            split_image_file(merged_img_file, bandwidth, diff_threshold, size_threshold, num_units, bgcolor_option, orientation_option)
            remove_image_files([merged_img_file])
            print_image_files(num_units, path_prefix, img_url_prefix, page_url, img_ext, unit_num, do_flip_right_to_left)
            unit_num = unit_num + 1
    else:
        # only split mode
        for i in range(len(img_file_list)):
            img_file = img_file_list[i]
            img_url = img_url_list[i]
            logger.debug("img_file=" + img_file)
            logger.debug("img_url=" + img_url)
            if split_image_file(img_file, bandwidth, diff_threshold, size_threshold, num_units, bgcolor_option, orientation_option):
                if do_innercrop:
                    crop_image_files(num_units, path_prefix, img_url, img_ext)
                print_image_files(num_units, path_prefix, img_url_prefix, img_url, img_ext, None, do_flip_right_to_left)
            else:
                print("<img src='%s'/>" % img_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
