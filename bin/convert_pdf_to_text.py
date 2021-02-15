#!/usr/bin/env python


import sys
import os
import re
import logging
import logging.config
import pdftotext
from crawler import Crawler


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    sys.stdin.read()
    sys.stdin.flush()
    sys.stdin.close()

    if len(sys.argv) > 1:
        if os.path.isfile(sys.argv[1]):
            pdf_file = sys.argv[1]
        elif sys.argv[1].startswith("http"):
            pdf_file = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/pdf/" + str(os.getpid()) + ".pdf"
            crawler = Crawler()
            _, error = crawler.run(url=sys.argv[1], download_file=pdf_file)
            if error:
                LOGGER.error(error)
        else:
            return -1
    else:
        return -1

    with open(pdf_file, "rb") as f:
        pdf = pdftotext.PDF(f)
        for page in pdf:
            page = re.sub(r'\n', '<br>\n', page)
            page = re.sub(r'\s\s+', ' ', page)
            page = re.sub(r'\s{4,}', '  ', page)
            page = re.sub(r'^\s*\S+\s* - ', '\n - ', page)
            page = re.sub(r'(?<=\S)\s*(?P<bullet>[▶•])', '\n\g<bullet>', page)
            print(page)

    f.close()
    os.unlink(pdf_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
