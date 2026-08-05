#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bin.headless_browser import HeadlessBrowserBase


class TestHeadlessBrowserBase(unittest.TestCase):
    """Engine-agnostic behaviour of the shared base class: teardown fallbacks, the
    abstract launcher hook, cookie-jar discarding and the scrolling script's defensive
    paths. Both real engines inherit these, so a regression here breaks both at once."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _make_browser(self, **kwargs):
        with patch("bin.headless_browser.Env") as mock_env:
            mock_env.get.side_effect = lambda k, d="": {"FM_CRAWLER_ALLOW_PRIVATE_IPS": "false", "FM_CRAWLER_ALLOWED_HOSTS": ""}.get(k, d)
            defaults = dict(dir_path=self.tmp, timeout=5)
            defaults.update(kwargs)
            return HeadlessBrowserBase(**defaults)

    def test_close_session_falls_back_to_browser_close(self):
        # A context whose own close() fails (driver already half-dead) must still have its
        # browser process reaped, or the next launch contends with an orphaned browser.
        context = MagicMock()
        context.close.side_effect = RuntimeError("context already gone")
        browser = context.browser

        HeadlessBrowserBase._close_session({"context": context})

        browser.close.assert_called_once()

    def test_close_session_swallows_browser_close_failure(self):
        # Teardown is best-effort: it runs from atexit/SIGTERM handlers where raising
        # would abort the rest of the cleanup.
        context = MagicMock()
        context.close.side_effect = RuntimeError("context already gone")
        context.browser.close.side_effect = RuntimeError("browser already gone")

        HeadlessBrowserBase._close_session({"context": context})

    def test_launch_session_is_abstract(self):
        # The base class carries no launcher; each engine supplies its own.
        browser = self._make_browser()
        with self.assertRaises(NotImplementedError):
            browser._launch_session()

    def test_discard_persisted_cookies_removes_jar_and_is_idempotent(self):
        # Dropping the jar is how a stale/rejected Cloudflare clearance token is prevented
        # from being replayed; it must also tolerate an already-missing file.
        browser = self._make_browser()
        cookie_file = browser._get_cookie_dir() / browser.COOKIE_FILE
        cookie_file.write_text("[]", encoding="utf-8")

        browser._discard_persisted_cookies()
        self.assertFalse(cookie_file.exists())

        browser._discard_persisted_cookies()
        self.assertFalse(cookie_file.exists())

    @patch("bin.headless_browser.time.sleep")
    def test_run_scrolling_script_treats_non_numeric_scroll_height_as_zero(self, _mock_sleep):
        # Some pages return a non-numeric scrollHeight (overridden document.body); that must
        # degrade to "nothing to scroll" instead of raising out of the scrolling stage.
        browser = self._make_browser()
        scripts: list[str] = []

        def evaluate(script, *_args, **_kwargs):
            scripts.append(script)
            return "not-a-number" if "scrollHeight" in script else None

        page = MagicMock()
        page.evaluate.side_effect = evaluate

        browser._run_scrolling_script(page)

        self.assertEqual([s for s in scripts if "window.scrollTo" in s], [])
        # the completion marker is still injected so _wait_for_marker doesn't time out
        self.assertTrue(any("createElement" in s for s in scripts))

    @patch("bin.headless_browser.time.sleep")
    def test_run_scrolling_script_stops_when_scroll_height_becomes_invalid(self, _mock_sleep):
        # scrollHeight can turn unusable mid-scroll (navigation, DOM teardown). The
        # down-scroll loop must break out rather than propagate the conversion error.
        browser = self._make_browser()
        heights: list[int] = []

        def evaluate(script, *_args, **_kwargs):
            if "scrollHeight" in script:
                heights.append(1)
                return 1000 if len(heights) == 1 else "not-a-number"
            return None

        page = MagicMock()
        page.evaluate.side_effect = evaluate

        browser._run_scrolling_script(page)

        scroll_calls = [c for c in page.evaluate.call_args_list if "window.scrollTo" in c.args[0]]
        # one step down (pos 0), then the height probe fails and breaks; one step back up
        self.assertEqual(len(scroll_calls), 2)

    @patch("bin.headless_browser.time.sleep")
    def test_run_scrolling_script_swallows_marker_injection_failure(self, _mock_sleep):
        # The marker injection runs in a finally block; a page that rejects it (closed,
        # navigated away) must not turn the whole make_request into a failure.
        browser = self._make_browser()

        def evaluate(script, *_args, **_kwargs):
            if "scrollHeight" in script:
                return 0
            raise RuntimeError("page is closed")

        page = MagicMock()
        page.evaluate.side_effect = evaluate

        browser._run_scrolling_script(page)


if __name__ == "__main__":
    unittest.main()
