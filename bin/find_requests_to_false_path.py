#!/usr/bin/env python


import sys
import re
import requests
from requests import status_codes
from typing import Dict


def main() -> int:
    name_status_map: Dict[str, int] = {}

    for file in sys.argv[1:]:
        with open(file, 'r') as f:
            for line in f:
                m = re.search(r'\[\d+/\w+/\d+:\d+:\d+:\d+ \+\d+\] \"GET /xml/(?P<feed_name>.+)\.xml HTTP\S+\" (?P<status>\d+)', line)
                if m:
                    feed_name = m.group('feed_name')
                    status = int(m.group('status'))
                    name_status_map[feed_name] = status

    for name, status in name_status_map.items():
        if status == 200:
            color = 34
        elif status == 304:
            color = 31
        elif status == 404:
            color = 32
        elif status == 410:
            color = 39
        message = status_codes._codes[status][0]
        print('%-25s \033[1;%dm%d\033[0m %s' % (name, color, status, message))
    return 0

                
if __name__ == "__main__":
    sys.exit(main())
