#!/usr/bin/env python


import os
import json
import logging.config
from pathlib import Path
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import selenium

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"


class HeadlessBrowser:
    COOKIE_FILE = "cookies.headlessbrowser.json"
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

    def __init__(self, dir_path: Path = Path.cwd(), headers: Dict[str, Any] = None, copy_images_from_canvas: bool = False, simulate_scrolling: bool = False, disable_headless: bool = False, timeout: int = 60) -> None:
        LOGGER.debug(f"# HeadlessBrowser(dir_path={dir_path}, headers={headers}, copy_images_from_canvas={copy_images_from_canvas}, simulate_scrolling={simulate_scrolling}, disable_headless={disable_headless}, timeout={timeout})")
        self.dir_path: Path = dir_path
        self.headers: Dict[str, str] = headers if headers else { }
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = DEFAULT_USER_AGENT
        self.copy_images_from_canvas: bool = copy_images_from_canvas
        self.simulate_scrolling: bool = simulate_scrolling
        self.disable_headless: bool = disable_headless
        self.timeout: int = timeout

    def __del__(self):
        del self.headers

    def _write_cookies_to_file(self, driver) -> None:
        cookies = driver.get_cookies()
        cookie_file = self.dir_path / HeadlessBrowser.COOKIE_FILE
        with open(cookie_file, "w", encoding='utf-8') as f:
            json.dump(cookies, f)

    def _read_cookies_from_file(self, driver) -> None:
        cookie_file = self.dir_path / HeadlessBrowser.COOKIE_FILE
        if cookie_file.is_file():
            try:
                with open(cookie_file, "r", encoding='utf-8') as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        if "expiry" in cookie:
                            del cookie["expiry"]
                        driver.add_cookie(cookie)
            except selenium.common.exceptions.InvalidCookieDomainException:
                cookie_file.unlink(missing_ok=True)
                self._read_cookies_from_file(driver)

    def make_request(self, url, download_file=None) -> str:
        LOGGER.debug(f"# make_request(url={url}, download_file={download_file})")
        options = Options()
        if not self.disable_headless:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=ko_KR")
        options.add_argument(f"--user-agent={self.headers['User-Agent']}")

        chrome_driver_name = "chromedriver"
        driver = webdriver.Chrome(options=options, executable_path=chrome_driver_name)
        self.driver = driver
        driver.set_page_load_timeout(self.timeout)

        if "Referer" in self.headers:
            LOGGER.debug(f"visiting referer page '{self.headers['Referer']}'")
            driver.get(self.headers["Referer"])
            # bypass cloudflare test
            try:
                WebDriverWait(driver, self.timeout).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
            except selenium.common.exceptions.TimeoutException:
                pass
            self._write_cookies_to_file(driver)

        LOGGER.debug(f"getting the page '{url}'")
        driver.get(url)
        # bypass cloudflare test
        try:
            WebDriverWait(driver, self.timeout).until(expected_conditions.invisibility_of_element((By.ID, "cf-content")))
        except selenium.common.exceptions.TimeoutException:
            pass

        driver.set_script_timeout(self.timeout)
        # pretend to be a real browser
        LOGGER.debug("executing some scripts")
        driver.execute_script(HeadlessBrowser.SETTING_PLUGINS_SCRIPT)
        driver.execute_script(HeadlessBrowser.SETTING_LANGUAGES_SCRIPT)

        self._write_cookies_to_file(driver)

        LOGGER.debug("executing a script for metadata")
        driver.execute_script(HeadlessBrowser.GETTING_METADATA_SCRIPT)

        if self.copy_images_from_canvas:
            LOGGER.debug("converting canvas to images")
            driver.execute_script(HeadlessBrowser.CONVERTING_CANVAS_TO_IMAGES_SCRIPT)

        if self.simulate_scrolling:
            LOGGER.debug("simulating scrolling")
            try:
                driver.execute_script(HeadlessBrowser.SIMULATING_SCROLLING_SCRIPT)
            except selenium.common.exceptions.TimeoutException:
                pass

        LOGGER.debug("getting inner html")
        try:
            content = driver.find_element_by_tag_name("html")
            response = content.get_attribute("innerHTML")
        except selenium.common.exceptions.WebDriverException as e:
            LOGGER.error("Error: %s", str(e))
            response = ""

        LOGGER.debug("exiting driver")
        driver.close()
        driver.quit()
        return response
