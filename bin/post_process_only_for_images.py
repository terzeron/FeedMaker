#!/usr/bin/env python3


import re
import sys


def main() -> int:
    for line in sys.stdin:
        if re.search(r'<meta|style', line):
            print(line, end='')
        match = re.search(r'(?P<img_tag><img src=[\'"]?[^\'"]+[\'"]?[^>]*>)', line)
        if match:
            print(match.group('img_tag'))
    return 0


if __name__ == "__main__":
    sys.exit(main())
