# Decisions

Thirteen areas, all settled. REJECTED names the option that lost, because the
losing option is the one a future agent reinvents from first principles and
ships as an improvement.

Read this before changing an architectural choice, not to justify one — the
CODE line is where the current answer lives.

---

## 1. Brand tokens

**DECISION** Two hero colours — Orange Fire `#ff4500`, Midnight Navy `#191970`
— expanded into 11-step ramps by one published mix schedule: the 500 is the
brandbook value verbatim, 50–400 are it mixed with white at 92/84/68/42/20%,
600–950 with black at 16/34/52/70/84%, all sRGB.

**WHY** A new tint is then a mix, not a guess.

**CODE** `css/tokens.css § "Palette"`.

**REJECTED** Inventing a shade where it is needed. Two landings ago three
greens — `#30d158`, `#3dd629`, `#3fd62b` — sat in three stylesheets all meaning
the same green; the two landings after that each wrote their own AA-safe orange
(`#d63a00`, `#d93900`), green (`#006e3d`, `#00874a`) and muted grey (`#5f6673`,
`#656d7e`): six values for three roles.

The brandbook is not self-consistent and the ramps do not paper over it. "BG
SECONDARY" lists hex `#FF4500` beside RGB(243,244,245) — the RGB is right, the
hex is a paste of Orange Fire. "BG THIRD" is defined twice, `#DCDEEA` and
`#FFDACC`. Both survive under names that say which is which, so nobody has to
pick one and be silently wrong.

The ten brandbook hexes, so drift is detectable without opening a file:
`#ff4500` Orange Fire · `#191970` Midnight Navy · `#ffffff` BG main ·
`#f3f4f5` BG secondary · `#dcdeea` BG third (page 1) · `#ffdacc` BG third
(page 2) · `#1f1f1f` BG dark · `#e7e6e9` stroke · `#2a2a2a` text main ·
`#737b8c` text secondary, superseded by area 2.

---

## 2. The AA-safe pairing rule

**DECISION** The 500s stay hero colours for large type and filled shapes; as
small text they take a darker step from the same ramp schedule, named in the
token file rather than applied at the call site.

**WHY** Four pairings in the delivered design fall under WCAG AA 4.5:1 for
small text, and they are brand colours — so the fix is a token, not a redraw.

| drawn as | on | ratio | replacement |
|---|---|---|---|
| `#00a75c` consent links, 13px | white | 3.12 | `--green-on-light` → `--green-700` `#006e3d` |
| `#ff4500` "Log in", 14px | white | 3.44 | `--accent-on-light` → `--orange-600` `#d63a00` |
| `#737b8c` placeholders, credential labels | `#f3f4f5` | 3.86 | `--text-muted` → `--txt-secondary` `#5f6673` |
| `#737b8c` consent text, inactive tab | white | 4.25 | `--text-muted` → `--txt-secondary` `#5f6673` |

The fifth is the control the page exists to get pressed: the design sets white
on Orange Fire, 3.44:1. `--accent-ink` puts dark ink on it, which clears AA and
— unlike darkening the button — leaves the hero colour exactly as specified.
`--chrome-hint` `#9a9aa0` is the same move against the design's `#8e8e93`.

**CODE** `css/tokens.css § "Signals on a light background"`; the comments at
`css/form.css` lines 562 and 611.

**REJECTED** Leaving the brand colours and noting the failure — which is what
`tw-flip-cards-lp/README.md § 9.6` did: all four listed with their ratios and a
proposed fix that was never applied.

---

## 3. Typography

**DECISION** One family: Roboto, self-hosted, variable, with both axes (`wght`
100–900, `wdth` 75–100) and a real italic cut. Eight woff2 — six Roboto, one per
unicode subset per style, plus two one-glyph Noto Black cuts for the hryvnia.

**WHY** The promo headline is Roboto Condensed Black Italic, which with the
width axis present is this same family at `font-stretch: 75%` — a coordinate,
not a second download.

**CODE** `css/tokens.css § "Self-hosted type"` and `§ "Type"`; the two preloads
in `index.html`; `assets/fonts/OFL.txt`.

**REJECTED** Russo One, which the brandbook prescribes for headlines but no
delivered screen uses — it appears only on the brandbook's own pages, and the
screens are the specification. Also Inter, which the designer used for the card
and footer UI while the brandbook says Roboto. Neither is a substitution forced
by a missing file; both resolve in Figma, so Inter was a deliberate choice being
deliberately not carried.

Two subsets are preloaded, not one, and not because the default is Ukrainian:
the first paint draws both scripts. The copy is Cyrillic; the offer figures, the
tab labels and the UA apostrophe are latin, and the Cyrillic range stops short
of the apostrophe.

---

## 4. Layout — the three modes

**DECISION** The shell has no opinion about the page box: `css/shell.css` is
px, rem and `clamp()` of a viewport width, with no `vh`, `cqh`, `cqw` or `--u`
anywhere. The campaign picks mode A (scrolling page, the default and nothing to
do), B (the `css/stage.css` `<link>`, a fixed stage that never scrolls) or C
(an artboard `--u` unit, for the mechanic only).

**WHY** Those units are exactly what welded the two previous landings to their
own layouts — one page's header lived inside a container query on `#stage` and
could not be lifted out, the other's chrome was in artboard units and could not
be reused at any other size.

**CODE** `css/shell.css § header comment`; `css/stage.css § file header`;
`campaign/main.css § "Choosing a layout"`.

**REJECTED** A height in viewport units for the stage: on iOS `100vh` is the
tallest the viewport ever gets, so the page scrolls by exactly the height of the
browser chrome, and `svh`/`dvh` fix the number then reflow the whole layout every
time the URL bar slides. `position: fixed; inset: 0` is neither wrong nor
animated.

Also rejected: canvas sizing in the shell. A drawing buffer cannot be set from
CSS and the canvas belongs to the mechanic, so it lives in `campaign/main.js`.
There is no `js/stage.js`; do not go looking for one.

`css/stage.css` is the only stylesheet allowed to position the page. Two files
with an opinion about the page box is how a shell stops being reusable.

---

## 5. Header

**DECISION** Injected by `js/shell.js` into `<div data-tw="header">`, styled in
`css/shell.css`, and generated from `TW_LOCALES` filtered by
`campaign.languages`. Controls are 44px with a 16px label. One breakpoint,
700px, shared with the footer.

**WHY** Markup in a shared JS file is what makes the chrome shared at all — the
alternative, the same chrome pasted into every campaign's HTML, produced two
footers, two modals and no header at all across the last two pages.

**CODE** `js/shell.js § headerHTML()`; `css/shell.css § "header"` and
`§ "language listbox"`; `campaign.js § "Brand and chrome"`.

**REJECTED** `fetch('partials/header.html')` — dead on `file://`, which someone
will use. Server includes and Jekyll — both source repos ship `.nojekyll`
deliberately. Custom elements — the same `innerHTML` under a heavier lifecycle
plus a second thing to explain.

Also rejected: hand-writing the language options in HTML, as the previous
landing did with three `<li>`, which made adding a language a code change.

The design draws 32px pills with 13px text, missing the iOS tap target by 12px.
`header.mute: false` omits the speaker rather than disabling it — a campaign
with no audio should not render a dead control. The bar is a stacking context at
`z-index: 46`, which caps the language menu; the dialog is in the top layer and
outranks both.

What it costs, stated rather than defended: the chrome needs JavaScript and is
not in view-source. `<title>`, description and the campaign hero stay static in
the HTML, where a crawler reads them.

---

## 6. Footer

**DECISION** Two arrangements, not two sizes, at the same 700px breakpoint. The
DOM carries the mobile order — payments, then copyright — and the wide layout
restates its own with `order`.

**WHY** On a stage-mode page the height the wide arrangement saves is height the
mechanic keeps, so it applies as soon as there is room; reordering in CSS keeps
reading order and visual order matched in both, where moving the markup would
push the mismatch onto mobile.

**CODE** `js/shell.js § footerHTML()` and the `PAY` table;
`css/shell.css § "footer"`; `assets/img/icons/PAYMENTS-NOTICE.txt`.

**REJECTED** One shared size rule for the payment marks: the four have three
aspect ratios, and a rule that fits the Visa wordmark stretches the round ones.
Also rejected: a social row, which the design team removed when they redrew the
footer.

The logo is orange and navy and its navy half disappears on `--footer-bg`,
which is why the design stands it on a white plate in the wide node and leaves
it out of the mobile one.

---

## 7. The registration popup

**DECISION** A native `<dialog>` opened with `showModal()`. The dialog is the
scroll container, the card is not, and the close button is a sticky sibling of
the form. Two panels in one dialog — form and confirmation — so the promo header
stays and only the body swaps. Two geometries, a plain `@media (min-width: 480px)`.

**WHY** `showModal()` puts the card in the top layer, so it renders identically
over a fixed stage, an artboard hero and an ordinary scrolling page, with no
z-index negotiation and no ancestor `overflow` or `transform` able to trap it.

**CODE** `js/form.js § "The dialog is native"` and `§ "open / close"`;
`js/shell.js § dialogHTML()`; `css/form.css § "the dialog"` and
`§ "the wide card"`.

**REJECTED** A hand-rolled overlay `<div>`. It cost the previous landing about
eighty lines of focus trap, inert bookkeeping, Escape handling and scroll
locking that could not be shared, because the overlay was positioned inside a
stage only that page had.

Also rejected: a container query on the card. That version had to explain twice
that an element cannot be styled by its own container query and that a container
is measured by its content box — a 504px card with 24px of padding queries as
454 and never matches a 480 threshold.

Also rejected: scrolling on the form. The close button then scrolls away with
the content, and a phone held sideways leaves about 360px of height, less than
half of what the form needs, with no Escape key and almost no backdrop to tap.
The close button ships even though the Figma node has none, for the same reason.

The desktop card is not a scaled mobile card — padding 24→36, logo 101×18 →
247×44, promo type 16/84/34 → 24/100/44, while tabs, fields, checkbox and button
keep their mobile sizes exactly. Only what the design changes is in the query.

---

## 8. i18n

**DECISION** One HTML file, all languages. Nodes opt in with `data-i18n="key"`,
attributes with `data-i18n-attr="attr:key"`. `TW_STRINGS` (`js/strings.js`)
merges with `TW_CAMPAIGN.strings` (`campaign.js`), campaign winning. Fallback:
current locale → the first entry in `languages` → the key itself. Detection:
`?lang=` → `localStorage['tw-lang']` → `navigator.language` → first entry.

**WHY** A separate HTML file per language was tried in the last landing and
needed two dedicated CI jobs whose entire purpose was to detect that its own
three copies had drifted; one file cannot drift from itself.

**CODE** `js/i18n.js § "The model"`, `§ detect()`, `§ apply()`;
`js/strings.js § "Adding a language"` and the `TW_LOCALES` table.

**REJECTED** Markup inside a string. Sentences with links are five nodes —
`agree.pre` / `agree.terms` / `agree.mid` / `agree.privacy` / `agree.post` — so
a locale can reorder the words around the anchors; only the first fragment is a
real `<label>`, because a click on either link would otherwise toggle the
checkbox on its way to the anchor.

Also rejected: regex `replace` for interpolation. A value containing `$&` or
`$1` would be mangled by `String.replace`'s own substitution syntax, and an
offer amount is exactly the kind of string that arrives from a spreadsheet with
a stray character in it.

`ua` is a region subtag; the language is `uk`. The design and the menu say UA,
so `ua` stays the internal code and `TW_LOCALES.tag` carries the real BCP-47 tag
for `documentElement.lang`, the payload and detection. Without that map every
Ukrainian browser reports `uk-UA`, misses the table and lands on the fallback —
which only *looks* right because the fallback happens to be Ukrainian.

Adding a language is four edits and no new file. `?lang=` is deliberately not
persisted: a link that forces a language should not overwrite what the visitor
chose last visit. `\n` is a real line break; the markup carries no `<br>`.

---

## 9. Animation and motion

**DECISION** One curve, `--ease-out`. Entry is slower than exit everywhere —
the language menu enters at 180ms and leaves at 120ms, the dialog enters at
280ms behind a 60ms scrim lead and leaves at 160ms. `prefers-reduced-motion`
degrades, never removes.

**WHY** Arriving is worth watching and leaving is not: the visitor has already
decided, and a slow exit reads as an obstacle.

**CODE** `css/tokens.css § "Motion"`; `css/form.css § "the dialog"`;
`css/shell.css § "language listbox"`; `css/reset.css § prefers-reduced-motion`;
`campaign/main.js § "Rules that still apply"`.

**REJECTED** Per-component curves and durations. `tw-flip-cards-lp` carried five
plus a section that rewrote all of them under reduced motion.

The 60ms lead means the room dims first and then the thing arrives — one
property, and the whole difference between a modal appearing and a modal being
presented. `overlay` and `display` are transitioned with `allow-discrete`, which
is what lets a top-layer element animate out at all; `@starting-style` supplies
the "before" the browser otherwise has none of. A visitor who asked for less
motion did not ask for less feedback.

---

## 10. The asset pipeline

**DECISION** `raw/` holds the sources and is gitignored; `tools/optimize.py`
writes AVIF and WebP into `assets/img/` and the **outputs** are committed. Run
by hand, never at deploy time. That is the whole build system.

**WHY** A sibling repo shipped 22 MB of raw renders to a public GitHub repo and
they stayed downloadable from raw.githubusercontent.com long after the Pages
site was cleaned.

**CODE** `tools/optimize.py § module docstring`; `.gitignore`;
`references/art.md`.

**REJECTED** Shipping the Figma PNG: one 1.7 MB export became a 23 KB AVIF and
looks the same. Also rejected: a build step — the published site is these files.

Both formats ship because AVIF is roughly a fifth the size at the same quality
and WebP covers the rest; the AVIF `<source>` goes first and the widest media
query first, because first match wins and reversing it downloads the 375px crop
to every desktop. Transparency is flattened onto `--navy-950` unless
`--keep-alpha` is passed.

---

## 11. The form-submission seam

**DECISION** Three routes in precedence order: `form.onRegister(payload)` if it
is a function, else `form.endpoint` as a JSON POST, else nothing — the validated
payload goes to `console.info` and, with `form.demoDone`, the confirmation
screen is walked anyway.

**WHY** The page is fully demoable before the platform exists and cannot
silently half-ship: there is no state in which it looks wired and is not.

**CODE** `js/form.js § "submit"` and `§ "the confirmation screen"`;
`campaign.js § "The registration form"`.

**REJECTED** A plain HTML `action=` route alongside the JS one, which
`tw-flip-cards-lp` offered — the confirmation screen simply never appeared on
one of the two. Also rejected: `form-action` in the CSP, which does **not** fall
back to `default-src`; leaving it out is what keeps the form free to POST
wherever IT wires the endpoint, and adding it would break that wiring on the day
it happens.

The password is in the payload, because a registration hook without one is
useless — which is exactly why `endpoint` must point at the operator's own TLS
endpoint and nowhere else. Both credential values are written with
`textContent`, never `innerHTML`.

---

## 12. The analytics seam

**DECISION** `analytics.gtmId` and `analytics.metaPixelId` both empty is the
shipped default, and with both empty not one third-party request is made.
`TW.track()` always runs and is a no-op without an id.

**WHY** Zero third-party requests is what lets the CSP in `index.html` ship as
`'self'` and `'none'` throughout.

**CODE** `js/shell.js § injectAnalytics()` and `§ track()`;
`index.html § CSP comment block`; `campaign.js § "Analytics"` and
`§ "Tracking and affiliate"`.

**REJECTED** Putting the CSP swap in `campaign.js`. A `<meta>` policy cannot be
written from JavaScript, so setting either id is the one campaign edit that
lives outside that file — and a refusal appears only in the console, so the page
looks fine and silently sends nothing.

Also rejected: reading the passthrough lazily at click time. It is read once at
boot, because a mechanic may replace the query string with history state and the
affiliate click id has to survive that. `passthrough` is how an affiliate id
survives the landing page at all; neither earlier landing had it, and the ids
were lost. Meta's snippet is transcribed rather than eval'd from a string, so
`script-src` stays free of `'unsafe-inline'`.

---

## 13. Deployment

**DECISION** GitHub Pages from GitHub Actions. Guards run on every push **and
every pull request**; build and deploy only on `main`. The build stages an
explicit `cp` allowlist into `_site` — `index.html campaign.js .nojekyll css js
campaign assets` — never `cp -r .`.

**WHY** In the landing this workflow is taken from the guards lived inside the
build job, which only ran after a merge, so every guard reported a problem that
was already on `main`; that is how the hryvnia bug reached production.

**CODE** `.github/workflows/pages.yml`; `.gitignore`; `.nojekyll`.

**REJECTED** `cp -r .`, one careless commit away from publishing whatever lands
in the repo — `tools/`, `docs/`, `raw/` and the dotfiles must 404 on the live
URL. Also rejected: leaving the repository's Pages source on a branch, where the
legacy Jekyll builder succeeds, publishes the whole repository, bypasses the
allowlist entirely, and nothing warns you. That one is a settings change, not a
code change: see `references/checklist.md`.

## 14. Browser support

**DECISION** The floor is **Chrome/Edge 105+, Safari 16+, Firefox 110+**. Above
**Chrome/Edge 117+, Safari 17.4+, Firefox 129+** the dialog also animates in.
Nothing below the floor is tested and nothing below it is claimed.

**WHY** Four features set it, and only one of them fails hard:

| feature | where | floor | below it |
|---|---|---|---|
| `<dialog>` + `showModal()` + `::backdrop` | `css/form.css`, `js/form.js` | Safari 15.4 | the pop-up does not open — hard fail |
| `container: … / size` + `@container` | `css/stage.css` only | Chrome 105 / Safari 16 / Firefox 110 | the landscape footer-drop never applies; the page still works |
| `@starting-style` + `transition-behavior: allow-discrete` | `css/form.css` | Chrome 117 / Safari 17.4 / Firefox 129 | the dialog appears without its entry animation |
| `backdrop-filter` | `css/shell.css`, `css/form.css` | Chrome 76 / Safari 9 / Firefox 103 | the header bar is a flat colour |

So the container query in `css/stage.css` is what actually sets the floor, and
only a stage-mode campaign carries it. A scrolling campaign runs on Safari 15.4.

**CODE** `css/form.css § "the dialog"`; `css/stage.css § "short and wide"`;
`css/shell.css § "header"`.

**REJECTED** Feature-detecting any of these. `@starting-style` and
`backdrop-filter` degrade by themselves and need no code; the container query
does not degrade, but the campaigns that use it are the ones the team tests on
device anyway. A `@supports` fork would be a second layout to maintain for
browsers nobody has reported.

**NOT VERIFIED** Nobody has run this on a browser at the floor. The numbers
above are read off the features, not off a device. `references/checklist.md`
lists what cannot be closed from a desk; this belongs with it.
