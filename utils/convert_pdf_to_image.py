#!/usr/bin/env python


import sys
import os
import getopt
import logging.config
from pathlib import Path
from pdf2image import convert_from_path
from feed_maker_util import Cache, header_str
from crawler import Crawler


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
            pdf_file_path = Path(url_or_file)
        elif url_or_file.startswith("http"):
            pid = os.getpid()
            pdf_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "pdf"
            pdf_file_path = pdf_dir_path / (str(pid) + ".pdf")
            crawler = Crawler()
            result, error, _ = crawler.run(url=url_or_file, download_file=pdf_file_path)
            if not result:
                LOGGER.error(error)
        else:
            return -1
    else:
        return -1

    feed_name = Path.cwd().name
    feed_img_dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"]) / "img" / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    image_type = "JPEG"
    ext = ".jpg"

    images = convert_from_path(pdf_file_path)
    print(header_str)
    for num, image in enumerate(images):
        cache_file = Cache.get_cache_file_path(feed_img_dir_path, url_or_file)
        cache_url = Cache.get_cache_url(img_url_prefix, url_or_file, "")
        image_file = cache_file.with_suffix("." + str(num) + ext)
        image_url = cache_url + "." + str(num) + ext
        image.save(image_file, image_type)
        print(f"<img src='{image_url}'/>")

    pdf_file_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
