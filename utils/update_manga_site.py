#!/usr/bin/env python


import sys
import re
import json
import getopt
import logging.config
from pprint import pprint
from typing import Dict, Any
from pathlib import Path
from bin.feed_maker_util import Process, Config, NotFoundConfigFileError, InvalidConfigFileError, NotFoundConfigItemError


logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

# Constants
SITE_CONFIG_FILE = "site_config.json"
URL_PATTERN = r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>[^/]*)'
LIST_URL_PATTERN = r'(?P<pre>https?://[\w\.\-]+\D)(?P<variant_postfix>\d+)(?P<post>[\./].*)'


def print_usage() -> None:
    """Print usage information."""
    print("Usage:\t%s [ -t ] <site number>")
    print("\t\t\t-t: run for test (without updating)")


def load_site_config(site_config_path: Path) -> Dict[str, Any]:
    """Load and validate site configuration file."""
    if not site_config_path.is_file():
        raise NotFoundConfigFileError(f"can't find configuration file '{site_config_path}'")

    with site_config_path.open("r", encoding="utf-8") as f:
        site_config = json.load(f)
        if not site_config:
            raise InvalidConfigFileError(f"can't get configuration from '{site_config_path}' with invalid format")
        return site_config


def validate_site_config(site_config: Dict[str, Any]) -> tuple[str, str]:
    """Validate site configuration and return url and referer."""
    url = site_config.get("url", "")
    if not url:
        raise NotFoundConfigItemError("can't get configuration item 'url'")

    referer = site_config.get("referer", "")
    # Note: referer can be empty, only url is required

    return url, referer


def update_url_pattern(url: str, new_number: int) -> str:
    """Update URL pattern with new number."""
    return re.sub(URL_PATTERN, r'\g<pre>' + str(new_number) + r'\g<post>', url)


def update_list_url_pattern(list_url: str, new_number: int) -> str:
    """Update list URL pattern with new number."""
    m = re.search(LIST_URL_PATTERN, list_url)
    if m:
        return m.group("pre") + str(new_number) + m.group("post")
    return list_url


def save_site_config(site_config: Dict[str, Any], site_config_path: Path, test_run: bool) -> None:
    """Save site configuration to file."""
    if test_run:
        print(site_config.get("url", ""))
        print(site_config.get("referer", ""))
        pprint(site_config)
    else:
        temp_site_conf_file_path = site_config_path.with_suffix(site_config_path.suffix + ".temp")
        with temp_site_conf_file_path.open("w", encoding="utf-8") as outfile:
            json.dump(site_config, outfile, indent=2, ensure_ascii=False)
            temp_site_conf_file_path.rename(site_config_path)


def git_add_file(file_path: Path) -> None:
    """Add file to git."""
    git_cmd = f"git add {file_path}"
    _, error = Process.exec_cmd(git_cmd)
    if error:
        LOGGER.error("can't execute a command '%s', %r", git_cmd, error)


def update_feed_config(conf_file_path: Path, new_number: int, test_run: bool) -> None:
    """Update feed configuration file."""
    if not conf_file_path.is_file():
        return  # Skip if conf.json doesn't exist

    temp_conf_file_path = conf_file_path.with_suffix(conf_file_path.suffix + ".temp")

    with conf_file_path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)

        if "configuration" in data and "collection" in data["configuration"] and "list_url_list" in data["configuration"]["collection"]:
            new_list_url_list: list[str] = []
            for list_url in data["configuration"]["collection"]["list_url_list"]:
                new_list_url = update_list_url_pattern(list_url, new_number)
                new_list_url_list.append(new_list_url)
            data["configuration"]["collection"]["list_url_list"] = new_list_url_list

    if test_run:
        pprint(data)
        return

    with temp_conf_file_path.open("w", encoding="utf-8") as outfile:
        json.dump(data, outfile, indent=2, ensure_ascii=False)
        temp_conf_file_path.rename(conf_file_path)


def cleanup_feed_directory(entry_path: Path) -> None:
    """Clean up feed directory by removing newlist and xml files."""
    # Remove newlist directory
    newlist_path = entry_path / "newlist"
    if newlist_path.is_dir():
        for file_path in newlist_path.iterdir():
            file_path.unlink()
        newlist_path.rmdir()

    # Remove xml files
    try:
        xml_file_path = (entry_path / f"{entry_path.name}").with_suffix(".xml")
        old_xml_file_path = xml_file_path.with_suffix(xml_file_path.suffix + ".old")
        xml_file_path.unlink(missing_ok=True)
        old_xml_file_path.unlink(missing_ok=True)
    except FileNotFoundError:
        pass


def process_feed_directory(entry_path: Path, new_number: int, test_run: bool) -> None:
    """Process a single feed directory."""
    print(f"- {entry_path}: ", end='')
    conf_file_path = entry_path / Config.DEFAULT_CONF_FILE

    if not test_run:
        print(".", end='')

    update_feed_config(conf_file_path, new_number, test_run)

    if not test_run:
        print(".", end='')
        if conf_file_path.is_file():
            git_add_file(conf_file_path)

        print(".", end='')
        cleanup_feed_directory(entry_path)

        print(".", end='')
        print("")


def git_commit(new_url: str) -> None:
    """Commit changes to git."""
    git_cmd = f"git commit -m 'modify site url to {new_url}'"
    _, error = Process.exec_cmd(git_cmd)
    if error:
        LOGGER.error("can't execute a command '%s', %r", git_cmd, error)


def update_domain(test_run: bool, new_number: int) -> bool:
    """Update domain numbers in site configuration and feed configurations."""
    print("--- updating domain ---")

    # Update site config file
    print("- site_config.json")
    site_config_path = Path.cwd() / SITE_CONFIG_FILE

    # Load and validate site config
    site_config = load_site_config(site_config_path)
    url, referer = validate_site_config(site_config)

    # Update URLs
    if test_run:
        m = re.search(URL_PATTERN, url)
        if m:
            print(m.group("pre"))
            print(str(new_number))
            print(m.group("post"))

    new_url = update_url_pattern(url, new_number)
    new_referer = update_url_pattern(referer, new_number) if referer else ""

    # Update site config
    site_config["url"] = new_url
    if new_referer:
        site_config["referer"] = new_referer

    # Save site config
    save_site_config(site_config, site_config_path, test_run)

    # Git add site config
    if not test_run:
        git_add_file(site_config_path)

    # Update feed configurations
    for entry_path in Path.cwd().iterdir():
        if not entry_path.is_dir() or entry_path.name.startswith("."):
            continue

        process_feed_directory(entry_path, new_number, test_run)

        if test_run:
            break  # Only process first feed in test mode

    # Git commit
    if not test_run:
        print("- git commit")
        git_commit(new_url)

    return True


def check_site() -> bool:
    """Check site functionality."""
    print("--- checking site ---")
    cmd = "check_manga_site.py"
    result, error = Process.exec_cmd(cmd)
    if result:
        print(result)
    else:
        print(error)
    return True


def main() -> int:
    """Main function."""
    test_run = False
    optlist, args = getopt.getopt(sys.argv[1:], "t")
    for o, _ in optlist:
        if o == "-t":
            test_run = True

    if len(args) < 1:
        print_usage()
        return -1

    new_number = int(args[0])
    if update_domain(test_run, new_number) and not test_run:
        check_site()

    return 0


if __name__ == "__main__":
    sys.exit(main())
