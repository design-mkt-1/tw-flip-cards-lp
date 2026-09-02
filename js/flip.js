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

    /* ────────────────────────────────────────────────────────────────────
       IT INTEGRATION — START

       There are two ways to wire up the registration form. Pick one.

       A. PLAIN HTML  (recommended, needs no JavaScript knowledge)
          Set action and method on <form id="fc-form"> in index.html,
          ru.html and en.html. This script validates the fields, then steps
          out of the way and lets the browser submit the form normally.

       B. JAVASCRIPT HOOK
          Leave action empty and assign a function to onRegister below. It
          is called with (payload, form) once validation passes, and you own
          the request from that point.

       With neither set, NOTHING IS SENT. The validated payload is written to
       the browser console instead, so the page is fully demoable before it
       is wired.
       ──────────────────────────────────────────────────────────────────── */

    onRegister: null,        // function (payload, form) { ... }

    /* Extra values your platform needs on the submission: affiliate id,
       campaign, landing id, CSRF token. Each becomes a hidden input. */
    hiddenFields: {
      // promo_code: 'FLIP650',
      // landing_id: 'tw-flip-cards'
    },

    /* Destinations for the links that are deliberately left unwired.
       Empty means the link stays href="#" and does nothing. */
    termsUrl:   '',
    privacyUrl: '',
    loginUrl:   '',

    /* The phone country. Change all three together. */
    dialCode:    '+380',
    dialFlag:    '🇺🇦',
    phoneDigits: 9,          // digits expected after the dial code

    /* IT INTEGRATION — END
       ──────────────────────────────────────────────────────────────────── */


    /* ── Game. Marketing can tune these. ─────────────────────────────── */

    winPrizeId: 'p650',      // the prize the visitor is hunting for
    winTarget:  3,           // how many of them are hidden in the grid

    /* Nine cards: three of each prize. Change the counts to change the odds.
       They must add up to nine. */
    deck: [
      { id: 'p650', pct: '650%', fs: '250' },
      { id: 'p650', pct: '650%', fs: '250' },
      { id: 'p650', pct: '650%', fs: '250' },
      { id: 'p250', pct: '250%', fs: '50'  },
      { id: 'p250', pct: '250%', fs: '50'  },
      { id: 'p250', pct: '250%', fs: '50'  },
      { id: 'p100', pct: '100%', fs: '10'  },
      { id: 'p100', pct: '100%', fs: '10'  },
      { id: 'p100', pct: '100%', fs: '10'  }
    ],

    /* A card that is not a 650% stays face up. Everyone reaches the form,
       which is the point of a campaign page. Set this to a number of
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
      fsLabel:    'ФС',
      cardBack:   'Картка {n} з 9, сорочкою вгору. Натисніть, щоб перевернути.',
      cardFront:  'Картка {n}: {prize}.',
      cardWin:    'Картка {n}: {prize}. Знайдено!',
      p650: '650 відсотків плюс 250 фріспінів',
      p250: '250 відсотків плюс 50 фріспінів',
      p100: '100 відсотків плюс 10 фріспінів',
      progress:   'Знайдено {n} з 3 карток з бонусом 650 відсотків',
      win:        'Знайдено всі три картки. Відкриваємо форму реєстрації.',
      errPhone:   'Введіть 9 цифр номера',
      errEmail:   'Введіть коректну адресу email',
      errPassword:'Пароль має містити щонайменше {n} символів',
      errConsent: 'Потрібно підтвердити, що вам є 18 років',
      showPass:   'Показати пароль',
      hidePass:   'Сховати пароль'
    },
    ru: {
      fsLabel:    'ФС',
      cardBack:   'Карта {n} из 9, рубашкой вверх. Нажмите, чтобы перевернуть.',
      cardFront:  'Карта {n}: {prize}.',
      cardWin:    'Карта {n}: {prize}. Найдено!',
      p650: '650 процентов плюс 250 фриспинов',
      p250: '250 процентов плюс 50 фриспинов',
      p100: '100 процентов плюс 10 фриспинов',
      progress:   'Найдено {n} из 3 карт с бонусом 650 процентов',
      win:        'Найдены все три карты. Открываем форму регистрации.',
      errPhone:   'Введите 9 цифр номера',
      errEmail:   'Введите корректный адрес email',
      errPassword:'Пароль должен содержать не менее {n} символов',
      errConsent: 'Нужно подтвердить, что вам есть 18 лет',
      showPass:   'Показать пароль',
      hidePass:   'Скрыть пароль'
    },
    en: {
      fsLabel:    'FS',
      cardBack:   'Card {n} of 9, face down. Press to flip.',
      cardFront:  'Card {n}: {prize}.',
      cardWin:    'Card {n}: {prize}. Found!',
      p650: '650 percent plus 250 free spins',
      p250: '250 percent plus 50 free spins',
      p100: '100 percent plus 10 free spins',
      progress:   'Found {n} of 3 cards with the 650 percent bonus',
      win:        'All three cards found. Opening the registration form.',
      errPhone:   'Enter the 9 digits of your number',
      errEmail:   'Enter a valid email address',
      errPassword:'Password must be at least {n} characters',
      errConsent: 'Please confirm that you are 18 or older',
      showPass:   'Show password',
      hidePass:   'Hide password'
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

  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  var M = MESSAGES[lang] || MESSAGES.en;

  function t(key, vars) {
    var s = M[key] || key;
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
  var modal    = $('#fc-signup');
  var form     = $('#fc-form');

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
    box.lastChild.textContent = prize.fs + ' ' + t('fsLabel');
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

  function buildGrid() {
    var prizes = shuffle(CONFIG.deck.slice());
    var frag = document.createDocumentFragment();
    var winIndex = 0;

    for (var i = 0; i < prizes.length; i++) {
      var cell = buildCard(prizes[i], i);
      if (prizes[i].id === CONFIG.winPrizeId) {
        /* Drives the 80ms stagger of the marking sweep, in DOM order. */
        cell.style.setProperty('--i', String(winIndex++));
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

  function flipCard(cell) {
    var T = timing();
    var isWin = cell.dataset.prize === CONFIG.winPrizeId;
    var btn = cell.querySelector('.fc-card');

    /* Lock the board before the last winning flip starts, so a fast clicker
       cannot turn a tenth card while the win sequence runs. */
    if (isWin && state.found === CONFIG.winTarget - 1) state.locked = true;

    cell.dataset.flipping = '';
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
      cell.removeAttribute('data-flipping');
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
     Modal

     <dialog>.showModal() gives the focus trap, Escape, the inert background
     and top-layer rendering for free. Top layer matters here: the grid is
     full of preserve-3d stacking contexts, and a plain z-indexed overlay
     loses to those in Safari.
     ====================================================================== */

  function openModal() {
    if (!modal || modal.open) return;
    state.opened = true;
    modal.showModal();
    document.documentElement.classList.add('fc-noscroll');
  }

  function closeModal() {
    if (!modal || !modal.open) return;
    modal.close();
  }

  function onModalClose() {
    document.documentElement.classList.remove('fc-noscroll');
    if (state.lastCard) state.lastCard.focus();
  }


  /* ======================================================================
     Form
     ====================================================================== */

  var tabPhone = $('#fc-tab-phone');
  var tabEmail = $('#fc-tab-email');
  var panelPhone = $('#fc-panel-phone');
  var panelEmail = $('#fc-panel-email');
  var method = 'phone';

  function setTab(next) {
    method = next;
    var onPhone = next === 'phone';

    tabPhone.setAttribute('aria-selected', onPhone ? 'true' : 'false');
    tabEmail.setAttribute('aria-selected', onPhone ? 'false' : 'true');
    tabPhone.tabIndex = onPhone ? 0 : -1;
    tabEmail.tabIndex = onPhone ? -1 : 0;

    panelPhone.hidden = !onPhone;
    panelEmail.hidden = onPhone;

    clearError(panelPhone);
    clearError(panelEmail);
  }

  function onTabKey(ev) {
    if (ev.key !== 'ArrowLeft' && ev.key !== 'ArrowRight') return;
    ev.preventDefault();
    var next = method === 'phone' ? 'email' : 'phone';
    setTab(next);
    (next === 'phone' ? tabPhone : tabEmail).focus();
  }

  function showError(field, msg, errEl) {
    field.setAttribute('data-invalid', '');
    var input = field.querySelector('input');
    if (input) input.setAttribute('aria-invalid', 'true');
    /* role="alert" on the message element is what makes it announce when
       focus is somewhere else. Moving focus to the field as well covers the
       case where the visitor is already reading further down. */
    if (errEl) errEl.textContent = msg;
  }

  function clearError(field) {
    if (!field) return;
    field.removeAttribute('data-invalid');
    var input = field.querySelector('input');
    if (input) input.removeAttribute('aria-invalid');
    var err = field.querySelector('.fc-error');
    if (err) err.textContent = '';
  }

  function validate() {
    var firstBad = null;
    var pwField = $('#fc-password').closest('.fc-field');
    var consentRow = $('#fc-consent-row');

    clearError(panelPhone);
    clearError(panelEmail);
    clearError(pwField);
    consentRow.removeAttribute('data-invalid');
    $('#fc-err-consent').textContent = '';

    if (method === 'phone') {
      var digits = $('#fc-phone').value.replace(/\D/g, '');
      if (digits.length !== CONFIG.phoneDigits) {
        showError(panelPhone, t('errPhone'), $('#fc-err-phone'));
        firstBad = firstBad || $('#fc-phone');
      }
    } else {
      /* Deliberately loose. A full RFC 5322 pattern is unreadable and
         rejects addresses that work. The real check belongs on the server. */
      var email = $('#fc-email').value.trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) {
        showError(panelEmail, t('errEmail'), $('#fc-err-email'));
        firstBad = firstBad || $('#fc-email');
      }
    }

    /* Length only. Real complexity rules live in the platform and will
       differ from anything invented here. */
    if ($('#fc-password').value.length < CONFIG.passwordMinLength) {
      showError(pwField, t('errPassword', { n: CONFIG.passwordMinLength }),
                $('#fc-err-password'));
      firstBad = firstBad || $('#fc-password');
    }

    if (!$('#fc-consent').checked) {
      consentRow.setAttribute('data-invalid', '');
      $('#fc-err-consent').textContent = t('errConsent');
      firstBad = firstBad || $('#fc-consent');
    }

    if (firstBad) firstBad.focus();
    return !firstBad;
  }

  function readPayload() {
    var p = {
      method: method,
      phone: method === 'phone'
        ? CONFIG.dialCode + $('#fc-phone').value.replace(/\D/g, '')
        : '',
      email: method === 'email' ? $('#fc-email').value.trim() : '',
      password: $('#fc-password').value,
      consent: $('#fc-consent').checked,
      lang: lang,
      bonus: '650+250'
    };
    for (var k in CONFIG.hiddenFields) {
      if (Object.prototype.hasOwnProperty.call(CONFIG.hiddenFields, k)) {
        p[k] = CONFIG.hiddenFields[k];
      }
    }
    return p;
  }

  function onSubmit(ev) {
    if (!validate()) { ev.preventDefault(); return; }

    /* Route A: IT set an action, so let the browser submit it normally. */
    if (form.getAttribute('action')) return;

    ev.preventDefault();
    var payload = readPayload();

    /* Route B */
    if (typeof CONFIG.onRegister === 'function') {
      CONFIG.onRegister(payload, form);
      return;
    }

    console.info(
      '[tw-flip-cards] The form is valid but not wired to anything. ' +
      'Set an action on <form id="fc-form">, or CONFIG.onRegister at the ' +
      'top of js/flip.js. See README.md section 2. Payload:', payload);
  }

  function togglePassword() {
    var input = $('#fc-password');
    var btn = $('#fc-eye');
    var show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.setAttribute('aria-pressed', show ? 'true' : 'false');
    btn.setAttribute('aria-label', t(show ? 'hidePass' : 'showPass'));
  }


  /* ======================================================================
     Boot
     ====================================================================== */

  function applyLinks() {
    var map = [['#fc-terms', 'termsUrl'], ['#fc-privacy', 'privacyUrl'],
               ['#fc-login', 'loginUrl']];
    for (var i = 0; i < map.length; i++) {
      var el = $(map[i][0]);
      var url = CONFIG[map[i][1]];
      if (el && url) { el.href = url; el.rel = 'noopener'; }
    }
  }

  function applyDialCode() {
    var flag = $('.fc-input__flag');
    var dial = $('.fc-input__dial');
    if (flag) flag.textContent = CONFIG.dialFlag;
    if (dial) dial.textContent = CONFIG.dialCode;
  }

  function addHiddenFields() {
    for (var k in CONFIG.hiddenFields) {
      if (!Object.prototype.hasOwnProperty.call(CONFIG.hiddenFields, k)) continue;
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = k;
      input.value = CONFIG.hiddenFields[k];
      form.appendChild(input);
    }
  }

  function init() {
    if (!grid || !form || !modal) return;

    buildGrid();
    applyLinks();
    applyDialCode();
    addHiddenFields();

    grid.addEventListener('click', onGridClick);

    if (claim) claim.addEventListener('click', openModal);
    modal.addEventListener('close', onModalClose);
    $('#fc-close').addEventListener('click', closeModal);

    /* Clicking the backdrop closes. The dialog element itself fills the top
       layer, so a click that lands on it and not on the form is a backdrop
       click. */
    modal.addEventListener('click', function (ev) {
      if (ev.target === modal) closeModal();
    });

    tabPhone.addEventListener('click', function () { setTab('phone'); });
    tabEmail.addEventListener('click', function () { setTab('email'); });
    tabPhone.addEventListener('keydown', onTabKey);
    tabEmail.addEventListener('keydown', onTabKey);

    $('#fc-eye').addEventListener('click', togglePassword);
    form.addEventListener('submit', onSubmit);

    setPips(0);

    /* Exposed only so the board can be inspected during QA. Nothing in the
       page reads it. */
    window.TWFlip = { config: CONFIG, state: state, open: openModal };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
