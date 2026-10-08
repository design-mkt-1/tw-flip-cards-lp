/* tw-flip-cards — the campaign's own configuration.

   The registration card on this page is tw-lp-template's, file for file:
   css/tokens.css, css/form.css, js/strings.js, js/i18n.js, js/form.js and
   js/shell.js are that repo's, unmodified. This file is where the campaign
   speaks to them — the offer, the links, the form seam, the copy that is
   this campaign's rather than the shell's.

   Never edit those six. If one of them genuinely needs a change, it is made
   in tw-lp-template, SHARED.lock is bumped there, and the change is pulled
   down. That is the whole reason the card is shared code and not a second
   implementation kept equal by eye: this landing and tw-penalty had drifted
   into two different oranges, two different checkbox defaults and two
   different close buttons before it was.

   The mechanic — the nine cards, the deck, the flip — stays in js/flip.js and
   is configured there. It reaches the card through one seam: TWForm.open().
   ─────────────────────────────────────────────────────────────────────── */

window.TW_CAMPAIGN = {

  id: 'tw-flip-cards',

  /* ── The offer ────────────────────────────────────────────────
     NUMBERS ONLY; the words are in `strings` below and interpolate
     {percent} {amount} {currency} {spins}.

     hero: 'amount' — this is a casino offer and the money is the headline,
     where the sportsbook landing leads with a percent. The shell draws the
     hero figure large in Orange Fire and drops it to the smaller step
     because "250.000 ₴" is longer than five characters. See
     tw-lp-template CHANGELOG v1.0.4.

     currency is the hryvnia sign, which Roboto has at no weight: it is
     served from the two one-glyph Noto cuts in assets/fonts/, and
     `python tools/fonts.py --check` is what proves it still is. */
  offer: {
    percent:  '',
    amount:   '250.000',
    currency: '₴',
    spins:    '250',
    hero:     'amount',
    code:     '250000+250'   // what the platform is told; payload field `bonus`
  },

  /* ── Where the buttons go ─────────────────────────────────────
     '' leaves the anchor with NO href, so it is not a link at all: no tab
     stop, nothing announced, nothing to click. Never write '#'.

     terms and privacy BLOCK GO-LIVE. The card collects an 18+ consent, and
     consent text with no documents behind it is a compliance problem, not a
     cosmetic one. These four were CONFIG.termsUrl / privacyUrl / loginUrl /
     siteUrl in js/flip.js until the card became shared code. */
  links: {
    home:    '',
    login:   '',
    terms:   '',
    privacy: '',
    cta:     ''
  },

  /* Appended to every outbound link and copied onto the form payload. */
  params: {
    // utm_source:   'facebook',
    // utm_medium:   'cpc',
    // utm_campaign: 'flip-cards'
  },

  /* Query parameters on THIS page's URL that ride through to the outbound
     click — how an affiliate click id survives the landing. */
  passthrough: ['click_id', 'sub1', 'sub2', 'gclid', 'fbclid', 'ttclid'],

  /* Both empty means not one third-party request. Setting either also needs
     the CSP <meta> in index.html swapped for the analytics one. */
  analytics: {
    gtmId:       '',
    metaPixelId: '',
    debug:       false
  },

  /* ── The registration form ────────────────────────────────────
     endpoint '' means nothing is sent: the validated payload goes to
     console.info and, with demoDone true, the confirmation screen is walked
     anyway. IT sets `endpoint` and the form POSTs JSON to it; a response
     carrying { login, password } fills the confirmation screen.
     `onRegister(payload)` is the escape hatch and overrides `endpoint`.

     The payload carries the password, so `endpoint` must be the operator's
     own TLS endpoint and nowhere else. */
  form: {
    endpoint:     '',
    /* js/platform.js owns the registration: config, landing, reCAPTCHA, the
       POST and the SSO redirect. It overrides `endpoint`, which stays empty. */
    onRegister:   function (payload) { return window.TWPlatform.register(payload); },
    /* landing_id is NOT here any more: the platform's numeric id comes from
       config.json, and a string of ours would only compete with it. Anything
       put here is copied onto the request body BEFORE the platform's own
       fields, so it can add a field but never overwrite one. */
    hiddenFields: {},
    demoDone:     true,
    dialCode:     '+380',
    dialFlag:     'assets/img/icons/flag-ua.svg',
    phoneDigits:  9,
    passwordMin:  8
  },

  /* ── The IT platform (js/platform.js) ─────────────────────────
     In production the page reads `configUrl` from its own root:
       { "id": <number>, "email_registration": "<url>", "landing": "<url>" }
     Without that file the page is NOT connected: the form walks the demo
     confirmation screen and says so in the console.

     `dev` is IT's own TEMP_CONFIG, copied from their landing
     (_js/enums/enums.js) so this page can be tried before a real id exists.
     It is used ONLY on localhost, 127.0.0.1 or an origin starting with
     https://land-crm. TEMP: id 8 is IT's landing, not ours; replace it, or
     delete `dev`, once IT issues the real landing_id.

     supportEmail is shown on the "unavailable" card; IT hardcodes it. */
  platform: {
    configUrl:    'config.json',
    supportEmail: 'support@jack-pot.com',
    dev: {
      id: 8,
      email_registration: 'https://api2-land-dev.jack-pot.tech/api/jp/registration/email',
      landing:            'https://api2-land-dev.jack-pot.tech/api/jp/landing/8'
    }
  },

  /* ── Languages ────────────────────────────────────────────────
     All three, in header-menu order, and ONE HTML file for all of them.
     The menu swaps the table in place, the choice is kept in localStorage
     under 'tw-lang', and ?lang=ru forces one for an ad creative — the
     template's model, in js/i18n.js.

     There is no `languageUrls` here any more. This landing shipped three
     pre-translated HTML files until 2026-09-07, which meant the menu was a
     navigation control: picking a language reloaded the page. It also meant
     two CI jobs whose entire purpose was to notice that three copies of the
     same page had drifted apart. One file cannot drift from itself.

     'ua' is the internal code and 'uk' the real language tag; the map is in
     js/strings.js § TW_LOCALES, and <html lang> carries the tag. */
  languages: ['ua', 'ru', 'en'],

  /* ── Brand and chrome ─────────────────────────────────────────
     The bar and the footer are the shared ones now, built by js/shell.js
     into the two <div data-tw> markers in each HTML file. The landing drew
     its own footer until 2026-09-07 and had no header at all — three Top Win
     pages, three footers of three different heights.

     No mute: this mechanic has no audio, and a speaker that toggles nothing
     is worse than no speaker. themeColor stays unset because the <meta> in
     each head is already this campaign's. */
  brand: {
    logo:     'assets/img/logo-topwin.svg',
    logoAlt:  'TopWin',
    payments: ['visa', 'mastercard', 'tether', 'bitcoin']
  },
  header: { show: true, mute: false, lang: true },
  footer: { show: true },

  /* No audio in this mechanic, so no speaker and no pool. */
  sounds: {},

  /* ── Campaign copy ────────────────────────────────────────────
     ONLY what this campaign owns. Everything else the card says — the tabs,
     the fields, the errors, the consent sentence, the confirmation screen —
     is in js/strings.js and is the same in every campaign.

     Two overrides, both deliberate:
       promo.title  — this is the casino bonus, not the sports one
       promo.amount — the shipped string is 'до {amount} {currency}', a
                      qualifier under a headline. Here the amount IS the
                      headline, so it is the figure alone.

     The five page keys below are this landing's own copy — the document
     title, the hero, the board's label and the claim button. The footer's two
     lines used to be here too; they are the shell's now (footer.pay /
     footer.copy in js/strings.js), which is what "the same footer everywhere"
     means.

     Four of the five are ALSO written into index.html as real text, which is
     what paints before any script runs and what a crawler reads; js/i18n.js
     then renders the same words from here. Change one, change both.

     'title' is the fifth and is the <title data-i18n="title"> in the head.
     There is no matching <meta name="description"> key: a meta is not a
     data-i18n node, nothing re-renders it, and the description stays in the
     default locale. Ukrainian is that locale because it is first in
     `languages` above. */
  strings: {
    ua: {
      'title':           'TopWin — Переверни картки, забери свій бонус!',
      'promo.title':     'Вітальний казино бонус',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Переверни картки',
      'hero.2':          'забери свій бонус!',
      'game.label':      'Переверніть три картки та заберіть вітальний бонус',
      'pl.off.title':   'Сторінка тимчасово недоступна',
      'pl.off.text':    'Реєстрація зараз закрита. Спробуйте пізніше або напишіть нам:',
      'err.exists':     'Цей email уже зареєстровано. Увійдіть в акаунт',
      'err.recaptcha':  'Не вдалося пройти перевірку безпеки. Спробуйте ще раз',
      'cta.claim':       'Забрати бонус'
    },
    ru: {
      'title':           'TopWin — Переверни карты, забери свой бонус!',
      'promo.title':     'Приветственный казино бонус',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Переверни карты',
      'hero.2':          'забери свой бонус!',
      'game.label':      'Переверните три карты и заберите приветственный бонус',
      'pl.off.title':   'Страница временно недоступна',
      'pl.off.text':    'Регистрация сейчас закрыта. Попробуйте позже или напишите нам:',
      'err.exists':     'Этот email уже зарегистрирован. Войдите в аккаунт',
      'err.recaptcha':  'Не удалось пройти проверку безопасности. Попробуйте ещё раз',
      'cta.claim':       'Забрать бонус'
    },
    en: {
      'title':           'TopWin — Flip the cards, claim your bonus!',
      'promo.title':     'Welcome casino bonus',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Flip the cards',
      'hero.2':          'claim your bonus!',
      'game.label':      'Turn three cards and claim your welcome bonus',
      'pl.off.title':   'This page is temporarily unavailable',
      'pl.off.text':    'Registration is closed right now. Please try again later or write to us:',
      'err.exists':     'This email is already registered. Please log in',
      'err.recaptcha':  'The security check failed. Please try again',
      'cta.claim':       'Claim bonus'
    }
  }
};
