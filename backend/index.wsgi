#!/usr/bin/env python

import logging
import sys
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/terzeron/public_html/fmw/backend/')
sys.path.insert(1, '/home/terzeron/.pyenv/versions/flask/lib/python3.9/site-packages')

from index import app as application

