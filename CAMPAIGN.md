# Starting a new campaign

Eight steps. Nothing here is optional except step 6.

---

## 0. Clone the template — do not build from scratch

```bash
gh repo create design-mkt-1/tw-<campaign> --template design-mkt-1/tw-lp-template --private --clone
cd tw-<campaign>
```

No `gh`? Use **Use this template** on the repo page on GitHub, then clone.

Confirm you are starting clean:

```bash
python -m pip install fonttools brotli playwright
python -m playwright install chromium

python tools/drift.py            # → 14 shared file(s) match SHARED.lock
python tools/smoke.py            # → 2 viewport(s) x 3 language(s), all clean
python -m http.server 8000       # → http://127.0.0.1:8000
```

If `drift.py` fails on a fresh clone, the template itself is broken. Fix it
there, not here.

---

## 1. Read the skill first

`.claude/skills/topwin-lp/SKILL.md` came with the clone. It is the decisions
this repo is the consequence of, and it is shorter than the mistakes it
prevents.

---

## 2. Bound the mechanic before writing it

The mechanic is the one genuinely new decision per campaign. Everything else
is already settled.

Answer six things, in writing, before any code:

1. Does the visitor always win? (A campaign funnel usually says yes — both
   earlier landings decided this independently and identically.)
2. How many interactions before the pop-up opens?
3. What does the reveal show?
4. What happens under `prefers-reduced-motion`?
5. What happens on reload? (Nothing persists. That is deliberate for a
   campaign page.)
6. Which layout mode — scrolling, fixed stage, or artboard?

Get that approved. Then write it down in `docs/BRIEF.md`.

---

## 3. Fill in `campaign.js`, top to bottom

It is the only config file. Every key is commented in place.

- `id` — the repo name. Rides on the payload as `landing_id` and on every event.
- `offer` — **numbers only**. `percent`, `amount`, `currency`, `spins`, `code`.
  The words around them live in `strings`, once per locale, and interpolate
  `{percent} {amount} {currency} {spins}`. Changing 225% / 15000 to
  300% / 20000 is a two-value edit here and no language table is touched.
- `links` — `home`, `login`, `terms`, `privacy`, `cta`. **`terms` and
  `privacy` block go-live.** An empty string leaves the anchor with no `href`
  at all, which is the honest state of an unfilled seam; never write `"#"`.
- `params` — the campaign's UTM block, appended to every link and copied into
  the form payload.
- `passthrough` — query parameters on the landing URL that ride through to the
  outbound click. This is how an affiliate click id survives the page.
- `analytics` — leave empty unless someone named a vendor. Empty means zero
  third-party requests.
- `form.hiddenFields` — anything the platform wants on the payload.
- `header.mute` — `false` unless your mechanic has audio. A dead speaker in the
  bar is worse than no speaker.
- `strings` — only the keys this campaign owns. Anything the header, footer or
  dialog says is already in `js/strings.js` and must not be copied here.

---

## 4. Pick the layout mode

| mode | what you do |
|---|---|
| **scrolling page** — hero, sections, footer | nothing |
| **fixed stage** — full screen, never scrolls | uncomment `<link rel="stylesheet" href="css/stage.css">` in `index.html` |
| **the fold** — one screen of mechanic, footer below it | uncomment `<link rel="stylesheet" href="css/fold.css">` instead. Never both |
| **artboard unit** — pixel-exact Figma hero | define `--u` in `campaign/main.css` (there is a worked example in its header) |

Write which one, and why, in `docs/BRIEF.md`.

---

## 5. Build the mechanic

Three files and one markup block:

```
campaign/main.js       replace the demo
campaign/main.css      replace the demo styles
campaign/assets/       your art
index.html <main>      your markup, with data-i18n on every string
```

It must end in `TW.openForm()`. Do not reach into the dialog, do not
re-implement it, do not call `showModal()` yourself.

Raw exports go in `raw/img/` — gitignored on purpose — and become shipped
assets with:

```bash
python tools/optimize.py hero.png --widths 375,1280,1920
```

Never ship the Figma PNG.

---

## 6. Only if you set an analytics id

Swap the CSP `<meta>` in `index.html` for the commented analytics one. This is
the single campaign edit that cannot live in `campaign.js`: a meta policy
cannot be written from JavaScript, and a CSP refusal appears only in the
console — the page looks fine and silently sends nothing.

---

## 7. Finish the head

In `index.html`: the `<title>` fallback text, `<meta name="description">`, and
`theme-color` if the campaign's ground colour differs. The default-locale copy
in `<main>` should be the real words, so the right text paints before any
script runs.

---

## 8. The gate

Run all four. Each one prints its own evidence; none of them passes on
assertion.

```bash
python tools/drift.py            # you have not edited shared code
python tools/tokens.py --check   # no colour literal outside css/tokens.css
python tools/fonts.py --check    # run AFTER the final copy, including any ₴
python tools/smoke.py            # a real browser, every viewport, every language
```

Then, by hand, in a browser at 320px and at desktop:

- the pop-up opens when the mechanic completes, Escape closes it, the close
  button is visible and reachable, focus returns where it came from
- errors move focus to the **first** bad field only, and are announced
- every language switches every visible string and survives a reload
- `prefers-reduced-motion`: motion degrades, nothing disappears, press
  feedback survives
- one `<h1>`, no duplicate ids, no positive `tabindex`

Then ship:

```bash
git add -A && git commit -m "campaign: <name>" && git push
```

**Repository → Settings → Pages → Source: GitHub Actions.** Left on a branch,
the legacy builder publishes the entire repository and the `_site` allowlist
never runs. Afterwards, confirm on the live URL that `tools/`, `docs/` and
`raw/` all 404.

---

## What cannot be closed from a desk

Report these as open. Never as passed.

- **iOS Safari and Android Chrome, on the live URL**: rubber-band scrolling,
  the soft keyboard, landscape, `env(safe-area-inset-*)` on a notched device,
  pinch zoom.
- **Windows High Contrast** (`forced-colors`): the active tab still reads as
  selected, the consent tick is visible.

Both earlier landings declared these limits honestly rather than claiming
them. Do the same.

---

## If you need to change a shared file

Change it in `tw-lp-template`, bump `SHARED.lock` there, note it in that
repo's `CHANGELOG.md`, and pull it down. A decision that changes as well as
code edits `.claude/skills/topwin-lp/references/decisions.md` in the same
commit.

Fixing it here instead is precisely how two landings ended up with four
different oranges.
