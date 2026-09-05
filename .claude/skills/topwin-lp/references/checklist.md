# The pre-ship gate

Evidence, not assertion. Each blocking item names the command and the output
that closes it. Paste the output; do not summarise it.

## BLOCKING

Run from the repo root. The first four are the same four the CI runs, in the
same order, from `.github/workflows/pages.yml`.

```
python -m pip install fonttools brotli playwright
python -m playwright install chromium
```

1. **`python tools/drift.py`** — the 14 shared files match `SHARED.lock`.
   Passes with `drift: 14 shared file(s) match SHARED.lock`. Any `CHANGED` line
   means the clone has forked: move the change into the template, bump
   `SHARED.lock` there, pull it down. Never regenerate the lock in a clone.
2. **`python tools/tokens.py --check`** — no colour literal, no `rgb()`/`hsl()`
   call and no `--orange-N` / `--navy-N` outside `css/tokens.css`. Passes with
   `tokens: N stylesheet(s) clean`. Every offender is printed with its file and
   line.
3. **`python tools/fonts.py --check`** — every character `js/strings.js`,
   `campaign.js` and `index.html` can render exists in a shipped face. Passes
   with `fonts: N distinct character(s) in the copy, all covered by 8 shipped
   face(s)`. Run it **after** the final copy, especially if the copy contains
   `₴`.
4. **`python tools/smoke.py`** — a real browser at 1440×900 and 375×812, once
   per language. Passes with `smoke: 2 viewport(s) x N language(s), all clean`.
   It asserts: both bars mounted with a real box; the page opens at scrollY 0;
   nothing in flow below the footer; the closed dialog computes
   `display: none`; no `[data-i18n]` node rendering as its own key; no
   `href="#"` and no empty `href`; `TW.openForm()` opens and moves focus in;
   the promo block survives a language change; Escape closes; every tap target
   at least 24×24; a clean console.
   Add campaign assertions in `campaign/smoke.py` as `check(page, viewport, lang)`.
5. **The form is wired, or knowingly is not.** `form.endpoint` or
   `form.onRegister` set — or a written statement from the owner that the demo
   console route ships. There is no third state; `tools/smoke.py` allows the
   "not wired to anything" console line precisely so this stays a human
   decision.
6. **`links.terms` and `links.privacy` are non-empty.** The page collects an
   18+ consent. Check the rendered anchors carry an `href`, not just that the
   config has a value.
7. **The repository's Pages source is set to "GitHub Actions".** Settings →
   Pages. Left on a branch the legacy Jekyll builder publishes the whole
   repository and the workflow is still green.
8. **`tools/` 404s on the live URL.** Fetch `https://<site>/tools/drift.py`
   after the first deploy. A 200 means item 7 was not done. Check `raw/` and
   `.gitignore` the same way.

## VISUAL / A11Y — in a browser, at 320px and at desktop

Serve on a deliberately chosen port, not 8000 — an unrelated service holding it
cost two verification passes in a source repo:

```
python -m http.server 8099 --bind 127.0.0.1
```

- At 320px: nothing crosses the card's edge, no horizontal scrollbar anywhere,
  the dialog scrolls and the close button stays in its corner.
- At desktop: the card takes its own 504px geometry, the footer is in its wide
  arrangement.
- Every language switches every visible string and survives a reload; the
  choice persists, `?lang=` does not.
- Keyboard alone: Tab reaches every control; the language listbox takes arrows,
  Home/End, Enter/Space and Escape and hands focus back to its trigger; the
  dialog takes focus on open and returns it to the opener on close.
- Focus is visible on everything focusable. No focus ring on a heading nobody
  clicked.
- Small text against the AA table — nothing at `#00a75c` or `#ff4500` on white,
  nothing at `#737b8c` on white or on `#f3f4f5`.
- Every input at least 16px; every tap target at least 24px, 44px on the
  chrome controls.
- With `prefers-reduced-motion: reduce` forced in devtools: motion degrades,
  press feedback survives, nothing becomes unusable.
- With JavaScript off: the `noscript` line shows rather than a blank page.
- Network panel: zero requests to `googleapis`, `gstatic` or any third party
  with analytics unset. Only the subsets the page needs are downloaded.
- Console: clean apart from the "not wired to anything" line, if the form is
  knowingly unwired.

## CANNOT BE CLOSED FROM A DESK — report as open, never as passed

Both source repos declare these honestly and this template does the same.
Reporting them as passed on the strength of a devtools emulator is the failure
this section exists to prevent.

- **iOS Safari on the live URL.** No rubber-band on vertical drag. No page
  scroll with the soft keyboard open. Landscape. A notched device, for
  `env(safe-area-inset-*)` — those four values read 0 without
  `viewport-fit=cover`, so an emulator proves nothing. Pinch zoom still works;
  it is an accessibility feature and `touch-action: manipulation` deliberately
  leaves it alone.
- **Android Chrome on the live URL.** The same list.
- **Windows High Contrast / `forced-colors`.** The known hazards: a
  colour-filled active tab vanishes and must be redrawn as a border, and the
  consent checkbox is an `appearance: none` control whose tick is a background
  image. Reasoned, not observed.

If you have not run these on a real device, the correct report is "open", with
the device list. Not "should be fine".
