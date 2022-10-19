#!/usr/bin/env python


import sys
import os
import re
import json
import logging
import logging.config
from typing import Dict, Any, Optional, Tuple
from crawler import Crawler, Method
from feed_maker_util import URL, Process


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def read_config(site_config_file: str) -> Optional[Dict[str, Any]]:
    LOGGER.debug(f"# read_config(site_config_file={site_config_file})")
    with open(site_config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
        if config:
            if "url" not in config:
                print("no url in site config")
                return None
            if "keyword" not in config:
                print("no keyword in site config")
                return None
            if "num_retries" not in config:
                config["num_retries"] = 1
            if "encoding" not in config:
                config["encoding"] = "utf-8"
            if "headers" not in config:
                config["headers"] = {}
            if "timeout" not in config:
                config["timeout"] = 10
            return config
    return None


def clean_url(url: str, scheme: str = "https", path: str = "") -> str:
    if re.search(r'^//', url):
        new_url = re.sub(r'^//', scheme + '://', url) + path
        return new_url
    return url


def get_location_recursively(url: str, config: Dict[str, Any]) -> Tuple[str, str]:
    LOGGER.debug(f"# get_location_recursively(url={url}, config={config})")
    response = None
    response_headers = None
    crawler = Crawler(method=Method.GET, num_retries=config["num_retries"], render_js=config["render_js"], encoding=config["encoding"], headers=config["headers"], timeout=config["timeout"])
    try:
        response, _, response_headers = crawler.run(url, allow_redirects=False)
    except Exception as e:
        print("exception occurred")
        print(e)
        return "", ""

    response_size = len(response)
    new_url = ""
    if response_headers:
        if "Location" in response_headers:
            new_url = response_headers["Location"]
        elif "location" in response_headers:
            new_url = response_headers["location"]
    del crawler
    if new_url and response_size == 0:
        new_url = clean_url(new_url, URL.get_url_scheme(url), URL.get_url_path(url))
        new_url, response = get_location_recursively(new_url, config)
    else:
        new_url = url
    return new_url, response


def get(url: str, config: Dict[str, Any]) -> Tuple[bool, str, str]:
    LOGGER.debug(f"# get(url={url}, config={config})")
    print("getting start")
    new_url, response = get_location_recursively(url, config)
    if not response:
        print("no response")
        return False, "", new_url

    if config["keyword"] not in response:
        print("no keyword")
        return False, response, new_url

    if URL.get_url_domain(url) not in response:
        print("old url not found")
        return False, response, new_url

    print("getting end")
    #del crawler
    return True, response, new_url


def get_new_url(url: str, response: str, new_pattern: str, pre: str, num: int, domain_postfix: str, post: str) -> Tuple[str, int]:
    LOGGER.debug(f"# get_new_url(url='{url}', new_pattern='{new_pattern}', pre='{pre}', num={num}, domain_postfix='{domain_postfix}', post='{post}')")
    new_url: str = ""
    # try to find similar url
    url_count_map: Dict[str, int] = {}

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
    return new_url, new_number


def get_url_pattern(url: str) -> Tuple[str, str, int, str, str]:
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
        new_pattern = pre + '(\d+)' + domain_postfix + '(?:' + post + ')?'
        LOGGER.debug(f"type 1 pattern: {pre}, {domain_postfix}, {post}, {new_pattern}")
    return new_pattern, pre, num, domain_postfix, post


def print_new_url(url: str, new_url: str, new_number: str) -> None:
    if url == new_url:
        print("same url")
    else:
        print(f"no service from {url}")
        print(f"You can use a new url {new_url} from now on")
        print(f"New number: {new_number}")


def main() -> int:
    LOGGER.debug("# main()")
    new_url = ""
    site_config_file = "site_config.json"
    if not os.path.isfile(site_config_file):
        print("can't find site config file")
        return -1

    config = read_config(site_config_file)
    if not config:
        print(f"can't read configuration file '{site_config_file}'")
        return -1
    url = config["url"]
    print(f"url: {url}")

    new_pattern, pre, num, domain_postfix, post = get_url_pattern(url)
    LOGGER.debug(f"new_pattern='{new_pattern}', pre='{pre}', num={num}, domain_postfix='{domain_postfix}', post='{post}'")

    success, response, new_url = get(url, config)
    LOGGER.debug(f"success={success}, new_url='{new_url}'")
    if not success:
        if new_url:
            _, _, num, _, _ = get_url_pattern(new_url)
            print_new_url(url, new_url, num)
        else:
            new_url, new_number = get_new_url(url, response, new_pattern, pre, num, domain_postfix, post)
            if new_url:
                print_new_url(url, new_url, new_number)
            else:
                print("can't get new url from old url")

        return -1

    print("Ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
