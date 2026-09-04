#!/usr/bin/env python3
"""
Build the woff2 subsets in assets/fonts/ that the page self-hosts.

Run by hand, from the project root:

    python tools/fonts.py           # rebuild assets/fonts/
    python tools/fonts.py --check   # verify coverage only, no network

This is NOT a build step, for the same reason tools/optimize.py is not: the
published site serves assets/fonts/ directly and never runs this.

Needs fontTools with woff2 support:

    python -m pip install --upgrade "fonttools[woff]"


WHY THIS FILE EXISTS
--------------------
The four original woff2 files were downloaded from the Google Fonts CSS API by
hand and committed with no record of the request that produced them. On
2026-09-04 that cost us a bug that shipped to production.

The card copy was redrawn from percentages into hryvnia, so "250.000 %" became
"250.000 UAH". Nobody checked whether the shipped fonts had the hryvnia sign.
They do not -- and neither does Roboto, in any weight, width or release. The
sign fell back to a system font and rendered thin and narrow beside black
italic digits, on all nine cards and in the dialog, on all three languages.

The comment in styles.css that said "cyrillic-ext is not needed" had been true
when it was written and quietly stopped being true. Nothing failed, because a
missing glyph still renders *something*.

So: every subset is now declared here, with the exact characters it must carry,
and --check fails when a character the page renders is not covered. Run it in
CI. It is the guard that would have caught the hryvnia.


ON THE HRYVNIA
--------------
Roboto has no U+20B4. This is not a subsetting choice -- the glyph is absent
from the upstream font. The Google Fonts API even advertises U+20B4 in the
unicode-range it serves for Roboto's cyrillic-ext subset, but the woff2 behind
that range does not contain it. Figma has the same problem: the design file
renders the sign in a fallback face too, so the artboards are not a reference
for what it should look like.

It is taken from Noto Sans Black, chosen by the owner on 2026-09-04 from a
rendered comparison against Fira Sans and Montserrat. Noto is Google's
companion family to Roboto and sits closest: cap height 714/1000 against
Roboto's 1456/2048, a difference of 0.4% that no one can see. Two glyphs, one
per style, about a kilobyte each.
"""

from pathlib import Path
import argparse
import hashlib
import io
import re
import sys
import urllib.request

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "fonts"
OUT = ROOT / "assets" / "fonts"
PAGES = ("index.html", "ru.html", "en.html")

CSS_API = "https://fonts.googleapis.com/css2?family="

# The API hands out woff2 only to a client that looks like it can read woff2.
# With the default urllib agent it answers in truetype and every file doubles.
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# The prize block is the one place that runs upright. Everything else in the
# display family stays italic -- see the note on .fc-prize in styles.css.
#
# keep=None means the Google subset ships verbatim. Those four entries
# reproduce the committed files byte for byte, which is what makes this script
# safe to run: rebuilding does not quietly redraw the page.
FACES = (
    {
        "out": "roboto-var-black-italic-latin.woff2",
        "query": "Roboto:ital,wdth,wght@1,75..100,900",
        "subset": "latin",
        "keep": None,
        "note": "headline, offer block, confirmation title",
    },
    {
        "out": "roboto-var-black-italic-cyrillic.woff2",
        "query": "Roboto:ital,wdth,wght@1,75..100,900",
        "subset": "cyrillic",
        "keep": None,
        "note": "the same, in Ukrainian and Russian",
    },
    {
        "out": "inter-var-latin.woff2",
        "query": "Inter:wght@400..700",
        "subset": "latin",
        "keep": None,
        "note": "body text",
    },
    {
        "out": "inter-var-cyrillic.woff2",
        "query": "Inter:wght@400..700",
        "subset": "cyrillic",
        "keep": None,
        "note": "body text, in Ukrainian and Russian",
    },
    {
        "out": "roboto-var-black-upright-latin.woff2",
        "query": "Roboto:ital,wdth,wght@0,75..100,900",
        "subset": "latin",
        "keep": "0123456789. +FS",
        "note": "the prize lines on a card, which the redesign sets upright",
    },
    {
        "out": "noto-var-black-italic-hryvnia.woff2",
        "query": "Noto+Sans:ital,wdth,wght@1,62.5..100,900",
        "subset": "cyrillic-ext",
        "keep": "\u20b4",
        "note": "the hryvnia sign in the dialog, which stays italic",
    },
    {
        "out": "noto-var-black-upright-hryvnia.woff2",
        "query": "Noto+Sans:ital,wdth,wght@0,62.5..100,900",
        "subset": "cyrillic-ext",
        "keep": "\u20b4",
        "note": "the hryvnia sign on a card, upright with the prize digits",
    },
)

# Which faces have to cover which text. The page picks a face by family and
# style, so a character is only safe when the faces for ITS style carry it --
# checking the family as a whole would have passed the hryvnia bug, because
# the sign was missing from every face at once but nothing said which face was
# supposed to have it.
DISPLAY_CLASSES = (
    "fc-headline__a",
    "fc-headline__b",
    "fc-offer__title",
    "fc-offer__amount",
    "fc-offer__spins",
    "fc-done__title",
)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return r.read()


def source_for(face: dict) -> Path:
    """Download the Google subset this face is cut from, and cache it in raw/."""
    cached = RAW / ("gf-" + re.sub(r"[^A-Za-z0-9]+", "-", face["query"] + "-" + face["subset"]).strip("-") + ".woff2")
    if cached.exists():
        return cached

    css = fetch(CSS_API + face["query"]).decode("utf-8")
    # Each @font-face block is introduced by a /* subset-name */ comment.
    block = re.search(
        r"/\* %s \*/(.*?)(?=/\*|\Z)" % re.escape(face["subset"]), css, re.S
    )
    if not block:
        raise SystemExit(
            "Google Fonts served no %r subset for %s.\n"
            "The API changed its subset names, or the family no longer covers it."
            % (face["subset"], face["query"])
        )
    url = re.search(r"src:\s*url\(([^)]+)\)", block.group(1)).group(1)

    RAW.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(fetch(url))
    return cached


def cut(src: Path, keep: str, dest: Path) -> None:
    """Subset src down to `keep` and write dest as woff2.

    The wdth axis is kept, never pinned. styles.css asks the display family for
    font-stretch 75% on the headline and the offer block and 100% on the prize
    lines, and font-synthesis is none -- a face pinned to one width would be
    used at that width and silently ignore the other.
    """
    font = TTFont(src)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    s = subset.Subsetter(options=opts)
    s.populate(text=keep)
    s.subset(font)
    font.flavor = "woff2"
    font.save(dest)


def kb(n: int) -> str:
    return f"{n / 1024:6.1f} KB"


def build() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    changed = 0
    for face in FACES:
        dest = OUT / face["out"]
        before = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.exists() else None

        src = source_for(face)
        if face["keep"] is None:
            dest.write_bytes(src.read_bytes())
        else:
            cut(src, face["keep"], dest)

        after = hashlib.sha256(dest.read_bytes()).hexdigest()
        mark = "  new" if before is None else ("  CHANGED" if before != after else "")
        if mark:
            changed += 1
        print(f"  {face['out']:<40} {kb(dest.stat().st_size)}{mark}")
        print(f"      {face['note']}")

    total = sum(p.stat().st_size for p in OUT.glob("*.woff2"))
    print(f"\nassets/fonts total: {total / 1024:.1f} KB   ({changed} file(s) written)")
    return 0


# --------------------------------------------------------------------------
# Coverage check. Reads only what is on disk, so CI can run it with no network.
# --------------------------------------------------------------------------


def strip_markup(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    return re.sub(r"<[^>]*>", " ", html)


def page_text() -> tuple:
    """Split every page's text into what the display family renders and the rest."""
    display, body = set(), set()
    for name in PAGES:
        html = (ROOT / name).read_text(encoding="utf-8")
        rest = html
        for cls in DISPLAY_CLASSES:
            for m in re.finditer(
                r'<(\w+)[^>]*class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)</\1>' % re.escape(cls),
                html,
                re.S,
            ):
                text = strip_markup(m.group(2))
                # These elements are text-transform: uppercase, so the face has
                # to carry the uppercased forms, not the ones in the source.
                display |= set(text) | set(text.upper())
                rest = rest.replace(m.group(0), " ")
        body |= set(strip_markup(rest))
    return display, body


def script_text() -> tuple:
    """The prize lines and the messages flip.js writes at runtime."""
    js = (ROOT / "js" / "flip.js").read_text(encoding="utf-8")

    prize = set("+")  # the separator line, a literal in buildCard()
    deck = re.search(r"deck:\s*\[(.*?)\]", js, re.S)
    for pct, fs in re.findall(r"pct:\s*'([^']*)'\s*,\s*fs:\s*'([^']*)'", deck.group(1)):
        prize |= set(pct) | set(fs)
    for label in re.findall(r"fsLabel:\s*'([^']*)'", js):
        prize |= set(label)
    prize |= set("".join(prize).upper())  # .fc-prize is uppercased too

    # Everything else flip.js can put on screen goes through the body family.
    body = set()
    for key in ("cardBack", "cardFront", "cardWin", "progress", "win",
                "err\\w+", "copied", "showPass", "hidePass", "p\\d+k"):
        for s in re.findall(r"\b%s:\s*'([^']*)'" % key, js):
            body |= set(s)
    return prize, body


def covered_by(files: tuple) -> set:
    chars = set()
    for name in files:
        path = OUT / name
        if not path.exists():
            raise SystemExit(f"missing font: {path}")
        chars |= {chr(c) for c in TTFont(path).getBestCmap()}
    return chars


def check() -> int:
    display, body = page_text()
    prize, js_body = script_text()

    groups = (
        (
            "display, upright  (.fc-prize)",
            prize,
            ("roboto-var-black-upright-latin.woff2",
             "noto-var-black-upright-hryvnia.woff2"),
        ),
        (
            "display, italic   (headline, offer, confirmation title)",
            display,
            ("roboto-var-black-italic-latin.woff2",
             "roboto-var-black-italic-cyrillic.woff2",
             "noto-var-black-italic-hryvnia.woff2"),
        ),
        (
            "body              (everything else)",
            body | js_body,
            ("inter-var-latin.woff2", "inter-var-cyrillic.woff2"),
        ),
    )

    failed = False
    for label, needed, files in groups:
        needed = {c for c in needed if c.strip() and ord(c) > 0x20}
        missing = sorted(needed - covered_by(files))
        if missing:
            failed = True
            print("::error::%s cannot render: %s" % (
                label, ", ".join("%r (U+%04X)" % (c, ord(c)) for c in missing)))
            print("         faces checked: %s" % ", ".join(files))
            print("         Add the character to the right entry in tools/fonts.py "
                  "and re-run it.")
        else:
            print("  ok  %-56s %3d characters" % (label, len(needed)))

    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--check", action="store_true",
                    help="verify the shipped fonts cover the page, and stop")
    args = ap.parse_args()

    if args.check:
        return check()

    print("fonts")
    rc = build()
    if rc:
        return rc
    print("\ncoverage")
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
