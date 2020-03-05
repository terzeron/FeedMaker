#!/usr/bin/env python

import sys
import os
import re
import json
from crawler import Crawler, Method
from feed_maker_util import exec_cmd


def send_alarm(url: str, new_url: str) -> int:
    cmd = "send_msg_to_line.sh 'no service from %s'" % url
    _, error = exec_cmd(cmd)
    if error:
        print("can't execute a command '%s'" % cmd)
        return -1
    cmd = "send_msg_to_line.sh 'would you check the new site? %s'" % new_url
    _, error = exec_cmd(cmd)
    if error:
        print("can't execute a command '%s'" % cmd)
        return -1
    return 0


def main() -> int:
    do_send: bool = False
    site_config_file = "site_config.json"
    if not os.path.isfile(site_config_file):
        print("can't find site config file")
        return -1

    with open(site_config_file, "r") as f:
        site_config = json.load(f)
        url: str = ""
        keyword: str = ""
        num_retries: int = 1
        render_js: bool = False
        encoding: str = "utf-8"
        if site_config:
            if "url" in site_config:
                url = site_config["url"]
            else:
                print("no url in site config")
                return -1
            if "keyword" in site_config:
                keyword = site_config["keyword"]
            else:
                print("no keyword in site config")
                return -1
            if "num_retries" in site_config:
                num_retries = site_config["num_retries"]
            if "render_js" in site_config:
                render_js = site_config["render_js"]
            if "encoding" in site_config:
                encoding = site_config["encoding"]

    if not render_js:
        print("spidering start")
        crawler = Crawler(method=Method.HEAD)
        response = crawler.run(url)
        if response != "200":
            print(response)
            do_send = True
        print("spidering end")

    print("getting start")
    crawler = Crawler(method=Method.GET, num_retries=num_retries, render_js=render_js, encoding=encoding)
    response = crawler.run(url)

    if not response:
        print("no response")
        do_send = True
    if keyword not in response:
        print("no keyword")
        do_send = True
    if len(response) <= 10240:
        print("too small response")
        do_send = True
    print("getting end")

    if do_send:
        print("alarming start")
        new_url = re.sub(r'(?P<pre>https?://[\w\.]+\D)(?P<num>\d+)(?P<post>\D.*)', lambda m: m.group("pre") + str(int(m.group("num")) + 1) + m.group("post"), url)
        send_alarm(url, new_url)
        print("alarming end")
        return -1

    print("Ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
