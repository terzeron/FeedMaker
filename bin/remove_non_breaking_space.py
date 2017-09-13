#!/usr/bin/env python


import sys
import re


for line in sys.stdin:
    line = line.replace(u"\u00A0", " ")
    print(line, end='')
