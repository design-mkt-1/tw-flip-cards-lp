# TopWin — Flip the Cards

A static landing page. Plain HTML, one stylesheet, one script. No build step,
no npm, no dependencies of any kind.

Open it with any static server:

```
python -m http.server 8000     # then http://127.0.0.1:8000/
```

| File         | Language  | `<html lang>` |
|--------------|-----------|---------------|
| `index.html` | Ukrainian | `uk`          |
| `ru.html`    | Russian   | `ru`          |
| `en.html`    | English   | `en`          |

The three files are structurally identical. Only the text differs. Mount them
wherever your routing expects, for example `/ua/`, `/ru/` and `/en/`.

**The game:** nine cards face down, three of them hide the 650% + 250 FS
bonus. The visitor flips cards to find those three. When the third one turns
up, the registration form opens.

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
| 5 | Social profile links          | the five `<a class="fc-social" href="#">` in each HTML file            |
| 6 | Logo click target             | wrap `.fc-plate img` in an `<a>` in each HTML file                     |

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
  fetch('/api/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
}
```

With neither set, nothing is sent. The validated payload is written to the
browser console instead, so the page is fully demoable before it is wired.

---

## 3. What is intentionally not wired

- **No network request of any kind.** No `fetch`, no `XMLHttpRequest`, no
  analytics, no tag manager, no pixels, no cookies.
- **No password policy** beyond a minimum length (`CONFIG.passwordMinLength`,
  currently 8). Your platform's real rules will differ, so none were invented.
- **No CSRF token.** Add it through `CONFIG.hiddenFields`, or as a hidden
  input in the form.
- **No consent or cookie banner.**
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
  sideways squash. The card's shadow lives on `.fc-cell::before` for exactly
  this reason.
- **Remove `overflow: hidden` from `.fc-face`,** or add it to `.fc-flip`.
  Same reason, in reverse.

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
`href` in it means the files have drifted apart. The GitHub Actions workflow
runs a coarser version of the same check on every push.

Every element carrying translatable text also has a `data-i18n` attribute.
Nothing reads it. It is a marker, so the diff has a stable anchor and so a
future move to runtime translations is mechanical rather than a rewrite.

The eight or so strings that depend on what the visitor has done — card
labels for screen readers, the progress announcement, validation errors —
are in the `MESSAGES` table at the top of `js/flip.js`, keyed by language.

---

## 7. Assets

`raw/` holds the untouched Figma exports and `tools/optimize.py` turns them
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
| Fonts            | 4 WOFF2 subsets         | 117 KB |

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

---

## 9. Two questions for the design team

1. The phone prefix stays `🇺🇦 +380` in the Russian and English versions too.
   That is how the Figma file is drawn. If this campaign is not
   Ukraine-only, change `CONFIG.dialCode`, `dialFlag` and `phoneDigits`.
2. Figma styles the two consent links green only in the Ukrainian version, and
   sets the copyright line in bold only in the Russian one. Both were
   normalised across all three languages.
