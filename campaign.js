/* ═══════════════════════════════════════════════════════════════
   THE CAMPAIGN FILE

   This is the only file a new campaign edits, apart from campaign/main.js
   (the mechanic), campaign/assets/ (its art) and the <main> block in
   index.html.

   Nothing in js/ or css/ should be touched. `python tools/drift.py` fails CI
   if it is, and a change that genuinely belongs to every campaign belongs in
   the template repo, not in a clone — that is exactly how the last two
   landings ended up with four different oranges.

   Every key below ships with a working default and a comment saying what it
   does. Empty string means "not set", and every consumer treats it as an
   absence rather than as an empty value: an unset link is not a dead link,
   an unset endpoint is not a broken form.
   ═══════════════════════════════════════════════════════════════ */

window.TW_CAMPAIGN = {

  /* ── Identity ─────────────────────────────────────────────────
     `id` rides on the form payload as landing_id and on every analytics
     event. Use the repo name. */
  id: 'tw-flip-cards-lp',

  /* ── The offer ────────────────────────────────────────────────
     NUMBERS ONLY. The words around them live in `strings` below, once per
     locale, and interpolate {percent} {amount} {currency} {spins}.

     Written here once and never repeated per language. Changing the offer
     from 225% / 15000 to 300% / 20000 is a two-value edit in this block and
     no language table is touched.

     currency: 'UAH' is safe everywhere. '₴' also works — the template ships
     the two one-glyph Noto cuts that carry U+20B4, because Roboto has none at
     any weight and a missing glyph still renders something. If you change
     currency, run `python tools/fonts.py --check`.

     spins: '' hides the "+ N FS" line entirely. */
  offer: {
    percent:  '',            // this campaign leads with the amount, not a %
    amount:   '250.000',
    currency: '₴',           // U+20B4; the two Noto cuts in assets/fonts carry it
    spins:    '250',
    code:     'CARDS250K'    // what the platform is told; payload field `bonus`
  },

  /* ── Where the buttons go ─────────────────────────────────────
     '' leaves the anchor WITHOUT an href, so it is not a link at all: no tab
     stop, nothing announced, nothing to click. Never write href="#" — a mark
     that takes focus and then does nothing reads as a broken control.

       home     header logo
       login    "Already have an account? Log in", under the CTA
       terms    consent sentence, first link          ← BLOCKS GO-LIVE
       privacy  consent sentence, second link         ← BLOCKS GO-LIVE
       cta      the done screen's "GO TO WEBSITE" button

     terms and privacy block go-live because the page collects an 18+ consent.
     Dead consent links on a gambling registration form are a compliance
     problem, not a cosmetic one. */
  links: {
    home:    '',
    login:   '',
    terms:   '',
    privacy: '',
    cta:     ''
  },

  /* ── Tracking and affiliate ───────────────────────────────────
     `params` is appended to every URL in `links` above and copied into the
     form payload.

     `passthrough` names query parameters on THIS page's URL that ride through
     to the outbound click. That is how an affiliate click id survives the
     landing page: the ad network puts ?click_id=… on the landing URL, and the
     visitor arrives at the operator with the same id attached. Neither of the
     two earlier landings had this and the ids were lost. */
  params: {
    // utm_source:   'facebook',
    // utm_medium:   'cpc',
    // utm_campaign: 'demo-225'
  },
  passthrough: ['click_id', 'sub1', 'sub2', 'gclid', 'fbclid', 'ttclid'],

  /* ── Analytics ────────────────────────────────────────────────
     Both empty is the shipped default, and with both empty NOT ONE
     third-party request is made — which is why the CSP in index.html can stay
     'self'.

     If you set gtmId or metaPixelId you MUST also swap the CSP <meta> in
     index.html for the commented analytics line. A <meta> policy cannot be
     written from JavaScript, so this is the one edit that lives outside this
     file. A CSP refusal appears only in the console; the page looks fine and
     silently sends nothing.

     debug: true logs every TW.track() call instead of needing a tag
     assistant. */
  analytics: {
    gtmId:       '',
    metaPixelId: '',
    debug:       false
  },

  /* ── The registration form ────────────────────────────────────
     endpoint '' is the shipped default and means nothing is sent: the
     validated payload goes to console.info and, with demoDone true, the
     confirmation screen is walked anyway. The page is fully demoable before
     the platform exists, and it cannot silently half-ship.

     When IT is ready they set `endpoint` and the form POSTs JSON to it. A
     response carrying { login, password } fills the confirmation screen.
     `onRegister(payload)` is the escape hatch for anything more involved; it
     returns a promise and overrides `endpoint`.

     The password is in the payload, because a registration hook without one
     is useless — which means `endpoint` must point at the operator's own
     TLS endpoint and nowhere else.

     dialFlag is an SVG file, not an emoji: Windows renders 🇺🇦 as the
     letters "UA". */
  form: {
    endpoint:     '',
    onRegister:   null,
    hiddenFields: { landing_id: 'tw-flip-cards-lp' },
    demoDone:     true,
    dialCode:     '+380',
    dialFlag:     'assets/img/icons/flag-ua.svg',
    phoneDigits:  9,
    passwordMin:  8
  },

  /* ── The deck ─────────────────────────────────────────────────
     The nine cards, three per tier. The mechanic reads this through
     TW.config.deck; the top tier is not written here at all, it is built from
     `offer` above, so changing the offer changes the card the visitor wins
     and the figure in the dialog together.

     THIS BLOCK LIVES HERE FOR A REASON. tools/fonts.py reads js/strings.js,
     campaign.js and index.html — nothing else. A prize string kept in
     campaign/main.js would be text no glyph check has ever seen, which is
     exactly how ₴ once shipped in a font that has no hryvnia at any weight.

     `id` is what the mechanic compares against, `amount`/`spins` are what the
     card face shows. Nine entries, and the top tier's three come from the
     offer. */
  deck: [
    { id: 'p50k', amount: '50.000',  spins: '150' },
    { id: 'p50k', amount: '50.000',  spins: '150' },
    { id: 'p50k', amount: '50.000',  spins: '150' },
    { id: 'p25k', amount: '25.000',  spins: '50'  },
    { id: 'p25k', amount: '25.000',  spins: '50'  },
    { id: 'p25k', amount: '25.000',  spins: '50'  }
  ],

  /* ── Languages ────────────────────────────────────────────────
     Order is the order of the header menu. THE FIRST ENTRY IS THE DEFAULT
     AND THE FALLBACK, so its tables have to be complete.

     Every code listed needs an entry in js/strings.js (TW_STRINGS and
     TW_LOCALES) and in `strings` below. tools/smoke.py fails on any key that
     renders as its own key. */
  languages: ['ua', 'ru', 'en'],

  /* ── Brand and chrome ─────────────────────────────────────────
     These are the same in every TopWin campaign and are here only because a
     campaign occasionally needs one of them: header.mute should be false for
     a campaign with no audio, so the bar does not render a dead speaker. */
  brand: {
    logo:       'assets/img/logo-topwin.svg',
    logoAlt:    'Top Win',
    themeColor: '#00002e',                    // --navy-950
    payments:   ['visa', 'mastercard', 'tether', 'bitcoin']
  },
  header: { show: true, mute: false, lang: true },
  footer: { show: true },

  /* ── Campaign copy, per locale ────────────────────────────────
     ONLY the strings this campaign owns. Everything the header, the footer
     and the registration dialog say lives in js/strings.js and is never
     copied here — this table is merged OVER that one, so anything repeated
     here is a fork waiting to happen.

     Override a shell key deliberately if a campaign needs different words
     (a casino campaign wanting 'promo.title' to say casino rather than
     sports), and only then.

     \n is a real line break in the rendered text. Do not put markup in a
     string; if a sentence needs a link inside it, split it the way
     agree.pre / agree.terms / agree.mid / agree.privacy / agree.post are
     split in js/strings.js. */
  strings: {
    ua: {
      'title':        'Top Win — Переверни картки, забери свій бонус!',
      'hero.1':       'Переверни картки',
      'hero.2':       'забери свій бонус!',
      'game.label':   'Переверніть три картки та заберіть вітальний бонус',
      'cta.claim':    'Забрати бонус',

      /* The card faces and the live region. {amount} {currency} {spins} come
         from `offer`; {n} and {prize} the mechanic passes in. */
      'card.back':    'Картка {n} з 9, сорочкою вгору. Натисніть, щоб перевернути.',
      'card.front':   'Картка {n}: {prize}.',
      'card.win':     'Картка {n}: {prize}. Виграно!',
      'card.fs':      'FS',
      'prize.top':    '{amount} {currency} плюс {spins} фріспінів',
      'prize.p50k':   '50 тисяч гривень плюс 150 фріспінів',
      'prize.p25k':   '25 тисяч гривень плюс 50 фріспінів',
      'progress':     'Перевернуто {n} з 3 карток',
      'win':          'Усі три картки перевернуто. Відкриваємо форму реєстрації.',

      /* Two shell keys this campaign owns different words for: it is a casino
         offer, not a sports one, and the figure is the amount rather than a
         percentage. */
      'promo.title':  'Вітальний казино бонус',
      'promo.amount': '{amount} {currency}'
    },
    ru: {
      'title':        'Top Win — Переверни карты, забери свой бонус!',
      'hero.1':       'Переверни карты',
      'hero.2':       'забери свой бонус!',
      'game.label':   'Переверните три карты и заберите приветственный бонус',
      'cta.claim':    'Забрать бонус',

      'card.back':    'Карта {n} из 9, рубашкой вверх. Нажмите, чтобы перевернуть.',
      'card.front':   'Карта {n}: {prize}.',
      'card.win':     'Карта {n}: {prize}. Выиграно!',
      'card.fs':      'FS',
      'prize.top':    '{amount} {currency} плюс {spins} фриспинов',
      'prize.p50k':   '50 тысяч гривен плюс 150 фриспинов',
      'prize.p25k':   '25 тысяч гривен плюс 50 фриспинов',
      'progress':     'Перевёрнуто {n} из 3 карт',
      'win':          'Все три карты перевёрнуты. Открываем форму регистрации.',

      'promo.title':  'Приветственный казино бонус',
      'promo.amount': '{amount} {currency}'
    },
    en: {
      'title':        'Top Win — Flip the cards, claim your bonus!',
      'hero.1':       'Flip the cards',
      'hero.2':       'claim your bonus!',
      'game.label':   'Turn three cards and claim your welcome bonus',
      'cta.claim':    'Claim bonus',

      'card.back':    'Card {n} of 9, face down. Press to flip.',
      'card.front':   'Card {n}: {prize}.',
      'card.win':     'Card {n}: {prize}. Won!',
      'card.fs':      'FS',
      'prize.top':    '{amount} {currency} plus {spins} free spins',
      'prize.p50k':   '50 thousand hryvnia plus 150 free spins',
      'prize.p25k':   '25 thousand hryvnia plus 50 free spins',
      'progress':     'Turned {n} of 3 cards',
      'win':          'All three cards turned. Opening the registration form.',

      'promo.title':  'Welcome casino bonus',
      'promo.amount': '{amount} {currency}'
    }
  }
};
