#!/usr/bin/env python


import sys
import re
import pdftotext


def main() -> int:
    pdf_file = sys.argv[1]
    with open(pdf_file, "rb") as f:
        pdf = pdftotext.PDF(f)
        for page in pdf:
            page = re.sub(r'^\s+', ' ', page)
            page = re.sub(r'\s{4,}', '  ', page)
            page = re.sub(r'^\s*\S+\s* - ', '\n - ', page)
            page = re.sub(r'(?<=\S)\s*(?P<bullet>[▶•])', '\n\g<bullet>', page)
            print(page)

    return 0


if __name__ == "__main__":
    sys.exit(main())
