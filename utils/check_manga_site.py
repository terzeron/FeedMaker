#!/usr/bin/env python


import sys
import re
import json
import logging.config
from pathlib import Path
from typing import Any
from bin.crawler import Crawler, Method
from bin.feed_maker_util import URL, NotFoundConfigFileError, NotFoundConfigItemError


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def read_config(site_conf_file_path: Path) -> dict[str, Any]:
    LOGGER.debug("# read_config(site_conf_file_path='%s')", site_conf_file_path)
    with site_conf_file_path.open("r", encoding="utf-8") as f:
        config: dict[str, Any] = json.load(f)
        if config:
            if "url" not in config:
                print("no url in site config")
                raise NotFoundConfigItemError("can't get configuration item 'url'")
            if "keyword" not in config:
                print("no keyword in site config")
                raise NotFoundConfigItemError("can't get configuration item 'keyword'")
            return config

    raise NotFoundConfigFileError(f"can't find configuration file '{site_conf_file_path}'")


def clean_url(url: str, scheme: str = "https", path: str = "") -> str:
    if re.search(r'^//', url):
        new_url = re.sub(r'^//', scheme + '://', url) + path
        return new_url
    return url


def get_location_recursively(url: str, config: dict[str, Any]) -> tuple[str, str]:
    LOGGER.debug(f"# get_location_recursively(url={url}, config={config})")
    crawler = Crawler(method=Method.GET, num_retries=config.get("num_retries", 1), render_js=config.get("render_js", False), encoding=config.get("encoding", "utf-8"), headers=config.get("headers", None), timeout=config.get("timeout", 60))
    try:
        response, error, response_headers = crawler.run(url, allow_redirects=False)
        if not response:
            LOGGER.error(error)

        response_size = len(response)
        new_url = ""
        LOGGER.debug("response_size=%d, new_url='%s'", response_size, new_url)
        if response_headers:
            LOGGER.debug("response_headers=%r", response_headers)
            if "Location" in response_headers:
                new_url = response_headers["Location"]
            elif "location" in response_headers:
                new_url = response_headers["location"]
            if new_url:
                print(f"new_url '{new_url}' from location header")

        del crawler

        if not new_url and response_size > 0:
            return url, response

        if new_url and response_size == 0:
            new_url = clean_url(new_url, URL.get_url_scheme(url), URL.get_url_path(url))
            new_url, response = get_location_recursively(new_url, config)

        return new_url, response
    except Crawler.ReadTimeoutException as e:
        LOGGER.error(e)
        return "", ""


def get(url: str, config: dict[str, Any]) -> tuple[bool, str, str]:
    LOGGER.debug(f"# get(url={url}, config={config})")
    print("getting start")
    new_url, response = get_location_recursively(url, config)
    LOGGER.debug("new_url='%s', len(response)=%d", new_url, len(response))
    if not response:
        print("no response")
        return False, "", new_url

    keyword= config.get("keyword", "")
    if keyword not in response:
        print("no keyword")
        return False, response, ""

    if URL.get_url_domain(url) not in response:
        print(f"old url '{url}' not found")
        return False, response, new_url

    print("getting end")
    return True, response, new_url


def get_new_url(*, url: str, response: str, new_pattern: str, pre: str, num: int, domain_postfix: str, post: str) -> tuple[str, int]:
    LOGGER.debug(f"# get_new_url(url='{url}', new_pattern='{new_pattern}', pre='{pre}', num={num}, domain_postfix='{domain_postfix}', post='{post}')")
    # try to find similar url
    url_count_map: dict[str, int] = {}
    new_number = num

    matches = re.findall(new_pattern, str(response))
    for match in matches:
        if int(match) > num:
            new_url = pre + match + domain_postfix + post
            LOGGER.debug(f"new_url={new_url}")
            if new_url in url_count_map:
                url_count_map[new_url] += 1
            else:
                url_count_map[new_url] = 1

    if len(url_count_map) == 0:
        print("can't find new url")
        new_url = ""
        new_number = 0
    else:
        sorted_list = sorted(url_count_map.items(), key=lambda item: item[1], reverse=True)
        LOGGER.debug(sorted_list)
        new_url = sorted_list[0][0]
        m = re.search(new_pattern, new_url)
        if m:
            new_number = int(m.group(1))
    LOGGER.debug(f"new_url={new_url}, new_number={new_number}")
    return new_url, new_number


def get_url_pattern(url: str) -> tuple[str, str, int, str, str]:
    LOGGER.debug(f"# get_url_pattern(url={url})")
    new_pattern: str = ""
    pre: str = ""
    num: int = 0
    domain_postfix: str = ""
    post: str = ""
    m1 = re.search(r'(?P<pre>(https?:)?//[\w\.\-]+\D)(?P<num>\d+)(?P<domain_postfix>[^/]+)(?P<post>.*)', url)
    if m1:
        pre = m1.group("pre")
        num = int(m1.group("num"))
        domain_postfix = m1.group("domain_postfix")
        post = m1.group("post")
        new_pattern = pre + r'(\d+)' + domain_postfix + r'(?:' + post + r')?'
        LOGGER.debug(f"type 1 pattern: {pre}, {domain_postfix}, {post}, {new_pattern}")
    return new_pattern, pre, num, domain_postfix, post


def print_new_url(url: str, new_url: str, new_number: int) -> None:
    if url == new_url:
        print("same url")
    else:
        print(f"no service from {url}")
        print(f"You can use a new url {new_url} from now on")
        print(f"New number: {new_number}")


def main() -> int:
    LOGGER.debug("# main()")

    site_conf_file_path = Path.cwd() / "site_config.json"
    if not site_conf_file_path.is_file():
        print("can't find site config file")
        return -1

    config = read_config(site_conf_file_path)
    url = config.get("url", "")
    print(f"url: {url}")

    new_pattern, pre, num, domain_postfix, post = get_url_pattern(url)
    LOGGER.debug(f"new_pattern='{new_pattern}', pre='{pre}', num={num}, domain_postfix='{domain_postfix}', post='{post}'")

    success, response, new_url = get(url, config)
    LOGGER.debug("success=%r, len(response)=%d, new_url='%s'", success, len(response), new_url)
    if not success:
        if new_url:
            _, _, num, _, _ = get_url_pattern(new_url)
            LOGGER.debug(f"num={num}")
            print_new_url(url, new_url, num)
        else:
            new_url, new_number = get_new_url(url=url, response=response, new_pattern=new_pattern, pre=pre, num=num, domain_postfix=domain_postfix, post=post)
            LOGGER.debug(f"new_url={new_url}, new_number={new_number}")
            if new_url:
                print_new_url(url, new_url, new_number)
            else:
                print("can't get new url from old url")

        return -1

    print("Ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
