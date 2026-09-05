# Seams

Everything a campaign is allowed to wire, and what reads it. `''` always means
"not set", and every consumer treats it as an absence rather than as an empty
value: an unset link is not a dead link, an unset endpoint is not a broken form.

## The `campaign.js` contract

| key | read by | empty means |
|---|---|---|
| `id` | `js/shell.js § track()`, `js/form.js § payload()` | `landing_id` rides as `''` on every payload and event |
| `offer.percent` | `promo.pct` via `{percent}` | the `.tw-promo__pct` node is not rendered |
| `offer.amount` | `promo.amount` via `{amount}` | the amount line is not rendered |
| `offer.currency` | `promo.amount` via `{currency}` | the amount reads without a unit |
| `offer.spins` | `promo.spins` via `{spins}` | the "+ N FS" line is hidden entirely |
| `offer.code` | `js/form.js § payload()` as `bonus` | the platform is told no bonus code |
| `links.home` | header logo | the logo is not a link — no `href`, no tab stop |
| `links.login` | "Already have an account?" under the CTA | the anchor is not a link |
| `links.terms` | consent sentence, first link | **BLOCKS GO-LIVE** |
| `links.privacy` | consent sentence, second link | **BLOCKS GO-LIVE** |
| `links.cta` | the done screen's "GO TO WEBSITE" button | the button is inert |
| `params` | `js/shell.js § params()` → every `links` URL and the payload | no query appended, nothing added to the payload |
| `passthrough` | `js/shell.js`, read once at boot | nothing rides through from the landing URL |
| `analytics.gtmId` | `js/shell.js § injectAnalytics()` | GTM is not injected; no request |
| `analytics.metaPixelId` | same | the pixel is not injected; no request |
| `analytics.debug` | `js/shell.js § track()` | `TW.track()` logs nothing |
| `form.endpoint` | `js/form.js § onSubmit()` | nothing is sent; payload to `console.info` |
| `form.onRegister` | same, checked first | falls through to `endpoint` |
| `form.hiddenFields` | `js/form.js § payload()` | nothing extra on the payload |
| `form.demoDone` | `js/form.js § onSubmit()` | with nothing wired, the done screen is not walked |
| `form.dialCode` | phone prefix, and phone normalisation | defaults to `+380` |
| `form.dialFlag` | the flag beside the prefix — a file path, never an emoji | no flag image |
| `form.phoneDigits` | `js/form.js § phoneDigits()` | defaults to 9 |
| `form.passwordMin` | `js/form.js § CHECK.password` | defaults to 8 |
| `languages` | `js/i18n.js`, `js/shell.js § headerHTML()`, `tools/smoke.py` | defaults to `['ua']`; **the first entry is the default AND the fallback** |
| `brand.logo` | header, footer and the dialog's promo header | broken image in three places |
| `brand.logoAlt` | the same three | defaults to `Top Win` |
| `brand.themeColor` | overwrites the `theme-color` meta at boot | the static meta stands |
| `brand.payments` | `js/shell.js § PAY` table → footer badges | no payment row |
| `header.show` / `footer.show` | `js/shell.js § mountSlot()` | `false` removes the slot entirely |
| `header.mute` | the speaker button's markup | omitted, not disabled — no dead speaker |
| `header.lang` | the language listbox markup | omitted; also omitted with one language |
| `strings` | `js/i18n.js § tableFor()`, merged **over** `TW_STRINGS` | the shell's own copy stands |

Only override a `TW_STRINGS` key here deliberately — a casino campaign wanting
`promo.title` to say casino rather than sports. Anything else repeated here is
a fork waiting to happen.

## The form-submission seam

Precedence, checked in this order in `js/form.js § onSubmit()`:

1. `form.onRegister(payload)` if it is a function. It returns a promise and
   overrides `endpoint`. Resolve with `{ login, password }` to fill the
   confirmation screen; resolve with anything else and the screen falls back to
   what the visitor typed.
2. `form.endpoint` — a JSON POST with `Content-Type: application/json`. A
   non-2xx throws; the response is parsed as JSON if it parses. `err.network`
   is shown on rejection.
3. Neither — **the shipped default**. The validated payload goes to
   `console.info` with the text "not wired to anything", and with
   `form.demoDone: true` the confirmation screen is walked anyway. Loud in the
   console, invisible to the visitor, impossible to mistake for a working
   integration. That string is the one entry on `tools/smoke.py`'s console
   ignore-list.

The payload carries `method`, `contact`, `email`, `phone`, `password`,
`consent`, `lang` (the **BCP-47 tag**, not the internal code), `bonus`,
`landing_id`, then `hiddenFields`, then `TW.params()`. The password is in it,
which is why `endpoint` must point at the operator's own TLS endpoint and
nowhere else.

## The tracking seam

`params` is appended to every URL in `links` and copied into the form payload.
`passthrough` names query parameters on **this** page's URL that ride through to
the outbound click — it is read once at boot, because a mechanic may replace the
query string later and the affiliate click id has to survive that. Passed-in
values win over the campaign's own on key collision.

`TW.track(event, props)` always runs. It adds `landing_id`, `lang` and the
merged params to every payload, pushes to `dataLayer` if GTM is present, calls
`fbq('trackCustom', …)` if the pixel is present, and logs when
`analytics.debug` is true. With no id configured it does everything except
reach the network.

Events the template fires by itself:

| event | fired at |
|---|---|
| `lp_view` | end of boot, `js/shell.js § boot()` |
| `lang_change` | every language change, with `{ to }` |
| `form_submit` | validation passed, with `{ method }` |
| `form_success` | the send resolved, with `{ method }` |

`game_win` is fired by the demo mechanic in `campaign/main.js`, not by the
shell — it is the example, and a campaign names its own.

`TW.on(name, fn)` subscribes to the four events the shell emits: `register`
(the confirmation screen filled, with the result object), `lang` (the new
code), `formopen`, `formclose`. A listener that throws is caught and reported,
so a campaign hook cannot strand the visitor in a half-open dialog.

## The five URL seams

`home`, `login`, `terms`, `privacy`, `cta`. `js/shell.js § wireLinks()` sets
`href` when `TW.url(name)` returns a string and **removes** the attribute when
it returns null. An element with no `href` is simply not a link — no tab stop,
nothing announced. Never write `href="#"`; `tools/smoke.py` fails on it.

`terms` and `privacy` block go-live. The page collects an 18+ consent, and dead
consent links on a gambling registration form are a compliance problem.

## The analytics CSP swap

`index.html` ships a policy of `'self'` and `'none'` throughout, which is only
correct because the default campaign makes zero third-party requests. Setting
`analytics.gtmId` or `analytics.metaPixelId` means commenting out that `<meta>`
and uncommenting the analytics one directly below it, which adds
`googletagmanager.com` and `connect.facebook.net` to `script-src` and the
matching image and connect origins.

This cannot live in `campaign.js`: **a `<meta>` policy cannot be written from
JavaScript.** It is parsed with the document, long before any script runs. A
refusal appears only in the console, so the page looks fine and silently sends
nothing.

`form-action` is deliberately absent from both policies, and it does not fall
back to `default-src` — that is what leaves the form free to POST wherever IT
wires `form.endpoint`. `frame-ancestors` is absent because browsers ignore it in
a meta policy; writing it would only look like protection.

## `window.TW` — the complete surface

Read out of `js/shell.js § window.TW`. This is all of it; the mechanic reaches
the shell through this object and nothing else.

```
TW.config                 the parsed campaign.js
TW.t(key, vars)           translated string, {name} filled from vars and offer
TW.lang()                 current internal code, '' before i18n boots
TW.setLang(code)          change it
TW.url(name)              links.<name> with params appended, or null
TW.params()               campaign params merged with the passthrough
TW.openForm()             open the registration dialog
TW.closeForm()
TW.showDone(res)          fill and show the confirmation screen directly
TW.track(event, props)
TW.on(name, fn)           'register' | 'lang' | 'formopen' | 'formclose'
TW.emit(name, data)
TW.ready(fn)              run once the chrome is mounted and i18n applied
```

`window.TWForm` (`mount`, `open`, `close`, `showDone`, `isOpen`) and
`window.TWI18n` (`init`, `t`, `set`, `apply`, `langs`, `current`, `tag`,
`onChange`) exist because the shared files talk to each other. A campaign uses
`TW`.
