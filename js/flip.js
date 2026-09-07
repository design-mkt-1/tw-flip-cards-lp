/* ==========================================================================
   TopWin — Flip the Cards
   Plain JavaScript, no dependencies, no build step.

   Everything you need to change during integration is in CONFIG below,
   between the IT INTEGRATION markers. Nothing else in this file is meant to
   be edited.
   ========================================================================== */

(function () {
  'use strict';

  var CONFIG = {

    /* Everything IT wires — the form endpoint, the four link destinations,
       the hidden fields, the phone country, the bonus code — moved to
       campaign.js when the registration card became tw-lp-template's. This
       file is the mechanic and nothing else now. See README.md section 1. */

    /* ── Game. Marketing can tune these. ─────────────────────────────── */

    winPrizeId: 'p250k',     // the prize the visitor is hunting for
    winTarget:  3,           // how many of them the visitor has to turn

    /* The visitor goes 3 of 3: every card they turn lands the top prize, so
       there is no miss and no hunt. It is what the campaign asks for — a
       short, certain path to the form — not an accident of the deck.

       The prize is assigned at flip time, in promote(), rather than at build
       time. The six they never turn are dealt the losing tiers and open at
       the end, dimmed, so the board finishes showing exactly three top prizes
       with the ladder they were playing against behind them.

       Set this to false for the original game, where three winners are hidden
       among nine and the deck below sets the odds. */
    alwaysWin: true,

    /* Nine cards: three of each prize. They must add up to nine. The counts
       set the odds only when alwaysWin is false; while it is true the deck is
       just where the card text and the six unseen losing faces come from.
       The three tiers are the card variants the design draws — winning /
       not_win_1 / not_win_2 (Figma 12:287, 29:584, 29:592) — which is why the
       top card matches the dialog's offer. */
    deck: [
      { id: 'p250k', pct: '250.000 ₴', fs: '250' },
      { id: 'p250k', pct: '250.000 ₴', fs: '250' },
      { id: 'p250k', pct: '250.000 ₴', fs: '250' },
      { id: 'p50k',  pct: '50.000 ₴',  fs: '150' },
      { id: 'p50k',  pct: '50.000 ₴',  fs: '150' },
      { id: 'p50k',  pct: '50.000 ₴',  fs: '150' },
      { id: 'p25k',  pct: '25.000 ₴',  fs: '50'  },
      { id: 'p25k',  pct: '25.000 ₴',  fs: '50'  },
      { id: 'p25k',  pct: '25.000 ₴',  fs: '50'  }
    ],

    /* A card that is not the top prize stays face up. Everyone reaches the
       form, which is the point of a campaign page. Set this to a number of
       milliseconds if you want wrong cards to turn back over instead. */
    flipBackMs: 0,

    passwordMinLength: 8
  };


  /* ======================================================================
     Runtime strings. These are the only texts not written in the HTML,
     because they depend on what the visitor has done.
     ====================================================================== */

  var MESSAGES = {
    uk: {
      /* Latin FS, not ФС: the Ukrainian artboards write it that way on both
         the cards and the dialog's offer block. */
      fsLabel:    'FS',
      cardBack:   'Картка {n} з 9, сорочкою вгору. Натисніть, щоб перевернути.',
      cardFront:  'Картка {n}: {prize}.',
      cardWin:    'Картка {n}: {prize}. Виграно!',
      p250k: '250 тисяч гривень плюс 250 фріспінів',
      p50k:  '50 тисяч гривень плюс 150 фріспінів',
      p25k:  '25 тисяч гривень плюс 50 фріспінів',
      /* Turned, not found. Under CONFIG.alwaysWin every card the visitor
         turns is the top prize, so there is nothing hidden to search for and
         "знайдено" would describe a game that is no longer being played. */
      progress:   'Перевернуто {n} з 3 карток',
      win:        'Усі три картки перевернуто. Відкриваємо форму реєстрації.',
      errPassword:'Пароль має містити щонайменше {n} символів',
    },
    ru: {
      fsLabel:    'FS',
      cardBack:   'Карта {n} из 9, рубашкой вверх. Нажмите, чтобы перевернуть.',
      cardFront:  'Карта {n}: {prize}.',
      cardWin:    'Карта {n}: {prize}. Выиграно!',
      p250k: '250 тысяч гривен плюс 250 фриспинов',
      p50k:  '50 тысяч гривен плюс 150 фриспинов',
      p25k:  '25 тысяч гривен плюс 50 фриспинов',
      progress:   'Перевёрнуто {n} из 3 карт',
      win:        'Все три карты перевёрнуты. Открываем форму регистрации.',
      errPassword:'Пароль должен содержать не менее {n} символов',
    },
    en: {
      fsLabel:    'FS',
      cardBack:   'Card {n} of 9, face down. Press to flip.',
      cardFront:  'Card {n}: {prize}.',
      cardWin:    'Card {n}: {prize}. Won!',
      p250k: '250 thousand hryvnia plus 250 free spins',
      p50k:  '50 thousand hryvnia plus 150 free spins',
      p25k:  '25 thousand hryvnia plus 50 free spins',
      progress:   'Turned {n} of 3 cards',
      win:        'All three cards turned. Opening the registration form.',
      errPassword:'Password must be at least {n} characters',
    }
  };


  /* ======================================================================
     Utilities
     ====================================================================== */

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* One table so every delay in the win sequence comes from one place, and
     reduced motion shortens the whole thing rather than leaving dead air. */
  function timing() {
    return reduceMotion.matches
      ? { flip: 220, hold:  80, reveal:   0 }
      : { flip: 520, hold: 240, reveal: 240 };
  }

  /* The table is looked up on every call, never captured once.

     Until 2026-09-07 this landing served one pre-translated HTML file per
     language, so the language could not change after load and freezing it
     here was safe. It serves ONE file for all three now, and the header menu
     swaps the table in place: a captured `M` would leave every card's
     accessible name and every progress announcement in whichever language the
     visitor happened to arrive in, for the rest of the session. Nothing would
     look wrong on screen -- the nine cards draw digits -- which is exactly why
     it has to be a lookup and not a variable.

     Keyed off <html lang>, which js/i18n.js rewrites to the real BCP-47 tag
     BEFORE it notifies anyone: 'uk' here, not the internal 'ua' code, which
     is why this table's keys are uk/ru/en. */
  function messages() {
    var tag = (document.documentElement.lang || 'en').slice(0, 2);
    return MESSAGES[tag] || MESSAGES.en;
  }

  function t(key, vars) {
    var s = messages()[key] || key;
    if (vars) {
      for (var k in vars) {
        if (Object.prototype.hasOwnProperty.call(vars, k)) {
          s = s.split('{' + k + '}').join(vars[k]);
        }
      }
    }
    return s;
  }

  function $(sel, root) { return (root || document).querySelector(sel); }

  /* Fisher-Yates. Shuffles the PRIZES, never the DOM nodes: card 1 to 9 stay
     where they are, so the tab order stays the reading order. Moving the
     nodes would silently scramble the keyboard path. */
  function shuffle(a) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }


  /* ======================================================================
     Elements and state
     ====================================================================== */

  var grid     = $('#fc-grid');
  var progress = $('#fc-progress');
  var status   = $('#fc-status');
  var claim    = $('#fc-claim');

  var state = { found: 0, locked: false, lastCard: null, opened: false };


  /* ======================================================================
     Building the grid
     ====================================================================== */

  function buildCard(prize, index) {
    var n = index + 1;
    var li = document.createElement('li');
    li.className = 'fc-cell';
    li.dataset.face = 'back';
    li.dataset.prize = prize.id;
    li.dataset.pos = String(n);

    var btn = document.createElement('button');
    btn.className = 'fc-card';
    btn.type = 'button';

    var flip = document.createElement('span');
    flip.className = 'fc-flip';

    var back = document.createElement('span');
    back.className = 'fc-face fc-face--back';
    back.setAttribute('aria-hidden', 'true');

    var front = document.createElement('span');
    front.className = 'fc-face fc-face--front';
    front.setAttribute('aria-hidden', 'true');

    var box = document.createElement('span');
    box.className = 'fc-prize';
    box.innerHTML =
      '<span class="fc-prize__pct"></span>' +
      '<span class="fc-prize__plus">+</span>' +
      '<span class="fc-prize__fs"></span>';
    box.firstChild.textContent = prize.pct;
    /* No separator: the design sets it solid, "250FS". */
    box.lastChild.textContent = prize.fs + t('fsLabel');
    front.appendChild(box);

    flip.appendChild(back);
    flip.appendChild(front);
    btn.appendChild(flip);

    /* Both faces are hidden from assistive tech and the accessible name comes
       only from this label. Without that, a screen reader would read the
       prize off a card that is still face down and give the game away. */
    var label = document.createElement('span');
    label.className = 'fc-sr';
    label.dataset.role = 'label';
    label.textContent = t('cardBack', { n: n });
    btn.appendChild(label);

    li.appendChild(btn);
    return li;
  }

  /* What the nine cards are built as.

     Under alwaysWin the deck's own top-prize entries are never dealt. The
     three cards that win are the three the visitor turns, and promote() writes
     the prize onto them — so if a top-prize card were also lying in the grid
     unturned, the board would end showing six of them. Dealing only the losing
     tiers is what leaves exactly three at the end: the visitor's, with the
     ladder they were playing against behind them.

     The deck stays the single source of the card text either way. */
  function dealtDeck() {
    var deck = CONFIG.deck;
    if (!CONFIG.alwaysWin) return shuffle(deck.slice());

    /* One entry per losing TIER, not per losing card. Dealt round robin, so
       nine cards come out as evenly as two tiers divide — five and four.
       Cycling the six losing cards instead would deal six of the first tier
       and three of the second, which reads as a lopsided ladder. */
    var tiers = [];
    var seen = {};
    for (var i = 0; i < deck.length; i++) {
      if (deck[i].id === CONFIG.winPrizeId) continue;
      if (seen[deck[i].id]) continue;
      seen[deck[i].id] = true;
      tiers.push(deck[i]);
    }
    /* A deck of nothing but top prizes: nothing to deal, fall back rather
       than hand back an empty grid. */
    if (!tiers.length) return shuffle(deck.slice());

    var hand = [];
    for (var j = 0; j < deck.length; j++) hand.push(tiers[j % tiers.length]);
    return shuffle(hand);
  }

  function buildGrid() {
    var prizes = dealtDeck();
    var frag = document.createDocumentFragment();
    var winIndex = 0;

    for (var i = 0; i < prizes.length; i++) {
      var cell = buildCard(prizes[i], i);

      /* The orange-outlined face art, applied from styles.css. Set at build
         time rather than at flip time so the image is fetched with the page,
         not in the middle of the first winning flip. */
      if (CONFIG.alwaysWin) {
        /* These three are not the winners — under alwaysWin the winners are
           whichever three get turned. They carry the attribute so that BOTH
           faces are fetched at load: three ask for winning_card.webp and six
           for simple_card.webp, and by the time either is needed it is cached.
           promote() moves it onto the cards actually turned, revealRest()
           takes it off these. */
        if (i < CONFIG.winTarget) cell.dataset.winFace = '';
      } else if (prizes[i].id === CONFIG.winPrizeId) {
        /* Drives the 80ms stagger of the marking sweep, in DOM order. */
        cell.style.setProperty('--i', String(winIndex++));
        cell.dataset.winFace = '';
      }
      frag.appendChild(cell);
    }
    grid.appendChild(frag);
  }


  /* ======================================================================
     The game
     ====================================================================== */

  function announce(text) { if (status) status.textContent = text; }

  function setLabel(cell, key) {
    var label = cell.querySelector('[data-role="label"]');
    if (!label) return;
    label.textContent = t(key, {
      n: cell.dataset.pos,
      prize: t(cell.dataset.prize)
    });
  }

  /* Which of the three label keys a cell should be carrying, read off its own
     state. setLabel writes the label; this is what decides which one. */
  function labelKey(cell) {
    if (cell.dataset.face !== 'front') return 'cardBack';
    return 'win' in cell.dataset ? 'cardWin' : 'cardFront';
  }

  /* The nine accessible names are written into the DOM once, when a card is
     built or turned, so they do not follow a language change on their own.
     This is what makes them follow it. Wired to TW's 'lang' event in init().

     #fc-status is deliberately NOT rewritten here. It is aria-live="polite":
     writing to it makes a screen reader speak, and speaking the progress
     sentence again because someone opened the language menu would be an
     announcement the visitor did nothing to cause. The stale sentence is
     never re-read where it sits, and the next card they turn announces in the
     new language.

     The visible prize text is not rewritten either, and does not need to be:
     it is digits plus fsLabel, which is the string 'FS' in all three tables
     because that is how the artboards draw it in every language. */
  function relabel() {
    if (!grid) return;
    var cells = grid.querySelectorAll('.fc-cell');
    for (var i = 0; i < cells.length; i++) setLabel(cells[i], labelKey(cells[i]));
  }

  /* The top prize, read out of the deck rather than written down a second
     time. tools/fonts.py --check builds the card subset by parsing CONFIG.deck
     with a regex, so a prize string that lives anywhere else is a prize string
     whose glyphs nobody guarantees. That is exactly how the hryvnia sign
     shipped in no font at all. */
  function topPrize() {
    for (var i = 0; i < CONFIG.deck.length; i++) {
      if (CONFIG.deck[i].id === CONFIG.winPrizeId) return CONFIG.deck[i];
    }
    return CONFIG.deck[0];
  }

  /* alwaysWin: the card the visitor just turned becomes the top prize. Only
     what they actually see is rewritten — the six they never turn keep the
     losing tiers they were built with. */
  function promote(cell) {
    var prize = topPrize();
    var pct = cell.querySelector('.fc-prize__pct');
    var fs  = cell.querySelector('.fc-prize__fs');

    cell.dataset.prize = prize.id;
    /* The orange-outlined art has to travel with the text, or the card draws
       a plain face over the top prize. buildGrid put it on three cards to get
       the image fetched at load; this is where it lands on the right ones. */
    cell.dataset.winFace = '';
    if (pct) pct.textContent = prize.pct;
    if (fs)  fs.textContent  = prize.fs + t('fsLabel');
  }

  /* The cards the visitor never turned open too, once the win has landed, so
     the ladder they were playing against is visible behind the three that won.
     They are NOT promoted: they show the losing tiers the deck built them as,
     which is also why data-win-face has to come off any that were carrying it
     for the preload — a 50.000 card must not draw the top prize's frame. */
  function revealRest() {
    var rest = grid.querySelectorAll('.fc-cell:not([data-win])');
    var T = timing();

    for (var i = 0; i < rest.length; i++) {
      (function (cell, order) {
        if (cell.dataset.face === 'front') return;
        window.setTimeout(function () {
          var btn = cell.querySelector('.fc-card');
          delete cell.dataset.winFace;
          cell.dataset.face = 'front';
          if (btn) btn.setAttribute('aria-pressed', 'true');
          setLabel(cell, 'cardFront');
        }, order * Math.round(T.flip / 8));
      }(rest[i], i));
    }
  }

  function flipCard(cell) {
    var T = timing();
    var btn = cell.querySelector('.fc-card');

    if (CONFIG.alwaysWin) {
      /* Before anything reads dataset.prize: isWin below, and setLabel, which
         speaks the prize out loud to a screen reader. */
      promote(cell);
      /* Stagger in the order they were turned, not in DOM order. Two rules
         read --i and both assume 0, 1, 2: the 80ms marking sweep and the
         phase offset of the breathe loop. Set before the flip attributes, so
         the value is in place when those transitions start. */
      cell.style.setProperty('--i', String(state.found));
    }

    var isWin = cell.dataset.prize === CONFIG.winPrizeId;

    /* Lock the board before the last winning flip starts, so a fast clicker
       cannot turn a tenth card while the win sequence runs. */
    if (isWin && state.found === CONFIG.winTarget - 1) state.locked = true;

    cell.dataset.face = 'front';
    if (isWin) cell.dataset.win = '';
    btn.style.willChange = 'transform';
    btn.setAttribute('aria-pressed', 'true');
    state.lastCard = btn;

    setLabel(cell, isWin ? 'cardWin' : 'cardFront');

    /* A timer, not a transitionend listener: under reduced motion the
       transform never transitions, so the event would never fire and the
       will-change layer would leak. Dropping will-change is also what forces
       the crisp re-rasterisation at rest. */
    window.setTimeout(function () {
      btn.style.willChange = '';
    }, T.flip);

    if (isWin) {
      state.found += 1;
      setPips(state.found);
      announce(t('progress', { n: state.found }));
      if (state.found === CONFIG.winTarget) runWinSequence();
    } else if (CONFIG.flipBackMs > 0) {
      window.setTimeout(function () {
        cell.dataset.face = 'back';
        btn.setAttribute('aria-pressed', 'false');
        setLabel(cell, 'cardBack');
      }, CONFIG.flipBackMs);
    }
  }

  function setPips(n) {
    if (!progress) return;
    var pips = progress.children;
    for (var i = 0; i < pips.length; i++) {
      if (i < n) pips[i].setAttribute('data-on', '');
      else pips[i].removeAttribute('data-on');
    }
  }

  function runWinSequence() {
    var T = timing();
    announce(t('win'));

    /* The pause between the third card landing and the board reacting is
       where the visitor's own recognition happens. Without it the modal
       covers the moment they played for. */
    window.setTimeout(function () {
      grid.dataset.phase = 'reveal';
      if (claim) claim.setAttribute('data-on', '');
      /* Only under alwaysWin. With the switch off this is the original game,
         where the visitor turned losers on the way and the board they end on
         is the board they made — leaving it alone is what keeps "false"
         a true restore rather than a third, half-new game. */
      if (CONFIG.alwaysWin) revealRest();
    }, T.flip + T.hold);

    window.setTimeout(openModal, T.flip + T.hold + T.reveal);
  }

  function onGridClick(ev) {
    var cell = ev.target.closest ? ev.target.closest('.fc-cell') : null;
    if (!cell || !grid.contains(cell)) return;
    if (state.locked || cell.dataset.face === 'front') return;
    flipCard(cell);
  }


  /* ======================================================================
     The registration card

     It is tw-lp-template's, whole: js/shell.js builds it from campaign.js,
     js/form.js drives it. The focus trap, Escape, the top layer, the two
     tabs, the validation, the phone normalisation, the confirmation screen
     and its copy buttons all live there now, in code every Top Win landing
     shares. What stood here was a second implementation of the same design,
     and the two had already drifted: a checkbox that shipped unticked, a
     deeper orange on the button, a login link in a different colour.

     What is left is the seam. TWForm.open() is the entire coupling between
     a mechanic and the card.
     ====================================================================== */

  function openModal() {
    if (!window.TWForm) return;
    state.opened = true;

    /* js/form.js hands focus back to whatever held it when the card opened.
       The win sequence opens from a timer, so give it the card the visitor
       turned last -- otherwise focus returns to <body> and the keyboard
       path restarts at the top of the page. */
    if (state.lastCard) state.lastCard.focus({ preventScroll: true });

    /* The page behind the card scrolls; the template's landings do not, so
       this rule is this campaign's. <dialog> makes the background inert, not
       unscrollable. */
    document.documentElement.classList.add('fc-noscroll');
    TWForm.open();
  }

  function closeModal() {
    if (window.TWForm) TWForm.close();
  }


  /* ======================================================================
     Boot
     ====================================================================== */

  function init() {
    if (!grid) return;

    buildGrid();
    grid.addEventListener('click', onGridClick);
    if (claim) claim.addEventListener('click', openModal);
    setPips(0);

    /* The card's own close, backdrop click, tab switching, validation, eye
       toggle and copy buttons were all wired here. js/form.js owns them now,
       for every Top Win landing at once.

       One thread does come back. This page scrolls behind the card, and
       <dialog> makes the background inert, not unscrollable: openModal()
       locks the page and the shell says when to let go. */
    if (window.TW) {
      TW.on('formclose', function () {
        document.documentElement.classList.remove('fc-noscroll');
      });

      /* The second thread. js/i18n.js re-renders every [data-i18n] node in the
         page, and the nine cards carry none: their accessible names are built
         here, from the MESSAGES table above. Without this, switching to
         English left a screen reader reading "Картка 4 з 9" over a board the
         rest of the page had already translated. */
      TW.on('lang', relabel);
    }

    /* The public surface, kept for QA: drive the board by hand without
       turning nine cards. The card itself answers on TWForm / TW. */
    window.TWFlip = {
      config:   CONFIG,
      state:    state,
      open:     openModal,
      close:    closeModal,
      showDone: function (res) { if (window.TWForm) TWForm.showDone(res); }
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
