#!/usr/bin/env python

import sys
import re
import getopt
import logging.config
from pathlib import Path
from utils.image_downloader import ImageDownloader
from bin.feed_maker_util import Config, IO, PathUtil, Env
from bin.crawler import Crawler


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    feed_dir_path = Path.cwd()

    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if not feed_dir_path.is_dir():
        LOGGER.error("can't find such a directory '%s'", PathUtil.short_path(feed_dir_path))
        return -1

    page_url = args[0]
    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)

    config = Config(feed_dir_path)
    extraction_conf = config.get_extraction_configs()
    headers = {
        "User-Agent": extraction_conf.get("user_agent", ""),
        "Referer": page_url
    }
    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    line_list = IO.read_stdin_as_line_list()
    for line in line_list:
        m = re.search(r'<img[^>]*src=[\"\'](?P<img_url>[^\"\']+)[\"\']', line)
        if m:
            img_url = m.group("img_url")
            _, new_img_url = ImageDownloader.download_image(crawler, feed_img_dir_path, img_url)
            if new_img_url:
                print(f"<img src='{new_img_url}'/>")
            else:
                print("<img src='not_found.png' alt='not exist or size 0'/>")
        else:
            print(line, end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
