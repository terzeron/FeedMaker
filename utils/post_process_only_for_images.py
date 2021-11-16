#!/usr/bin/env python


import re
import sys
import getopt


def print_usage() -> None:
    print(f"Usage:\t{sys.argv[0]} [ <option> ]")
    print("options")
    print("\t-u\t\tleave only unique images")


def main() -> int:
    leave_only_unique_images: bool = False

    try:
        opts, _ = getopt.getopt(sys.argv[1:], "f:u")
    except getopt.GetoptError:
        print_usage()
        sys.exit(-1)
    for o, _ in opts:
        if o == "-u":
            leave_only_unique_images = True

    prev_img_tag: str = ""
    for line in sys.stdin:
        if re.search(r'<(meta|style)', line):
            print(line, end='')
        match = re.search(r'(?P<img_tag><img src=[\'"]?[^\'"]+[\'"]?[^>]*>)', line)
        if match:
            img_tag = match.group("img_tag")
            if not leave_only_unique_images or img_tag != prev_img_tag:
                print(img_tag)
            prev_img_tag = img_tag

    return 0


if __name__ == "__main__":
    sys.exit(main())
