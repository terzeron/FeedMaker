#!/usr/bin/env python


import sys
import os
import re
from enum import Enum
import time
import getopt
import requests
import logging
import logging.config
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import selenium
from typing import Dict, Optional, Union, Any


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
logger = logging.getLogger()


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class HeadlessBrowser:
    def __init__(self, sleep_time=None):
        self.sleep_time = sleep_time
        
    def make_request(self, url) -> Optional[str]:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        chrome_driver = "chromedriver"
        driver = webdriver.Chrome(options=options, executable_path=chrome_driver)

        driver.get(url)
        if self.sleep_time:
            # necessary to circumvent javascript challenge of cloudflare
            time.sleep(self.sleep_time)
            
        try:
            #content = driver.find_element_by_tag_name("body")
            #response = content.get_attribute("innerHTML")
            response = driver.page_source
        except selenium.common.exceptions.WebDriverException as e:
            logger.error(e)
            sys.exit(-1)

        driver.close() 
        driver.quit()
        return response
    

class Crawler():
    def __init__(self, method, headers, timeout, num_retries=1, sleep_time=None, do_render_js=False, download_file=None, encoding=None) -> None:
        self.method = method
        self.timeout = timeout
        self.num_retries = num_retries
        self.sleep_time = sleep_time
        self.do_render_js = do_render_js
        self.headers = headers
        self.download_file = download_file
        self.encoding = encoding

    def make_request(self, url) -> Any:
        if self.do_render_js:
            browser = HeadlessBrowser(self.sleep_time)
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
                    if self.encoding:
                        response.encoding = self.encoding
                    else:
                        response.encoding = 'utf-8'
                    return response.text
            #print(response.status_code)
        return None
            
    def run(self, url) -> int:
        response = None
        for i in range(self.num_retries):
            response = self.make_request(url)
            if response:
                break
            else:
                logger.debug("wait for seconds and retry")
                time.sleep(10)
        if not response:
            logger.warning("can't get response from '%s'" % url)
            sys.exit(-1)
           
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


def print_usage() -> None:
    print("Usage:\t%s [ <option> ... <option> ] <url>" % sys.argv[0])
    print("options")
    print("\t--spider\t\t\tno download, just trying")
    print("\t--render-js\t\t\tphantomjs rendering")
    print("\t--download <file>\t\tdownload as a file, instead of stdout")
    print("\t--header <header string>\tspecify header string")
    print("\t--encoding <encoding>\t\tspecify encoding of content")
    print("\t--ua <user agent string>")
    print("\t--referer <referer>")
    print("\t--retry <# of retries>")
    print("\t--sleep <seconds>")

    
def main() -> int:
    method = Method.GET
    headers = {"Accept-Encoding": "gzip, deflate", "User-Agent": "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36", "Accept": "*/*", "Connection": "Keep-Alive"}
    timeout = 10
    num_retries = 1
    sleep_time = None
    do_render_js = False
    download_file: Optional[str] = None
    encoding: Optional[str] = None
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["spider", "render-js", "download=", "encoding=", "ua=", "referer=", "header=", "timeout=", "retry=", "sleep="])
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
        elif o == "--retry":
            num_retries = int(a)
        elif o == "--sleep":
            sleep_time = int(a)
        elif o == "--download":
            download_file = a
        elif o == "--encoding":
            encoding = a

    url = args[0]
    
    crawler = Crawler(method, headers, timeout, num_retries, sleep_time, do_render_js, download_file, encoding)
    return crawler.run(url)

    
if __name__ == "__main__":
    sys.exit(main())

