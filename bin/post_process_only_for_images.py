#!/usr/bin/env python


import os
import sys
import re


def main():
	for line in sys.stdin:
		if re.search(r'<meta|style', line):
			print line,
		match = re.search(r'(?P<img_tag><img src=[\'"]?http://[^\'"]+[\'"]?[^>]*>)', line)
		if match:
			print match.group('img_tag')

					
if __name__ == "__main__":
	main()
