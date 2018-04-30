#!/usr/bin/env python


import sys
import os
import re
from enum import Enum
import time
import getopt
import requests
from feedmakerutil import die
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium
from typing import Dict, Optional
from logger import Logger


logger = Logger("crawler.py")


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class HeadlessBrowser:
    def make_request(self, url):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920x1080")
        chrome_driver = "chromedriver"
        driver = webdriver.Chrome(chrome_options=chrome_options, executable_path=chrome_driver)

        driver.get(url)
        try:
            content = driver.find_element_by_tag_name("body")
            response = content.get_attribute("innerHTML")
        except selenium.common.exceptions.WebDriverException as e:
            die(e)

        driver.close()
        driver.quit()
        return response
    

class Crawler():
    def __init__(self, method, headers, timeout, do_render_js=False, download_file=None, encoding=None):
        self.method = method
        self.timeout = timeout
        self.do_render_js = do_render_js
        self.headers = headers
        self.headers.update({"Accept-Encoding": "gzip, deflate"})
        self.download_file = download_file
        self.encoding = encoding

    def make_request(self, url) -> Optional[str]:
        if self.do_render_js:
            browser = HeadlessBrowser()
            return browser.make_request(url) 
        else:
            #print(url, self.method, self.headers)
            if self.method == Method.GET:
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
            elif self.method == Method.HEAD:
                response = requests.head(url, headers=self.headers, timeout=self.timeout)
            elif self.method == Method.POST:
                response = requests.post(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                if self.download_file:
                    response.raw.decode_content = True
                    return response
                else:
                    if self.encoding and self.encoding != "utf-8":
                        response.encoding = self.encoding
                    return response.text
            #print(response.status_code)
        return None
            
    def run(self, url) -> int:
        response = self.make_request(url)
        if not response:
            die("can't get response from '%s'" % url)
    
        if self.method == Method.HEAD:
            pass
        elif self.download_file:
            with open(self.download_file, 'wb') as f:
                for chunk in response:
                    f.write(chunk)
    
        # post processing
    
        if self.download_file:
            self.download_path = os.path.expanduser(self.download_file)
            os.utime(self.download_path, (time.time(), time.time()))
        else:
            print(response)

        return 0


def print_usage():
    print("Usage:\t%s [ <option> ... <option> ] <url>" % sys.argv[0])
    print("options")
    print("\t--spider\t\t\tno download, just trying")
    print("\t--render-js\t\t\tphantomjs rendering")
    print("\t--download <file>\t\tdownload as a file, instead of stdout")
    print("\t--header <header string>\tspecify header string")
    print("\t--encoding <encoding>\t\tspecify encoding of content")
    print("\t--ua <user agent string>")
    print("\t--referer <referer>")

    
def main():
    method = Method.GET
    headers: Dict[str, str] = {}
    timeout = 10
    do_render_js = False
    download_file: Optional[str] = None
    encoding: Optional[str] = None
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["spider", "render-js", "download=", "encoding=", "ua=", "referer=", "header=", "timeout="])
    except getopt.GetoptError as err:
        print_usage()
        sys.exit(-1)

    for o, a in opts:
        if o == "-h":
            print_usage()
            sys.exit(0)
        elif o == "--spider":
            method = Method.HEAD
        elif o == "--ua":
            headers["User-Agent"] = a
        elif o == "--referer":
            headers["Referer"] = a
        elif o == "--render-js":
            do_render_js = True
        elif o == "--header":
            m = re.search(r'^(?P<key>[^:]+)\s*:\s*(?P<value>.+)\s*$', a)
            if m:
                key = m.group("key")
                value = m.group("value")
                headers[key] = value
        elif o == "--timeout":
            timeout = int(a)
        elif o == "--download":
            download_file = a
        elif o == "--encoding":
            encoding = a

    url = args[0]
    
    crawler = Crawler(method, headers, timeout, do_render_js, download_file, encoding)
    crawler.run(url)

    
if __name__ == "__main__":
    sys.exit(main())

