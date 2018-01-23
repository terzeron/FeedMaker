#!/usr/bin/env python3

import sys


def main():
    header_str = '''<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no"/>
<style>img { max-width: 100%; margin-top: 0px; margin-bottom: 0px; }</style>'''
    print(header_str)
    
    for buf in sys.stdin:
        print(buf, end="")

            
if __name__ == "__main__":
    main()
