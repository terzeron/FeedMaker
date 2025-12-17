#!/usr/bin/env python3
import importlib
import sys

REQUIRED = ["pytest", "pytest_cov", "coverage"]

for name in REQUIRED:
    try:
        importlib.import_module(name)
    except Exception:
        sys.exit(1)

sys.exit(0)

