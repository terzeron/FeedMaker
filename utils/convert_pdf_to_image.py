#!/usr/bin/env python


import sys
import os
import getopt
import logging.config
from pathlib import Path
from pdf2image import convert_from_path # type: ignore[import]
from bin.feed_maker_util import FileManager, Env, header_str
from bin.crawler import Crawler


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def main() -> int:
    sys.stdin.read()
    sys.stdin.flush()
    sys.stdin.close()
    feed_dir_path = Path.cwd()

    optlist, args = getopt.getopt(sys.argv[1:], "f:")
    for o, a in optlist:
        if o == "-f":
            feed_dir_path = Path(a)

    if len(args) == 1:
        url_or_file = args[0]
        if Path(url_or_file).is_file():
            pdf_file_path = Path(url_or_file)
        elif url_or_file.startswith("http"):
            pid = os.getpid()
            pdf_dir_path = Path(Env.get("WEB_SERVICE_PDF_DIR_PREFIX"))
            pdf_file_path = pdf_dir_path / f"{pid}.pdf"
            crawler = Crawler()
            result, error, _ = crawler.run(url=url_or_file, download_file=pdf_file_path)
            if not result:
                LOGGER.error(error)
        else:
            return -1
    else:
        return -1

    feed_name = feed_dir_path.name
    feed_img_dir_path = Path(Env.get("WEB_SERVICE_IMAGE_DIR_PREFIX")) / feed_name
    feed_img_dir_path.mkdir(exist_ok=True)
    img_url_prefix = Env.get("WEB_SERVICE_IMAGE_URL_PREFIX") + "/" + feed_name
    image_type = "JPEG"
    suffix = ".jpg"

    images = convert_from_path(pdf_file_path)
    print(header_str)
    for num, image in enumerate(images):
        cache_file_path = FileManager.get_cache_file_path(feed_img_dir_path, url_or_file)
        cache_url = FileManager.get_cache_url(img_url_prefix, url_or_file, "")
        image_file = cache_file_path.with_stem(cache_file_path.stem + "_" + str(num))
        image_url = cache_url + "_" + str(num) + suffix
        image.save(image_file, image_type)
        print(f"<img src='{image_url}'/>")

    pdf_file_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
