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
else — section 7 for the fonts one, and a closed dialog left in normal flow
for the other, which is why `smoke.py` measures geometry rather than markup.

| File         | Language  | `<html lang>` |
|--------------|-----------|---------------|
| `index.html` | Ukrainian | `uk`          |
| `ru.html`    | Russian   | `ru`          |
| `en.html`    | English   | `en`          |

The three files are structurally identical. Only the text differs. Mount them
wherever your routing expects, for example `/ua/`, `/ru/` and `/en/`.

**The game:** nine cards face down. **The visitor goes 3 of 3** — whichever
three cards they turn, all three land the 250.000 ₴ + 250FS top prize. There
is no miss and nothing to hunt for. When the third one turns, the board locks
and the registration form opens, offering the same welcome bonus, and the six
cards nobody turned open behind it showing the 50.000 ₴ + 150FS / 25.000 ₴ +
50FS ladder they were played against.

That is `CONFIG.alwaysWin` in `js/flip.js`, and it is what the campaign asks
for. The deck below it is where the odds live when it is off.

---

## 1. What you need to change

**Everything you wire is in `campaign.js`, at the root of the repo.** It is one
file of commented settings and nothing else — no build step, no framework.

The registration card itself is not this landing's code. It is `tw-lp-template`'s,
shared with every other Top Win landing so that one design cannot become three
drawings of itself: `css/tokens.css`, `css/form.css`, `js/strings.js`,
`js/i18n.js`, `js/form.js` and `js/shell.js` are that repo's files, unmodified.
**Do not edit them here.** A change one of them needs is made in the template
and pulled down. `js/flip.js` is the game, and `campaign.js` is the campaign.

| # | What | Where |
|---|------|-------|
| 1 | Where the form submits | `form.endpoint` in `campaign.js`, **or** `form.onRegister` |
| 2 | Extra values on the submission | `form.hiddenFields` — affiliate id, campaign, CSRF token |
| 3 | Terms / Privacy / Login links | `links.terms`, `links.privacy`, `links.login` |
| 4 | Phone country | `form.dialCode`, `form.dialFlag`, `form.phoneDigits` |
| 5 | Where the confirmation screen's button goes | `links.cta` |
| 6 | What the platform is told the bonus was | `offer.code` — travels as `bonus` on the payload |
| 7 | The header logo's destination | `links.home` |
| 8 | Tracking that rides through to the operator | `params` and `passthrough` |

**Rows 1 and 3 block go-live. The rest do not.**

Until row 1 is done the form sends nothing at all: it validates, then writes
the payload to the browser console and walks the confirmation screen anyway —
to a visitor it looks like a completed registration that quietly went nowhere.
Until row 3 is done, the Terms and Privacy anchors carry **no `href` at all**:
they are plain text inside the consent label, which is the honest state of an
unfilled seam but not the finished one. A page that collects an 18+ consent
needs the two documents behind it, and that is a compliance problem rather
than a cosmetic one.

Rows 2 and 4 to 8 all have working defaults and can follow later.

`form.dialFlag` takes either an emoji or a path to an 18 × 18 image, and it
ships as an image because Windows has no flag glyphs: Segoe UI Emoji draws 🇺🇦
as the bare letters "UA".

---

## 2. Wiring the form

> **There is a Content-Security-Policy `<meta>` in the head of all three
> pages.** The card posts JSON with `fetch`, and `default-src 'self'` covers
> that — so an endpoint on **another origin** needs that origin added to
> `connect-src` in the policy, in all three files. A CSP refusal appears
> **only in the browser console**: the submit looks like it simply did nothing.

**A. An endpoint.** Set it in `campaign.js` and the card POSTs JSON to it.

```js
form: { endpoint: 'https://api.example.com/signup', ... }
```

A response carrying `{ "login": "…", "password": "…" }` fills the confirmation
screen. Any other JSON, or none, and the screen shows what the visitor typed.
A non-2xx response, or a network failure, shows the card's own error line and
leaves the visitor on the form.

**B. A function**, when the request needs more than that. It overrides
`endpoint` and you own the request from the moment validation passes.

```js
form: {
  onRegister: function (payload) {
    // payload = { method, contact, email, phone, password, consent, lang,
    //             bonus, landing_id, ...hiddenFields, ...params }
    return fetch('/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json(); })
      .then(function (d) { return { login: d.login, password: d.password }; });
  }
}
```

With neither set, nothing is sent: the payload goes to `console.info` and,
because `form.demoDone` is true, the confirmation screen is walked anyway. The
page is fully demoable before the platform exists — and it says so loudly in
the console, so it cannot be mistaken for a working integration.

**The `action=` route is gone.** This landing used to let the browser submit
the form natively; the shared card does not have that route, because a native
submit navigates away and the confirmation screen is the point of the design.
Use `endpoint` — it is the same amount of work and one line.

---

## 2a. The confirmation screen

The card has a second panel: **Реєстрація успішна!**, the login and password
your platform issued, a copy button on each, and a button to the site. The
logo and the offer block stay; only the body under them swaps, so the card is
never closed and reopened.

It appears by itself when the request resolves. To drive it by hand:

```js
TW.showDone({ login: '+380 93 123 4567', password: 'a1B2c3D4' });
```

Both values are inserted with `textContent`, never as HTML. `links.cta` is the
orange button's destination; left empty it carries no `href` and is inert.

Copying uses `navigator.clipboard`, which needs a secure context. Over `https`
it works; opened from `file://` it falls back to selecting the text so `Ctrl+C`
still gets it.

---

## 3. What is intentionally not wired

- **No network request of any kind.** No `fetch`, no `XMLHttpRequest`, no
  analytics, no tag manager, no pixels, no cookies.
- **No password policy** beyond a minimum length (`form.passwordMin` in
  `campaign.js`, currently 8). Your platform's real rules will differ, so none
  were invented.
- **No CSRF token.** Add it through `form.hiddenFields`.
- **No consent or cookie banner.**
- **No credentials are invented.** The confirmation screen shows whatever you
  hand it and nothing else; with nothing wired it never opens.
- **Game state is not persisted.** Reloading restarts the game. That is
  deliberate for a campaign page.
- **Nobody can lose, and nobody turns more than three.** The board locks the
  moment the third card lands, so everyone reaches the form in exactly three
  clicks. That is the point of a funnel page. `CONFIG.flipBackMs` in
  `js/flip.js` only matters with `alwaysWin` off, where wrong cards exist and
  stay face up by default.

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
- **Edit the card.** `css/tokens.css`, `css/form.css`, `js/strings.js`,
  `js/i18n.js`, `js/form.js` and `js/shell.js` are `tw-lp-template`'s files.
  A change one of them needs goes into that repo, where `SHARED.lock` is
  bumped, and comes back down here. Fixing it in this clone is how one design
  became three drawings of itself in the first place.
- **Reuse the class name `fc-copy` for anything new.** It is already the
  hero's copy block, and it is `position: absolute`.

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

Every element carrying translatable text also has a `data-i18n` attribute,
and since the card became shared code those attributes ARE read: `js/i18n.js`
renders them from `campaign.js § strings` for the page's own language. The
words in the HTML are still what paints first and what a crawler sees, so the
two have to agree — change one, change the other, in the same commit.

The strings that depend on what the visitor has done — card labels for screen
readers, the progress announcement — are in the `MESSAGES` table at the top of
`js/flip.js`. **Everything the registration card says is in `js/strings.js`,**
which is the template's file and the same in every Top Win landing; the
handful of words this campaign owns override it from `campaign.js`.

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
- `#fc-status` is a live region that announces progress as cards are turned.
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
   Ukraine-only, change `form.dialCode`, `form.dialFlag` and
   `form.phoneDigits` in `campaign.js`.
2. Figma styles the two consent links green only in the Ukrainian version, and
   sets the copyright line in bold only in the Russian one. Both were
   normalised across all three languages.
3. ~~**The cards and the form now promise different things.**~~ **Resolved
   2026-09-04.** The design team redrew the cards in hryvnia (Figma variants
   `winning` / `not_win_1` / `not_win_2`), so the top card and the form now
   promise the same 250.000 ₴ + 250FS. The ladder beneath it is 50.000 ₴ +
   150FS and 25.000 ₴ + 50FS. The card text lives in `CONFIG.deck`.

   While `CONFIG.alwaysWin` is on, every card the visitor turns is promoted to
   250.000 ₴ + 250FS. The two lower tiers are what the other six are dealt, and
   they open dimmed at the end, so all three tiers are still drawn and the deck
   stays the one place the card text lives.

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
