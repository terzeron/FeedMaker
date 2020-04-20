#!/usr/bin/env python


import sys
import os
import re
from enum import Enum
import time
import getopt
import json
import logging
import logging.config
from typing import Optional
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import selenium


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
COOKIE_FILE = "cookies.json"


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class HeadlessBrowser:
    def __init__(self, headers) -> None:
        self.headers = headers

    def make_request(self, url) -> str:
        LOGGER.debug("HeadlessBrowser.make_request('%s')", url)
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=ko_KR")
        options.add_argument("--user-agent=%s" % self.headers['User-Agent'])

        chrome_driver_name = "chromedriver"
        driver = webdriver.Chrome(options=options, executable_path=chrome_driver_name)

        driver.get(url)

        if os.path.isfile(COOKIE_FILE):
            with open(COOKIE_FILE, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    driver.add_cookie(cookie)

        try:
            WebDriverWait(driver, 10).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
        except selenium.common.exceptions.TimeoutException:
            pass

        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})")
        #driver.execute_script("const getParameter = WebGLRenderingContext.getParameter;WebGLRenderingContext.prototype.getParameter = function(parameter) {if (parameter === 37445) {return 'NVIDIA Corporation'} if (parameter === 37446) {return 'NVIDIA GeForce GTX 980 Ti OpenGL Engine';}return getParameter(parameter);};")

        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)

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
            LOGGER.error(e)
            return ""

        driver.close()
        driver.quit()
        return response


class Crawler():
    def __init__(self, method=Method.GET, headers={}, timeout=10, num_retries=1, render_js=False, download_file=None, encoding=None, verify_ssl=True) -> None:
        self.method = method
        self.timeout = timeout
        self.num_retries = num_retries
        self.render_js = render_js
        self.headers = headers
        self.download_file = download_file
        self.encoding = encoding
        self.verify_ssl = verify_ssl

    def make_request(self, url, data=None) -> str:
        LOGGER.debug("Crawler.make_request('%s')", url)
        if self.render_js:
            LOGGER.debug("headless browser")
            self.headers['User-Agent'] = "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"
            browser = HeadlessBrowser(self.headers)
            return browser.make_request(url)

        LOGGER.debug("requests client")
        if self.method == Method.GET:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
        elif self.method == Method.POST:
            response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, data)
        elif self.method == Method.HEAD:
            response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            return str(response.status_code)

        if response.status_code != 200:
            LOGGER.debug("response.status_code=%d", response.status_code)
            return ""

        if self.download_file:
            response.raw.decode_content = True
            with open(self.download_file, 'wb') as f:
                for chunk in response:
                    f.write(chunk)
            download_path = os.path.expanduser(self.download_file)
            os.utime(download_path, (time.time(), time.time()))
            return "200"

        if self.encoding:
            response.encoding = self.encoding
        else:
            response.encoding = 'utf-8'

        return response.text


    def run(self, url, data=None) -> str:
        response = None
        for i in range(self.num_retries):
            response = self.make_request(url, data)
            if response:
                break
            LOGGER.debug("wait for seconds and retry (#%d)", i)
            time.sleep(5)
        if not response:
            LOGGER.debug("can't get response from '%s'", url)
            return ""

        return response


def print_usage() -> None:
    print("Usage:\t%s [ <option> ... <option> ] <url>" % sys.argv[0])
    print("options")
    print("\t--spider\t\t\tno download, just trying")
    print("\t--render-js=true/false\t\tphantomjs rendering")
    print("\t--verify-ssl=true/false\t\tssl certificate verification")
    print("\t--download=<file>\t\tdownload as a file, instead of stdout")
    print("\t--header=<header string>\tspecify header string")
    print("\t--encoding=<encoding>\t\tspecify encoding of content")
    print("\t--user-agent=<user agent string>")
    print("\t--referer=<referer>")
    print("\t--retry=<# of retries>")


def main() -> int:
    method = Method.GET
    headers = {"Accept-Encoding": "gzip, deflate", "User-Agent": "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36", "Accept": "*/*", "Connection": "Keep-Alive"}
    timeout = 10
    num_retries = 1
    render_js = False
    download_file: Optional[str] = None
    encoding: Optional[str] = None
    verify_ssl: bool = True

    if len(sys.argv) == 1:
        print_usage()
        sys.exit(-1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["spider", "render-js=", "verify-ssl=", "download=", "encoding=", "user-agent=", "referer=", "header=", "timeout=", "retry="])
    except getopt.GetoptError:
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
        elif o == "--download":
            download_file = a
        elif o == "--encoding":
            encoding = a

    url = args[0]

    crawler = Crawler(method, headers, timeout, num_retries, render_js, download_file, encoding, verify_ssl)
    response = crawler.run(url)
    print(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
