#!/Usr/bin/env python3


import sys
import os
import re
import getopt
import subprocess
import feedmakerutil
from logger import Logger


logger = Logger("aggregate_titles.py")


def print_usage():
    print("_usage: %s\t[ -t <threshold> ] <output file>\n" % (sys.argv[0]))


def main():
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
    line_num_link_map = {}
    title_existence_set = set([])

    # split link and title into two separate files
    # and make line number & link mapping table
    with open(intermediate_file, 'w', encoding='utf-8') as out_file:
        line_num = 1
        for line in feedmakerutil.read_stdin_as_line_list():
            if re.search(r"^\#", line):
                continue
            line = line.rstrip()
            (link, title) = line.split("\t")        
            line_num_link_map[line_num] = link + "\t" + title
        
            clean_title = title.lower()
            clean_title = re.sub(r'[\s\!-\/\:-\@\[-\`]*', '', clean_title)
            if clean_title in title_existence_set:
                continue
            else:
                title_existence_set.add(clean_title)
            out_file.write("%s\n" % (title))
            line_num += 1

    # hierarchical clustering
    cluster_dir = os.environ["FEED_MAKER_HOME"] + "/../HierarchicalClustering"
    cmd = "%s/hcluster -t '%f' -s stop_words.txt '%s' '%s'" % (cluster_dir, threshold, intermediate_file, temp_output_file)
    logger.debug(cmd)
    (result, error) = feedmakerutil.exec_cmd(cmd)
    logger.debug(result)

    # convert & extract temporary output file
    cmd = "awk -F'\\t' '$2 >= 3 { for (i = 3; i < NF; i += 2) { print $(i) FS $(i + 1) } }' '%s'" % (temp_output_file)
    logger.debug(cmd)
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE) as p:
        with open(output_file, 'w', encoding='utf-8') as out_file:
            for line in p.stdout:
                line = line.rstrip()
                (line_num, title) = line.split("\t")
                out_file.write("%d\n" % (line_num_link_map[line_num]))


if __name__ == "__main__":
    sys.exit(main())
