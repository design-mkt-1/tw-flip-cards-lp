---
name: topwin-lp
description: >
  Build, change or review a TopWin (Top Win) campaign landing page — a static
  UA/RU/EN promo LP with a hero game mechanic, a registration pop-up and an
  affiliate/tracking seam, built from the tw-lp-template repo. Use for "fac un
  landing nou pentru TopWin", "landing nou", "LP nou de campanie", "new TopWin
  LP", "new campaign landing", or any work touching campaign.js, css/tokens.css,
  js/i18n.js, the registration popup, the Orange Fire #ff4500 / Midnight Navy
  #191970 brand tokens, WCAG AA colour pairings, self-hosted Roboto woff2
  subsets, the hryvnia ₴ font carve-out, or the GitHub Pages _site deploy. Also
  use before adding a new language, a new hero mechanic (scratch card, wheel,
  flip cards, penalty), or a new offer to an existing LP.
---

# TopWin campaign landing page

`tw-lp-template` is a finished, working static landing page: a shared header,
footer and registration `<dialog>` around a `<main>` block that each campaign
replaces with its own hero mechanic. No bundler, no npm, no runtime
dependencies — `defer` script order is the dependency graph, and the deploy is
a file copy.

**The boundary rule: if a browser executes it, it lives in the repo. If an
agent's judgment executes it, it lives in this skill.** This skill therefore
contains no CSS and no JS. When you need a value, open the file named here. An
agent that finds itself typing `--orange-500: #ff4500` into a new file has
already failed — it should have cloned the template.

## The non-negotiables

Each of these was paid for once. The reasoning is in `references/decisions.md`;
do not relitigate it here.

- Colours live in `css/tokens.css` and are reached through the semantic layer
  (`--accent`, `--accent-on-light`, `--text-muted`, `--surface-field`,
  `--danger`). No hex, no `rgb()`, no `--orange-N` / `--navy-N` anywhere else.
- The four failing AA pairings, with what replaces them — never write the left
  column as small text:

  | drawn as | on | ratio | use instead |
  |---|---|---|---|
  | `#00a75c` | white | 3.12 | `--green-on-light` |
  | `#ff4500` | white | 3.44 | `--accent-on-light` |
  | `#737b8c` | `#f3f4f5` | 3.86 | `--text-muted` |
  | `#737b8c` | white | 4.25 | `--text-muted` |

  White ink on untouched Orange Fire is the fifth, at 3.44:1 — the CTA keeps
  the hero colour and takes dark ink through `--accent-ink`.
- One font family. Roboto, self-hosted, both axes. `font-stretch: 75%` IS
  "Condensed"; `--font-stretch-tight` names it. Never name a second family, and
  never write `font-variation-settings: "wdth" 75` beside it.
- The hryvnia sign U+20B4 is served from two one-glyph Noto Black cuts, not
  from Roboto, which has none at any weight. Change the copy, run
  `python tools/fonts.py --check`.
- `css/shell.css` is layout-neutral: px, rem and `clamp()` of a viewport width
  only — no `vh`, `cqh`, `cqw` or `--u`. The campaign picks one of three layout
  modes (scrolling page / `css/stage.css` / artboard `--u`), documented at the
  top of `campaign/main.css`.
- The registration card is a native `<dialog>` opened with `showModal()`, and
  `TW.openForm()` is the only seam into it. Never call `showModal()` yourself,
  never re-implement the card, never reach into its DOM.
- Offer figures are numbers in `campaign.js § "The offer"` and are interpolated
  into every locale as `{percent} {amount} {currency} {spins}`. They are never
  written into a language table.
- An unset link gets NO `href`. Never `"#"` — a mark that takes focus, is
  announced as a link and then does nothing is a broken control.
- `links.terms` and `links.privacy` block go-live. The page collects an 18+
  consent; dead consent links on a gambling registration form are a compliance
  problem, not a cosmetic one.
- Every `input` is at least 16px, including the ones the design draws at 15.
  Below that iOS Safari zooms the page on focus.
- `css/reset.css` forces `[hidden] { display: none !important }` and `display`
  cannot be transitioned. Show/hide is always a two-step: unhide, let one frame
  pass, then add the class the transition runs on.
- `prefers-reduced-motion` DEGRADES, never removes. A 3D flip becomes a
  crossfade; press feedback survives. Someone who asked for less motion did not
  ask for less feedback.

## Never touch / always edit

**Never touch** — verbatim from the `SHARED` list in `tools/drift.py`, hashed in
`SHARED.lock`, checked by `python tools/drift.py`:

```
css/reset.css   css/tokens.css   css/shell.css   css/form.css   css/stage.css
js/strings.js   js/i18n.js       js/form.js      js/shell.js
tools/drift.py  tools/tokens.py  tools/smoke.py  tools/fonts.py
.github/workflows/pages.yml
```

A change one of these genuinely needs is made **in the template**, `SHARED.lock`
is bumped there, and the clone pulls it down. Regenerating `SHARED.lock` in a
clone silences the alarm instead of answering it.

**Always edit** — this is the campaign:

```
campaign.js                 every seam and every campaign string
campaign/main.js            the mechanic
campaign/main.css           the mechanic's styles, cmp- prefixed
campaign/assets/            its art
campaign/smoke.py           optional; expose check(page, viewport, lang)
index.html                  the <main> block, the CSP meta, the stage.css <link>
assets/img/                 committed outputs of tools/optimize.py
```

## Where to look

| symptom | read |
|---|---|
| "why is it built this way", about to change an architectural choice | `references/decisions.md` |
| something renders wrong and nothing errored; a fix that "does not apply" | `references/traps.md` |
| wiring the form, the tracking, a URL, analytics, or a mechanic to the shell | `references/seams.md` |
| about to say it is done, or about to push | `references/checklist.md` |
| generating or cutting out imagery | `references/art.md` |

## A new campaign, in eight steps

1. Clone `tw-lp-template` into the new repo. Set `id` in `campaign.js` to the
   repo name; it rides on every payload and every analytics event.
2. Specify the mechanic (see Composition below). Nothing else is up for design.
3. Fill `campaign.js`: `offer` figures, the five `links`, `params` /
   `passthrough`, the `form` block, `languages`, `brand` / `header` / `footer`,
   and only the strings the campaign owns.
4. Replace the `<main id="tw-main">` block in `index.html` with the hero's
   static markup. It is the first paint and the LCP element, so it is HTML, not
   script; every string carries `data-i18n="key"` with the default locale's
   words written inline.
5. Choose the layout mode in `campaign/main.css § "Choosing a layout"` — A
   scrolling page (default), B the `css/stage.css` `<link>`, or C an artboard
   `--u` unit. Text the visitor reads stays in real px in all three.
6. Build the mechanic in `campaign/main.js` and `campaign/main.css`. Classes
   are `cmp-`; the shell owns `tw-`. The mechanic reaches the shell only
   through `window.TW`, and the win calls `TW.openForm()`.
7. Art: sources into `raw/` (gitignored), `python tools/optimize.py`, commit
   the outputs. See `references/art.md`.
8. Ship: `references/checklist.md`, then push. Set the repository's Pages
   source to "GitHub Actions" and verify `tools/` 404s on the live URL.

`CAMPAIGN.md` in the repo root is the same procedure written out for a person,
with the exact commands. Follow it; these eight steps are the map.

## Composition with installed skills

**Use:**

- `superpowers:brainstorming` — for the **mechanic spec only**. Invoke it with:
  "Brainstorm only the hero game mechanic for this TopWin landing page.
  Everything else in this document is already decided, do not brainstorm it:
  colours, typography, layout modes, the header, the footer, the registration
  dialog, i18n, the seams and the deploy."
- `superpowers:verification-before-completion` — at the ship gate, over
  `references/checklist.md`. Evidence before claims: paste the guards' output.
- `animate` — for **new** motion only, never to revisit existing motion. Quote
  the template's constraints into the invocation: one curve, `--ease-out`;
  entry slower than exit; `prefers-reduced-motion` degrades and never removes;
  no `filter` or `box-shadow` on a node that rotates in 3D; `[hidden]` is a
  two-step because `display` cannot be transitioned.

**Forbidden:**

- `ui-ux-pro-max:design-system` and `ui-ux-pro-max:brand`. They derive a scale,
  a palette and a naming convention. TopWin has all three, arbitrated in
  writing in `css/tokens.css`. Running them produces a fifth orange.

**Ignore:**

- `ui-ux-pro-max:design`, `apple-design`, `emil-design-eng` — real taste, but
  general. This project's defect is too many sources of taste; a third is not
  the fix.
- `superpowers:test-driven-development` — no framework, no `package.json`, no
  runner. Verification is the four guards in `tools/`.

TEMPLATE-REV: v1.0.1 — before starting, compare this against the template's
HEAD tag; if they differ, read the template's diff before trusting any path or
value quoted here.
