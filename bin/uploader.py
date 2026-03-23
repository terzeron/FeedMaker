#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import shutil
import logging.config
from pathlib import Path
from bin.feed_maker_util import Data, PathUtil, Env


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


class Uploader:
    @staticmethod
    def upload(rss_file_path: Path) -> int:
        LOGGER.debug("# upload(rss_file_path='%s'", PathUtil.short_path(rss_file_path))
        public_feed_dir_path = Path(Env.get("WEB_SERVICE_FEED_DIR_PREFIX"))
        old_rss_file_path = rss_file_path.with_suffix(rss_file_path.suffix + ".old")

        if not rss_file_path.is_file():
            LOGGER.error("Error: Upload failed! No new RSS file")
            return -1

        LOGGER.info("new rss file exists")
        public_feed_file_path = public_feed_dir_path / rss_file_path.name

        if old_rss_file_path.is_file():
            if Data.compare_two_rss_files(rss_file_path, old_rss_file_path) and public_feed_file_path.is_file():
                LOGGER.warning("Warning: upload skipped, no change from old rss file")
                return 0
            LOGGER.info("uploading: files are different or public feed file is missing")
        else:
            LOGGER.info("old rss file doesn't exist")
            shutil.copy(rss_file_path, old_rss_file_path)

        shutil.copy(rss_file_path, public_feed_dir_path)
        LOGGER.info("upload success!")
        shutil.copy(rss_file_path, old_rss_file_path)
        LOGGER.info("replace old rss file with new rss file")
        return 0


def main() -> int:
    return Uploader.upload(Path.cwd() / sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
