#!/usr/bin/env python


import sys
import os
import re
import time
import getopt
import json
import logging.config
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import requests
from headless_browser import HeadlessBrowser

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class RequestsClient:
    COOKIE_FILE = "cookies.requestsclient.json"

    def __init__(self, dir_path: Path=Path.cwd(), render_js: bool=False, method: Method=Method.GET, headers: Dict[str, Any]=None, timeout: int=60, encoding: str="utf-8", verify_ssl: bool=True) -> None:
        LOGGER.debug(
            f"# RequestsClient(dir_path={dir_path}, render_js={render_js}, method={method}, headers={headers}, timeout={timeout}, encoding={encoding}, verify_ssl={verify_ssl})")
        self.dir_path: Path = dir_path
        self.method: Method = method
        self.timeout: int = timeout
        self.headers: Dict[str, str] = headers or {}
        self.cookies: Dict[str, str] = {}
        self.encoding: str = encoding or "utf-8"
        self.verify_ssl: bool = verify_ssl

    def __del__(self):
        del self.headers

    def write_cookies_to_file(self, cookies) -> None:
        cookie_data: List[Dict[str, Any]] = []
        for k, v in cookies.iteritems():
            cookie_data.append({"name": k, "value": v})
        cookie_file = self.dir_path / RequestsClient.COOKIE_FILE
        with cookie_file.open("w", encoding='utf-8') as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)
            
    def read_cookies_from_file(self) -> None:
        cookie_file = self.dir_path / RequestsClient.COOKIE_FILE
        if cookie_file.is_file():
            cookie_str: str = ""
            with cookie_file.open("r", encoding='utf-8') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    self.cookies.update({cookie["name"]: cookie["value"]})
            LOGGER.debug(f"self.cookies={self.cookies}")

    def make_request(self, url, data=None, download_file: Path=None, allow_redirects=True) -> Tuple[str, str, Dict[str, Any], Optional[int]]:
        LOGGER.debug(f"# make_request(url='{url}', allow_redirects={allow_redirects})")

        if "Referer" in self.headers and self.headers["Referer"]:
            LOGGER.debug(f"visiting referer page '{self.headers['Referer']}'")
            self.read_cookies_from_file()
            response = None
            try:
                response = requests.get(self.headers['Referer'], headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=allow_redirects)
            except requests.exceptions.ConnectionError as e:
                LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
                LOGGER.warning("<!-- ")
                LOGGER.warning(e)
                LOGGER.warning(" -->")
                return "", f"can't connect to '{url}' for temporary network error", {}, None
            except requests.exceptions.ReadTimeout as e:
                LOGGER.warning(f"Warning: can't read data from '{url}' for timeout")
                LOGGER.warning(e)
                return "", f"Warning: can't read data from '{url}' for timeout", {}, None
            if response.cookies:
                self.write_cookies_to_file(response.cookies)

        self.read_cookies_from_file()
        response = None
        try:
            if self.method == Method.GET:
                cookie_str = '; '.join([f'{name}={value}' for name, value in self.cookies.items()])
                self.headers["Cookie"] = cookie_str
                LOGGER.debug(f"self.headers={self.headers}")
                response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=allow_redirects)
            elif self.method == Method.POST:
                response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, data=data)
            elif self.method == Method.HEAD:
                response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
                return str(response.status_code), "", dict(response.headers), response.status_code
        except requests.exceptions.ConnectionError as e:
            LOGGER.warning(f"Warning: can't connect to '{url}' for temporary network error")
            LOGGER.warning(e)
            return "", f"can't connect to '{url}' for temporary network error", {}, None
        except requests.exceptions.ReadTimeout as e:
            LOGGER.warning(f"Warning: can't read data from '{url}' for timeout")
            LOGGER.warning(e)
            return "", f"Warning: can't read data from '{url}' for timeout", {}, None

        # explicit null check required
        if response is None:
            return "", f"can't get response from '{url}'", {}, None
        if response.cookies:
            self.write_cookies_to_file(response.cookies)
        if response.status_code != 200:
            LOGGER.debug(f"response.status_code={response.status_code}")
            return "", f"can't get response from '{url}' with status code '{response.status_code}'", dict(response.headers), response.status_code

        if download_file:
            response.raw.decode_content = True
            with download_file.open('wb') as f:
                f.writelines(response)
            os.utime(download_file, (time.time(), time.time()))
            return "200", "", {}, response.status_code

        if self.encoding:
            response.encoding = self.encoding
        else:
            response.encoding = 'utf-8'

        if not re.search(r'<meta\s+property="og:url"\s+content="[^"]+"\s*/?>', response.text):
            result = re.sub(r'</head>', f'<meta property="og:url" content="{response.request.url}"/>\n</head>',
                            response.text)
            return result, "", dict(response.headers), response.status_code
        return response.text, "", dict(response.headers), response.status_code


class Crawler():
    class ReadTimeoutException(Exception):
        def __init__(self):
            super().__init__("Read timed out")

    def __init__(self, dir_path: Path=Path.cwd(), render_js=False, method=Method.GET, headers={}, timeout=60, num_retries=1, encoding=None, verify_ssl=True, copy_images_from_canvas=False, simulate_scrolling=False, disable_headless=False, blob_to_dataurl=False) -> None:
        LOGGER.debug(f"# Crawler(dir_path={dir_path}, render_js={render_js}, method={method}, headers={headers}, timeout={timeout}, num_retries={num_retries}, encoding={encoding}, verify_ssl={verify_ssl}, copy_images_from_canvas={copy_images_from_canvas}, simulate_scrolling={simulate_scrolling}, disable_headless={disable_headless}, blob_to_dataurl={blob_to_dataurl})")
        self.dir_path = dir_path
        self.render_js = render_js
        self.method = method
        self.headers = headers or {}
        if "User-Agent" not in self.headers or not self.headers["User-Agent"]:
            self.headers["User-Agent"] = DEFAULT_USER_AGENT
        self.timeout = timeout
        self.num_retries = num_retries
        self.encoding = encoding
        self.verify_ssl = verify_ssl
        self.copy_images_from_canvas = copy_images_from_canvas
        self.simulate_scrolling = simulate_scrolling
        self.disable_headless = disable_headless
        self.blob_to_dataurl = blob_to_dataurl
        if self.render_js:
            # headless browser
            self.headless_browser = HeadlessBrowser(dir_path=self.dir_path, headers=self.headers, copy_images_from_canvas=copy_images_from_canvas, simulate_scrolling=simulate_scrolling, disable_headless=disable_headless, blob_to_dataurl=blob_to_dataurl, timeout=timeout)
        else:
            self.requests_client = RequestsClient(dir_path=self.dir_path, method=method, headers=self.headers, timeout=timeout, encoding=encoding, verify_ssl=verify_ssl)

    def __del__(self):
        del self.headers
        if self.render_js:
            del self.headless_browser
        else:
            del self.requests_client

    @staticmethod
    def get_option_str(options: Dict[str, Any]) -> str:
        LOGGER.debug("# get_option_str()")

        option_str: str = ""
        if "render_js" in options:
            render_js = "true" if options["render_js"] else "false"
            option_str += f" --render-js={render_js}"
        if "verify_ssl" in options:
            verify_ssl = "true" if options["verify_ssl"] else "false"
            option_str += f" --verify-ssl={verify_ssl}"
        if "copy_images_from_canvas" in options:
            copy_images_from_canvas = "true" if options["copy_images_from_canvas"] else "false"
            option_str += f" --copy-images-from-canvas={copy_images_from_canvas}"
        if "simulate_scrolling" in options:
            simulate_scrolling = "true" if options["simulate_scrolling"] else "false"
            option_str += f" --simulate-scrolling={simulate_scrolling}"
        if "blob_to_dataurl" in options:
            blob_to_dataurl = "true" if options["blob_to_dataurl"] else "false"
            option_str += f" --blob-to-dataurl={blob_to_dataurl}"
        if "disable_headless" in options:
            disable_headless = "true" if options["disable_headless"] else "false"
            option_str += f" --disable-headless={disable_headless}"
        if "user_agent" in options and options["user_agent"]:
            user_agent = options["user_agent"]
            option_str += f" --user-agent='{user_agent}'"
        if "referer" in options and options["referer"]:
            referer = options["referer"]
            option_str += f" --referer='{referer}'"
        if "encoding" in options and options["encoding"]:
            encoding = options["encoding"]
            option_str += f" --encoding='{encoding}'"
        if "header_list" in options:
            for header in options["header_list"]:
                option_str += f" --header='{header}'"
        if "timeout" in options:
            timeout = options["timeout"] or "60"
            option_str += f" --timeout={timeout}"

        return option_str

    def run(self, url, data=None, download_file: Path = None, allow_redirects: bool = True) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        LOGGER.debug(f"# run(url={url}, data={data}, download_file={download_file}, allow_redirects={allow_redirects})")
        error: str = ""
        headers: Dict[str, Any] = {}
        for i in range(self.num_retries):
            if self.render_js:
                response = self.headless_browser.make_request(url, download_file=download_file)
                if response:
                    return response, "", None
            else:
                try:
                    response, error, headers, status_code = self.requests_client.make_request(url, download_file=download_file, data=data, allow_redirects=allow_redirects)
                    if response:
                        return response, "", None
                except requests.exceptions.ReadTimeout as e:
                    raise Crawler.ReadTimeoutException from e

                if status_code in (401, 403, 404, 405, 410):
                    # no retry in case of
                    #   401 Unauthorized
                    #   403 Forbidden
                    #   404 Not Found
                    #   405 Method Not Allowed
                    #   410 Gone
                    break
                LOGGER.debug(f"wait for seconds and retry (#{i})")
                time.sleep(5)

        return "", error, headers


def print_usage() -> None:
    print(f"Usage:\t{sys.argv[0]} [ <option> ... <option> ] <url>")
    print("options")
    print("\t--spider\t\t\tno download, just trying")
    print("\t--render-js=true/false\t\tphantomjs rendering")
    print("\t--verify-ssl=true/false\t\tssl certificate verification")
    print("\t--copy-images-from-canvas=true/false\t\timage in canvas element (in headless browser)")
    print("\t--simulate-scrolling=true/false\t\tsimulate scrolling (in headless browser)")
    print("\t--disable-headless=true/false\t\tshow browser (in headless browser)")
    print("\t--blob-to-dataurl=true/false\t\tconvert blob to data URL (in headless browser)")
    print("\t--download=<file>\t\tdownload as a file, instead of stdout")
    print("\t--header=<header string>\tspecify header string")
    print("\t--encoding=<encoding>\t\tspecify encoding of content")
    print("\t--user-agent=<user agent string>")
    print("\t--referer=<referer>")
    print("\t--retry=<# of retries>")


def main() -> int:
    LOGGER.debug("# main()")
    feed_dir_path = Path.cwd()
    method = Method.GET
    headers = {"Accept-Encoding": "gzip, deflate", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36", "Accept": "*/*", "Connection": "Keep-Alive"}
    timeout = 60
    num_retries = 1
    render_js = False
    download_file = None
    encoding: str = "utf-8"
    verify_ssl: bool = True
    copy_images_from_canvas: bool = False
    simulate_scrolling: bool = False
    disable_headless: bool = False
    blob_to_dataurl: bool = False

    if len(sys.argv) == 1:
        print_usage()
        sys.exit(-1)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:", ["spider", "render-js=", "verify-ssl=", "copy-images-from-canvas=", "simulate-scrolling=", "disable-headless=", "blob-to-dataurl=", "download=", "encoding=", "user-agent=", "referer=", "header=", "timeout=", "retry="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(-1)

    for o, a in opts:
        if o == "-h":
            print_usage()
            sys.exit(0)
        elif o == "-f":
            feed_dir_path = Path(a)
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
        elif o == "--blob-to-dataurl":
            blob_to_dataurl = (a == "true")
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
            download_file = Path(a)
        elif o == "--encoding":
            encoding = a

    url = args[0]

    crawler = Crawler(dir_path=feed_dir_path, render_js=render_js, method=method, headers=headers, timeout=timeout, num_retries=num_retries, encoding=encoding, verify_ssl=verify_ssl, copy_images_from_canvas=copy_images_from_canvas, simulate_scrolling=simulate_scrolling, disable_headless=disable_headless, blob_to_dataurl=blob_to_dataurl)
    response, error, _ = crawler.run(url, download_file=download_file)
    if not response:
        LOGGER.error(error)
    print(response)
    return 0


if __name__ == "__main__":
    sys.exit(main())
