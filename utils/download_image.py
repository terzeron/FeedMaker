#!/usr/bin/env python

import sys
import re
import getopt
import logging.config
from pathlib import Path
from utils.image_downloader import ImageDownloader
from bin.feed_maker_util import Config, IO, PathUtil
from bin.crawler import Crawler


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    feed_dir_path = Path.cwd()

    optlist, _ = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if not feed_dir_path.is_dir():
        LOGGER.error("Invalid directory: %s", PathUtil.short_path(feed_dir_path))
        return -1

    config = Config(feed_dir_path)
    extraction_conf = config.get_extraction_configs()
    headers = {"User-Agent": extraction_conf.get("user_agent", None), "Referer": ""}
    crawler = Crawler(dir_path=feed_dir_path, headers=headers, num_retries=2)

    feed_img_dir_path = Path("/path/to/feed_img_dir")
    feed_img_dir_path.mkdir(exist_ok=True)

    line_list = IO.read_stdin_as_line_list()
    for line in line_list:
        m = re.search(r'<img[^>]*src=[\"\'](?P<img_url>[^\"\']+)[\"\']', line)
        if m:
            img_url = m.group("img_url")
            img_path = ImageDownloader.download_image(crawler, feed_img_dir_path, img_url)
            if img_path:
                print(f"<img src='{img_path}'/>")
            else:
                print("<img src='not_found.png' alt='not exist or size 0'/>")
        else:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
