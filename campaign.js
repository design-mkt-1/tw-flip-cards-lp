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
     the CSP <meta> in all three HTML files swapped for the analytics one. */
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
    onRegister:   null,
    hiddenFields: { landing_id: 'tw-flip-cards' },
    demoDone:     true,
    dialCode:     '+380',
    dialFlag:     'assets/img/icons/flag-ua.svg',
    phoneDigits:  9,
    passwordMin:  8
  },

  /* ── Language ─────────────────────────────────────────────────
     ONE entry, and it is the page's own — this landing serves three HTML
     files, one per language, each pre-translated, with hreflang between
     them. js/i18n.js only ever selects a code that appears here, so on
     ru.html neither a stale localStorage entry nor ?lang=en can leave the
     card speaking a different language than the page around it.

     'ua' is the internal code and 'uk' the real language tag; the map is in
     js/strings.js § TW_LOCALES, and <html lang> gets the tag. */
  languages: [{ uk: 'ua', ru: 'ru', en: 'en' }[document.documentElement.lang] || 'ua'],

  /* ── Brand and chrome ─────────────────────────────────────────
     header and footer are this landing's own markup, in the three HTML
     files, so the shell must not draw its own: with show:false js/shell.js
     mounts the dialog and nothing else. themeColor is left unset for the
     same reason — the <meta> in the head is already this campaign's. */
  brand: {
    logo:    'assets/img/logo-topwin.svg',
    logoAlt: 'TopWin'
  },
  header: { show: false },
  footer: { show: false },

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

     The six page keys below are this landing's own copy — the hero, the
     board's label, the claim button, the footer. They are ALSO written into
     the three HTML files as real text, which is what paints before any
     script runs and what a crawler reads; js/i18n.js then renders the same
     words from here. Change one, change both. */
  strings: {
    ua: {
      'promo.title':     'Вітальний казино бонус',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Переверни картки',
      'hero.2':          'забери свій бонус!',
      'game.label':      'Переверніть три картки та заберіть вітальний бонус',
      'cta.claim':       'Забрати бонус',
      'footer.payments': 'Способи оплати',
      'footer.rights':   '© 2026 Усі права захищені'
    },
    ru: {
      'promo.title':     'Приветственный казино бонус',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Переверни карты',
      'hero.2':          'забери свой бонус!',
      'game.label':      'Переверните три карты и заберите приветственный бонус',
      'cta.claim':       'Забрать бонус',
      'footer.payments': 'Способы оплаты',
      'footer.rights':   '© 2026 Все права защищены'
    },
    en: {
      'promo.title':     'Welcome casino bonus',
      'promo.amount':    '{amount} {currency}',
      'hero.1':          'Flip the cards',
      'hero.2':          'claim your bonus!',
      'game.label':      'Turn three cards and claim your welcome bonus',
      'cta.claim':       'Claim bonus',
      'footer.payments': 'Payment methods',
      'footer.rights':   '© 2026 All rights reserved'
    }
  }
};
