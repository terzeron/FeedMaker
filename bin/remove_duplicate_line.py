#!/usr/bin/env python3


import os
import sys
import re


def removeDuplicates(seq):
    seen = set()
    seenAdd = seen.add
    return [ x for x in seq if not (x in seen or seenAdd(x))]


def main():
    totalList = []

    for line in sys.stdin:
        p = re.compile(r'^\#')
        match = p.match(line)
        if match:
            # skip comments
            continue
        totalList.append(line)

    totalList = removeDuplicates(totalList)

    totalList.sort()
    for item in totalList:
        print(item, end='')


if __name__ == "__main__":
    main()
