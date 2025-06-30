#!/usr/bin/env python


import sys
import re
import getopt
from bin.feed_maker_util import IO


def main() -> int:
    url_prefix = "https://terms.naver.com/"
    state = 0

    num_of_recent_feeds = 30
    optlist, _ = getopt.getopt(sys.argv[1:], "f:n:")
    for o, a in optlist:
        if o == '-n':
            num_of_recent_feeds = int(a)

    result_list = []
    for line in IO.read_stdin_as_line_list():
        if state == 0:
            m = re.search(r'<strong class="title">', line)
            if m:
                state = 1
        elif state == 1:
            m = re.search(r'<a href="/(?P<url>entry\.naver\?[^"]+)"[^>]*>(?P<title>[^<]+)</a>', line)
            if m:
                url = m.group("url")
                url = url.replace('&amp;', '&')
                title = m.group("title")
                link = url_prefix + url
                result_list.append((link, title))
                state = 0

    for (link, title) in result_list[:num_of_recent_feeds]:
        print(f"{link}\t{title}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
