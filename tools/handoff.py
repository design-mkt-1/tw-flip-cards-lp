#!/usr/bin/env python3
"""Zip exactly what a server should serve, plus a note for whoever hosts it.

Ported from tw-lp-template, whose registration card this landing now uses.
The idea is the same and is the whole reason this is a script rather than a
zip command someone types once a quarter: the deploy allowlist in
.github/workflows/pages.yml is the only statement anywhere of what belongs on
a public URL, so this READS that line instead of restating it. A second copy
of the list is a second thing to forget, and what it produces -- tools/,
raw/ or the Figma exports handed to a third party -- is the failure this
repo's .gitignore already carries a comment about.

    python tools/handoff.py                 # -> dist/tw-flip-cards-<date>.zip
    python tools/handoff.py --out build     # somewhere else

The zip is what IT uploads: open index.html from any static server, no build
step, no runtime dependency, no third-party request. README-IT.md goes in with
it and says what still has to be wired.
"""

import argparse
import datetime as dt
import re
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"

# Never shipped, whatever the workflow says. A belt for the allowlist's braces:
# if someone ever writes `cp -r . _site/`, this is what still refuses.
NEVER = ("tools", "docs", "raw", ".git", ".github", ".claude")

SKIP_DIRS = ("__pycache__",)


def allowlist():
    """The paths the Pages build stages, read out of the workflow."""
    text = WORKFLOW.read_text(encoding="utf-8")
    m = re.search(r"cp -r (.+?) _site/", text)
    if not m:
        sys.exit(f"handoff: no `cp -r ... _site/` line in {WORKFLOW}")
    names = [n for n in m.group(1).split() if n]
    bad = [n for n in names if n.split("/")[0] in NEVER or n == "."]
    if bad:
        sys.exit("handoff: the workflow stages something that must not ship: "
                 + ", ".join(bad))
    return names


README = """# tw-flip-cards — for whoever hosts this

A static landing page: nine cards face down, the visitor turns three, and the
third one opens the registration card. No build step, no server-side code, no
runtime dependency, and as shipped not one third-party request. Upload the
contents of this archive to any web server or object store.

Everything is referenced with RELATIVE paths, so it runs from the root of a
domain or from a subfolder without an edit.

## 0. One file, three languages

    index.html   Ukrainian, Russian and English

There is one HTML page. The globe in the header opens a language menu; the
page re-renders in place, with no reload and no second URL, and the choice is
remembered in the browser under `localStorage['tw-lang']`.

`index.html?lang=ru` — or `?lang=en`, or `?lang=ua` — forces one language for
that visit. That is what an advertising creative written in one language
should link to. It is deliberately NOT remembered: a link that forces a
language must not overwrite what the visitor picked last time.

Ukrainian is the default and is what the page paints before any script runs,
so it is also what `<title>` and `<meta name="description">` hand to a
crawler or a link preview. If the page has to be INDEXED in Russian or
English, that needs real separate URLs from your routing; the archive carries
no `hreflang` claiming they exist.

**This landing shipped three pre-translated HTML files until 2026-09-07.** If
anything you run — routing, an ad, a QR code — still points at `/ru.html` or
`/en.html`, those two URLs are gone and will answer 404. `?lang=ru` and
`?lang=en` on index.html are the replacements.

## 1. campaign.js is the only file you edit

It sits at the root of the archive and is one file of commented settings.

**The registration card is not this landing's code.** It is shared with the
other Top Win landings — `css/tokens.css`, `css/form.css`, `js/strings.js`,
`js/i18n.js`, `js/form.js`, `js/shell.js` — so that one design cannot become
three drawings of itself. Editing those here means the next landing gets a
different card. `js/flip.js` is the game.

## 2. The five links

`campaign.js` -> `links`. Each is a URL or an empty string:

    home     the logo in the card's header
    login    "Already have an account? Log in", under the button
    terms    the consent sentence, first link      <- BLOCKS GO-LIVE
    privacy  the consent sentence, second link     <- BLOCKS GO-LIVE
    cta      the "GO TO WEBSITE" button on the confirmation screen

An empty string leaves the anchor with NO href, so it is not a link at all:
no tab stop, nothing announced, nothing to click. **Do not write `"#"`** --
that is a control which takes focus, is announced as a link and does nothing,
and it is what these four shipped as until 2026-09-07.

`terms` and `privacy` block go-live because the page collects an 18+ consent.
Dead consent links on a gambling registration form are a compliance problem,
not a cosmetic one.

## 3. The form

`campaign.js` -> `form.endpoint`. Set it and the card POSTs JSON there; a
response carrying `{{ "login": "...", "password": "..." }}` fills the
confirmation screen. `form.onRegister(payload)` is the escape hatch for
anything more involved: it returns a promise and overrides `endpoint`.

The payload:

    {{ method: 'email' | 'phone',
      contact: the one that was filled in,
      email, phone, password, consent,
      lang: 'uk' | 'ru' | 'en',
      bonus: '{bonus}',
      landing_id: '{landing}',
      ...form.hiddenFields, ...params }}

It carries the password, which means **`endpoint` must be your own TLS
endpoint and nowhere else**. `form.hiddenFields` is copied onto every payload
as-is — a CSRF token belongs there.

Leave both empty and NOTHING IS SENT: the validated payload goes to the
browser console and the confirmation screen is walked anyway, so the page is
demoable before the platform exists. It says so in the console, loudly, so it
cannot be mistaken for a working integration.

**There is no `action=` route.** An earlier version of this landing let the
browser submit the form natively. The shared card does not: a native submit
navigates away, and the confirmation screen is the point of the design.

**The Content-Security-Policy `<meta>` in the head of index.html.** The card
posts with `fetch`, which `default-src 'self'` covers — so an endpoint on
ANOTHER origin needs that origin added to `connect-src`. A CSP refusal appears
only in the console: the submit looks like it did nothing.

## 4. Tracking, and the affiliate click id

`campaign.js` -> `params` is appended to every outbound link and copied into
the form payload.

`campaign.js` -> `passthrough` names query parameters on the LANDING page's
own URL that ride through to the outbound click:

    {passthrough}

That is how an affiliate click id survives the page: the network puts
`?click_id=...` on the landing URL and the visitor arrives at the operator
with the same id attached. If your redirect drops these, the attribution is
lost here and nowhere else.

`analytics.gtmId` / `analytics.metaPixelId` are empty and with both empty the
page makes no third-party request at all. Setting either also needs the CSP
`<meta>` in index.html swapped for the analytics one — a meta policy cannot be
written from JavaScript.

## 5. The offer

`campaign.js` -> `offer`, as numbers: `amount`, `currency`, `spins`, and
`code`, which is what the platform is told the visitor was promised. The
words around them are in `strings` in the same file, one entry per language.
Changing 250.000 to 500.000 is one edit and no language table is touched.

The nine cards are separate: `CONFIG.deck` in `js/flip.js` is where the card
faces get their text. If you change the offer, change the deck's top prize
with it — they are meant to promise the same thing.

## 6. Browsers

The hard requirement is `<dialog>` with `showModal()`: Chrome/Edge 79+,
Safari 15.4+, Firefox 98+. Below that the registration card does not open at
all, which is a failure and not a degradation.

Everything else degrades quietly: the card's entry animation needs
`@starting-style` (Chrome 117, Safari 17.4, Firefox 129) and simply appears
without it, and `backdrop-filter` falls back to a flat colour.

These numbers are read off the features the page uses, not measured on
devices. Nobody has run this on a browser at the floor.

## 7. What is NOT in this archive

`tools/`, `docs/` and the Figma exports in `raw/`. They are development files
and have no business on a public URL — the guards, the asset pipeline and the
integration notes live in the repository instead:

    https://github.com/design-mkt-1/tw-flip-cards-lp

The live preview is https://design-mkt-1.github.io/tw-flip-cards-lp/ and is
built from the same allowlist this archive is built from.
"""


def campaign_value(key):
    """One value out of campaign.js, read as text. Good enough for a README and
    deliberately not a JS parser.

    The trailing `// comment` is cut off first: `code` and half the other keys
    carry one, and without this the README told IT the bonus code was
    "250000+250'   // what the platform is told".
    """
    text = (ROOT / "campaign.js").read_text(encoding="utf-8")
    m = re.search(r"^\s*" + key + r":\s*(.+?),?\s*$", text, re.M)
    if not m:
        return ""
    value = re.sub(r"\s*//.*$", "", m.group(1)).strip()
    return value.rstrip(",").strip("'\"")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="dist", help="where to write the zip (default: dist)")
    args = ap.parse_args()

    name = campaign_value("id") or ROOT.name
    stamp = dt.date.today().isoformat()
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}-{stamp}.zip"

    readme = README.format(
        bonus=campaign_value("code"),
        landing=name,
        passthrough=campaign_value("passthrough") or "[]",
    )

    staged = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for entry in allowlist():
            path = ROOT / entry
            if not path.exists():
                print(f"handoff: {entry} is in the workflow but not in the repo", file=sys.stderr)
                continue
            if path.is_file():
                z.write(path, entry)
                staged.append(entry)
            else:
                for f in sorted(path.rglob("*")):
                    if not f.is_file():
                        continue
                    rel = f.relative_to(ROOT).as_posix()
                    if any(d in f.parts for d in SKIP_DIRS):
                        continue
                    z.write(f, rel)
                    staged.append(rel)
        z.writestr("README-IT.md", readme)
        staged.append("README-IT.md")

    # The check. Cheap, and it is the whole reason to have a script.
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    for required in ("index.html", "campaign.js"):
        assert required in names, f"handoff: the archive has no {required}"
    leaked = [n for n in names if n.split("/")[0] in NEVER
              or any(d in n.split("/") for d in SKIP_DIRS)]
    assert not leaked, "handoff: the archive contains " + ", ".join(leaked)

    size = zip_path.stat().st_size
    print(f"handoff: {zip_path.relative_to(ROOT).as_posix()} "
          f"— {len(names)} file(s), {size / 1024:.0f} kB")
    print("         staged: " + ", ".join(allowlist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
