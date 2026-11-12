#!/usr/bin/env python3
"""Fail if any tracked file names the other brand.

TopWin and IT's other casino brand are two separate projects. The template was
first copied from IT's reference landing, which belonged to that other brand,
and its support address and its dev landing travelled along: on 2026-11-11 the
"unavailable" card of every TopWin landing showed the other brand's support
address, and "Вхід" on localhost led to the other brand's casino. Decision 21
in .claude/skills/topwin-lp/references/decisions.md.

This guard reads every file git tracks (all of them, binary included, .git
excluded) and fails on the other brand's name in any spelling, its domains,
or the name of its dev landing, case-insensitive. The patterns are assembled
from pieces below so that this file does not match itself.

One exception, decision 24 (owner, 2026-11-12): TopWin and the other brand
share one platform and database, and campaign.js `platform.dev` carries IT's
own TEMP_CONFIG. The guard removes exactly three strings from campaign.js
before it looks: the dev host and the two dev URLs listed in ALLOWED_IN_CAMPAIGN.
Nothing else is allowed, there or anywhere: the other brand's support address,
its casino domain, a different path on the dev host, or the dev host in any
other file all still fail.

Run:
    python tools/brands.py            # exit 1 and a file:line list on any hit
"""

import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

# jack + optional separator + pot covers the name in every spelling and both of
# its domains (.cc, .tech, .com); land + 330 is the name of its dev landing.
_NAME = "jack" + r"[-_ .]?" + "pot"
_LANDING = "land" + "330"
PATTERN = re.compile("|".join([_NAME, _LANDING]), re.IGNORECASE)

# The only text the other brand's name may appear in (decision 24), and only in
# campaign.js: the dev host with exactly one of the two dev paths, each up to
# and including the closing quote, so a longer path or another host fails.
# Assembled from pieces for the same reason as the pattern.
_DEV_HOST = "https://api2-land-dev." + "jack" + "-" + "pot" + ".tech"
ALLOWED_IN_CAMPAIGN = [
    _DEV_HOST + "/api/jp/registration/email'",
    _DEV_HOST + "/api/jp/landing/8'",
]
CAMPAIGN = "campaign.js"


def scrub(rel: str, line: str) -> str:
    """The line with the exact allowed dev URLs removed, for campaign.js only."""
    if rel == CAMPAIGN:
        for ok in ALLOWED_IN_CAMPAIGN:
            line = line.replace(ok, "")
    return line


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, check=True,
                             capture_output=True, stdin=subprocess.DEVNULL).stdout
        return [ROOT / p for p in out.decode("utf-8").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        # No git (a downloaded archive): every file under the root but .git.
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.relative_to(ROOT).parts]


def main() -> int:
    hits = []
    files = tracked_files()
    for path in files:
        if not path.is_file():
            continue                      # deleted in the work tree, still in the index
        text = path.read_bytes().decode("utf-8", errors="replace")
        rel = path.relative_to(ROOT).as_posix()
        for no, line in enumerate(text.splitlines(), 1):
            m = PATTERN.search(scrub(rel, line))
            if m:
                hits.append("%s:%d: %s" % (rel, no, m.group(0)))
    if hits:
        print("brands: the other brand is named in %d place(s). TopWin and that brand are\n"
              "separate projects; a value TopWin does not have yet stays empty and is asked\n"
              "from IT (decision 21)." % len(hits))
        for h in hits:
            print("  " + h)
        return 1
    print("brands: %d tracked file(s), none names the other brand" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
