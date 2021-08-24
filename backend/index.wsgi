#!/usr/bin/env python

import logging
import sys
import os

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/terzeron/public_html/fmw/backend')
sys.path.insert(1, '/home/terzeron/.pyenv/versions/fm/lib/python3.9/site-packages')
sys.path.insert(1, '/home/terzeron/workspace/fm/bin')

home_dir = "/home/terzeron/workspace/fm"
work_dir = "/home/terzeron/workspace/fma"
www_feeds_dir = "/home/terzeron/public_html/xml"
cartoon_split_home_dir = "/home/terzeron/workspace/CartoonSplit"
pyenv_dir = "/home/terzeron/.pyenv/plugins/pyenv-virtualenv/shims:/home/terzeron/.pyenv/shims:/home/terzeron/.pyenv/bin"

os.environ["FEED_MAKER_HOME_DIR"] = home_dir
os.environ["FEED_MAKER_WORK_DIR"] = work_dir
os.environ["FEED_MAKER_WWW_FEEDS_DIR"] = www_feeds_dir
os.environ["LC_ALL"] = "ko_KR.utf8"
os.environ["LANG"] = "ko_KR.utf8"
os.environ["PATH"] = home_dir + "/bin:" + cartoon_split_home_dir + ":" + pyenv_dir + ":" + os.environ["PATH"]
os.environ["PYTHONPATH"] = home_dir + "/bin"

os.chdir("/home/terzeron/public_html/fmw/backend")

from app import app as application

