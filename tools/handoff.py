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
runtime dependency. It talks to YOUR platform's API (section 3) and to Google
reCAPTCHA, and to nothing else. Upload the contents of this archive to any web
server or object store, then do section 3.

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

## 1. campaign.js and config.json are what you touch

`campaign.js` sits at the root of the archive and is one file of commented
settings. `config.json` is the file YOU add next to it (section 3).

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

**These now come from your landing API** (`data.rules`, `data.policy`,
`data.login`), with the page's query string appended. The values in
`campaign.js` are only the fallback for a field the API leaves out.
`terms` and `privacy` still matter: the page collects an 18+ consent, and dead
consent links on a gambling registration form are a compliance problem, not a
cosmetic one.

## 3. The platform connection -- WHAT WE NEED FROM YOU

`js/platform.js` is written against your own reference landing (the zip you
sent), step for step. The form is **email + password only**: the phone tab is
removed because the API is `registration/email`.

How it works:

1. `GET config.landing` on every load (`Content-Type` and `Accept:
   application/json`). `data.active` false -> a "temporarily unavailable" card
   with `support@jack-pot.com`, in UA / RU / EN, and nothing else works.
   Otherwise the Terms / Privacy / Login links come from `rules` / `policy` /
   `login`, and reCAPTCHA v3 loads with `data.recaptcha_key`.
2. Submit: reCAPTCHA token (action `register`), the visitor's IP from
   `api.ipify.org`, then `POST config.email_registration`:

       {{ email, password, landing_id, language, currency, country, promocode,
         receivePromos: true, clientIp, "g-recaptcha-response",
         ...URL params from the whitelist below }}

   `language` is `uk`, `ru` or `en`. The URL params are spread FIRST, so a
   parameter called `email` or `landing_id` cannot overwrite the real field.
3. Success: `response.data.accessToken` is POSTed to `<casino>/api/welcome` as
   `tmpToken`, with `redirect=<casino>/<lang>/<redirect_link>?<page query>`.
   `<casino>` is the host of `data.rules`. The confirmation screen that shows a
   login and a password is never shown.
4. Errors: `{{ errors: [msg] }}`. "already registered" and anything mentioning
   reCAPTCHA get their own translated message; everything else is the generic
   "could not send".

**Development.** On localhost, 127.0.0.1 or `https://land-crm...` it uses
`campaign.js` -> `platform.dev`, which is YOUR `TEMP_CONFIG` copied verbatim
(landing id 8, `api2-land-dev.jack-pot.tech`). Replace or delete it.

**Production.** The page fetches `config.json` from the site root:

    {{ "id": <numeric landing_id>,
      "email_registration": "https://<api host>/api/jp/registration/email",
      "landing": "https://<api host>/api/jp/landing/<id>" }}

**WITHOUT `config.json` THE PAGE IS NOT CONNECTED.** It still looks finished:
the form validates, writes a warning to the browser console and shows the demo
confirmation screen. Check the console on the first deploy.

### What you have to supply or change

1. **`config.json`**, with the real **`landing_id`** for this landing (the
   zip's 8 is your own landing, not ours) and the **production API host**.
2. **CORS** on the landing and registration endpoints for the domain this page
   is served from: a `GET` carrying `Content-Type: application/json` (so a
   preflight) and a JSON `POST`.
3. **The reCAPTCHA v3 key** (`recaptcha_key` in the landing response) must be
   registered for THIS page's domain with Google.
4. **The Content-Security-Policy `<meta>` in `index.html`**, in two places. A
   CSP refusal shows ONLY in the browser console; the visitor sees nothing:
   - add the production API origin to `connect-src` (only your dev host is
     there, marked TEMP);
   - add `form-action 'self' https://<casino domain>` for the `/api/welcome`
     POST. The directive is absent today because that domain comes from the
     API at runtime and could not be written here.
5. **Confirm, because we could not test against the real API:**
   - the registration endpoint accepts `language: "uk"` and `"ru"` (your
     landing sends `en` / `de`);
   - the casino site has `/uk/` and `/ru/` routes for the redirect, and what
     `redirect_link` should be;
   - whether the registration error texts are stable English strings: we match
     "already registered" and "recaptcha" loosely, anything else is generic;
   - that `status.json` in your zip is read by your infrastructure, not by the
     page: nothing here references it.
6. **The reCAPTCHA v3 badge is hidden** (`.grecaptcha-badge` in `css/styles.css`),
   as your landing does it. The `clientIp` from `api.ipify.org` is sent too, as
   your landing does it. Both follow your LP.

The password is in the registration body, so `email_registration` must be your
own TLS endpoint and nowhere else.

---

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

GA, Yandex Metrika and GTM load from the landing API response, as in your
landing: `js/platform.js` injects them, and the CSP `<meta>` in index.html
already names their domains. Invalid IDs are skipped with a console warning.
Known limit: GTM loads whatever tags your container holds, and those may need
more CSP domains. Only the console on the first real test shows which.
`analytics.gtmId` / `analytics.metaPixelId` in campaign.js are still read by
the shared template's `js/shell.js`, so they are a second, separate GTM and
Meta Pixel source. Leave them empty unless you want that.

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
