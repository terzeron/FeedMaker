#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `psutil`.

Purpose
-------
Pin the psutil surface bin/feed_maker_util.py uses to find and terminate
runaway crawler processes. It iterates `psutil.process_iter()`, reads
each process via `proc.as_dict(attrs=["pid", "cmdline"])`, swallows
`psutil.NoSuchProcess` for vanished processes, and calls
`psutil.Process(pid).terminate()`. A psutil upgrade that drops the
`as_dict` attrs contract or relocates NoSuchProcess would break the
kill logic, so the surface is pinned here.

Reference call sites (production code):
    bin/feed_maker_util.py:22    import psutil
    bin/feed_maker_util.py:176   for proc in psutil.process_iter():
    bin/feed_maker_util.py:177   proc.as_dict(attrs=["pid", "cmdline"])
    bin/feed_maker_util.py:178   except psutil.NoSuchProcess:
    bin/feed_maker_util.py:199   psutil.Process(pid).terminate()
"""

import os
import unittest

import psutil


class PsutilSurfaceTest(unittest.TestCase):
    def test_no_such_process_is_an_exception(self) -> None:
        # bin/feed_maker_util.py:178/201 -- except psutil.NoSuchProcess
        self.assertTrue(issubclass(psutil.NoSuchProcess, Exception))

    def test_process_iter_yields_processes(self) -> None:
        # bin/feed_maker_util.py:176 -- for proc in psutil.process_iter()
        procs = list(psutil.process_iter())
        self.assertTrue(procs)
        self.assertTrue(hasattr(procs[0], "as_dict"))

    def test_as_dict_returns_requested_attrs(self) -> None:
        # bin/feed_maker_util.py:177 -- proc.as_dict(attrs=["pid", "cmdline"])
        for proc in psutil.process_iter():
            try:
                info = proc.as_dict(attrs=["pid", "cmdline"])
            except psutil.NoSuchProcess:
                continue
            self.assertIn("pid", info)
            self.assertIn("cmdline", info)
            return
        self.fail("no inspectable process found")

    def test_process_has_terminate_method(self) -> None:
        # bin/feed_maker_util.py:199 -- psutil.Process(pid).terminate()
        # Use the current process; only assert terminate is callable (never call it).
        proc = psutil.Process(os.getpid())
        self.assertTrue(callable(proc.terminate))


if __name__ == "__main__":
    unittest.main()
