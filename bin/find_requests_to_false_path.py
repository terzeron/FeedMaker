#!/usr/bin/env python


import sys
import re
import requests


def main():
    name_status_map = {}

    for file in sys.argv[1:]:
        with open(file, 'r') as f:
            for line in f:
                m = re.search(r'\[\d+/\w+/\d+:\d+:\d+:\d+ \+\d+\] \"GET /xml/(?P<feed_name>.+)\.xml HTTP\S+\" (?P<status>\d+)', line)
                if m:
                    feed_name = m.group('feed_name')
                    status = m.group('status')
                    name_status_map[feed_name] = status
    for name in name_status_map:
        status = int(name_status_map[name])
        if status == 200:
            color = 34
        elif status == 304:
            color = 31
        elif status == 404:
            color = 32
        elif status == 410:
            color = 39
        message = requests.status_codes._codes[status][0]
        print('%-25s \033[1;%dm%d\033[0m %s' % (name, color, status, message))

                
if __name__ == "__main__":
    sys.exit(main())
