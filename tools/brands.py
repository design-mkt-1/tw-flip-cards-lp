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
        for no, line in enumerate(text.splitlines(), 1):
            m = PATTERN.search(line)
            if m:
                hits.append("%s:%d: %s" % (path.relative_to(ROOT).as_posix(), no, m.group(0)))
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
