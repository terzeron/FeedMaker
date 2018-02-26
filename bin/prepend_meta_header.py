#!/usr/bin/env python3

import sys
import feedmakerutil
from logger import Logger


logger = Logger("prepend_meta_header.py")


def main():
    print(feedmakerutil.header_str)
    
    for buf in sys.stdin:
        print(buf, end="")

            
if __name__ == "__main__":
    main()
