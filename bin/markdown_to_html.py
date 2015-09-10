#!/usr/bin/env python3


import os
import sys
import re
import feedmakerutil


def main():
    cmd = "markdown"
    html = feedmakerutil.execCmd(cmd)
    html = re.sub(r'(?P<url>https?://[^"\'\<\>]+)', r'<a href="\g<url>">\g<url></a>', html)
    print(html)
    

if __name__ == "__main__":
    main()
