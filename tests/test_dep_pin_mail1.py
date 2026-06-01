#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency-pinning test for the external dependency `mail1`.

Purpose
-------
Pin the mail1 surface bin/notification.py relies on for sending email
notifications. notification.py calls `mail1.send(...)` with eight keyword
arguments. A mail1 upgrade that renames any of those kwargs (e.g.
`smtp_host` -> `host`) would silently break notifications, so the
keyword surface is pinned here via signature inspection. The call is not
executed (it would open an SMTP connection).

Reference call sites (production code):
    bin/notification.py:14    import mail1
    bin/notification.py:179   mail1.send(subject=, text=, sender=, recipients=,
                              smtp_host=, smtp_port=, username=, password=)
"""

import inspect
import unittest

import mail1


class Mail1SurfaceTest(unittest.TestCase):
    def test_send_is_callable(self) -> None:
        self.assertTrue(callable(mail1.send))

    def test_send_accepts_every_kwarg_notification_passes(self) -> None:
        # bin/notification.py:179 passes exactly these eight keyword args.
        params = inspect.signature(mail1.send).parameters
        accepts_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        for kw in ("subject", "text", "sender", "recipients", "smtp_host", "smtp_port", "username", "password"):
            self.assertTrue(kw in params or accepts_var_kw, f"mail1.send no longer accepts keyword '{kw}'")


if __name__ == "__main__":
    unittest.main()
