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
    def __init__(self, headers, sleep_time=None):
        self.headers = headers
        self.sleep_time = sleep_time
        
    def make_request(self, url) -> Optional[str]:
        logger.debug("HeadlessBrowser.make_request('%s')" % url)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=ko_KR")
        options.add_argument("--user-agent=%s" % self.headers['User-Agent'])
        
        chrome_driver = "chromedriver"
        driver = webdriver.Chrome(options=options, executable_path=chrome_driver)

        driver.get(url)
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})")
        #driver.execute_script("const getParameter = WebGLRenderingContext.getParameter;WebGLRenderingContext.prototype.getParameter = function(parameter) {if (parameter === 37445) {return 'NVIDIA Corporation'} if (parameter === 37446) {return 'NVIDIA GeForce GTX 980 Ti OpenGL Engine';}return getParameter(parameter);};")
        if self.sleep_time:
            # necessary to circumvent javascript challenge of cloudflare
            time.sleep(self.sleep_time)

        driver.execute_script('''
        div = document.createElement("DIV");
        div.className = "images_from_canvas";
        var canvas_list = document.getElementsByTagName("canvas"); 
        for (var i = 0; i < canvas_list.length; i++) {
            img_data = canvas_list[i].toDataURL("image/png");
            img = document.createElement("IMG");
            img.src = img_data;
            div.appendChild(img);
        }
        document.body.appendChild(div);
        ''')
            
        try:
            content = driver.find_element_by_tag_name("html")
            response = content.get_attribute("innerHTML")
            #response = driver.page_source
        except selenium.common.exceptions.WebDriverException as e:
            logger.error(e)
            sys.exit(-1)

        driver.close() 
        driver.quit()
        return response
    

class Crawler():
    def __init__(self, method, headers, timeout, num_retries=1, sleep_time=None, render_js=False, download_file=None, encoding=None, verify_ssl=True) -> None:
        self.method = method
        self.timeout = timeout
        self.num_retries = num_retries
        self.sleep_time = sleep_time
        self.render_js = render_js
        self.headers = headers
        self.download_file = download_file
        self.encoding = encoding
        self.verify_ssl = verify_ssl

    def make_request(self, url) -> Any:
        logger.debug("Crawler.make_request('%s')" % url)
        if self.render_js:
            logger.debug("headless browser")
            browser = HeadlessBrowser(self.headers, self.sleep_time)
            return browser.make_request(url) 
        else:
            logger.debug("requests client")
            if self.method == Method.GET:
                response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            elif self.method == Method.HEAD:
                response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            elif self.method == Method.POST:
                response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
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
            else:
                logger.debug("response.status_code=%d" % response.status_code)

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
    print("\t--render-js\t\t\ttrue or false, phantomjs rendering")
    print("\t--verify-ssl\t\t\ttrue or false, ssl certificate verification")
    print("\t--download=<file>\t\tdownload as a file, instead of stdout")
    print("\t--header=<header string>\tspecify header string")
    print("\t--encoding=<encoding>\t\tspecify encoding of content")
    print("\t--user-agent=<user agent string>")
    print("\t--referer=<referer>")
    print("\t--retry=<# of retries>")
    print("\t--sleep-time=<seconds>")

    
def main() -> int:
    method = Method.GET
    headers = {"Accept-Encoding": "gzip, deflate", "User-Agent": "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36", "Accept": "*/*", "Connection": "Keep-Alive"}
    timeout = 10
    num_retries = 1
    sleep_time = None
    render_js = False
    download_file: Optional[str] = None
    encoding: Optional[str] = None
    verify_ssl: bool = True

    if len(sys.argv) == 1:
        print_usage()
        sys.exit(-1)
        
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["spider", "render-js=", "verify-ssl=", "download=", "encoding=", "user-agent=", "referer=", "header=", "timeout=", "retry=", "sleep-time="])
    except getopt.GetoptError as err:
        print_usage()
        sys.exit(-1)

    for o, a in opts:
        if o == "-h":
            print_usage()
            sys.exit(0)
        elif o == "--spider":
            method = Method.HEAD
        elif o == "--user-agent":
            headers["User-Agent"] = a
        elif o == "--referer":
            headers["Referer"] = a
        elif o == "--render-js":
            render_js = (a == "true")
        elif o == "--verify-ssl":
            verify_ssl = (a == "true")
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
        elif o == "--sleep-time":
            sleep_time = int(a)
        elif o == "--download":
            download_file = a
        elif o == "--encoding":
            encoding = a

    url = args[0]
    
    crawler = Crawler(method, headers, timeout, num_retries, sleep_time, render_js, download_file, encoding, verify_ssl)
    return crawler.run(url)

    
if __name__ == "__main__":
    sys.exit(main())

