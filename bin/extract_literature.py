#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import sys
from bs4 import BeautifulSoup
from feedmakerutil import IO


def read_file(file):
    fp = open(file)
    html = ""
    for line in fp:
        html += line
    fp.close()
    return html


def traverse_element(element):
    prev_href = None
    for a in element.findAll('a'):
        img = a.find('img')
        if prev_href != a['href']:
            print("%s\t%s" % (a['href'].encode("utf-8"), img['alt'].encode("utf-8")), end='')
        else:
            print("- %s" % img['alt'].encode("utf-8"))

        prev_href = a['href']


def main():
    html = IO.read_stdin()
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.find(attrs={"id": "navercast_div"})
    if text:
        print(text)


if __name__ == "__main__":
    sys.exit(main())
