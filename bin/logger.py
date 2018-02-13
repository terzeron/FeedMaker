#!/usr/bin/env python3
# -*- encoding: utf-8 -*-


import os
import getpass
import logging
import logging.handlers
from smtplib import SMTP
from typing import Any, List, Dict, no_type_check


class Logger:
    def __init__(self, name: str = "feedmaker") -> None:
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        file_logging_level = logging.INFO
        mail_logging_level = logging.WARN

        path_prefix: str = ""
        if os.getenv("FEED_MAKER_CWD"):
            path_prefix = os.getenv("FEED_MAKER_CWD") + "/logs/"
        fh = logging.FileHandler(path_prefix + "feedmaker.log")
        fh.setLevel(file_logging_level)
        kid = getpass.getuser()
        formatter = logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s][" + kid + "] %(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)


    def __del__(self) -> None:
        del self.logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.critical(msg, *args, **kwargs)

