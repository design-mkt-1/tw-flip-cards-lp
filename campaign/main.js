/* ═══════════════════════════════════════════════════════════════
   TW-FLIP-CARDS — the mechanic

   Nine cards, face down. Every card the visitor turns is the top prize, and
   the third one opens the registration card. There is no miss and no hunt:
   the campaign asks for a short, certain path to the form.

   This is all that survived js/flip.js. The other two thirds of that file --
   the tabs, the validation, the payload, the confirmation screen, the copy
   buttons, the four URL seams and the language switch -- are js/form.js,
   js/shell.js and js/i18n.js now, and are not reimplemented here.

   ── The seam ─────────────────────────────────────────────────
     TW.ready(fn)       run once the chrome is mounted and a language applied
     TW.openForm()      open the registration dialog — the point of the page
     TW.t(key, vars)    a translated string; the offer figures fill themselves
     TW.on('lang')      relabel the nine cards when the language changes
     TW.sound(name, v)  one of campaign.js § sounds, at volume v
     TW.track(event)    analytics; a no-op unless an id is configured
     TW.config          campaign.js, including the deck and the offer

   Never call showModal(), never reach into the dialog: the shell owns focus,
   the scroll lock, Escape and the confirmation screen. The old flip.js owned
   all four and is the reason this landing had its own focus trap to maintain.
   ═══════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ── the game's own settings ────────────────────────────────
     The deck and the offer are campaign.js's -- they are copy, and
     tools/fonts.py only reads campaign.js, js/strings.js and index.html. What
     is left here is behaviour. */

  var WIN_TARGET = 3;     // how many cards the visitor turns
  var TOP_ID = 'top';     // the id the turned cards are promoted to

  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* One table, so every delay in the win sequence comes from one place and
     reduced motion shortens the whole thing rather than leaving dead air. */
  function timing() {
    return reduceMotion.matches
      ? { flip: 220, hold:  80, reveal:   0 }
      : { flip: 520, hold: 240, reveal: 240 };
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

  var grid, progress, status, claim;
  var state = { found: 0, locked: false };

  /* The top prize is the offer, not a tenth deck entry. Changing
     campaign.js § offer changes the card the visitor wins and the figure in
     the dialog in the same edit — which is what stops the two disagreeing,
     the way three landings' worth of hard-coded amounts once did. */
  function topPrize() {
    var o = TW.config.offer || {};
    return { id: TOP_ID, amount: o.amount || '', spins: o.spins || '' };
  }

  /* One entry per losing TIER, dealt round robin, so nine cards come out as
     evenly as the tiers divide. campaign.js § deck holds the losing tiers
     only: the three top-prize cards are the three the visitor turns, and if a
     top-prize card were also lying in the grid unturned the board would end
     up showing six of them. */
  function dealtDeck() {
    var deck = (TW.config.deck || []).slice();
    var tiers = [];
    var seen = {};
    for (var i = 0; i < deck.length; i++) {
      if (seen[deck[i].id]) continue;
      seen[deck[i].id] = true;
      tiers.push(deck[i]);
    }
    if (!tiers.length) tiers = [topPrize()];

    var hand = [];
    for (var j = 0; j < 9; j++) hand.push(tiers[j % tiers.length]);
    return shuffle(hand);
  }

  /* What a card says out loud. The prize name is a string key, so a card that
     has been promoted announces the offer and one that has not announces its
     own tier. */
  function prizeText(cell) {
    return TW.t('prize.' + cell.dataset.prize);
  }

  function setLabel(cell, key) {
    var label = cell.querySelector('[data-role="label"]');
    if (!label) return;
    label.textContent = TW.t(key, { n: cell.dataset.pos, prize: prizeText(cell) });
  }

  function labelAll() {
    var cells = grid.querySelectorAll('.cmp-cell');
    for (var i = 0; i < cells.length; i++) {
      var cell = cells[i];
      var key = cell.dataset.face === 'front'
        ? (cell.hasAttribute('data-win') ? 'card.win' : 'card.front')
        : 'card.back';
      setLabel(cell, key);
      writeFace(cell);
    }
  }

  /* ── building the grid ──────────────────────────────────────── */

  function writeFace(cell) {
    var prize = cell.dataset.prize === TOP_ID ? topPrize() : cell._prize;
    if (!prize) return;
    var o = TW.config.offer || {};
    var pct = cell.querySelector('.cmp-prize__pct');
    var fs  = cell.querySelector('.cmp-prize__fs');
    /* The currency rides with the amount on the card exactly as it does in
       the dialog's offer line. No separator before FS: the design sets it
       solid, "250FS". */
    if (pct) pct.textContent = prize.amount + (o.currency ? ' ' + o.currency : '');
    if (fs)  fs.textContent  = prize.spins + TW.t('card.fs');
  }

  function buildCard(prize, index) {
    var n = index + 1;
    var li = document.createElement('li');
    li.className = 'cmp-cell';
    li.dataset.face = 'back';
    li.dataset.prize = prize.id;
    li.dataset.pos = String(n);
    li._prize = prize;

    var btn = document.createElement('button');
    btn.className = 'cmp-card';
    btn.type = 'button';

    var flip = document.createElement('span');
    flip.className = 'cmp-flip';

    var back = document.createElement('span');
    back.className = 'cmp-face cmp-face--back';
    back.setAttribute('aria-hidden', 'true');

    var front = document.createElement('span');
    front.className = 'cmp-face cmp-face--front';
    front.setAttribute('aria-hidden', 'true');

    var box = document.createElement('span');
    box.className = 'cmp-prize';
    box.innerHTML =
      '<span class="cmp-prize__pct"></span>' +
      '<span class="cmp-prize__plus">+</span>' +
      '<span class="cmp-prize__fs"></span>';
    front.appendChild(box);

    flip.appendChild(back);
    flip.appendChild(front);
    btn.appendChild(flip);

    /* Both faces are hidden from assistive tech and the accessible name comes
       only from this label. Without that, a screen reader would read the prize
       off a card that is still face down and give the game away. */
    var label = document.createElement('span');
    label.className = 'tw-sr-only';
    label.dataset.role = 'label';
    btn.appendChild(label);

    li.appendChild(btn);
    writeFace(li);
    setLabel(li, 'card.back');
    return li;
  }

  function buildGrid() {
    var prizes = dealtDeck();
    var frag = document.createDocumentFragment();

    for (var i = 0; i < prizes.length; i++) {
      var cell = buildCard(prizes[i], i);
      /* Three cards carry the winning face from the start so BOTH card images
         are fetched with the page — three ask for winning_card.webp and six
         for simple_card.webp. These three are not the winners: promote() moves
         the attribute onto whichever cards are actually turned, revealRest()
         takes it off the ones that were not. */
      if (i < WIN_TARGET) cell.dataset.winFace = '';
      frag.appendChild(cell);
    }
    grid.appendChild(frag);
  }

  /* ── the game ───────────────────────────────────────────────── */

  function announce(text) { if (status) status.textContent = text; }

  /* The card the visitor just turned becomes the top prize. Only what they
     actually see is rewritten — the six they never turn keep the losing tiers
     they were built with, so the board finishes showing the ladder they were
     playing against. */
  function promote(cell) {
    cell.dataset.prize = TOP_ID;
    /* The orange-outlined art has to travel with the text, or the card draws
       a plain face over the top prize. */
    cell.dataset.winFace = '';
    writeFace(cell);
  }

  /* The cards the visitor never turned open too, once the win has landed.
     They are NOT promoted, which is also why data-win-face has to come off any
     that were carrying it for the preload: a 50.000 card must not draw the top
     prize's frame. */
  function revealRest() {
    var rest = grid.querySelectorAll('.cmp-cell:not([data-win])');
    var T = timing();

    for (var i = 0; i < rest.length; i++) {
      (function (cell, order) {
        if (cell.dataset.face === 'front') return;
        window.setTimeout(function () {
          var btn = cell.querySelector('.cmp-card');
          delete cell.dataset.winFace;
          cell.dataset.face = 'front';
          if (btn) btn.setAttribute('aria-pressed', 'true');
          setLabel(cell, 'card.front');
        }, order * Math.round(T.flip / 8));
      }(rest[i], i));
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

  function flipCard(cell) {
    var T = timing();
    var btn = cell.querySelector('.cmp-card');

    /* Before anything reads dataset.prize — setLabel speaks it out loud. */
    promote(cell);
    /* Stagger in the order they were turned, not in DOM order. Two rules read
       --i and both assume 0, 1, 2: the 80ms marking sweep and the phase offset
       of the breathe loop. Set before the flip attributes, so the value is in
       place when those transitions start. */
    cell.style.setProperty('--i', String(state.found));

    /* Lock the board before the last flip starts, so a fast clicker cannot
       turn a tenth card while the win sequence runs. */
    if (state.found === WIN_TARGET - 1) state.locked = true;

    cell.dataset.face = 'front';
    cell.dataset.win = '';
    btn.style.willChange = 'transform';
    btn.setAttribute('aria-pressed', 'true');
    /* With the rotation, not before it: the swish is the card in the air and
       the tap inside the clip lands about where the face passes edge-on. */
    TW.sound('flip', 0.7);

    setLabel(cell, 'card.win');

    /* A timer, not a transitionend listener: under reduced motion the
       transform never transitions, so the event would never fire and the
       will-change layer would leak. Dropping will-change is also what forces
       the crisp re-rasterisation at rest. */
    window.setTimeout(function () { btn.style.willChange = ''; }, T.flip);

    state.found += 1;
    setPips(state.found);
    /* Quieter than the card, and after it: the mark filling is a confirmation,
       not an event of its own. */
    TW.sound('pip', 0.45);
    announce(TW.t('progress', { n: state.found }));
    TW.track('card_flip', { turned: state.found });

    if (state.found === WIN_TARGET) runWinSequence();
  }

  function runWinSequence() {
    var T = timing();
    announce(TW.t('win'));

    /* The pause between the third card landing and the board reacting is where
       the visitor's own recognition happens. Without it the dialog covers the
       moment they played for. */
    window.setTimeout(function () {
      grid.dataset.phase = 'reveal';
      if (claim) claim.setAttribute('data-on', '');
      revealRest();
      /* With the board's own reveal, and it is 900ms long against the 240ms
         before the dialog opens -- so it plays UNDER the form appearing and
         is gone shortly after. Anything longer would be still playing over
         somebody else's moment. */
      TW.sound('win', 0.8);
    }, T.flip + T.hold);

    window.setTimeout(function () {
      /* The two lines the whole integration comes down to. */
      TW.track('game_win', { mechanic: 'flip-cards' });
      TW.openForm();
    }, T.flip + T.hold + T.reveal);
  }

  function onGridClick(ev) {
    var cell = ev.target.closest ? ev.target.closest('.cmp-cell') : null;
    if (!cell || !grid.contains(cell)) return;
    if (state.locked || cell.dataset.face === 'front') return;
    flipCard(cell);
  }

  /* ── boot ───────────────────────────────────────────────────── */

  function init() {
    grid     = $('#cmp-grid');
    progress = $('#cmp-progress');
    status   = $('#cmp-status');
    claim    = $('#cmp-claim');
    if (!grid) return;

    buildGrid();
    setPips(0);

    grid.addEventListener('click', onGridClick);

    /* Shown once the board is won, and after the card is dismissed it is the
       way back into it. It is also the no-JS fallback: css/… hides it until
       [data-on], and the <noscript> block in index.html shows it. */
    if (claim) claim.addEventListener('click', function () { TW.openForm(); });

    /* Nine accessible names, three card faces and one live region, all of them
       campaign copy. The old landing served three HTML files instead and kept
       them in step with a CI job that counted tags. */
    TW.on('lang', labelAll);
  }

  window.CMPCards = {
    state: state,
    found: function () { return state.found; }
  };

  TW.ready(init);
}());
