#!/usr/bin/env python

import logging
import sys
import os

logging.basicConfig(stream=sys.stderr)
sys.path.append('/home/terzeron/.pyenv/versions/fmw/lib/python3.9/site-packages')
sys.path.append('/home/terzeron/public_html/fmw/backend')
sys.path.append('/home/terzeron/.pyenv/versions/fm/lib/python3.9/site-packages')
sys.path.append('/home/terzeron/workspace/fm/bin')

fm_home_dir = "/home/terzeron/workspace/fm"
fm_work_dir = "/home/terzeron/workspace/fma"
fm_www_feeds_dir = "/home/terzeron/public_html/xml"
cartoon_split_home_dir = "/home/terzeron/workspace/CartoonSplit"
pyenv_dir = "/home/terzeron/.pyenv/plugins/pyenv-virtualenv/shims:/home/terzeron/.pyenv/shims:/home/terzeron/.pyenv/bin"
chromedriver_dir = "/home/terzeron/bin"
if "/usr/bin" not in os.environ["PATH"]:
    os.envrion["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin"

os.environ["FEED_MAKER_HOME_DIR"] = fm_home_dir
os.environ["FEED_MAKER_WORK_DIR"] = fm_work_dir
os.environ["FEED_MAKER_WWW_FEEDS_DIR"] = fm_www_feeds_dir
os.environ["LC_ALL"] = "ko_KR.utf8"
os.environ["LANG"] = "ko_KR.utf8"
os.environ["PATH"] = ":".join([fm_home_dir + "/bin", cartoon_split_home_dir, pyenv_dir, chromedriver_dir, os.environ["PATH"]])
os.environ["PYTHONPATH"] = fm_home_dir + "/bin"

os.chdir("/home/terzeron/public_html/fmw/backend")

from app import app as application

