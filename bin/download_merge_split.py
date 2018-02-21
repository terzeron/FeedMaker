#!/usr/bin/env python3


import os
import sys
import re
import getopt
import time
import feedmakerutil
from feedmakerutil import debug_print
from feedmakerutil import Cache


def download_image(path_prefix, img_url, img_ext, page_url):
    debug_print("# download_image(%s, %s, %s, %s)" % (path_prefix, img_url, img_ext, page_url))
    cache_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext)
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return True
    cmd = 'crawler.sh --download "%s" --referer "%s" "%s"' % (cache_file, page_url, img_url)
    debug_print("<!-- %s -->" % (cmd))
    (result, error) = feedmakerutil.exec_cmd(cmd)
    debug_print("<!-- %s -->" % (result))
    if error:
        time.sleep(5)
        (result, error) = feedmakerutil.exec_cmd(cmd)
        if error:
            return False
    if os.path.isfile(cache_file) and os.stat(cache_file).st_size > 0:
        return result
    return False


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i+n]


def get_total_height(img_size_list):
    debug_print("# get_total_height()")
    #
    # calculate the total height
    #
    total_height = 0
    for dimension in img_size_list:
        (width, height) = dimension.split("\t")
        total_height = total_height + int(height)
    debug_print("<!-- total_height=%d -->" % (total_height))
    return total_height


def download_image_and_read_metadata(path_prefix, img_ext, page_url):
    debug_print("# download_image_and_read_metadata(%s, %s, %s)" % (path_prefix, img_ext, page_url))
    #
    # read input and collect image files into the list
    # (file name, url and dimension)
    #
    img_file_list = []
    img_url_list = []
    img_size_list = []
    line_list = IO.read_stdin_as_line_list()
    for line in line_list:
        m1 = re.search(r"<img src=(?:[\"'])(?P<img_url>[^\"']+)(?:[\"'])( width='\d+%?')?/?>", line)
        if m1:
            img_url = m1.group("img_url")
            debug_print(img_url)
            # download
            cache_file = download_image(path_prefix, img_url, img_ext, page_url)
            if not cache_file:
                sys.stderr.write("Error: can't download the image from '%s'\n" % (img_url))
                continue
            img_file_list.append(cache_file)
            img_url_list.append(img_url)
            debug_print("<!-- %s -> %s -->" % (img_url, cache_file))
            cmd = "../../../CartoonSplit/size.py " + cache_file
            debug_print(cmd)
            (result, error) = feedmakerutil.exec_cmd(cmd)
            if error:
                sys.stderr.write("Error: can't get the size of image file '%s', cmd='%s'\n" % (cache_file, cmd))
                sys.exit(-1)

            m2 = re.search(r"^(?P<width>\d+)\s+(?P<height>\d+)", result)
            if m2:
                width = m2.group("width")
                height = m2.group("height")
                img_size_list.append("%s\t%s" % (width, height))
                debug_print("<!-- cache_file=cache_file, img_url=img_url, width=width, height=height -->")
        else:
            debug_print(line)
    return (img_file_list, img_url_list, img_size_list)


def split_image_list(img_file_list):
    debug_print("# split_image_list()")
    #
    # split array into 4 sub-array
    #
    img_file_partition_list = []
    partition_size = int((len(img_file_list) + 3) / 4) 
    debug_print("<!-- length=%d, partition_size=%d -->" % (len(img_file_list), partition_size))
    for i in range(int(len(img_file_list) / partition_size)):
        img_file_partition_list.append(img_file_list[i * partition_size : (i+1) * partition_size])
    debug_print(img_file_partition_list)
    return img_file_partition_list


def merge_image_files(img_file_list, path_prefix, img_url, img_ext, num):
    debug_print("# merge_image_files()")
    #
    # merge mode
    #
    merged_img_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext, num)
    cmd  = "../../../CartoonSplit/merge.py " + merged_img_file + " "
    for cache_file in img_file_list:
        cmd = cmd + cache_file + " "
    debug_print(cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    debug_print(result)
    if error:
        sys.stderr.write("Error: can't merge the image files, cmd='%s'\n" % (cmd))
        sys.exit(-1)
    return merged_img_file


def crop_image_file(img_file):
    debug_print("# crop_imagefile()")
    #
    # crop mode (optional)
    #
    cmd = "innercrop -f 4 -m crop \"%s\" \"%s.temp\" && mv -f \"%s.temp\" \"%s\"" % (img_file, img_file, img_file, img_file)
    debug_print(cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    if error:
        sys.stderr.write("Error: can't crop the image file '%s', cmd='%s'\n" % (img_file, cmd))
        sys.exit(-1)


def remove_image_files(img_file_list):
    debug_print("# remove_image_files()")
    #
    # remove the original image
    # 
    cmd = "rm -f "
    for cache_file in img_file_list:
        cmd = cmd + "'" + cache_file + "' "
    debug_print(cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    debug_print(result)
    if error:
        return False
    return True
        

def split_image_file(img_file, num_units, bgcolor_option, orientation_option):
    debug_print("# split_image_file(%s, %d, %s, %s)" % (img_file, num_units, bgcolor_option, orientation_option))
    #
    # split the image
    #
    cmd = "../../../CartoonSplit/split.py -b 10 -t 0.03 -n %d %s %s %s" % (num_units, orientation_option, bgcolor_option, img_file)
    debug_print(cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    debug_print(result)
    if error:
        sys.stderr.write("Error: can't split the image file, cmd='%s'\n" % (cmd))
        sys.exit(-1)


def print_image_files(num_units, path_prefix, img_url_prefix, img_url, img_ext, num, do_flip_right_to_left):
    debug_print("# print_image_files(%d, %s, %s, %s, %s, %d, %s)" % (num_units, path_prefix, img_url_prefix, img_url, img_ext, num if num else 0, do_flip_right_to_left))
    # print the split images
    if not do_flip_right_to_left:
        custom_range = range(num_units)
    else:
        custom_range = reversed(range(num_units))
        for i in custom_range:
            split_img_file = Cache.get_cache_file_name(path_prefix, img_url, img_ext, num, i + 1)
            debug_print("split_img_file=" + split_img_file)
            if os.path.exists(split_img_file):
                split_img_url = Cache.get_cache_url(img_url_prefix, img_url, img_ext, num, i + 1)
                print("<img src='%s''/>" % (split_img_url))


def main():
    global is_debug_mode
    
    cmd = "basename " + os.getcwd()
    debug_print(cmd);
    (result, error) = feedmakerutil.exec_cmd(cmd)
    feed_name = result.rstrip()
    debug_print("<!-- feed_name=%s -->" % (feed_name))
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS"] + "/img/" + feed_name
    debug_print("<!--- path_prefix=%s -->" % (path_prefix))
    feedmakerutil.make_path(path_prefix)

    img_url_prefix = "http://terzeron.net/xml/img/" + feed_name
    img_prefix = ""
    img_index = -1
    img_ext = "jpg"
    num_units = 25
    cmd = ""
    result = ""

    # options
    bgcolor_option = ""
    do_merge = False
    do_innercrop = False
    orientation_option = ""
    do_flip_right_to_left = False
    optlist, args = getopt.getopt(sys.argv[1:], "c:milvd")
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
            num_units = 3
        elif o == "-d":
            is_debug_mode = True
            
    page_url = args[0]
    (img_file_list, img_url_list, img_size_list) = download_image_and_read_metadata(path_prefix, img_ext, page_url)
    debug_print(img_file_list)
    if len(img_file_list) == 0:
        sys.exit(0)

    if do_merge:
        # merge-split mode
        total_height = get_total_height(img_size_list)
        img_file_partition_list = split_image_list(img_file_list)
    
        num = 1
        for img_file_list in img_file_partition_list:
            if len(img_file_list) == 0:
                continue

            merged_img_file = merge_image_files(img_file_list, path_prefix, page_url, img_ext, num)

            if do_innercrop:
                crop_image_file(merged_img_file)
                
            remove_image_files(img_file_list)
            split_image_file(merged_img_file, num_units, bgcolor_option, orientation_option)
            remove_image_files([merged_img_file])
            print_image_files(num_units, path_prefix, img_url_prefix, page_url, img_ext, num, do_flip_right_to_left)
            num = num + 1
    else:
        # only split mode
        for i in range(len(img_file_list)):
            img_file = img_file_list[i]
            img_url = img_url_list[i]
            debug_print("img_file=" + img_file)
            debug_print("img_url=" + img_url)
            split_image_file(img_file, num_units, bgcolor_option, orientation_option)
            print_image_files(num_units, path_prefix, img_url_prefix, img_url, img_ext, None, do_flip_right_to_left)
                

                                 
if __name__ == "__main__":
    main()
