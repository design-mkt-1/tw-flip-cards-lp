# tw-flip-cards-lp

The Top Win flip-the-cards landing page, built on
[`tw-lp-template`](https://github.com/design-mkt-1/tw-lp-template).

Nine cards, face down, on a hero artboard. Every card the visitor turns is the
top prize; the third one opens the registration card. Static: no build step, no
runtime dependencies, no third-party request.

## What is the template's, and what is this repo's

Everything in `css/`, `js/`, `tools/` and `.github/` came from the template and
must not be edited here — `python tools/drift.py` fails if one of them changes.
A fix that belongs to every campaign is made in the template repo and pulled
down; that is how `ul, ol { list-style: none }` reached `css/reset.css` in
v1.0.1, after this landing's grid drew a marker beside all nine cards.

This campaign is four files:

| file | what it is |
|---|---|
| `campaign.js` | the offer, the deck's losing tiers, the seams, the copy in three languages |
| `campaign/main.js` | the game: build, flip, promote, reveal, then `TW.openForm()` |
| `campaign/main.css` | the artboard, the hero, the headline, the grid and the card |
| `campaign/smoke.py` | the mechanic's own browser check |
| `index.html` | the `<main>` block, the hero `<picture>` and the `css/stage.css` link |

## What the retrofit changed, beyond the shell

- **One HTML file, not three.** `ru.html` and `en.html` are gone, and with them
  the CI job that kept their tag sequences identical. Language is a runtime
  switch in `js/i18n.js` and a menu in the header, so adding a fourth language
  is a table in `campaign.js` rather than a fourth file.
- **The four dead links are gone by construction.** `js/shell.js` sets an
  `href` when `campaign.js § links` has one and removes the attribute when it
  does not — never `"#"`. `tools/smoke.py` fails the build on a `href="#"`.
- **`raw/` is untracked.** It was 30 files and 4.2 MB in a public repo,
  including seven Google Fonts sources. It is in `.gitignore` now. The blobs
  remain reachable in the history of `main` until that history is rewritten —
  a separate, deliberate operation.
- **The hero's logo plate is gone.** `css/shell.css` puts the mark in the
  header bar, and two logos on one screen is not the design honoured, it is
  the design doubled.
- **The prize figures come from the offer.** `campaign.js § offer` fills the
  three winning cards and the dialog's offer line from the same two numbers.
  The losing tiers sit in `campaign.js § deck` — deliberately in that file,
  because `tools/fonts.py` reads only `js/strings.js`, `campaign.js` and
  `index.html`, and a prize string kept anywhere else is text no glyph check
  has seen. That is exactly how ₴ once shipped in a font that has no hryvnia.

## Before it goes live

`campaign.js § links` is empty. `terms` and `privacy` block go-live: the card
collects an 18+ consent, and dead consent links on a gambling registration form
are a compliance problem. `form.endpoint` is empty too, so a submitted form
logs its payload and walks the confirmation screen — demoable before the
platform exists, and unable to silently half-ship.

## Running it

```bash
python -m pip install fonttools brotli playwright
python -m playwright install chromium

python tools/drift.py            # the shared files are the template's
python tools/tokens.py --check   # no colour literal outside css/tokens.css
python tools/fonts.py --check    # every rendered character exists in a face, ₴ included
python tools/smoke.py            # 2 viewports x 3 languages, plus campaign/smoke.py
python -m http.server 8000
```

**Repository → Settings → Pages → Source: GitHub Actions.**
