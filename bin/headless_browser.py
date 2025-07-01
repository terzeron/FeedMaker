#!/usr/bin/env python


import json
import logging.config
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from shutil import which
import urllib3

from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import selenium

from bin.feed_maker_util import PathUtil

logging.config.fileConfig(Path(__file__).parent.parent / "logging.conf")
LOGGER = logging.getLogger()

if TYPE_CHECKING:
    from _typeshed import SupportsWrite


class HeadlessBrowser:
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS = "rendering_completed_in_converting_canvas"
    ID_OF_RENDERING_COMPLETION_IN_SCROLLING = "rendering_completed_in_scrolling"
    ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB = "rendering_completed_in_converting_blob"
    COOKIE_FILE = "cookies.headlessbrowser.json"
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    
    # Class-level driver cache for reuse in tests
    _driver_cache: Optional[webdriver.Chrome] = None
    _driver_options_hash: Optional[str] = None
    
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
        
        // Wait for initial page load
        await sleep(1000);
        
        // Scroll down
        var bottom = document.body.scrollHeight;
        for (var i = 0; i < bottom; i += 349) {
            window.scrollTo(0, i);
            await sleep(200);
            bottom = document.body.scrollHeight;
        }
        
        // Scroll up
        for (var i = bottom; i >= 0; i -= 683) {
            window.scrollTo(0, i);
            await sleep(200);
        }
        
        // Wait for images to load and JavaScript to execute
        // Check for the completion marker that the page's JavaScript creates
        var maxWaitTime = 10000; // 10 seconds
        var startTime = Date.now();
        while (Date.now() - startTime < maxWaitTime) {
            // Check if the page's JavaScript has added the completion marker
            var completionMarker = document.getElementById("rendering_completed_in_scrolling");
            if (completionMarker) {
                break;
            }
            await sleep(500);
        }
        
        // Additional wait for any final JavaScript execution
        await sleep(1000);
        
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

    def __init__(self, *, dir_path: Path = Path.cwd(), headers: Optional[dict[str, str]] = None, copy_images_from_canvas: bool = False, simulate_scrolling: bool = False, disable_headless: bool = False, blob_to_dataurl: bool = False, timeout: int = 60) -> None:
        LOGGER.debug("# HeadlessBrowser(dir_path=%s, headers=%r, copy_images_from_canvas=%s, simulate_scrolling=%s, disable_headless=%s, blob_to_dataurl=%s, timeout=%d)", PathUtil.short_path(dir_path), headers, copy_images_from_canvas, simulate_scrolling, disable_headless, blob_to_dataurl, timeout)
        self.dir_path: Path = dir_path
        self.headers: dict[str, str] = headers if headers is not None else {}
        if "User-Agent" not in self.headers:
            self.headers["User-Agent"] = HeadlessBrowser.DEFAULT_USER_AGENT
        self.copy_images_from_canvas: bool = copy_images_from_canvas
        self.simulate_scrolling: bool = simulate_scrolling
        self.disable_headless: bool = disable_headless
        self.blob_to_dataurl: bool = blob_to_dataurl
        self.timeout: int = timeout

    def __del__(self) -> None:
        del self.headers

    @classmethod
    def _get_options_hash(cls, options: Options) -> str:
        """Generate a hash for driver options to check if driver can be reused"""
        import hashlib
        # Create a string representation of the key options
        options_str = f"{options.arguments}"
        return hashlib.md5(options_str.encode()).hexdigest()

    @classmethod
    def _get_cached_driver(cls, options: Options) -> Optional[webdriver.Chrome]:
        """Get cached driver if available and compatible"""
        if cls._driver_cache is None:
            return None
        
        current_hash = cls._get_options_hash(options)
        if cls._driver_options_hash != current_hash:
            # Options changed, need new driver
            cls._cleanup_cached_driver()
            return None
        
        # Check if driver is still alive
        try:
            cls._driver_cache.current_url  # Test if driver is responsive
            return cls._driver_cache
        except Exception:
            cls._cleanup_cached_driver()
            return None

    @classmethod
    def _set_cached_driver(cls, driver: webdriver.Chrome, options: Options) -> None:
        """Cache the driver for reuse"""
        cls._driver_cache = driver
        cls._driver_options_hash = cls._get_options_hash(options)

    @classmethod
    def _cleanup_cached_driver(cls) -> None:
        """Clean up cached driver"""
        if cls._driver_cache:
            try:
                cls._driver_cache.quit()
            except Exception:
                pass
            cls._driver_cache = None
            cls._driver_options_hash = None

    @classmethod
    def cleanup_all_drivers(cls) -> None:
        """Clean up all cached drivers (for use in tearDown)"""
        cls._cleanup_cached_driver()

    def _write_cookies_to_file(self, driver: webdriver.Chrome) -> None:
        cookies = driver.get_cookies()
        cookie_file = self.dir_path / HeadlessBrowser.COOKIE_FILE
        with cookie_file.open("w", encoding='utf-8') as f:  # type: SupportsWrite[str]
            json.dump(cookies, f, indent=2, ensure_ascii=False)

    def _read_cookies_from_file(self, driver: webdriver.Chrome) -> None:
        cookie_file = self.dir_path / HeadlessBrowser.COOKIE_FILE
        if cookie_file.is_file():
            try:
                with cookie_file.open("r", encoding='utf-8') as f:
                    cookies = json.load(f)
                    for cookie in cookies:
                        if "expiry" in cookie:
                            del cookie["expiry"]
                        driver.add_cookie(cookie)
            except InvalidCookieDomainException:
                cookie_file.unlink(missing_ok=True)
                self._read_cookies_from_file(driver)

    def make_request(self, url: str, download_file: Optional[Path] = None) -> str:
        LOGGER.debug(f"# make_request(url={url}, download_file={download_file})")
        driver = None
        driver_created = False
        
        try:
            options = Options()
            if not self.disable_headless:
                options.add_argument("--headless")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            options.add_argument("--disable-gpu")
            options.add_argument("--lang=ko_KR")
            options.add_argument(f"--user-agent={self.headers['User-Agent']}")
            # Add stability options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")

            # Try to reuse cached driver first
            driver = self._get_cached_driver(options)
            if driver is None:
                LOGGER.debug("Creating new Chrome driver")
                chrome_driver_path = which("chromedriver")
                if not chrome_driver_path:
                    raise FileNotFoundError("chromedriver not found in PATH")
                service = Service(executable_path=chrome_driver_path)
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(self.timeout)
                self._set_cached_driver(driver, options)
                driver_created = True
            else:
                LOGGER.debug("Reusing cached Chrome driver")
                # Reset timeout for cached driver
                driver.set_page_load_timeout(self.timeout)

            referer = self.headers.get("Referer", "")
            if referer:
                LOGGER.debug(f"visiting referer page '{referer}'")
                driver.get(referer)
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
                LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
                LOGGER.warning("<!-- %r -->", e)
                return ""
            except urllib3.exceptions.NewConnectionError as e:
                LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
                LOGGER.warning("<!-- %r -->", e)
                return ""
            except selenium.common.exceptions.TimeoutException as e:
                LOGGER.warning(f"<!-- Warning: can't can't read data from '{url}' for timeout -->")
                LOGGER.warning("<!-- %r -->", e)
                return ""
            except selenium.common.exceptions.WebDriverException as e:
                LOGGER.warning(f"<!-- Warning: can't connect to '{url}' for temporary network error -->")
                LOGGER.warning("<!-- %r -->", e)
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
                    LOGGER.warning("Scrolling script timed out, continuing...")

            if self.blob_to_dataurl:
                LOGGER.debug("converting blob to dataurl")
                driver.execute_script(HeadlessBrowser.CONVERTING_BLOB_TO_DATAURL_SCRIPT)

            # Wait for completion markers with better error handling
            for option, waiting_div_id in ((self.copy_images_from_canvas, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_CANVAS), (self.simulate_scrolling, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_SCROLLING), (self.blob_to_dataurl, HeadlessBrowser.ID_OF_RENDERING_COMPLETION_IN_CONVERTING_BLOB)):
                if option:
                    try:
                        WebDriverWait(driver, self.timeout).until(
                            expected_conditions.presence_of_element_located((By.ID, waiting_div_id)))
                        LOGGER.debug(f"Found completion marker: {waiting_div_id}")
                    except selenium.common.exceptions.TimeoutException:
                        LOGGER.warning(f"Timeout waiting for completion marker: {waiting_div_id}")

            LOGGER.debug("getting inner html")
            try:
                response = driver.page_source
            except selenium.common.exceptions.WebDriverException as e:
                LOGGER.error("Error: %s", str(e))
                response = ""

            return response

        except RuntimeError as e:
            LOGGER.error(f"Unexpected error in make_request: {e}")
            return ""
        finally:
            # Only close driver if it was newly created or if there was an error
            if driver and driver_created and driver != self._driver_cache:
                try:
                    LOGGER.debug("Closing newly created driver")
                    driver.close()
                    driver.quit()
                except RuntimeError as e:
                    LOGGER.warning(f"Error closing driver: {e}")
            elif driver and driver == self._driver_cache:
                # For cached driver, just clear any alerts and reset state
                try:
                    # Clear any alerts
                    driver.switch_to.alert.dismiss()
                except Exception:
                    pass  # No alert present
                
                # Clear local storage and cookies for clean state
                try:
                    driver.execute_script("window.localStorage.clear();")
                    driver.execute_script("window.sessionStorage.clear();")
                except Exception:
                    pass  # Might fail if no page loaded
