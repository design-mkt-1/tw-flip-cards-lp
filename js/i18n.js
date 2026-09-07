/* Top Win i18n — the runtime translation engine and the language listbox.

   SHARED FILE. A campaign never edits this; tools/drift.py fails CI if it
   moves. To add a language, edit js/strings.js and campaign.js — see the
   header of js/strings.js for the four steps.

   ── The model ────────────────────────────────────────────────
   One HTML file, one page, all languages. Nodes opt in with data-i18n="key";
   attributes with data-i18n-attr="attr:key" (semicolon-separated for more
   than one). Nothing translatable is hardcoded in a component, which is what
   lets a language be added without touching one.

   The alternative — a separate HTML file per language — was tried in the last
   landing and needed two dedicated CI jobs whose entire purpose was to detect
   that its own three copies had drifted apart. A template that exists to stop
   divergence must not ship a three-way copy of every page. One file cannot
   drift from itself.

   ── Two tables, merged ───────────────────────────────────────
   TW_STRINGS (js/strings.js) is the shell's copy and is the same in every
   campaign. TW_CAMPAIGN.strings (campaign.js) is this campaign's own. The
   campaign wins on collision, so a campaign that needs a different
   'promo.title' overrides it without forking the shell table.

   ── Interpolation ────────────────────────────────────────────
   {name} is replaced from t()'s second argument, and always from the offer
   figures in campaign.js on top of that. This is why '225%' is not written
   three times: the number lives once, in campaign.js, and each locale writes
   only the sentence around it.

   ── Fallback chain ───────────────────────────────────────────
   current locale -> the first entry in `languages` -> the key itself. The
   first language listed in campaign.js is therefore the one whose table has
   to be complete. A key that renders as its own key is a bug tools/smoke.py
   fails on. */

(function () {
  'use strict';

  var C = window.TW_CAMPAIGN || {};
  var LANGS = (C.languages && C.languages.length ? C.languages : ['ua']).slice();
  var FALLBACK = LANGS[0];
  var STORE_KEY = 'tw-lang';

  /* Must match the exit transition on .tw-langmenu in css/shell.css. */
  var EXIT_MS = 120;

  var lang = FALLBACK;
  var watchers = [];
  var btn, menu, options;
  var hideTimer = 0;

  /* The merged table, built once per language on first use. */
  var TABLE = {};

  /* ── tables ───────────────────────────────────────────────── */

  function tableFor(code) {
    if (TABLE[code]) return TABLE[code];
    var shell = (window.TW_STRINGS || {})[code] || {};
    var camp = (C.strings || {})[code] || {};
    var out = {}, k;
    for (k in shell) if (Object.prototype.hasOwnProperty.call(shell, k)) out[k] = shell[k];
    for (k in camp) if (Object.prototype.hasOwnProperty.call(camp, k)) out[k] = camp[k];
    TABLE[code] = out;
    return out;
  }

  /* Every string can reach the offer figures without being handed them.
     Written as a function rather than captured once so a campaign that
     changes the offer at runtime -- an A/B split, a query parameter -- gets
     the new numbers on the next render. */
  function offerVars() {
    var o = C.offer || {};
    return {
      percent:  o.percent  || '',
      amount:   o.amount   || '',
      currency: o.currency || '',
      spins:    o.spins    || '',
      code:     o.code     || ''
    };
  }

  /* ── lookup ───────────────────────────────────────────────── */

  function t(key, vars) {
    var value = tableFor(lang)[key];
    if (value == null) value = tableFor(FALLBACK)[key];
    if (value == null) return key;
    return fill(value, vars);
  }

  /* Split rather than replace with a regex: a value that happens to contain
     $& or $1 would be mangled by String.replace's own substitution syntax,
     and an offer amount is exactly the kind of string that arrives from a
     spreadsheet with a stray character in it. */
  function fill(value, vars) {
    if (value.indexOf('{') < 0) return value;
    var all = offerVars(), k;
    if (vars) for (k in vars) if (Object.prototype.hasOwnProperty.call(vars, k)) all[k] = vars[k];

    var out = '', i = 0;
    while (i < value.length) {
      var open = value.indexOf('{', i);
      if (open < 0) { out += value.slice(i); break; }
      var close = value.indexOf('}', open);
      if (close < 0) { out += value.slice(i); break; }
      out += value.slice(i, open);
      var name = value.slice(open + 1, close);
      out += (all[name] == null ? '{' + name + '}' : all[name]);
      i = close + 1;
    }
    return out;
  }

  /* \n means a real line break in the rendered text. The markup carries no
     <br> anywhere, so a locale can break a headline where its own words
     break rather than where Ukrainian's do. */
  function setText(el, value) {
    if (value.indexOf('\n') < 0) { el.textContent = value; return; }
    el.textContent = '';
    value.split('\n').forEach(function (line, i) {
      if (i) el.appendChild(document.createElement('br'));
      el.appendChild(document.createTextNode(line));
    });
  }

  /* Re-render one subtree. js/form.js calls it with the done panel after it
     swaps the account label between phone and email; a campaign calls it
     after it builds markup of its own. */
  function apply(root) {
    root = root || document;

    Array.prototype.forEach.call(root.querySelectorAll('[data-i18n]'), function (el) {
      setText(el, t(el.getAttribute('data-i18n')));
    });

    Array.prototype.forEach.call(root.querySelectorAll('[data-i18n-attr]'), function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var at = pair.indexOf(':');
        if (at > 0) el.setAttribute(pair.slice(0, at).trim(), t(pair.slice(at + 1).trim()));
      });
    });

    /* The BCP-47 tag, not our internal code. lang="ua" asks a screen reader
       to read Ukrainian as a language that does not exist. */
    var meta = (window.TW_LOCALES || {})[lang];
    document.documentElement.lang = (meta && meta.tag) || lang;
  }

  function set(next) {
    if (LANGS.indexOf(next) < 0 || next === lang) return;
    lang = next;
    try { localStorage.setItem(STORE_KEY, next); } catch (e) { /* private mode */ }
    apply();
    syncSelector();
    watchers.forEach(function (fn) { fn(next); });
  }

  /* ?lang= wins, then the saved choice, then the browser, then the first
     language in campaign.js.

     The query parameter exists so a media buyer can point one creative at
     ?lang=ru without the template needing a second HTML file. It is not
     persisted: a link that forces a language should not overwrite what the
     visitor chose on a previous visit. */
  function detect() {
    var forced = new URLSearchParams(location.search).get('lang');
    if (forced && LANGS.indexOf(forced) >= 0) return forced;

    var saved = null;
    try { saved = localStorage.getItem(STORE_KEY); } catch (e) { /* private mode */ }
    if (LANGS.indexOf(saved) >= 0) return saved;

    /* Matched against the real language tags, not against our own codes: a
       Ukrainian browser reports uk-UA, which never equals "ua". Comparing the
       two directly landed every Ukrainian visitor on the fallback and only
       looked correct because the fallback happens to be Ukrainian. */
    var nav = (navigator.language || '').slice(0, 2).toLowerCase();
    for (var i = 0; i < LANGS.length; i++) {
      var meta = (window.TW_LOCALES || {})[LANGS[i]];
      if (meta && meta.tag === nav) return LANGS[i];
    }
    return FALLBACK;
  }

  /* ── the listbox ──────────────────────────────────────────── */

  /* A listbox, not a modal: focus moves along the options with the arrow keys
     instead of being trapped, and Tab hands focus back to the trigger and
     carries on. This deliberately does not reuse the focus handling in
     js/form.js -- that pattern is for dialogs and would strand the visitor
     here. */

  /* reset.css forces [hidden] to display:none !important and display cannot
     be transitioned, so the menu's open state is a class: unhide, let one
     frame pass, then add it. The dialog does the same two-step. */
  function nextFrame(fn) {
    requestAnimationFrame(function () { requestAnimationFrame(fn); });
  }

  function isOpen() { return btn.getAttribute('aria-expanded') === 'true'; }

  function openMenu(focusIndex) {
    clearTimeout(hideTimer);
    menu.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    nextFrame(function () { menu.classList.add('is-open'); });

    document.addEventListener('keydown', onKeydown, true);
    document.addEventListener('pointerdown', onPointerDown, true);

    var i = typeof focusIndex === 'number' ? focusIndex : LANGS.indexOf(lang);
    options[Math.max(0, i)].focus({ preventScroll: true });
  }

  function closeMenu(restoreFocus) {
    if (!isOpen()) return;
    menu.classList.remove('is-open');
    btn.setAttribute('aria-expanded', 'false');

    document.removeEventListener('keydown', onKeydown, true);
    document.removeEventListener('pointerdown', onPointerDown, true);

    /* Focus has to leave before the menu is taken out of the layout, or the
       browser drops it on <body> and the next Tab restarts from the top of
       the page. */
    if (restoreFocus !== false) btn.focus({ preventScroll: true });
    else if (menu.contains(document.activeElement)) document.activeElement.blur();

    clearTimeout(hideTimer);
    hideTimer = setTimeout(function () { menu.hidden = true; }, EXIT_MS);
  }

  function move(step) {
    var here = options.indexOf(document.activeElement);
    var next = (here + step + options.length) % options.length;
    options[next].focus({ preventScroll: true });
  }

  function onKeydown(ev) {
    switch (ev.key) {
      case 'Escape':    ev.preventDefault(); closeMenu(); break;
      case 'ArrowDown': ev.preventDefault(); move(1); break;
      case 'ArrowUp':   ev.preventDefault(); move(-1); break;
      case 'Home':      ev.preventDefault(); options[0].focus({ preventScroll: true }); break;
      case 'End':       ev.preventDefault(); options[options.length - 1].focus({ preventScroll: true }); break;
      case 'Enter':
      case ' ':
        if (options.indexOf(document.activeElement) >= 0) {
          ev.preventDefault();
          choose(document.activeElement);
        }
        break;
      case 'Tab':
        /* Hand focus back to the trigger and let the Tab carry on from there,
           forwards or backwards. Closing with `false` blurs instead, which is
           the exact failure closeMenu warns about. */
        closeMenu();
        break;
    }
  }

  function onPointerDown(ev) {
    if (!menu.contains(ev.target) && ev.target !== btn) closeMenu(false);
  }

  function choose(option) {
    set(option.getAttribute('data-lang'));
    closeMenu();
  }

  function syncSelector() {
    if (!btn) return;
    var code = btn.querySelector('.tw-lang__code');
    if (code) code.textContent = lang.toUpperCase();

    /* The trigger carries a globe, the way the design draws it, so there is
       no flag on it to keep in step with the choice -- only the code and
       which row shows its tick. */
    options.forEach(function (o) {
      o.setAttribute('aria-selected', String(o.getAttribute('data-lang') === lang));
    });
  }

  /* The markup is built by js/shell.js from TW_LOCALES filtered by
     campaign.languages, so this only wires what it finds. A campaign with
     header.lang = false has no trigger and this is a no-op. */
  function wireSelector() {
    btn = document.querySelector('.tw-lang');
    menu = document.querySelector('.tw-langmenu');
    if (!btn || !menu) return;

    options = Array.prototype.slice.call(menu.querySelectorAll('[data-lang]'));
    options.forEach(function (o) {
      o.addEventListener('click', function () { choose(o); });
    });

    btn.addEventListener('click', function () {
      if (isOpen()) closeMenu(); else openMenu();
    });

    /* Opening straight onto an end of the list is the expected shortcut. */
    btn.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); openMenu(0); }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); openMenu(options.length - 1); }
    });

    syncSelector();
  }

  function init() {
    lang = detect();
    apply();
    wireSelector();
  }

  window.TWI18n = {
    init: init,
    t: t,
    set: set,
    apply: apply,
    langs: LANGS,
    current: function () { return lang; },
    tag: function () {
      var meta = (window.TW_LOCALES || {})[lang];
      return (meta && meta.tag) || lang;
    },
    onChange: function (fn) { watchers.push(fn); }
  };
}());
