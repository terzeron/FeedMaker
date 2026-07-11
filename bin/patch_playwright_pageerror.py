#!/usr/bin/env python
"""Guard Playwright's PageError dispatcher against a missing `location`.

Playwright 1.61.0's bundled Node driver (coreBundle.js) reads
`pageError.location.url/.lineNumber/.columnNumber` when dispatching a page's
uncaught error. The Firefox backend (camoufox engine) can emit a pageError
whose `location` is undefined, which breaks the driver *server process* in two
ways, both uncaught exceptions that kill the driver and every browser session
(observed as "Headless browser session is dead"):

  1. `pageError.location.url` -> TypeError (reading 'url' of undefined), and
  2. even with optional chaining, the event's protocol validator requires
     `location.url` to be a string, so `undefined` -> ValidationError.

So optional chaining alone is NOT enough: the fields must also fall back to
valid-typed defaults ("" for url, 0 for line/column). This runs in the driver's
own JS, so it cannot be worked around from our Python code.

Re-run this after any `pip install`/`playwright install` that reinstalls the
driver, since that overwrites the vendored bundle. Idempotent: matches the
pristine form, the (insufficient) optional-chaining-only form, and its own
final form, so re-running is a no-op once fully patched.
"""

import re
import sys
from pathlib import Path

# Match `pageError.location.FIELD`, the optional-chaining-only `pageError.location?.FIELD`,
# and the already-final `(pageError.location?.FIELD ?? DEFAULT)` — collapsing all to the
# final guarded form with a valid-typed default. The `\(*`/`\)*` absorb any surrounding
# parens we added on a prior run so re-applying normalizes to exactly one pair instead of
# nesting another (true idempotency; also self-heals an over-wrapped bundle). In this
# object literal each site is `FIELD: <value>,`, so the only parens adjacent to
# `pageError.location` are ours — the trailing `\)*` stops at the comma/newline.
FIELD_RE = re.compile(r'\(*pageError\.location\??\.(url|lineNumber|columnNumber)(?:\s*\?\?\s*(?:""|0))?\)*')
_DEFAULTS = {"url": '""', "lineNumber": "0", "columnNumber": "0"}


def _guard(match: "re.Match[str]") -> str:
    field = match.group(1)
    return f"(pageError.location?.{field} ?? {_DEFAULTS[field]})"


def find_bundles() -> list[Path]:
    root = Path.home() / "workspace"
    return sorted(root.glob("*/.venv/lib/python*/site-packages/playwright/driver/package/lib/coreBundle.js"))


def patch_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, count = FIELD_RE.subn(_guard, text)
    if new_text == text:
        return 0  # nothing matched, or already fully guarded (subn is idempotent)
    backup = path.with_suffix(path.suffix + ".orig")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    path.write_text(new_text, encoding="utf-8")
    return count


def main() -> int:
    targets = [Path(a) for a in sys.argv[1:]] or find_bundles()
    if not targets:
        print("no coreBundle.js found", file=sys.stderr)
        return 1
    total = 0
    for path in targets:
        if not path.exists():
            print(f"skip (missing): {path}")
            continue
        n = patch_file(path)
        total += n
        print(f"{'patched' if n else 'already guarded'} ({n}): {path}")
    print(f"total occurrences guarded: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
