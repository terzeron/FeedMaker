#!/usr/bin/env python
"""Stop Playwright's Firefox driver from sending `legacyInterceptor` to camoufox.

Playwright 1.65's bundled Node driver (coreBundle.js) always adds
`downloadOptions.legacyInterceptor` to `Browser.setDownloadOptions` when it
creates a Firefox context. camoufox's Juggler protocol schema (checked up to
v159.0-beta.42) does not describe that property, so every `new_page` fails:

  Found property "<root>.downloadOptions.legacyInterceptor" - false which is
  not described in this scheme

The camoufox engine then returns empty and the crawler falls back to
cloakbrowser. This runs in the driver's own JS, so our Python code cannot work
around it. The patch sends the property only when
PLAYWRIGHT_FIREFOX_LEGACY_DOWNLOADS is set, so default behavior is unchanged
for Playwright's own Firefox (the property defaults to false).

Re-run this after any `pip install` that reinstalls the driver. Idempotent:
only the pristine form matches, so re-running is a no-op once patched.
"""

import re
import sys
from pathlib import Path

LEGACY_RE = re.compile(r"legacyInterceptor:\s*!!process\.env\.PLAYWRIGHT_FIREFOX_LEGACY_DOWNLOADS")
REPLACEMENT = "...(process.env.PLAYWRIGHT_FIREFOX_LEGACY_DOWNLOADS ? { legacyInterceptor: true } : {})"
BACKUP_SUFFIX = ".orig-downloadoptions"


def find_bundles() -> list[Path]:
    root = Path.home() / "workspace"
    return sorted(root.glob("*/.venv/lib/python*/site-packages/playwright/driver/package/lib/coreBundle.js"))


def patch_file(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    new_text, count = LEGACY_RE.subn(REPLACEMENT, text)
    if count == 0:
        return 0
    backup = path.with_suffix(path.suffix + BACKUP_SUFFIX)
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
        print(f"{'patched' if n else 'already patched or not applicable'} ({n}): {path}")
    print(f"total occurrences patched: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
