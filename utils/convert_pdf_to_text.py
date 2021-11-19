#!/usr/bin/env python


import sys
import os
import re
import getopt
import logging.config
from pathlib import Path
from crawler import Crawler
from pdftotext import PDF

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    sys.stdin.read()
    sys.stdin.flush()
    sys.stdin.close()

    _, args = getopt.getopt(sys.argv[1:], "f:")

    if len(args) == 1:
        url_or_file = args[0]
        if os.path.isfile(url_or_file):
            pdf_file_path = Path(Path.cwd() / url_or_file)
        elif url_or_file.startswith("http"):
            pid = os.getpid()
            pdf_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "pdf"
            pdf_file_path = pdf_dir_path / (str(pid) + ".pdf")
            crawler = Crawler()
            result, error, _ = crawler.run(url=url_or_file, download_file=pdf_file_path)
            if not result:
                LOGGER.error(error)
        else:
            LOGGER.error(f"neither file or url: {url_or_file}")
            return -1
    else:
        return -1

    with open(pdf_file_path, "rb") as f:
        pdf = PDF(f)
        for page in pdf:
            print(page)
            page = re.sub(r'\n', '<br>\n', page)
            page = re.sub(r'\s\s+', ' ', page)
            page = re.sub(r'\s{4,}', '  ', page)
            page = re.sub(r'^\s*\S+\s* - ', '\n - ', page)
            page = re.sub(r'(?<=\S)\s*(?P<bullet>[▶•])', '\n\g<bullet>', page)
            print(page)

    pdf_file_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
