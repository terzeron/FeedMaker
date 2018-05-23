#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import logging
import logging.handlers
import os
import sys
from typing import Any


class Logger:
    def __init__(self, name: str = "feedmaker") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        total_log_file_logging_level = logging.INFO
        feed_file_logging_level = logging.DEBUG
        stream_logging_level = logging.INFO

        path_prefix: str = ""
        if os.getenv("FEED_MAKER_WORK_DIR"):
            path_prefix = os.getenv("FEED_MAKER_WORK_DIR") + "/logs/"

        tfh = logging.handlers.TimedRotatingFileHandler(path_prefix + "feedmaker.log", when="D", interval=1, backupCount=2)
        tfh.setLevel(total_log_file_logging_level)
        tfh_formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d] %(message)s")
        tfh.setFormatter(tfh_formatter)
        self.logger.addHandler(tfh)

        ffh = logging.handlers.TimedRotatingFileHandler("run.log", when="D", interval=1, backupCount=2)
        ffh.setLevel(feed_file_logging_level)
        ffh_formatter = logging.Formatter("[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d] %(message)s")
        ffh.setFormatter(ffh_formatter)
        self.logger.addHandler(ffh)

        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(stream_logging_level)
        sh_formatter = logging.Formatter("%(message)s")
        sh.setFormatter(sh_formatter)
        self.logger.addHandler(sh)

    def __del__(self) -> None:
        del self.logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warn(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def err(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.error(msg, *args, **kwargs)

    def crit(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.critical(msg, *args, **kwargs)

