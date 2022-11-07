#!/usr/bin/env python


import os
import json
import logging.config
import urllib3
from pathlib import Path
from typing import Dict, Any
from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import selenium

logging.config.fileConfig(os.environ["FEED_MAKER_HOME_DIR"] + "/bin/logging.conf")
LOGGER = logging.getLogger()


class HeadlessBrowser:
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS = "rendering_completed_in_converting_canvas"
    ID_OF_RENDERING_COMPLETION_IN_SCROLLING = "rendering_completed_in_scrolling"
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB = "rendering_completed_in_converting_blob"
    COOKIE_FILE = "cookies.headlessbrowser.json"
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36"
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
        }
        '''
    CONVERTING_CANVAS_TO_IMAGES_SCRIPT = '''
        (async function () {
            div = document.createElement("DIV");
            div.className = "images_from_canvas";
            var canvas_list = document.getElementsByTagName("canvas");
            for (var i = 0; i < canvas_list.length; i++) {
                img_data = canvas_list[i].toDataURL("image/png");
                img = document.createElement("IMG");
                img.src = img_data;
                div.appendChild(img);
            }
            document.body.appendChild(div);
        }());
        
        var div = document.createElement("DIV");
        document.body.appendChild(div);
        div.id = "%s";
        ''' % ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS
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
            await sleep(200);
        }
        var div = document.createElement("DIV");
        document.body.appendChild(div);
        div.id = "%s";
        ''' % ID_OF_RENDERING_COMPLETION_IN_SCROLLING
    SETTING_PLUGINS_SCRIPT = "Object.defineProperty(navigator, 'plugins', {get: function() {return[1, 2, 3, 4, 5];},});"
    SETTING_LANGUAGES_SCRIPT = "Object.defineProperty(navigator, 'languages', {get: function() {return ['ko-KR', 'ko']}})"
    CONVERTING_BLOB_TO_DATAURL_SCRIPT = '''
        function readFileAsync(file, img) {
            const reader = new FileReader();
            const promise = new Promise((resolve) => {
                reader.onload = ((img) => {
                    return (e) => {
                        resolve([e.target.result, img]);
                    };
                })(img);
                reader.readAsDataURL(file);
            });
            return promise;
        }
        (async function () {
            var images = document.getElementsByTagName("img");
            for (var i = 0; i < images.length; i++) {
                if (images[i] && images[i].src && images[i].src.startsWith("blob:")) {
                    const response = await fetch(images[i].src);
                    const data = await response.arrayBuffer();
                    var returnedBlob = new Blob([data], {type: 'image/png'});
                    await readFileAsync(returnedBlob, images[i]).then(([dataURL, img]) => {
                        if (img && img.src) {
                            img.src = dataURL;
                        }
                    })
                }
            }
            var div = document.createElement("DIV");
            document.body.appendChild(div);
            div.id = "%s";
        }());
        ''' % ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB

    def __init__(self, dir_path: Path = Path.cwd(), headers: Dict[str, Any] = None,
                 copy_images_from_canvas: bool = False, simulate_scrolling: bool = False,
                 disable_headless: bool = False, blob_to_dataurl: bool = False, timeout: int = 60) -> None:
        LOGGER.debug(
            f"# HeadlessBrowser(dir_path={dir_path}, headers={headers}, copy_images_from_canvas={copy_images_from_canvas}, simulate_scrolling={simulate_scrolling}, disable_headless={disable_headless}, blob_to_dataurl={blob_to_dataurl}, timeout={timeout})")
        self.dir_path: Path = dir_path
        self.headers: Dict[str, str] = headers if headers else {}
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = HeadlessBrowser.DEFAULT_USER_AGENT
        self.copy_images_from_canvas: bool = copy_images_from_canvas
        self.simulate_scrolling: bool = simulate_scrolling
        self.disable_headless: bool = disable_headless
        self.blob_to_dataurl: bool = blob_to_dataurl
        self.timeout: int = timeout

    def __del__(self):
        del self.headers

    def _write_cookies_to_file(self, driver) -> None:
        cookies = driver.get_cookies()
        cookie_file = self.dir_path / HeadlessBrowser.COOKIE_FILE
        with open(cookie_file, "w", encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)

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
            except InvalidCookieDomainException:
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
        driver.set_page_load_timeout(self.timeout)

        if "Referer" in self.headers:
            LOGGER.debug(f"visiting referer page '{self.headers['Referer']}'")
            driver.get(self.headers["Referer"])
            # bypass cloudflare test
            try:
                WebDriverWait(driver, self.timeout).until(
                    expected_conditions.invisibility_of_element((By.ID, "cf-content")))
            except selenium.common.exceptions.TimeoutException:
                pass
            self._write_cookies_to_file(driver)

        LOGGER.debug(f"getting the page '{url}'")
        try:
            driver.get(url)
        except urllib3.exceptions.ProtocolError as e:
            LOGGER.warning(f"Warning: can't connect to '{url}' for temporary network error")
            LOGGER.warning(e)
            LOGGER.debug("exiting driver")
            driver.close()
            driver.quit()
            return ""
        except urllib3.exceptions.NewConnectionError as e:
            LOGGER.warning(f"Warning: can't connect to '{url}' for temporary network error")
            LOGGER.warning(e)
            LOGGER.debug("exiting driver")
            driver.close()
            driver.quit()
            return ""
        except selenium.common.exceptions.TimeoutException as e:
            LOGGER.warning(f"Warning: can't can't read data from '{url}' for timeout")
            LOGGER.warning(e)
            LOGGER.debug("exiting driver")
            driver.close()
            driver.quit()
            return ""
        except selenium.common.exceptions.WebDriverException as e:
            LOGGER.warning(f"Warning: can't connect to '{url}' for temporary network error")
            LOGGER.warning(e)
            LOGGER.debug("exiting driver")
            driver.close()
            driver.quit()
            return ""

        # bypass cloudflare test
        try:
            WebDriverWait(driver, self.timeout).until(
                expected_conditions.invisibility_of_element((By.ID, "cf-content")))
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

        if self.blob_to_dataurl:
            LOGGER.debug("converting blob to dataurl")
            driver.execute_script(HeadlessBrowser.CONVERTING_BLOB_TO_DATAURL_SCRIPT)

        for option, waiting_div_id in [
            (self.copy_images_from_canvas, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS),
            (self.simulate_scrolling, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING),
            (self.blob_to_dataurl, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB)]:
            if option:
                try:
                    WebDriverWait(driver, self.timeout).until(
                        expected_conditions.presence_of_element_located((By.ID, waiting_div_id)))
                except selenium.common.exceptions.TimeoutException:
                    pass

        LOGGER.debug("getting inner html")
        try:
            response = ""
            for element in driver.find_elements(By.NAME, "html"):
                response = response + element.get_attribute("innerHTML")
        except selenium.common.exceptions.WebDriverException as e:
            LOGGER.error("Error: %s", str(e))
            response = ""

        LOGGER.debug("exiting driver")
        driver.close()
        driver.quit()
        return response
