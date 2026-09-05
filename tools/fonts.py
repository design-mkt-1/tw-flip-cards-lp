#!/usr/bin/env python3
"""Fail if the page can render a character the shipped fonts do not contain.

This exists because of one bug, and the bug is worth the tool.

Roboto has no hryvnia sign. Not at any weight, not at any width, not in any
release -- and the Google Fonts API advertises U+20B4 inside a Roboto subset
whose file does not contain the glyph. Figma cannot draw it either, so the
artboards show a fallback face and are no reference. A landing page shipped
with nine cards priced in ₴, in three languages, and nothing failed: a missing
glyph still renders SOMETHING, from whatever face the system picks.

So the declared `unicode-range` in a stylesheet is not evidence. This reads the
actual cmap out of each woff2 and compares it with every character the page can
actually produce.

Run:
    python -m pip install fonttools brotli
    python tools/fonts.py --check

Scope, stated so nobody looks for the other half: this checks coverage, it does
not rebuild the subsets. The template ships eight finished woff2 and a campaign
almost never needs new ones. If a campaign's copy does reach a character no
shipped face carries, the fix is a new subset cut with pyftsubset, and the
recipes in the two source landings are the reference.
ponytail: check-only; add a rebuild path when a campaign actually needs one.
"""

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

# Everything the page can put on screen: the shell's copy, the campaign's copy
# and whatever is written straight into the HTML.
SOURCES = [ROOT / "js" / "strings.js", ROOT / "campaign.js", ROOT / "index.html"]

# Characters that never reach a glyph: markup, code, and the whitespace and
# control characters no font is asked for.
IGNORE = set(" \t\r\n")


def shipped() -> set:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        print("fonts: fonttools is not installed.\n"
              "  python -m pip install fonttools brotli", file=sys.stderr)
        raise SystemExit(1)

    covered = set()
    files = sorted(FONTS.glob("*.woff2"))
    if not files:
        print(f"fonts: no woff2 in {FONTS}", file=sys.stderr)
        raise SystemExit(1)

    for path in files:
        try:
            font = TTFont(str(path), fontNumber=0, lazy=True)
        except Exception as exc:                       # a corrupt or non-woff2 file
            print(f"fonts: cannot read {path.name}: {exc}", file=sys.stderr)
            raise SystemExit(1)
        for table in font["cmap"].tables:
            covered |= set(table.cmap.keys())
        font.close()

    return covered, files


# Quoted strings only. Everything outside them is JavaScript, CSS or markup --
# identifiers and comments, none of which the visitor ever sees. Comments
# inside the sources are prose in English and would drag half the latin-ext
# range in with them.
STRING = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")
JS_ESCAPE = re.compile(r"\\[nrt\\'\"]")


def rendered() -> dict:
    """character -> the first file and line it appears in, for the report."""
    where = {}
    for path in SOURCES:
        if not path.is_file():
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in STRING.finditer(line):
                text = JS_ESCAPE.sub("", match.group(1) or match.group(2) or "")
                for ch in text:
                    if ch in IGNORE or ord(ch) < 0x20:
                        continue
                    where.setdefault(ch, f"{path.name}:{n}")
    return where


def main() -> int:
    covered, files = shipped()
    used = rendered()

    missing = {ch: at for ch, at in used.items() if ord(ch) not in covered}

    if missing:
        print(f"fonts: {len(missing)} character(s) the shipped faces do not carry\n")
        for ch, at in sorted(missing.items()):
            print(f"  U+{ord(ch):04X}  {ch!r}  first seen at {at}")
        print(
            "\nA missing glyph does not fail loudly -- the browser draws it from\n"
            "whatever face it can find, so the page looks fine and the type is wrong.\n"
            "Either change the copy, or cut a subset that carries these and add its\n"
            "@font-face to css/tokens.css with the matching unicode-range."
        )
        return 1

    print(f"fonts: {len(used)} distinct character(s) in the copy, "
          f"all covered by {len(files)} shipped face(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
