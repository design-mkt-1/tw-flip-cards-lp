# TopWin — Flip the Cards

A static landing page. Plain HTML, one stylesheet, one script. No build step,
no npm, no dependencies of any kind.

Open it with any static server:

```
python -m http.server 8000     # then http://127.0.0.1:8000/
```

Two guards run on every pull request, and both run by hand too. Neither is a
build step — the published site is these files:

```
python tools/fonts.py --check   # every character the page renders is in the fonts
python tools/smoke.py           # the pages, in a real browser (needs Playwright)
```

`smoke.py` serves the project on a loopback port and loads all three pages at
two viewports, asserting what no text check can see: the page opens at the top,
nothing is left in flow below the footer, the closed dialog is `display: none`,
the console is clean. Both guards exist because a bug shipped past everything
else — section 7 for the fonts one, section 10 of `css/styles.css` for this one.

| File         | Language  | `<html lang>` |
|--------------|-----------|---------------|
| `index.html` | Ukrainian | `uk`          |
| `ru.html`    | Russian   | `ru`          |
| `en.html`    | English   | `en`          |

The three files are structurally identical. Only the text differs. Mount them
wherever your routing expects, for example `/ua/`, `/ru/` and `/en/`.

**The game:** nine cards face down, three of them hide the 250.000 ₴ + 250FS
top prize. The visitor flips cards to find those three. When the third one
turns up, the registration form opens, offering the same welcome bonus. The
other six cards run a 50.000 ₴ + 150FS / 25.000 ₴ + 50FS ladder beneath it.

---

## 1. What you need to change

Everything in rows 1 to 3 sits inside one commented block at the top of
`js/flip.js`, between `IT INTEGRATION — START` and `IT INTEGRATION — END`.

| # | What                          | Where                                                                 |
|---|-------------------------------|-----------------------------------------------------------------------|
| 1 | Where the form submits        | `action=` on `<form id="fc-form">` in all 3 HTML files, **or** `CONFIG.onRegister` |
| 2 | Extra values on the submission | `CONFIG.hiddenFields` — affiliate id, campaign, CSRF token             |
| 3 | Terms / Privacy / Login links | `CONFIG.termsUrl`, `CONFIG.privacyUrl`, `CONFIG.loginUrl`              |
| 4 | Phone country                 | `CONFIG.dialCode`, `CONFIG.dialFlag`, `CONFIG.phoneDigits`             |
| 5 | Where the confirmation screen's button goes | `CONFIG.siteUrl`                                 |
| 6 | What the platform is told the bonus was | `CONFIG.bonusCode` — travels as `bonus` on the payload |
| 7 | Logo click target             | wrap `.fc-plate img` in an `<a>` in each HTML file                     |

`CONFIG.dialFlag` takes either an emoji or a path to an 18 x 18 image, and
ships as `assets/img/icons/flag-ua.svg`. Windows has no flag glyphs at all —
Segoe UI Emoji renders 🇺🇦 as the bare letters "UA" — so the emoji the Figma
file uses cannot be shipped as text.

Marketing can change the prizes and the odds in `CONFIG.deck`, `winPrizeId`
and `winTarget`, also at the top of `js/flip.js`.

---

## 2. Wiring the form — pick one route

**A. Plain HTML.** Set `action` and `method` on `<form id="fc-form">` in all
three files. The script validates the fields, then gets out of the way and the
browser submits the form normally. No JavaScript changes at all.

```html
<form class="fc-form" id="fc-form" novalidate action="/signup" method="post">
```

**B. JavaScript.** Leave `action=""` and assign a function. It is called once
validation passes, and you own the request from that point.

```js
onRegister: function (payload, form) {
  // payload = { method, phone, email, password, consent, lang, bonus, ...hiddenFields }
  return fetch('/api/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(function (r) { return r.json(); })
    .then(function (d) { return { login: d.login, password: d.password }; });
}
```

With neither set, nothing is sent. The validated payload is written to the
browser console instead, so the page is fully demoable before it is wired.

---

## 2a. The confirmation screen

The dialog has a second screen: **Реєстрація успішна!**, with the login and
password your platform issued, a copy button on each, and a button to the
site. It is a second panel inside the same `<dialog>` — the close button, the
logo and the offer block are shared — so it swaps in place and the dialog is
never closed and reopened.

Two ways to reach it, and they match the two routes above.

**Return the credentials.** If `onRegister` returns a promise that resolves
with `{ login, password }`, the screen fills itself in and appears. That is
the snippet in route B above.

**Or call it yourself,** at whatever moment suits your flow:

```js
TWFlip.showDone({ login: '+380 93 123 4567', password: 'a1B2c3D4' });
TWFlip.showForm();   // back to the form
```

Both values are inserted with `textContent`, never as HTML. Pass `''` for
either one and that row is hidden. Set `CONFIG.siteUrl` for the orange button;
left empty it stays inert.

On **route A** the screen never appears — the browser navigates to your
`action` and your own page renders the result.

To walk the screen end to end before the platform exists, set
`CONFIG.autoDone: true`. It fires only on the route where nothing is wired at
all, so it cannot reach production: set an `action` or an `onRegister` and it
is skipped.

Copying uses `navigator.clipboard`, which needs a secure context. Over `https`
it works; opened from `file://` it falls back to selecting the text so `Ctrl+C`
still gets it.

---

## 3. What is intentionally not wired

- **No network request of any kind.** No `fetch`, no `XMLHttpRequest`, no
  analytics, no tag manager, no pixels, no cookies.
- **No password policy** beyond a minimum length (`CONFIG.passwordMinLength`,
  currently 8). Your platform's real rules will differ, so none were invented.
- **No CSRF token.** Add it through `CONFIG.hiddenFields`, or as a hidden
  input in the form.
- **No consent or cookie banner.**
- **No credentials are invented.** The confirmation screen shows whatever you
  hand it and nothing else; with nothing wired it never opens.
- **Game state is not persisted.** Reloading restarts the game. That is
  deliberate for a campaign page.
- **Every card can be flipped.** A visitor who turns all nine always finds the
  three winners and reaches the form. That is the point of a funnel page. Set
  `CONFIG.flipBackMs` to a number of milliseconds if you want wrong cards to
  turn back over instead.

---

## 4. Embedding into an existing page

- Every class is prefixed `fc-`. Nothing can collide.
- The CSS reset is scoped to `.fc-root`. **Keep that wrapper `<div>`.**
- Section 0 of `css/styles.css` is the only part that styles `html` and
  `body`. Delete that section when embedding, and nothing else in the file
  can touch the host page.
- Demote `<main class="fc-hero">` to a `<div>` if your page already has a
  `<main>`.
- The modal is a native `<dialog>` opened with `showModal()`, so it renders in
  the browser's top layer and ignores any `z-index`, `overflow` or `transform`
  in your surrounding page.

**Browser support:** Chrome and Edge 105+, Firefox 121+, Safari 15.4+. Uses
`<dialog>`, `:focus-visible`, `:where()`, custom properties, and AVIF images
with a WebP fallback.

---

## 5. Please do not

- **Rename the `fc-` classes**, or remove `data-prize` / `data-pos` /
  `data-face`. `js/flip.js` selects on them.
- **Add `font-variation-settings: "wdth" 75`.** Figma reports it next to the
  font name, but the stylesheet already sets that axis with `font-stretch`.
  Writing both condenses the headline twice.
- **Replace the hero with a PNG.** The Figma export is 1.7 MB; the shipped
  AVIF is 23 KB and looks the same.
- **Put a CSS `filter` on `.fc-flip` or `.fc-face`.** `filter` forces
  `transform-style` back to `flat`, and the card flip collapses into a
  sideways squash. The same goes for `box-shadow` on the rotating nodes: the
  cards deliberately cast no CSS shadow at all.
- **Remove `overflow: hidden` from `.fc-face`,** or add it to `.fc-flip`.
  Same reason, in reverse.
- **Move the scrolling back onto `.fc-form`.** The `<dialog>` is the scroll
  container and `.fc-close` is a sticky sibling of the form, not a child of
  it. Put `overflow-y: auto` on the card again and the close button scrolls
  away with the content — on a phone held sideways that leaves no way out.
- **Reuse the class name `fc-copy` for anything new.** It is already the
  hero's copy block, and it is `position: absolute`. The copy buttons on the
  confirmation screen are `fc-cred__copy` for exactly that reason.

---

## 6. Editing the copy

`index.html` is the master. Make structural changes there first, then apply
the same change to `ru.html` and `en.html` in the same commit.

**Keep translated text on the same line as the original.** That one rule is
what makes this check work:

```
git diff --no-index --word-diff=color index.html ru.html
```

Only translated words should appear in that output. A tag, a class or an
`href` in it means the files have drifted apart.

The GitHub Actions workflow runs two mechanical versions of the same check on
every push: the three files must carry the same number of `<` characters, and
their **tag sequences** must be identical element for element. The second one
is what catches a reordered tab or a panel nested one level deeper — the
character count alone would not.

Every element carrying translatable text also has a `data-i18n` attribute.
Nothing reads it. It is a marker, so the diff has a stable anchor and so a
future move to runtime translations is mechanical rather than a rewrite.

The eight or so strings that depend on what the visitor has done — card
labels for screen readers, the progress announcement, validation errors —
are in the `MESSAGES` table at the top of `js/flip.js`, keyed by language.

---

## 7. Assets

`raw/` holds the Figma exports and `tools/optimize.py` turns them
into `assets/img/`. Neither is served; the Pages workflow copies only the
files a browser requests. Re-run the script by hand if the raw exports change:

```
python -m pip install --upgrade Pillow
python tools/optimize.py
```

| Asset            | Shipped as              | Size   |
|------------------|-------------------------|--------|
| Hero, desktop    | AVIF 1920 and 1280      | 23 KB  |
| Hero, mobile     | AVIF 375                | 4 KB   |
| Card back        | WebP, blur baked in     | 6 KB   |
| Icons and logo   | SVG                     | ~20 KB |
| Fonts            | 7 WOFF2 subsets         | 126 KB |

**Fonts have their own script**, `tools/fonts.py`, and `assets/fonts/` should
never be edited by hand:

```
python -m pip install --upgrade "fonttools[woff]"
python tools/fonts.py           # rebuild
python tools/fonts.py --check   # verify coverage, no network
```

Four of the seven files are Google Fonts subsets carried through verbatim, so
a rebuild reproduces them byte for byte. Three are cut tight: the upright face
for the prize lines on a card, and one hryvnia glyph per style.

**The hryvnia sign is not Roboto.** Roboto has no `₴` at any weight, width or
release — the Google Fonts API even advertises `U+20B4` in the unicode-range it
serves for Roboto's `cyrillic-ext` subset, but the file behind that range does
not contain the glyph. Figma cannot draw it either, so the artboards show a
fallback and are no reference for it. It comes from Noto Sans Black, Google's
companion family to Roboto: cap height 714/1000 against Roboto's 1456/2048, a
difference of 0.4%. If the copy ever changes, run `--check` — it is wired into
CI and fails on any character the shipped faces cannot render.

Three icons are not straight Figma exports:

- `flag-ua.svg` is not an export at all. It is the stand-in for the 🇺🇦
  emoji. See row 4 of section 1.
- `icon-eye.svg` is an export **plus one shape**. Figma's export of node
  12:523 carries only the almond; the pupil is a second circle that the
  exporter drops. It is restored by hand in `raw/img/icon-eye.svg`, and a
  fresh export will lose it again.
- `icon-copy.svg` is drawn by hand. Figma composes the copy button out of two
  frame borders (`19:2532` / `19:2533`) rather than a vector node, so there is
  nothing there to export.

The five `social-*.svg` files are still in `raw/` but are no longer copied
into `assets/`: the footer the design team redrew (`19:2691` / `19:2784`) has
no social row. Put the five lines back into `SVG_PASSTHROUGH` in
`tools/optimize.py` if it ever returns.

Two things worth knowing about the assets:

**The hero background is flattened.** In Figma it is eight layers composited
with `plus-lighter`, `color-dodge` and `screen`. Reproducing that in the DOM
would mean eight large images and a blend pass every frame, so it ships as one
flat image per breakpoint.

**The mobile hero is 1x only.** Figma will not render a node above its natural
size, and the mobile frame is 375 px wide. The scene is soft and glowing so it
holds up, but for a sharper retina version export node `12:311` from Figma at
2x, save it as `raw/img/hero-mobile@2x.png` and extend `tools/optimize.py`.

---

## 8. Accessibility notes

These are load-bearing. Please keep them when you integrate.

- Each card is a real `<button>`. Both of its faces are `aria-hidden`, and the
  accessible name comes from a visually hidden span that the script rewrites
  on each flip. Without that, a screen reader reads the prize off a card that
  is still face down and the game is over before the first click.
- `#fc-status` is a live region that announces progress as cards are found.
- Validation errors use `role="alert"` **and** move focus to the first bad
  field. Both are needed: the first announces, the second locates.
- The password field is `autocomplete="new-password"`, not
  `autocomplete="off"` — the latter fights password managers.
- Every input is at least 16px. Anything smaller makes iOS Safari zoom the
  page on focus, which looks like a bug mid-registration.
- Under `prefers-reduced-motion` the flip becomes a crossfade rather than
  disappearing, and the press feedback is deliberately kept.
- The green tick on a valid field is `aria-hidden`. The state a screen reader
  needs is `aria-invalid` on the input, which the script already writes, and
  announcing "valid" on every blur would say nothing the absence of an error
  does not already say.
- The dialog scrolls, the card does not, and the close button is sticky. A
  phone held sideways leaves about 360px of height — less than half of what
  the form needs — and there is no Escape key on a touch device.
- On the confirmation screen focus moves to the heading, and the dialog's
  `aria-labelledby` follows it, so the new screen is announced without the
  dialog being closed and reopened.

---

## 9. Open questions for the design team

1. The phone prefix stays Ukrainian, `+380`, in the Russian and English
   versions too. That is how the Figma file is drawn. If this campaign is not
   Ukraine-only, change `CONFIG.dialCode`, `dialFlag` and `phoneDigits`.
2. Figma styles the two consent links green only in the Ukrainian version, and
   sets the copyright line in bold only in the Russian one. Both were
   normalised across all three languages.
3. ~~**The cards and the form now promise different things.**~~ **Resolved
   2026-09-04.** The design team redrew the cards in hryvnia (Figma variants
   `winning` / `not_win_1` / `not_win_2`), so the top card and the form now
   promise the same 250.000 ₴ + 250FS. The ladder beneath it is 50.000 ₴ +
   150FS and 25.000 ₴ + 50FS. The card text lives in `CONFIG.deck`.

   That redraw shipped a bug with it, fixed on 2026-09-04: the hryvnia sign
   was in none of the fonts, so it rendered in a system fallback — thin and
   narrow beside black italic digits, on all nine cards and in the dialog, in
   all three languages. Nothing failed, because a missing glyph still draws
   *something*. Section 7 explains where the sign now comes from, and
   `tools/fonts.py --check` runs on every pull request so a copy change cannot
   do this again.
4. **The registration form is only drawn in Ukrainian** (`19:2017`); only the
   footer has all three languages. The Russian and English strings in the form
   and on the confirmation screen were translated here and should be read by
   someone who owns the copy. The amount is now written `250.000 ₴` on all
   three pages: Figma spelled it `250000 ГРН` in the dialog and `250.000 ₴` on
   the cards, and the owner picked the card notation for both (2026-09-04).
   Free spins are `FS` in every language for the same reason — the Ukrainian
   artboards use the Latin form on both surfaces.
5. **The popup node has no close button.** One was kept: Escape is not a
   discoverable dismissal on a touch device, and with the card filling a
   phone screen there is almost no backdrop left to tap.
6. **Four colours in the new design fall short of WCAG AA (4.5:1) for small
   text.** They are brand colours, so they were left alone — this is a note,
   not a change:

   | element | colour on | ratio |
   |---|---|---|
   | consent links, 13px | `#00a75c` on white | 3.12 |
   | "Увійти", 14px | `#ff4500` on white | 3.44 |
   | placeholders, credential labels | `#737b8c` on `#f3f4f5` | 3.86 |
   | consent text, inactive tab | `#737b8c` on white | 4.25 |

   `#6b7280` for `--fc-muted` and `#007a43` for `--fc-link` would clear AA and
   are hard to tell apart from the current pair. The one place this **was**
   changed is the error message: Figma draws it `#e53935`, which is 4.23:1 at
   12px, so the text uses `#c62828` (5.07:1) from the same red ramp while the
   field outline stays exactly `#e53935` as drawn.
