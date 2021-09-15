#!/usr/bin/env python


import sys

for line in sys.stdin:
    line = line.replace(u"\u00A0", " ")
    print(line, end='')
