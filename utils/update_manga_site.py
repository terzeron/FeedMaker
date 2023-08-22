#!/usr/bin/env python


import sys
import os
import re
import json
import getopt
import logging.config
from pprint import pprint
from typing import Optional
from pathlib import Path
from bin.feed_maker_util import Process


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()


def print_usage() -> None:
    print("Usage:\t%s [ -t ] <site number>")
    print("\t\t\t-t: run for test (without updating)")


def update_domain(test_run: bool, new_number: int) -> bool:
    print("--- updating domain ---")
    new_referer: Optional[str] = ""

    # update site config file
    print("- site_config.json")
    site_config_file = "site_config.json"
    if not os.path.isfile(site_config_file):
        print("can't find site config file")
        return False

    # read site config file
    with open(site_config_file, "r", encoding="utf-8") as f:
        site_config = json.load(f)
        if site_config:
            if "url" in site_config:
                if test_run:
                    m = re.search(r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>[^/]*)', site_config["url"])
                    if m:
                        print(m.group("pre"))
                        print(str(new_number))
                        print(m.group("post"))
                new_url = re.sub(r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>[^/]*)', r'\g<pre>' + str(new_number) + r'\g<post>', site_config["url"])
            else:
                print("no url in site config")
                return False
            if "referer" in site_config:
                new_referer = re.sub(r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>[^/]*)', r'\g<pre>' + str(new_number) + r'\g<post>', site_config["referer"])
        else:
            print("empty site config")
            return False

    # write site config file
    if new_url:
        site_config["url"] = new_url
    if new_referer:
        site_config["referer"] = new_referer
    if test_run:
        print(new_url)
        print(new_referer)
        pprint(site_config)
    else:
        temp_site_config_file = site_config_file + ".temp"
        with open(temp_site_config_file, "w", encoding="utf-8") as outfile:
            json.dump(site_config, outfile, indent=2, ensure_ascii=False)
            os.rename(temp_site_config_file, site_config_file)

    # git add
    if not test_run:
        print("- git add")
        git_cmd: str = f"git add {site_config_file}"
        _, error = Process.exec_cmd(git_cmd)
        if error:
            LOGGER.error(f"can't execute a command '{git_cmd}', {error}")

    # update config files of all feeds which belongs to the site
    for entry in os.listdir("."):
        if not os.path.isdir(os.path.join(".", entry)) or entry.startswith("."):
            continue
        print(f"- {entry}: ", end='')
        conf_file = os.path.join(entry, "conf.json")
        if not test_run:
            print(".", end='')
        temp_conf_file = conf_file + ".temp"
        with open(conf_file, "r", encoding="utf-8") as infile:
            data = json.load(infile)
            if "configuration" in data and "collection" in data["configuration"] and "list_url_list" in data["configuration"]["collection"]:
                new_list_url_list = []
                for list_url in data["configuration"]["collection"]["list_url_list"]:
                    m = re.search(r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>(\.|/).*)', list_url)
                    if m:
                        new_list_url = m.group("pre") + str(new_number) + m.group("post")
                        new_list_url_list.append(new_list_url)
                data["configuration"]["collection"]["list_url_list"] = new_list_url_list

        if test_run:
            pprint(data)
            break

        with open(temp_conf_file, "w", encoding="utf-8") as outfile:
            json.dump(data, outfile, indent=2, ensure_ascii=False)
            os.rename(temp_conf_file, conf_file)

        if not test_run:
            print(".", end='')
            git_cmd = f"git add {conf_file}"
            _, error = Process.exec_cmd(git_cmd)
            if error:
                LOGGER.error(f"can't execute a command '{git_cmd}', {error}")

        if not test_run:
            print(".", end='')
            if os.path.isdir(os.path.join(".", entry, "newlist")):
                for e in os.listdir(os.path.join(".", entry, "newlist")):
                    os.remove(os.path.join(".", entry, "newlist", e))
                os.rmdir(os.path.join(".", entry, "newlist"))

        if not test_run:
            print(".", end='')
            try:
                xml_file_path = Path.cwd() / entry / f"{entry}.xml"
                old_xml_file_path = xml_file_path.with_suffix(xml_file_path.suffix + ".old")
                xml_file_path.unlink(missing_ok=True)
                old_xml_file_path.unlink(missing_ok=True)
            except FileNotFoundError:
                pass
            print("")

    if not test_run:
        print("- git commit")
        git_cmd = f"git commit -m 'modify site url to {new_url}'"
        _, error = Process.exec_cmd(git_cmd)
        if error:
            LOGGER.error(f"can't execute a command '{git_cmd}', {error}")

    return True


def check_site() -> bool:
    print("--- checking site ---")
    cmd = "check_manga_site.py"
    result, error = Process.exec_cmd(cmd)
    if result:
        print(result)
    else:
        print(error)
    return True


def main() -> int:
    test_run = False
    optlist, args = getopt.getopt(sys.argv[1:], "t")
    for o, _ in optlist:
        if o == "-t":
            test_run = True

    if len(args) < 1:
        print_usage()
        return -1

    new_number = int(args[0])
    if update_domain(test_run, new_number):
        if not test_run:
            check_site()

    return 0


if __name__ == "__main__":
    sys.exit(main())
