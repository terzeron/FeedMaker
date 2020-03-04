#!/usr/bin/env python


import sys
import os
import re
import getopt
import subprocess
import logging
import logging.config
from typing import Set, Dict
from feed_maker_util import IO, exec_cmd


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


def print_usage() -> None:
    print("_usage: %s\t[ -t <threshold> ] <output file>\n" % (sys.argv[0]))


def main() -> int:
    threshold: float = 0.0
    optlist, args = getopt.getopt(sys.argv[1:], "t:")
    for o, a in optlist:
        if o == "-t":
            threshold = float(a)
            print("%f" % threshold)

    if len(args) < 1:
        print_usage()
        return -1

    file_prefix = args[0]
    intermediate_file = file_prefix + ".intermediate"
    temp_output_file = file_prefix + ".temp"
    output_file = file_prefix + ".output"
    line_num_link_map: Dict[int, str] = {}
    title_existence_set: Set[str] = set([])

    # split link and title into two separate files
    # and make line number & link mapping table
    with open(intermediate_file, 'w', encoding='utf-8') as out_file:
        line_num = 1
        for line in IO.read_stdin_as_line_list():
            if re.search(r"^#", line):
                continue
            line = line.rstrip()
            (link, title) = line.split("\t")
            line_num_link_map[line_num] = link + "\t" + title

            clean_title = title.lower()
            clean_title = re.sub(r'[\s!-/:-@\[-`]*', '', clean_title)
            if clean_title not in title_existence_set:
                title_existence_set.add(clean_title)
            out_file.write("%s\n" % title)
            line_num += 1

    # hierarchical clustering
    cluster_dir = os.environ["FEED_MAKER_HOME_DIR"] + "/../HierarchicalClustering"
    cmd = "%s/hcluster -t '%f' -s stop_words.txt '%s' '%s'" % (cluster_dir, threshold, intermediate_file, temp_output_file)
    logger.debug(cmd)
    result, error = exec_cmd(cmd)
    logger.debug(result, error)

    # convert & extract temporary output file
    cmd = "awk -F'\\t' '$2 >= 3 { for (i = 3; i < NF; i += 2) { print $(i) FS $(i + 1) } }' '%s'" % temp_output_file
    logger.debug(cmd)
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as p:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            for line in p.stdout:
                line = line.rstrip()
                (line_num_str, title) = line.split("\t")
                line_num = int(line_num_str)
                out_file.write("%s\n" % (line_num_link_map[line_num]))

    return 0


if __name__ == "__main__":
    sys.exit(main())
