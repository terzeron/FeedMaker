#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Learning test for the external dependency `filelock`.

Purpose
-------
Pin the FileLock / Timeout surface used by bin/run.py. A filelock upgrade
that renames Timeout, changes the timeout kwarg, or breaks the context
manager protocol would silently break the cron-runner's mutual exclusion.

Reference call sites (production code):
    bin/run.py:11   from filelock import FileLock, Timeout
    bin/run.py:54   with FileLock(str(lock_file_path), timeout=5):
    bin/run.py:86   except Timeout:
    bin/run.py:158  with FileLock(str(lock_file_path), timeout=1):
"""

import tempfile
import unittest
from pathlib import Path

from filelock import FileLock, Timeout


# -----------------------------------------------------------------------------
# 1. Import surface
# -----------------------------------------------------------------------------


class FilelockImportSurfaceTest(unittest.TestCase):
    def test_filelock_is_a_class(self) -> None:
        self.assertTrue(isinstance(FileLock, type))

    def test_timeout_is_an_exception_class(self) -> None:
        # run.py:86/161 -- except Timeout
        self.assertTrue(isinstance(Timeout, type))
        self.assertTrue(issubclass(Timeout, Exception))


# -----------------------------------------------------------------------------
# 2. FileLock(path, timeout=N) context manager protocol
# -----------------------------------------------------------------------------


class FileLockContextManagerTest(unittest.TestCase):
    """Pin the `with FileLock(str(path), timeout=N):` shape."""

    def test_filelock_accepts_path_string_and_timeout_kwarg(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            lock_path = str(Path(t) / "run.lock")
            with FileLock(lock_path, timeout=5):
                pass  # acquired and released without raising

    def test_filelock_blocks_when_already_held_until_timeout(self) -> None:
        # run.py uses Timeout to detect "another runner is already executing".
        with tempfile.TemporaryDirectory() as t:
            lock_path = str(Path(t) / "run.lock")
            outer = FileLock(lock_path, timeout=1)
            with outer:
                # Try a second acquire with timeout=0 (immediate fail).
                inner = FileLock(lock_path, timeout=0)
                with self.assertRaises(Timeout):
                    with inner:
                        self.fail("inner lock should not have been acquired")

    def test_filelock_can_be_reacquired_after_release(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            lock_path = str(Path(t) / "run.lock")
            with FileLock(lock_path, timeout=1):
                pass
            # After exit, another caller can acquire immediately.
            with FileLock(lock_path, timeout=1):
                pass


if __name__ == "__main__":
    unittest.main()
