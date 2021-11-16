#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import sys
import shutil
import logging.config
from pathlib import Path
from feed_maker_util import Data

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class Uploader:
    @staticmethod
    def upload(rss_file_path: Path) -> int:
        LOGGER.debug(f"# upload(rss_file_path={rss_file_path}")
        dir_path = Path(os.environ["FEED_MAKER_WWW_FEEDS_DIR"])
        old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")

        if rss_file_path.is_file():
            LOGGER.info("new rss file exists")
            if old_rss_file_path.is_file():
                if Data.compare_two_rss_files(rss_file_path, old_rss_file_path):
                    LOGGER.warning("Warning: upload failed! no change from old rss file")
                    return 0
                LOGGER.info("two files are different")
            else:
                LOGGER.info("old rss file doesn't exist")
                shutil.copy(rss_file_path, old_rss_file_path)
        else:
            LOGGER.error("Error: Upload failed! No new RSS file")
            return -1

        shutil.copy(rss_file_path, dir_path)
        LOGGER.info("upload success!")
        shutil.copy(rss_file_path, old_rss_file_path)
        LOGGER.info("replace old rss file with new rss file")
        return 0


def main() -> int:
    return Uploader.upload(Path.cwd() / sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
