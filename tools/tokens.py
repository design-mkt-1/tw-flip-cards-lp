#!/usr/bin/env python3
"""Fail if a colour literal appears in any stylesheet except css/tokens.css.

This is the smallest guard in the repo and the one that would have caught
every colour divergence in this project's history.

The two landings that came before this template each invented their own
AA-safe orange (#d63a00 and #d93900), their own AA-safe green (#006e3d and
#00874a) and their own muted grey (#5f6673 and #656d7e) -- six values for
three roles. The generation before that shipped three different greens
(#30d158, #3dd629, #3fd62b) in three stylesheets, all meant to be the same
green. Every one of those was a hex literal typed into a file that was not
the token file.

So: colours live in css/tokens.css. Everything else asks for the semantic
layer -- --accent, --accent-on-light, --text-muted, --surface-field, --danger.
Reaching for a ramp step by number (--orange-600) is also refused, for the
same reason: the number stops tracking the brand the moment the brand moves.

Run:
    python tools/tokens.py --check     # exit 1 and list every offender
    python tools/tokens.py             # same thing; --check is for symmetry
                                       # with tools/fonts.py
"""

import re
import sys
from pathlib import Path

# Windows consoles still default to cp1252, and these tools report Ukrainian
# and Russian copy back to the user. Without this the report itself crashes on
# the first Cyrillic character -- which turns a real finding into a traceback.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "css"
ALLOWED = {"tokens.css"}

# A hex colour, or an rgb()/rgba()/hsl()/hsla() call. Written to skip things
# that merely look like one: an id selector (#tw-main), a fragment in a url().
HEX = re.compile(r"(?<![\w#])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FUNC = re.compile(r"\b(?:rgba?|hsla?)\s*\(")

# --orange-600 and friends. The semantic names (--accent, --accent-on-light)
# are what a stylesheet is allowed to say.
RAMP = re.compile(r"--(?:orange|navy)-(?:50|100|200|300|400|500|600|700|800|900|950)\b")

# Comments are prose and quote hexes on purpose -- the whole point of some of
# them is to record what the design said before it was corrected.
COMMENT = re.compile(r"/\*.*?\*/", re.S)


def offenders(path: Path):
    text = path.read_text(encoding="utf-8")
    # Blank out comments but keep the line count, so reported lines are real.
    text = COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)

    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for pattern, what in ((HEX, "hex literal"), (FUNC, "colour function"), (RAMP, "ramp step")):
            for m in pattern.finditer(line):
                out.append((n, what, m.group(0).strip()))
    return out


def main() -> int:
    if not CSS.is_dir():
        print(f"tokens: no {CSS} directory", file=sys.stderr)
        return 1

    found = []
    checked = 0
    for path in sorted(CSS.glob("*.css")):
        if path.name in ALLOWED:
            continue
        checked += 1
        for line, what, text in offenders(path):
            found.append(f"{path.relative_to(ROOT).as_posix()}:{line}: {what} {text}")

    if found:
        print(f"tokens: {len(found)} colour literal(s) outside css/tokens.css\n")
        for row in found:
            print("  " + row)
        print(
            "\nColours belong in css/tokens.css and are reached through the semantic\n"
            "layer (--accent, --accent-on-light, --text-muted, --surface-field,\n"
            "--danger, ...). If the value you need has no token, add one there --\n"
            "with a comment saying where it comes from -- rather than writing it here."
        )
        return 1

    print(f"tokens: {checked} stylesheet(s) clean, no colour literals outside tokens.css")
    return 0


if __name__ == "__main__":
    sys.exit(main())
