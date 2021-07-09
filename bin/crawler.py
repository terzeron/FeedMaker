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
from typing import Dict, List, Any, Tuple, Optional
from requests.structures import CaseInsensitiveDict
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import selenium


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
COOKIE_FILE_FOR_HEADLESS_BROWSER = "cookies.headlessbrowser.json"
COOKIE_FILE_FOR_REQUESTS_CLIENT = "cookies.requestsclient.json"
DEFAULT_USER_AGENT = "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class HeadlessBrowser:
    GETTING_METADATA_SCRIPT = '''
        var metas = document.getElementsByTagName("meta");
        var has_og_url_property = false;
        for (var i = 0; i < metas.length; i++) {
            var meta = metas[i];
            if (meta.getAttribute("property") == "og:url") {
                has_og_url_property = true;
            }
        }
        if (!has_og_url_property) {
            console.log("no og url prop");
            var new_meta = document.createElement("meta");
            new_meta.setAttribute("property", "og:url");
            new_meta.setAttribute("content", window.location.href);
            document.head.appendChild(new_meta);
        }'''
    CONVERTING_CANVAS_TO_IMAGES_SCRIPT = '''
        div = document.createElement("DIV");
        div.className = "images_from_canvas";
        var canvas_list = document.getElementsByTagName("canvas");
        for (var i = 0; i < canvas_list.length; i++) {
            img_data = canvas_list[i].toDataURL("image/png");
            img = document.createElement("IMG");
            img.src = img_data;
            div.appendChild(img);
        }
        document.body.appendChild(div);'''
    SIMULATING_SCROLLING_SCRIPT = '''
        function sleep(ms) {
           return new Promise(resolve => setTimeout(resolve, ms));
        }
        await sleep(1000);
        var bottom = document.body.scrollHeight;
        for (var i = 0; i < bottom; i += 349) {
            window.scrollTo(0, i);
            await sleep(200);
            bottom = document.body.scrollHeight;
        }
        for (var i = bottom; i >= 0; i -= 683) {
            window.scrollTo(0, i);
            await sleep(400);
        }'''
    SETTING_PLUGINS_SCRIPT = "Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});"
    SETTING_LANGUAGES_SCRIPT = "Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})"
    SETTING_WEBGL_SCRIPT = "const getParameter = WebGLRenderingContext.getParameter;WebGLRenderingContext.prototype.getParameter = function(parameter) { if (parameter === 37445) { return 'NVIDIA Corporation' } if (parameter === 37446) { return 'NVIDIA GeForce GTX 980 Ti OpenGL Engine';}return getParameter(parameter); };"

    def __init__(self, headers, copy_images_from_canvas, simulate_scrolling, disable_headless) -> None:
        LOGGER.debug("# HeadlessBrowser(headers=%r, copy_images_from_canvas=%r, simulate_scrolling=%r, disable_headless=%r)", headers, copy_images_from_canvas, simulate_scrolling, disable_headless)
        self.headers = headers
        self.copy_images_from_canvas = copy_images_from_canvas
        self.simulate_scrolling = simulate_scrolling
        self.disable_headless = disable_headless

    def write_cookies_to_file(self, driver, cookie_file):
        cookies = driver.get_cookies()
        with open(cookie_file, "w") as f:
            json.dump(cookies, f)

    def read_cookies_from_file(self, driver, cookie_file):
        if os.path.isfile(cookie_file):
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    driver.add_cookie(cookie)

    def make_request(self, url, download_file=None) -> str:
        LOGGER.debug("# make_request(url=%r, download_file=%r)", url, download_file)
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
        driver.set_script_timeout(240)

        if "Referer" in self.headers:
            driver.get(self.headers["Referer"])
            try:
                WebDriverWait(driver, 60).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
            except selenium.common.exceptions.TimeoutException:
                pass
            self.write_cookies_to_file(driver, COOKIE_FILE_FOR_HEADLESS_BROWSER)

        driver.get(url)
        try:
            self.read_cookies_from_file(driver, COOKIE_FILE_FOR_HEADLESS_BROWSER)
        except selenium.common.exceptions.InvalidCookieDomainException:
            os.remove(COOKIE_FILE_FOR_HEADLESS_BROWSER)
            self.read_cookies_from_file(driver, COOKIE_FILE_FOR_HEADLESS_BROWSER)

        # bypass cloudflare test
        try:
            WebDriverWait(driver, 60).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
        except selenium.common.exceptions.TimeoutException:
            pass

        # pretend to be a real browser
        driver.execute_script(HeadlessBrowser.SETTING_PLUGINS_SCRIPT)
        driver.execute_script(HeadlessBrowser.SETTING_LANGUAGES_SCRIPT)
        #driver.execute_script(HeadlessBrowser.SETTING_WEBGL_SCRIPT)
        
        self.write_cookies_to_file(driver, COOKIE_FILE_FOR_HEADLESS_BROWSER)

        driver.execute_script(HeadlessBrowser.GETTING_METADATA_SCRIPT)

        if self.copy_images_from_canvas:
            driver.execute_script(HeadlessBrowser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT)

        if self.simulate_scrolling:
            driver.execute_script(HeadlessBrowser.SIMULATING_SCROLLING_SCRIPT)

        try:
            content = driver.find_element_by_tag_name("html")
            response = content.get_attribute("innerHTML")
        except selenium.common.exceptions.WebDriverException as e:
            LOGGER.error(e)
            response = ""

        driver.close()
        driver.quit()
        return response


class RequestsClient():
    def __init__(self, render_js=False, method=Method.GET, headers={}, timeout=60, encoding=None, verify_ssl=True) -> None:
        LOGGER.debug("# RequestsClient(render_js=%r, method=%r, headers=%r, timeout=%d, encoding=%r, verify_ssl=%r)", render_js, method, headers, timeout, encoding, verify_ssl)
        self.method = method
        self.timeout = timeout
        self.headers = headers
        self.encoding = encoding
        self.verify_ssl = verify_ssl

    def write_cookies_to_file(self, cookies, cookie_file):
        cookie_data: List[Dict[str, Any]] = []
        for k, v in cookies.iteritems():
            cookie_data.append({"name": k, "value": v})
        LOGGER.debug("Set-Cookie: %s", cookie_data)
        with open(cookie_file, "w") as f:
            json.dump(cookie_data, f)

    def read_cookies_from_file(self, cookie_file):
        if os.path.isfile(cookie_file):
            cookie_str: str = ""
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    cookie_str = cookie_str + cookie["name"] + "=" + cookie["value"] + "; "
            self.headers["Cookie"] = cookie_str
            LOGGER.debug("Cookie: %s", self.headers["Cookie"])

    def make_request(self, url, data=None, download_file=None) -> Tuple[str, Optional[CaseInsensitiveDict[str]], int]:
        LOGGER.debug("# make_request('%s')", url)

        self.read_cookies_from_file(COOKIE_FILE_FOR_REQUESTS_CLIENT)

        if self.method == Method.GET:
            response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
        elif self.method == Method.POST:
            response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, data=data)
        elif self.method == Method.HEAD:
            response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
            return str(response.status_code), response.headers, response.status_code

        if response.status_code != 200:
            LOGGER.debug("response.status_code=%d", response.status_code)
            return "", None, response.status_code

        if response.cookies:
            self.write_cookies_to_file(response.cookies, COOKIE_FILE_FOR_REQUESTS_CLIENT)
                
        if download_file:
            response.raw.decode_content = True
            with open(download_file, 'wb') as f:
                for chunk in response:
                    f.write(chunk)
            download_path = os.path.expanduser(download_file)
            os.utime(download_path, (time.time(), time.time()))
            return "200", None, response.status_code

        if self.encoding:
            response.encoding = self.encoding
        else:
            response.encoding = 'utf-8'

        if not re.search(r'<meta\s+property="og:url"\s+content="[^"]+"\s*/?>', response.text):
            result = re.sub(r'</head>', '<meta property="og:url" content="%s"/>\n</head>' % response.request.url, response.text)
            return result, response.headers, response.status_code
        return response.text, response.headers, response.status_code


class Crawler():
    class ReadTimeoutException(Exception):
        def __init__(self):
            super().__init__("Read timed out")

    def __init__(self, render_js=False, method=Method.GET, headers={}, timeout=60, num_retries=1, encoding=None, verify_ssl=True, copy_images_from_canvas=False, simulate_scrolling=False, disable_headless=False) -> None:
        LOGGER.debug("# Crawler(render_js=%r, method=%r, headers=%r, timeout=%d, num_retries=%d, encoding=%r, verify_ssl=%r, copy_images_from_canvas=%r, simulate_scrolling=%r, disable_headless=%r)", render_js, method, headers, timeout, num_retries, encoding, verify_ssl, copy_images_from_canvas, simulate_scrolling, disable_headless)
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

    def run(self, url, data=None, download_file=None) -> Tuple[str, Any]:
        LOGGER.debug("# run(url=%s, data=%r, download_file=%r)", url, data, download_file)
        response = None
        headers = None
        for i in range(self.num_retries):
            if self.render_js:
                response = self.headless_browser.make_request(url, download_file=download_file)
            else:
                try:
                    response, headers, status_code = self.requests_client.make_request(url, download_file=download_file, data=data)
                except requests.exceptions.ReadTimeout as e:
                    raise Crawler.ReadTimeoutException from e

            if response:
                return response, headers if headers else None
            if status_code in [401, 403, 404, 405, 410]:
                # no retry in case of
                #   401 Unauthorized
                #   403 Forbidden
                #   404 Not Found
                #   405 Method Not Allowed
                #   410 Gone
                break
            LOGGER.debug("wait for seconds and retry (#%d)", i)
            time.sleep(5)

        LOGGER.debug("can't get response from '%s'", url)
        return "", None


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
    LOGGER.debug("# main()")
    method = Method.GET
    headers = {"Accept-Encoding": "gzip, deflate", "User-Agent": "Mozillla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36", "Accept": "*/*", "Connection": "Keep-Alive"}
    timeout = 60
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
    response, _ = crawler.run(url, download_file=download_file)
    print(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
