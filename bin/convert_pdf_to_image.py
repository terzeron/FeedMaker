#!/usr/bin/env python


import sys
import os
import logging
import logging.config
from pdf2image import convert_from_path
from feed_maker_util import Cache, exec_cmd, make_path
from crawler import Crawler


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def get_feed_name() -> str:
    cmd = "basename " + os.getcwd()
    result, error = exec_cmd(cmd)
    if error:
        LOGGER.warning("can't execute command '%s', %s", cmd, error)
        return ""
    return result.rstrip()

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

    feed_name = get_feed_name()
    path_prefix = os.environ["FEED_MAKER_WWW_FEEDS_DIR"] + "/img/" + feed_name
    make_path(path_prefix)
    img_url_prefix = "https://terzeron.com/xml/img/" + feed_name
    image_type = "JPEG"
    ext = ".jpg"

    images = convert_from_path(pdf_file)
    num = 0
    for image in images:
        cache_file = Cache.get_cache_file_name(path_prefix, sys.argv[1])
        cache_url = Cache.get_cache_url(img_url_prefix, sys.argv[1], "")
        image.save(cache_file + "." + str(num) + ext, image_type)
        print("<img src='%s%s'/>" % (cache_url + "." + str(num), ext))
        num = num + 1

    os.unlink(pdf_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
