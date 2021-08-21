#!/usr/bin/env python

import logging
import sys
import os

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/terzeron/public_html/fmw/')
sys.path.insert(1, '/home/terzeron/.pyenv/versions/fm/lib/python3.9/site-packages')
sys.path.insert(1, '/home/terzeron/workspace/fm/bin')

os.environ["FEED_MAKER_HOME_DIR"] = "/home/terzeron/workspace/fm"
os.environ["FEED_MAKER_WORK_DIR"] = "/home/terzeron/workspace/fma"
os.environ["FEED_MAKER_WWW_FEEDS_DIR"] = "/home/terzeron/public_html/xml"
os.environ["LC_ALL"] = "ko_KR.utf8"
os.environ["LANG"] = "ko_KR.utf8"

os.chdir("/home/terzeron/public_html/fmw")

from app import app as application

