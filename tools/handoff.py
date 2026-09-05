#!/usr/bin/env python3
"""Zip exactly what a server should serve, plus a note for whoever hosts it.

The deploy allowlist lives in .github/workflows/pages.yml and is the only
statement anywhere of what belongs on a public URL. This script READS that line
rather than restating it: a second copy of the list is a second thing to
forget, and the failure it produces -- tools/, docs/ or raw/ handed to a third
party -- is the one this repo's .gitignore already carries a comment about.

    python tools/handoff.py                 # -> dist/<repo>-<date>.zip
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

# Dev files that live INSIDE a directory the allowlist wants. campaign/ is
# staged because the mechanic is there, and the campaign's own Playwright check
# sits beside it -- served, it is the same mistake as publishing tools/, and it
# arrives through a door that is supposed to be open. .github/workflows/pages.yml
# deletes the same two after its copy.
SKIP_FILES = ("campaign/smoke.py",)
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


README = """# {name} — for whoever hosts this

A static landing page. No build step, no server-side code, no runtime
dependency, and -- with `analytics` unset in `campaign.js` -- not one
third-party request. Upload the contents of this archive to any web server or
object store and open `index.html`.

Everything is referenced with RELATIVE paths, so it runs from the root of a
domain or from a subfolder without an edit.

## 1. The five links

`campaign.js` -> `links`. Each one is a URL or an empty string:

    home     the header logo
    login    "Already have an account? Log in"
    terms    the consent sentence, first link      <- BLOCKS GO-LIVE
    privacy  the consent sentence, second link     <- BLOCKS GO-LIVE
    cta      the "GO TO WEBSITE" button on the confirmation screen

An empty string leaves the anchor with NO href, so it is not a link at all: no
tab stop, nothing announced, nothing to click. **Do not write `"#"`.**

`terms` and `privacy` block go-live because the page collects an 18+ consent.
Dead consent links on a gambling registration form are a compliance problem,
not a cosmetic one.

## 2. The form

`campaign.js` -> `form.endpoint`. Set it and the page POSTs JSON there; leave
it empty and the validated payload goes to the browser console and the
confirmation screen is walked anyway, so the page is fully demoable before the
platform exists.

The payload carries the password, because a registration hook without one is
useless -- which means **`endpoint` must be your own TLS endpoint and nowhere
else**. A response carrying `{{ "login": "...", "password": "..." }}` fills the
confirmation screen. `form.onRegister(payload)` is the escape hatch for
anything more involved; it returns a promise and overrides `endpoint`.

`form.hiddenFields` is copied onto every payload as-is.

## 3. Tracking, and the affiliate click id

`campaign.js` -> `params` is appended to every outbound link and copied into
the form payload.

`campaign.js` -> `passthrough` names query parameters on the LANDING page's own
URL that ride through to the outbound click:

    {passthrough}

That is how an affiliate click id survives the page: the network puts
`?click_id=...` on the landing URL, and the visitor arrives at the operator
with the same id attached. If your redirect drops these, the attribution is
lost here and nowhere else.

`analytics.gtmId` / `analytics.metaPixelId` are empty by default and with both
empty the page makes no third-party request. If you set either, the
Content-Security-Policy `<meta>` in `index.html` has to be swapped for the
commented analytics one directly beneath it -- a meta policy cannot be written
from JavaScript, and a CSP refusal appears only in the console: the page looks
fine and silently sends nothing.

## 4. Languages

`campaign.js` -> `languages`, in header-menu order; the first is the default
and the fallback. `?lang=xx` on the URL overrides it. All the copy is in
`campaign.js` and `js/strings.js`; there is no per-language HTML file.

## 5. Browsers

Floor: Chrome/Edge 105, Safari 16, Firefox 110. Full motion from Chrome/Edge
117, Safari 17.4, Firefox 129. Below the floor the registration pop-up does not
open -- that one is a hard fail, not a degradation.

## 6. What is NOT in this archive

The four guards in `tools/`, the docs and any source art. They are development
files and have no business on a public URL. The repository is the place for
them: {repo}
"""


def campaign_value(key):
    """One value out of campaign.js, read as text. Good enough for a README and
    deliberately not a JS parser."""
    text = (ROOT / "campaign.js").read_text(encoding="utf-8")
    m = re.search(r"^\s*" + key + r":\s*(.+?),?\s*$", text, re.M)
    return m.group(1).strip().strip("',\"") if m else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="dist", help="where to write the zip (default: dist)")
    args = ap.parse_args()

    name = campaign_value("id") or ROOT.name
    stamp = dt.date.today().isoformat()
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}-{stamp}.zip"

    passthrough = campaign_value("passthrough") or "[]"
    readme = README.format(
        name=name,
        repo=f"https://github.com/design-mkt-1/{ROOT.name}",
        passthrough=passthrough,
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
                    if rel in SKIP_FILES or any(d in f.parts for d in SKIP_DIRS):
                        continue
                    z.write(f, rel)
                    staged.append(rel)
        z.writestr("README-IT.md", readme)
        staged.append("README-IT.md")

    # The check. Cheap, and it is the whole reason to have a script rather than
    # a zip command someone types from memory once a quarter.
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    assert "index.html" in names, "handoff: the archive has no index.html"
    leaked = [n for n in names if n.split("/")[0] in NEVER
              or n in SKIP_FILES or any(d in n.split("/") for d in SKIP_DIRS)]
    assert not leaked, "handoff: the archive contains " + ", ".join(leaked)

    size = zip_path.stat().st_size
    print(f"handoff: {zip_path.relative_to(ROOT).as_posix()} "
          f"— {len(names)} file(s), {size / 1024:.0f} kB")
    print("         staged: " + ", ".join(allowlist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
