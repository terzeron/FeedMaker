#!/usr/bin/env python3


import os
import sys
import re


def remove_duplicates(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if not (x in seen or seen_add(x))]


def main():
    total_list = []

    for line in sys.stdin:
        p = re.compile(r'^\#')
        match = p.match(line)
        if match:
            # skip comments
            continue
        total_list.append(line)

    total_list = remove_duplicates(total_list)

    total_list.sort()
    for item in total_list:
        print(item, end='')


if __name__ == "__main__":
    main()
