#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `selenium`.

Purpose
-------
Pin the selenium surface used by bin/headless_browser.py. selenium 4.x
restructured many namespaces (`webdriver.chrome.options.Options` →
`webdriver.ChromeOptions`, `desired_capabilities` removal, `find_element`
signature change). A future 4.x → 5.x bump could move things again.

These tests don't launch a real Chrome -- launching a browser in CI is
flaky and slow. They pin: (a) every import name production reaches for,
(b) class/symbol identity of constants used in selectors and conditions,
(c) constructor + ChromeOptions API.

Reference call sites (production code):
    bin/headless_browser.py:19-23  imports
    bin/headless_browser.py:335    options = webdriver.ChromeOptions()
    bin/headless_browser.py:337    options.add_argument("--headless")
    bin/headless_browser.py:355    driver = webdriver.Chrome(options=options)
    bin/headless_browser.py:370    expected_conditions.presence_of_element_located((By.NAME, ...))
    bin/headless_browser.py:378    driver.find_element(By.NAME, password_field)
    bin/headless_browser.py:392    from selenium.webdriver.common.keys import Keys
"""

import inspect
import unittest

from selenium import webdriver
from selenium.common.exceptions import InvalidCookieDomainException, NoAlertPresentException, SessionNotCreatedException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait


# -----------------------------------------------------------------------------
# 1. Import-time symbol surface
# -----------------------------------------------------------------------------


class SeleniumImportSurfaceTest(unittest.TestCase):
    """Every name headless_browser.py:19-23 reaches for must remain."""

    def test_webdriver_module_exposes_chrome_and_chrome_options(self) -> None:
        self.assertTrue(hasattr(webdriver, "Chrome"))
        self.assertTrue(hasattr(webdriver, "ChromeOptions"))

    def test_all_five_exception_classes_are_exception_subclasses(self) -> None:
        for cls in (InvalidCookieDomainException, SessionNotCreatedException, TimeoutException, WebDriverException, NoAlertPresentException):
            self.assertTrue(isinstance(cls, type))
            self.assertTrue(issubclass(cls, Exception), f"{cls.__name__} must be an Exception")

    def test_by_locator_constants_are_strings(self) -> None:
        # headless_browser.py uses By.NAME, By.CSS_SELECTOR, By.ID -- these are
        # passed positionally to find_element(...) which expects str values.
        for name in ("NAME", "CSS_SELECTOR", "ID", "TAG_NAME", "XPATH"):
            self.assertTrue(hasattr(By, name), f"By.{name} missing")
            self.assertIsInstance(getattr(By, name), str)

    def test_keys_module_exposes_named_keys(self) -> None:
        # bin/headless_browser.py:392 -- from selenium.webdriver.common.keys import Keys
        # Production submits forms by sending RETURN or TAB; pin those.
        for name in ("RETURN", "ENTER", "TAB"):
            self.assertTrue(hasattr(Keys, name), f"Keys.{name} missing")

    def test_expected_conditions_exposes_callables_production_uses(self) -> None:
        # headless_browser.py:370 / 469 / 500 / 536
        for name in ("presence_of_element_located", "invisibility_of_element_located"):
            self.assertTrue(hasattr(expected_conditions, name))
            self.assertTrue(callable(getattr(expected_conditions, name)))


# -----------------------------------------------------------------------------
# 2. ChromeOptions surface
# -----------------------------------------------------------------------------


class ChromeOptionsCallShapeTest(unittest.TestCase):
    """Pin ChromeOptions().add_argument() and .arguments used in production."""

    def test_chrome_options_can_be_instantiated(self) -> None:
        opts = webdriver.ChromeOptions()
        self.assertTrue(hasattr(opts, "add_argument"))

    def test_add_argument_then_arguments_attribute(self) -> None:
        # headless_browser.py:337-347 -- many .add_argument() calls
        # headless_browser.py:259    -- f"{options.arguments}" is hashed
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless")
        opts.add_argument("--window-size=1920,1080")
        args = opts.arguments
        # `.arguments` returns a list-like of strings.
        self.assertIn("--headless", args)
        self.assertIn("--window-size=1920,1080", args)


# -----------------------------------------------------------------------------
# 3. webdriver.Chrome(options=...) constructor accepts the kwarg
# -----------------------------------------------------------------------------


class ChromeDriverConstructorTest(unittest.TestCase):
    """Pin webdriver.Chrome(options=...) kwarg name (was `chrome_options=` before 4.x)."""

    def test_chrome_constructor_accepts_options_kwarg(self) -> None:
        sig = inspect.signature(webdriver.Chrome.__init__)
        self.assertIn("options", sig.parameters)


# -----------------------------------------------------------------------------
# 4. find_element(by, value) signature
# -----------------------------------------------------------------------------


class FindElementCallShapeTest(unittest.TestCase):
    """Pin find_element(by, value) -- the 4.x form selenium production uses."""

    def test_find_element_takes_two_positional_args(self) -> None:
        # headless_browser.py:378 -- driver.find_element(By.NAME, password_field)
        # Pre-4.x had find_element_by_name(value) instead; we depend on the
        # 4.x unified API.
        from selenium.webdriver.remote.webdriver import WebDriver

        sig = inspect.signature(WebDriver.find_element)
        params = [p for p in sig.parameters if p != "self"]
        # Must accept (by, value) at minimum.
        self.assertGreaterEqual(len(params), 2)
        self.assertEqual(params[0], "by")
        self.assertEqual(params[1], "value")


# -----------------------------------------------------------------------------
# 5. WebDriverWait(driver, timeout) constructor + .until(cond)
# -----------------------------------------------------------------------------


class WebDriverWaitCallShapeTest(unittest.TestCase):
    """Pin WebDriverWait(driver, timeout).until(cond) used in headless_browser.py."""

    def test_constructor_accepts_two_positional_args(self) -> None:
        sig = inspect.signature(WebDriverWait.__init__)
        params = [p for p in sig.parameters if p != "self"]
        self.assertGreaterEqual(len(params), 2)
        self.assertEqual(params[0], "driver")
        self.assertIn("timeout", params)

    def test_wait_has_until_method(self) -> None:
        # Production: wait.until(expected_conditions.presence_of_element_located(...))
        self.assertTrue(callable(WebDriverWait.until))


# -----------------------------------------------------------------------------
# 6. expected_conditions factories return callables that take a driver
# -----------------------------------------------------------------------------


class ExpectedConditionsCallShapeTest(unittest.TestCase):
    """Pin: ec.presence_of_element_located((By, value)) returns a callable."""

    def test_presence_of_element_located_accepts_locator_tuple(self) -> None:
        cond = expected_conditions.presence_of_element_located((By.NAME, "username"))
        self.assertTrue(callable(cond))

    def test_invisibility_of_element_located_accepts_locator_tuple(self) -> None:
        cond = expected_conditions.invisibility_of_element_located((By.ID, "cf-content"))
        self.assertTrue(callable(cond))


if __name__ == "__main__":
    unittest.main()
