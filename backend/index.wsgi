#!/usr/bin/env python

import logging
import sys
import os

logging.basicConfig(stream=sys.stderr)

home_dir = "/home/terzeron"
fm_home_dir = home_dir + "/workspace/fm"
fm_work_dir = home_dir + "/workspace/fma"
fm_www_feeds_dir = home_dir + "/public_html/xml"
cartoon_split_home_dir = home_dir + "/workspace/CartoonSplit"
chromedriver_dir = home_dir + "/bin"
pyenv_dir = home_dir + "/.pyenv/plugins/pyenv-virtualenv/shims:/home/terzeron/.pyenv/shims:/home/terzeron/.pyenv/bin"

sys.path.append(home_dir + "/.pyenv/versions/fm/lib/python3.9/site-packages")
sys.path.append(fm_home_dir + "/backend")
sys.path.append(fm_home_dir + "/bin")
sys.path.append(fm_home_dir + "/utils")

os.environ["HOME"] = home_dir
os.environ["FEED_MAKER_HOME_DIR"] = fm_home_dir
os.environ["FEED_MAKER_WORK_DIR"] = fm_work_dir
os.environ["FEED_MAKER_WWW_FEEDS_DIR"] = fm_www_feeds_dir
os.environ["LC_ALL"] = "ko_KR.utf8"
os.environ["LANG"] = "ko_KR.utf8"
if "/usr/bin" not in os.environ["PATH"]:
    os.environ["PATH"] = "/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin"
os.environ["PATH"] = ":".join([fm_home_dir + "/bin", fm_home_dir + "/utils", cartoon_split_home_dir, pyenv_dir, chromedriver_dir, os.environ["PATH"]])
os.environ["PYTHONPATH"] = fm_home_dir + "/bin"

from app import app as application
