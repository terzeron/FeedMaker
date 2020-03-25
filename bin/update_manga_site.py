#!/usr/bin/env python


import sys
import os
import re
import json
import logging
from feed_maker_util import exec_cmd


logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


def print_usage() -> None:
    print("Usage:\t%s <site number>")


def main() -> int:
    if len(sys.argv) < 2:
        print_usage()
        return -1
    site_num = sys.argv[1]

    # update site config file
    site_config_file = "site_config.json"
    if not os.path.isfile(site_config_file):
        print("can't find site config file")
        return -1

    with open(site_config_file, "r") as f:
        site_config = json.load(f)
        if site_config:
            if "url" in site_config:
                new_url = re.sub(r'(?P<pre>https?://[\w\.]+\D)(?P<num>\d+)(?P<post>\D.*)', r'\g<pre>' + site_num + r'\g<post>', site_config["url"])
            else:
                print("no url in site config")
                return -1

    with open(site_config_file, "w") as f:
        site_config["url"] = new_url
        json.dump(site_config, f, ensure_ascii=False)

    cmd: str = "git add %s; git commit -m 'modify site url'" % site_config_file
    result, error = exec_cmd(cmd)
    if error:
        LOGGER.error("can't git add '%s' & commit, %s", site_config_file, error)
            
    # update config files of all feeds which belongs to the site
    for entry in os.listdir("."):
        if not os.path.isdir(os.path.join(".", entry)) or entry.startswith("."):
            continue
        conf_file = os.path.join(entry, "conf.xml")
        ifile = open(conf_file, "r")
        temp_conf_file = conf_file + ".temp"
        ofile = open(temp_conf_file, "w")
        for line in ifile:
            m = re.search(r'(?P<pre><list_url><!\[CDATA\[https?://[\w\.]+\D)(?P<num>\d+)(?P<post>\D.*]]></list_url>)', line)
            if m:
                line = "            " + m.group("pre") + site_num + m.group("post") + "\n"
            ofile.write(line)
        ifile.close()
        ofile.close()
        os.rename(temp_conf_file, conf_file)

        cmd: str = "git add %s; git commit -m 'modify site url'" % conf_file
        result, error = exec_cmd(cmd)
        if error:
            LOGGER.error("can't git add '%s' & commit, %s", conf_file, error)
            
        if os.path.isdir(os.path.join(".", entry, "newlist")):
            for e in os.listdir(os.path.join(".", entry, "newlist")):
                os.remove(os.path.join(".", entry, "newlist", e))
            os.rmdir(os.path.join(entry, "newlist"))

    return 0


if __name__ == "__main__":
    sys.exit(main())
