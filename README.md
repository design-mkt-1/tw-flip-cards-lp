# TopWin — Flip the Cards

A static landing page. Plain HTML, one stylesheet, one script. No build step,
no npm, no dependencies of any kind.

Open it with any static server:

```
python -m http.server 8000     # then http://127.0.0.1:8000/
```

Three guards run on every pull request, and all run by hand too. None is a
build step — the published site is these files:

```
python tools/fonts.py --check     # every character the page renders is in the fonts
python tools/smoke.py             # the pages, in a real browser (needs Playwright)
python tools/platform_test.py     # the IT platform connection, against a stub
```

`platform_test.py` plays the registration against a **stubbed** platform —
inactive landing, success and the SSO hand-off, email taken, reCAPTCHA failure,
network failure — in all three languages. `smoke.py` uses the same stub
(`tools/platform_stub.py`), because the page asks the platform for its landing
on every load and that must never be a real request from CI or a laptop.

`smoke.py` serves the project on a loopback port and loads the page once per
language at each of two viewports, asserting what no text check can see: the
page opens at the top, nothing is left in flow below the footer, the closed
dialog is `display: none`, the console is clean, and the visitor still goes
3 of 3. Both guards exist because a bug shipped past everything else — section
7 for the fonts one, and a closed dialog left in normal flow for the other,
which is why `smoke.py` measures geometry rather than markup.

**One HTML file, three languages.** `index.html` is the whole page. The globe
in the header swaps the language in place — no reload, no second URL — and the
choice is kept in `localStorage['tw-lang']`. `?lang=ru`, `?lang=en` or
`?lang=ua` forces one for a single visit, which is what a one-language ad
creative should link to; it is not persisted, so it cannot overwrite what the
visitor chose before.

Ukrainian is the default: it is what is written in the markup, so it is what
paints before any script runs and what a crawler and a link preview read out
of `<title>` and `<meta name="description">`.

> **`ru.html` and `en.html` were deleted on 2026-09-07** and those two URLs now
> 404. Anything still pointing at them — routing, an ad, a QR code — has to move
> to `?lang=ru` / `?lang=en`. The page also carries no `hreflang` any more,
> because there is nothing left to point at: `?lang=ru` is the same document,
> not a URL a search engine can index as Russian. Indexing per language would
> need real per-language URLs from the host's routing.

Until that day this landing served one pre-translated HTML file per language.
It cost two CI jobs whose only purpose was to notice that three copies of the
same page had drifted apart, and it made the language menu a navigation
control: picking a language reloaded the page. One file cannot drift from
itself.

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
| 1 | The platform: registration, landing, reCAPTCHA, login redirect | `js/platform.js`, `platform` in `campaign.js`, and a `config.json` on the server — section 2 |
| 2 | Extra values on the submission | `form.hiddenFields` — copied onto the request body, never over a real field |
| 3 | Terms / Privacy / Login links | come from the platform's landing API (`rules`, `policy`, `login`); `links.*` is only the fallback |
| 4 | ~~Phone country~~ | unused: the phone tab is removed, the API is email-only |
| 5 | Where the confirmation screen's button goes | `links.cta` |
| 6 | What the platform is told the bonus was | `offer.code` — travels as `bonus` on the payload |
| 7 | The header logo's destination | `links.home` |
| 8 | Tracking that rides through to the operator | `params` and `passthrough` |

**Row 1 blocks go-live.** Until a `config.json` exists next to `index.html`
the page is **not connected**: the form validates, writes a warning to the
browser console and walks the demo confirmation screen — to a visitor it looks
like a completed registration that quietly went nowhere. That demo is
deliberate (the GitHub Pages preview needs it) and it is the first thing to
check on a fresh deploy.

Row 3 is no longer a separate task: once the landing API answers, the Terms and
Privacy links come from it. They are still a compliance matter — if the API
omits `rules` or `policy`, those two anchors have no `href` and the consent
sentence has no documents behind it.

Rows 2 and 5 to 8 all have working defaults and can follow later.

`form.dialFlag` takes either an emoji or a path to an 18 × 18 image, and it
ships as an image because Windows has no flag glyphs: Segoe UI Emoji draws 🇺🇦
as the bare letters "UA".

---

## 2. The platform connection

`js/platform.js` is this landing's own file (not the template's). It follows
IT's reference landing step for step, so their deploy drops in. **The form is
email + password only** — the phone tab is removed, because the API is
`registration/email`.

1. **Config.** On `localhost`, `127.0.0.1` or an origin starting with
   `https://land-crm` the page uses `platform.dev` in `campaign.js`, which is
   IT's own `TEMP_CONFIG` (landing id **8**, `api2-land-dev.jack-pot.tech`).
   **Everywhere else** it fetches `config.json` from the site root:
   `{ "id": <number>, "email_registration": "<url>", "landing": "<url>" }`.
2. **Landing.** `GET config.landing` on every load. If `data.active` is false
   the page shows a "temporarily unavailable" card (mailto
   `platform.supportEmail`) in the visitor's language and nothing else works.
   Otherwise `data.rules` / `policy` / `login` become the Terms, Privacy and
   Login links (with the page's query string appended), and reCAPTCHA v3 is
   loaded with `data.recaptcha_key`.
3. **Submit.** `grecaptcha.execute(key, {action: 'register'})`, the visitor's IP
   from `api.ipify.org` (3 s ceiling, `""` on failure), then
   `POST config.email_registration` with
   `email, password, landing_id, language, currency, country, promocode,
   receivePromos: true, clientIp, g-recaptcha-response`. `language` is `uk`,
   `ru` or `en`. The URL parameters in `campaign.js § passthrough` and
   `form.hiddenFields` go **first**, so they can add fields and can never
   overwrite one of those.
4. **Success.** `response.data.accessToken` is POSTed (hidden form,
   `application/x-www-form-urlencoded`) to `<casino>/api/welcome` as `tmpToken`,
   with `redirect=<casino>/<lang>/<redirect_link>?<page query>`; `<casino>` is
   the host of `data.rules`. The player arrives logged in. The template's
   confirmation screen — which shows a login and a password — is **never shown**.
5. **Errors.** `{ "errors": ["…"] }` is read: "already registered" and
   anything mentioning reCAPTCHA get their own message in UA / RU / EN
   (`campaign.js § strings`: `err.exists`, `err.recaptcha`). Anything else,
   including a network failure, is the template's generic "could not send".
   While the request runs the submit button is disabled.

> **The Content-Security-Policy `<meta>` in `index.html` is written for this**
> and names the origins one by one. Two things are open and **both fail
> silently** (a CSP refusal appears only in the browser console):
> the **production API origin** must be added to `connect-src` (only IT's dev
> host is there, marked TEMP), and **`form-action 'self' https://<casino>`**
> must be added for the SSO POST once IT names the casino domain. See the
> comment above the `<meta>`.

The password is in the registration body, so `config.email_registration` must
be the operator's own TLS endpoint and nowhere else.

`form.endpoint` and `form.onRegister` in `campaign.js` are no longer the seam:
`onRegister` calls `window.TWPlatform.register`, which overrides `endpoint`.

---

## 2a. The confirmation screen

The template's second panel (**Реєстрація успішна!**, login and password, copy
buttons) is **only reachable in demo mode** now — no `config.json`. With the
platform connected, success is the SSO redirect and this panel never opens, so
the password the visitor typed is never put back on screen.

---

## 3. What is intentionally not wired

- **Network requests are only the platform's:** `config.json`, the landing
  and registration APIs, `api.ipify.org`, and Google reCAPTCHA. The ipify
  `clientIp` and the hidden reCAPTCHA badge both follow IT's LP. No analytics,
  no tag manager, no pixels unless `analytics.*` is set, and no cookies of
  ours (reCAPTCHA sets its own).
- **No password policy** beyond a minimum length (`form.passwordMin` in
  `campaign.js`, currently 8). Your platform's real rules will differ, so none
  were invented.
- **No CSRF token.** `form.hiddenFields` would carry one onto the request body.
- **No consent flag in the request.** IT's body has none and ours matches; the
  tick-box is checked locally only.
- **No consent or cookie banner.**
- **No credentials are invented or shown.** The platform logs the player in
  through the SSO redirect.
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

`index.html` is the only page. **Translations are not in it** — they are in
`campaign.js § strings`, one block per language, and `js/i18n.js` renders every
element carrying a `data-i18n` attribute from there.

There are five such keys and they are this landing's own copy:

| Key          | Where it renders                                  |
|--------------|---------------------------------------------------|
| `title`      | `<title>` in the head                             |
| `hero.1`     | the white headline line                           |
| `hero.2`     | the gold headline line                            |
| `game.label` | the board's heading, for screen readers only      |
| `cta.claim`  | the claim button under the board                  |

The Ukrainian for four of them is **also written into `index.html` as real
text**, because that is what paints before any script runs and what a crawler
reads. The two have to agree — change one, change the other, in the same
commit. `title` is the exception only in that the head's copy is likewise the
Ukrainian one.

`<meta name="description">` has no key and is not translated. A `<meta>` is
not a `data-i18n` node, nothing re-renders it, and it stays in the default
locale — the one thing three separate HTML files used to give us for free.

Two mechanical CI checks used to guard this section: the three files had to
carry the same number of `<` characters and identical tag sequences. Both are
gone with the files they compared.

The strings that depend on what the visitor has done — the card labels for
screen readers, the progress announcement — are in the `MESSAGES` table at the
top of `js/flip.js`, keyed by BCP-47 tag (`uk` / `ru` / `en`) rather than by
our internal codes. That table is **looked up on every call, never captured
once**, and `js/flip.js` re-writes the nine card labels on `TW.on('lang')`.
Freezing it was safe while one file was one language; it is not any more, and
the failure would be silent — the cards draw digits, so nothing on screen
would look wrong while a screen reader read the board in the language the
visitor arrived in.

**Everything the registration card says is in `js/strings.js`,** which is the
template's file and the same in every Top Win landing; the handful of words
this campaign owns override it from `campaign.js`.

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
   someone who owns the copy. The amount is now written `250.000 ₴` in all
   three languages: Figma spelled it `250000 ГРН` in the dialog and `250.000 ₴` on
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
