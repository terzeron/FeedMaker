#!/usr/bin/env python


import sys
import os
import re
import time
import getopt
import json
import tempfile
import logging.config
from enum import Enum
from pathlib import Path
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urljoin

import urllib3
import requests
from requests.cookies import RequestsCookieJar

from bin.feed_maker_util import PathUtil, Env, URLSafety
from bin.headless_browser import HeadlessBrowser

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


class _LoginFormParser(HTMLParser):
    """login_url 페이지의 HTML에서 <form> 내 hidden 필드, action URL, 입력 필드명을 추출한다."""

    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._current_form: Optional[dict[str, Any]] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attr_dict = dict(attrs)
        if tag == "form":
            self._current_form = {"action": attr_dict.get("action", ""), "method": attr_dict.get("method", "post").lower(), "hidden_fields": {}, "has_password_field": False, "password_field_name": "", "text_field_names": []}
        elif tag == "input" and self._current_form is not None:
            input_type = attr_dict.get("type", "text").lower()
            name = attr_dict.get("name", "")
            if input_type == "hidden":
                value = attr_dict.get("value", "")
                if name:
                    self._current_form["hidden_fields"][name] = value
            elif input_type == "password":
                self._current_form["has_password_field"] = True
                if name:
                    self._current_form["password_field_name"] = name
            elif input_type in ("text", "email", "tel") and name:
                self._current_form["text_field_names"].append(name)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None


class LoginManager:
    """`.login.json` 기반 로그인 관리."""

    LOGIN_CONFIG_FILE = ".login.json"
    REQUIRED_FIELDS = ("login_url", "id", "password")

    @staticmethod
    def load_login_config(dir_path: Path) -> Optional[dict[str, str]]:
        config_file = dir_path / LoginManager.LOGIN_CONFIG_FILE
        if not config_file.is_file():
            return None
        try:
            with config_file.open("r", encoding="utf-8") as f:
                config = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            LOGGER.warning("Failed to read %s: %s", config_file, e)
            return None
        for field in LoginManager.REQUIRED_FIELDS:
            if not config.get(field):
                LOGGER.warning("Missing required field '%s' in %s", field, config_file)
                return None
        return config

    @staticmethod
    def parse_login_form(html: str, login_url: str) -> tuple[str, dict[str, str], str, str]:
        """로그인 폼을 파싱하여 (post_url, hidden_fields, id_field_name, password_field_name)을 반환한다."""
        parser = _LoginFormParser()
        parser.feed(html)
        # password 필드가 있는 form 우선 선택
        target_form = None
        for form in parser.forms:
            if form["has_password_field"]:
                target_form = form
                break
        if target_form is None and parser.forms:
            target_form = parser.forms[0]
        if target_form is None:
            return login_url, {}, "", ""
        action = target_form["action"]
        if action:
            post_url = urljoin(login_url, action)
        else:
            post_url = login_url
        password_field_name = target_form.get("password_field_name", "")
        text_fields = target_form.get("text_field_names", [])
        id_field_name = text_fields[0] if text_fields else ""
        return post_url, target_form["hidden_fields"], id_field_name, password_field_name

    @staticmethod
    def check_login_success(response: requests.Response) -> bool:
        if response.cookies and len(response.cookies) > 0:
            return True
        if response.status_code in (200, 302):
            LOGGER.warning("Login response has no cookies but status=%d, treating as success", response.status_code)
            return True
        return False


class Method(Enum):
    GET = 1
    HEAD = 2
    POST = 3


class RequestsClient:
    COOKIE_FILE = "cookies.requestsclient.json"

    def __init__(self, *, dir_path: Path = Path.cwd(), render_js: bool = False, method: Method = Method.GET, headers: Optional[dict[str, str]] = None, timeout: int = 60, encoding: str = "utf-8", verify_ssl: bool = True) -> None:
        LOGGER.debug("# RequestsClient(dir_path=%s, render_js=%s, method=%s, headers=%r, timeout=%d, encoding=%s, verify_ssl=%s)", PathUtil.short_path(dir_path), render_js, method, headers, timeout, encoding, verify_ssl)
        self.dir_path: Path = dir_path
        self.method: Method = method
        self.timeout: int = timeout
        self.headers: dict[str, str] = headers if headers is not None else {}
        self.cookies: dict[str, str] = {}
        self.encoding: str = encoding or "utf-8"
        self.verify_ssl: bool = verify_ssl
        self._cookie_dir: Optional[Path] = None
        self.allow_private_ips = Env.get("FM_CRAWLER_ALLOW_PRIVATE_IPS", "false").strip().lower() in ("1", "true", "yes", "on")
        self.allowed_hosts_raw = Env.get("FM_CRAWLER_ALLOWED_HOSTS", "")
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __del__(self) -> None:
        del self.headers

    def _get_cookie_dir(self) -> Path:
        if self._cookie_dir is not None:
            return self._cookie_dir
        if os.access(self.dir_path, os.W_OK):
            self._cookie_dir = self.dir_path
        else:
            import hashlib

            dir_hash = hashlib.md5(str(self.dir_path).encode()).hexdigest()[:12]
            fallback = Path(tempfile.gettempdir()) / "fm_cookies" / dir_hash
            fallback.mkdir(parents=True, exist_ok=True)
            LOGGER.info("Cookie dir '%s' not writable, using fallback '%s'", self.dir_path, fallback)
            self._cookie_dir = fallback
        return self._cookie_dir

    def write_cookies_to_file(self, cookies: RequestsCookieJar) -> None:
        self.read_cookies_from_file()
        for k, v in cookies.items():
            self.cookies[k] = v
        cookie_data = [{"name": k, "value": v} for k, v in self.cookies.items()]
        cookie_file = self._get_cookie_dir() / RequestsClient.COOKIE_FILE
        with cookie_file.open("w", encoding="utf-8") as f:
            json.dump(cookie_data, f, indent=2, ensure_ascii=False)

    def read_cookies_from_file(self) -> None:
        cookie_file = self._get_cookie_dir() / RequestsClient.COOKIE_FILE
        if cookie_file.is_file():
            with cookie_file.open("r", encoding="utf-8") as f:
                cookies = json.load(f)
                for cookie in cookies:
                    if "expiry" in cookie:
                        del cookie["expiry"]
                    c_name = cookie.get("name", "")
                    c_value = cookie.get("value", "")
                    if c_name and c_value:
                        self.cookies.update({c_name: c_value})
            # LOGGER.debug(f"self.cookies={self.cookies}")

    def login(self, config: dict[str, str]) -> bool:
        LOGGER.debug("# RequestsClient.login(login_url=%s)", config["login_url"])
        login_url = config["login_url"]
        try:
            login_page_response = requests.get(login_url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            LOGGER.warning("Failed to access login page '%s': %s", login_url, e)
            return False

        if login_page_response.cookies:
            self.write_cookies_to_file(login_page_response.cookies)

        post_url, hidden_fields, detected_id_field, detected_pw_field = LoginManager.parse_login_form(login_page_response.text, login_url)
        id_field = config.get("id_field") or detected_id_field
        pw_field = config.get("password_field") or detected_pw_field
        if not id_field or not pw_field:
            LOGGER.warning("Cannot determine login form field names (id_field=%r, password_field=%r)", id_field, pw_field)
            return False
        post_data = {id_field: config["id"], pw_field: config["password"]}
        post_data.update(hidden_fields)

        self.read_cookies_from_file()
        cookie_str = "; ".join([f"{name}={value}" for name, value in self.cookies.items()])
        login_headers = dict(self.headers)
        if cookie_str:
            login_headers["Cookie"] = cookie_str

        try:
            login_response = requests.post(post_url, headers=login_headers, data=post_data, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=True)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            LOGGER.warning("Login POST failed for '%s': %s", post_url, e)
            return False

        if login_response.cookies:
            self.write_cookies_to_file(login_response.cookies)

        success = LoginManager.check_login_success(login_response)
        if success:
            LOGGER.info("Login successful for '%s'", login_url)
        else:
            LOGGER.warning("Login failed for '%s' (status=%d)", login_url, login_response.status_code)
        return success

    def make_request(self, url: str, data: Any = None, download_file: Optional[Path] = None, allow_redirects: bool = True) -> tuple[str, str, dict[str, Any], Optional[int]]:
        LOGGER.debug(f"# make_request(url='{url}', allow_redirects={allow_redirects})")
        is_ok, reason = URLSafety.check_url(url, allow_private=self.allow_private_ips, allowed_hosts_raw=self.allowed_hosts_raw)
        if not is_ok:
            LOGGER.warning("Blocked URL: %s (%s)", url, reason)
            return "", f"blocked url: {reason}", {}, None

        referer = self.headers.get("Referer", "")
        if referer:
            is_ok, reason = URLSafety.check_url(referer, allow_private=self.allow_private_ips, allowed_hosts_raw=self.allowed_hosts_raw)
            if not is_ok:
                LOGGER.warning("Blocked referer URL: %s (%s)", referer, reason)
                return "", f"blocked url: {reason}", {}, None
            LOGGER.debug("visiting referer page '%s'", referer)
            self.read_cookies_from_file()
            try:
                referer_response = requests.get(referer, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=allow_redirects)
            except requests.exceptions.ConnectionError as e:
                LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
                LOGGER.warning("<!-- %r -->", e)
                return "", f"can't connect to '{url}' for temporary network error", {}, None
            except requests.exceptions.ReadTimeout as e:
                LOGGER.warning(f"<!-- Warning: can't read data from '{url}' for timeout -->")
                LOGGER.warning("<!-- %r -->", e)
                return "", f"Warning: can't read data from '{url}' for timeout", {}, None
            if referer_response.cookies:
                self.write_cookies_to_file(referer_response.cookies)

        self.read_cookies_from_file()
        response = None
        try:
            if self.method == Method.GET:
                cookie_str = "; ".join([f"{name}={value}" for name, value in self.cookies.items()])
                self.headers["Cookie"] = cookie_str
                # LOGGER.debug(f"self.headers={self.headers}")
                response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, allow_redirects=allow_redirects)
            elif self.method == Method.POST:
                response = requests.post(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl, data=data)
            elif self.method == Method.HEAD:
                response = requests.head(url, headers=self.headers, timeout=self.timeout, verify=self.verify_ssl)
                return str(response.status_code), "", dict(response.headers), response.status_code
        except requests.exceptions.ConnectionError as e:
            LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
            LOGGER.warning("<!-- %r -->", e)
            return "", f"can't connect to '{url}' for temporary network error", {}, None
        except requests.exceptions.ReadTimeout as e:
            LOGGER.warning(f"<!-- Warning: can't read data from '{url}' for timeout -->")
            LOGGER.warning("<!-- %r -->", e)
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
            with download_file.open("wb") as f:
                f.writelines(response)
            os.utime(download_file, (time.time(), time.time()))
            return "200", "", {}, response.status_code

        if self.encoding:
            response.encoding = self.encoding
        else:
            response.encoding = "utf-8"

        if not re.search(r'<meta\s+property="og:url"\s+content="[^"]+"\s*/?>', response.text):
            result = response.text.replace("</head>", f'<meta property="og:url" content="{response.request.url}"/>\n</head>')
            return result, "", dict(response.headers), response.status_code
        return response.text, "", dict(response.headers), response.status_code


class Crawler:
    class ReadTimeoutException(Exception):
        def __init__(self) -> None:
            super().__init__("Read timed out")

    def __init__(
        self,
        *,
        dir_path: Path = Path.cwd(),
        render_js: bool = False,
        method: Method = Method.GET,
        headers: Optional[dict[str, str]] = None,
        timeout: int = 60,
        num_retries: int = 1,
        encoding: str = "utf-8",
        verify_ssl: bool = True,
        copy_images_from_canvas: bool = False,
        simulate_scrolling: bool = False,
        disable_headless: bool = False,
        blob_to_dataurl: bool = False,
    ) -> None:
        LOGGER.debug(
            "# Crawler(dir_path=%s, render_js=%s, method=%s, headers=%r, timeout=%d, num_retries=%d, encoding=%s, verify_ssl=%s, copy_images_from_canvas=%s, simulate_scrolling=%s, disable_headless=%s, blob_to_dataurl=%s)",
            PathUtil.short_path(dir_path),
            render_js,
            method,
            headers,
            timeout,
            num_retries,
            encoding,
            verify_ssl,
            copy_images_from_canvas,
            simulate_scrolling,
            disable_headless,
            blob_to_dataurl,
        )
        self.dir_path = dir_path
        self.render_js = render_js
        self.method = method
        self.headers: dict[str, str] = headers if headers is not None else {}
        self.headers["User-Agent"] = self.headers.get("User-Agent", DEFAULT_USER_AGENT)
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

    def __del__(self) -> None:
        if self.headers:
            del self.headers
        if self.render_js:
            del self.headless_browser
        else:
            del self.requests_client

    @staticmethod
    def get_option_str(options: dict[str, Any]) -> str:
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
        if "headers" in options:
            header_str = ""
            for k, v in options["headers"].items():
                if header_str != "":
                    header_str += "; "
                if v and v != "None":
                    header_str += f"{k}: {v}"
            option_str += f" --header='{header_str}'"
        if "timeout" in options:
            timeout = options["timeout"] or "60"
            option_str += f" --timeout={timeout}"

        return option_str

    def _try_login(self) -> None:
        config = LoginManager.load_login_config(self.dir_path)
        if config is None:
            return
        # 쿠키 파일이 이미 존재하면 로그인 스킵
        if self.render_js:
            cookie_file = self.headless_browser._get_cookie_dir() / HeadlessBrowser.COOKIE_FILE
        else:
            cookie_file = self.requests_client._get_cookie_dir() / RequestsClient.COOKIE_FILE
        if cookie_file.is_file():
            LOGGER.debug("Cookie file exists, skipping login")
            return
        LOGGER.info("Attempting login via %s", config["login_url"])
        if self.render_js:
            success = self.headless_browser.login(config)
        else:
            success = self.requests_client.login(config)
        if not success:
            LOGGER.warning("Login failed, proceeding without login")

    def run(self, url: str, data: Any = None, download_file: Optional[Path] = None, allow_redirects: bool = True) -> tuple[str, str, Optional[dict[str, Any]]]:
        LOGGER.debug(f"# run(url={url}, data={data!r}, download_file={download_file}, allow_redirects={allow_redirects})")
        self._try_login()
        error: str = ""
        headers: dict[str, Any] = {}
        for i in range(self.num_retries):
            if self.render_js:
                response = self.headless_browser.make_request(url, download_file=download_file)
                if response:
                    return response, "", None
                if i < self.num_retries - 1:
                    LOGGER.debug(f"wait for seconds and retry (#{i})")
                    time.sleep(5)
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
            render_js = a == "true"
        elif o == "--verify-ssl":
            verify_ssl = a == "true"
        elif o == "--copy-images-from-canvas":
            copy_images_from_canvas = a == "true"
        elif o == "--simulate-scrolling":
            simulate_scrolling = a == "true"
        elif o == "--disable-headless":
            disable_headless = a == "true"
        elif o == "--blob-to-dataurl":
            blob_to_dataurl = a == "true"
        elif o == "--header":
            m = re.search(r"^(?P<key>[^:]+)\s*:\s*(?P<value>.+)\s*$", a)
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

    crawler = Crawler(
        dir_path=feed_dir_path,
        render_js=render_js,
        method=method,
        headers=headers,
        timeout=timeout,
        num_retries=num_retries,
        encoding=encoding,
        verify_ssl=verify_ssl,
        copy_images_from_canvas=copy_images_from_canvas,
        simulate_scrolling=simulate_scrolling,
        disable_headless=disable_headless,
        blob_to_dataurl=blob_to_dataurl,
    )
    response, error, _ = crawler.run(url, download_file=download_file)
    if not response:
        LOGGER.error(error)
    print(response)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
