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
from typing import Optional, Dict, List, Any
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
DEFAULT_USER_AGENT = "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class HeadlessBrowser:
    def __init__(self, headers, copy_images_from_canvas, simulate_scrolling, disable_headless) -> None:
        self.headers = headers
        self.copy_images_from_canvas = copy_images_from_canvas
        self.simulate_scrolling = simulate_scrolling
        self.disable_headless = disable_headless

    def make_request(self, url, download_file=None) -> str:
        LOGGER.debug("make_request(url=%r, download_file=%r)", url, download_file)
        options = Options()
        if not self.disable_headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=ko_KR")
        options.add_argument("--user-agent=%s" % self.headers['User-Agent'])

        chrome_driver_name = "chromedriver"
        driver = webdriver.Chrome(options=options, executable_path=chrome_driver_name)
        driver.set_script_timeout(60)

        if "Referer" in self.headers:
            driver.get(self.headers["Referer"])
            try:
                WebDriverWait(driver, 60).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
            except selenium.common.exceptions.TimeoutException:
                pass

            cookies = driver.get_cookies()
            with open(COOKIE_FILE, "w") as f:
                json.dump(cookies, f)

        driver.get(url)

        if os.path.isfile(COOKIE_FILE):
            with open(COOKIE_FILE, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    driver.add_cookie(cookie)

        try:
            WebDriverWait(driver, 60).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
        except selenium.common.exceptions.TimeoutException:
            pass

        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})")
        #driver.execute_script("const getParameter = WebGLRenderingContext.getParameter;WebGLRenderingContext.prototype.getParameter = function(parameter) {if (parameter === 37445) {return 'NVIDIA Corporation'} if (parameter === 37446) {return 'NVIDIA GeForce GTX 980 Ti OpenGL Engine';}return getParameter(parameter);};")

        cookies = driver.get_cookies()
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)

        if self.copy_images_from_canvas:
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

        if self.simulate_scrolling:
            driver.execute_script('''
                function sleep(ms) {
                   return new Promise(resolve => setTimeout(resolve, ms));
                }
                var bottom = document.body.scrollHeight;
                for (var i = 0; i < bottom; i += 349) {
                    window.scrollTo(0, i);
                    await sleep(100);
                    bottom = document.body.scrollHeight;
                }
                for (var i = bottom; i >= 0; i -= 683) {
                    window.scrollTo(0, i);
                    await sleep(100);
                }
            ''')

        try:
            content = driver.find_element_by_tag_name("html")
            response = content.get_attribute("innerHTML")
            #response = driver.page_source
        except selenium.common.exceptions.WebDriverException as e:
            LOGGER.error(e)
            response = ""

        driver.close()
        driver.quit()
        return response


class RequestsClient():
    def __init__(self, render_js=False, method=Method.GET, headers={}, timeout=10, encoding=None, verify_ssl=True) -> None:
        LOGGER.debug("RequestsClient(render_js=%r, method=%r, headers=%r, timeout=%d, encoding=%r, verify_ssl=%r)", render_js, method, headers, timeout, encoding, verify_ssl)
        self.method = method
        self.timeout = timeout
        self.headers = headers
        self.encoding = encoding
        self.verify_ssl = verify_ssl

    def make_request(self, url, data=None, download_file=None) -> str:
        LOGGER.debug("make_request('%s')", url)

        if os.path.isfile(COOKIE_FILE):
            cookie_str: str = ""
            with open(COOKIE_FILE, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    cookie_str = cookie_str + cookie["name"] + "=" + cookie["value"] + "; "
            self.headers["Cookie"] = cookie_str
            LOGGER.debug("Cookie: %s", self.headers["Cookie"])

        if self.method == Method.GET:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
        elif self.method == Method.POST:
            response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, data=data)
        elif self.method == Method.HEAD:
            response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            return str(response.status_code)

        if response.status_code != 200:
            LOGGER.debug("response.status_code=%d", response.status_code)
            return ""

        if response.cookies:
            cookie_data: List[Dict[str, Any]] = []
            for k, v in response.cookies.iteritems():
                cookie_data.append({"name": k, "value": v})
            LOGGER.debug("Set-Cookie: %s", cookie_data)
            with open(COOKIE_FILE, "w") as f:
                json.dump(cookie_data, f)

        if download_file:
            response.raw.decode_content = True
            with open(download_file, 'wb') as f:
                for chunk in response:
                    f.write(chunk)
            download_path = os.path.expanduser(download_file)
            os.utime(download_path, (time.time(), time.time()))
            return "200"

        if self.encoding:
            response.encoding = self.encoding
        else:
            response.encoding = 'utf-8'

        return response.text


class Crawler():
    def __init__(self, render_js=False, method=Method.GET, headers={}, timeout=10, num_retries=1, encoding=None, verify_ssl=True, copy_images_from_canvas=True, simulate_scrolling=True, disable_headless=False) -> None:
        LOGGER.debug("Crawler(render_js=%r, method=%r, headers=%r, timeout=%d, num_retries=%d, encoding=%r, verify_ssl=%r, copy_images_from_canvas=%r, simulate_scrolling=%r, disable_headless=%r)", render_js, method, headers, timeout, num_retries, encoding, verify_ssl, copy_images_from_canvas, simulate_scrolling, disable_headless)
        self.render_js = render_js
        self.num_retries = num_retries
        if 'User-Agent' not in headers:
            headers['User-Agent'] = DEFAULT_USER_AGENT
        if render_js:
            # headless browser
            self.headless_browser = HeadlessBrowser(headers=headers, copy_images_from_canvas=copy_images_from_canvas, simulate_scrolling=simulate_scrolling, disable_headless=disable_headless)
        else:
            self.requests_client = RequestsClient(method=method, headers=headers, timeout=timeout, encoding=encoding, verify_ssl=verify_ssl)

    def __del__(self) -> None:
        if self.render_js:
            del self.headless_browser
        else:
            del self.requests_client

    def run(self, url, data=None, download_file=None) -> str:
        response = None
        for i in range(self.num_retries):
            if self.render_js:
                response = self.headless_browser.make_request(url, download_file=download_file)
            else:
                response = self.requests_client.make_request(url, download_file=download_file, data=data)

            if response:
                return response
            LOGGER.debug("wait for seconds and retry (#%d)", i)
            time.sleep(5)

        LOGGER.debug("can't get response from '%s'", url)
        return ""


def print_usage() -> None:
    print("Usage:\t%s [ <option> ... <option> ] <url>" % sys.argv[0])
    print("options")
    print("\t--spider\t\t\tno download, just trying")
    print("\t--render-js=true/false\t\tphantomjs rendering")
    print("\t--verify-ssl=true/false\t\tssl certificate verification")
    print("\t--copy-images-from-canvas=true/false\t\timage in canvas element (in headless browser)")
    print("\t--simulate-scrolling=true/false\t\tsimulate scrolling (in headless browser)")
    print("\t--disable-headless=true/false\t\tshow browser (in headless browser)")
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
    copy_images_from_canvas: bool = False
    simulate_scrolling: bool = False
    disable_headless: bool = False

    if len(sys.argv) == 1:
        print_usage()
        sys.exit(-1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["spider", "render-js=", "verify-ssl=", "copy-images-from-canvas=", "simulate-scrolling=", "disable-headless=", "download=", "encoding=", "user-agent=", "referer=", "header=", "timeout=", "retry="])
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
        elif o == "--copy-images-from-canvas":
            copy_images_from_canvas = (a == "true")
        elif o == "--simulate-scrolling":
            simulate_scrolling = (a == "true")
        elif o == "--disable-headless":
            disable_headless = (a == "true")
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

    crawler = Crawler(render_js=render_js, method=method, headers=headers, timeout=timeout, num_retries=num_retries, encoding=encoding, verify_ssl=verify_ssl, copy_images_from_canvas=copy_images_from_canvas, simulate_scrolling=simulate_scrolling, disable_headless=disable_headless)
    response = crawler.run(url, download_file=download_file)
    print(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
