/* The DOM that IT's registration code looks for -- nothing else.

   Registration and connection are IT's, 1:1 (owner, 2026-11-12, decision 25).
   IT's files sit in js/it/ as they came in their archive test6637.zip
   (_js/main.js, _js/analytics.js, _js/enums/*, _js/api/resilve-recaptcha.js,
   _js/utils/url.js, _js/utils/form-validations.js) and are loaded by
   index.html as <script type="module" src="js/it/main.js">. They run the
   config, the landing GET, ipify, reCAPTCHA, the POST, the validation, the
   success modal, the SSO hand-off, the errors and the analytics. This file
   contains none of that, and must not grow any of it back.

   What it does is give main.js the elements it queries with document
   .querySelector, on our dialog, so that main.js itself needs no selector
   change. It runs BEFORE main.js (a deferred classic script ahead of a module
   script in index.html) and after js/shell.js, which has built the dialog.

     IT looks for                  we give it
     .form-register                #tw-form (the submit event is IT's)
     .input-email / .input-password  #tw-email / #tw-password
     .input-wrap / .input-password-wrap  the two .tw-field boxes (IT toggles
                                   ".valid" on them; css/it-adapter.css draws it)
     .terms-wrap (class "active")  .tw-agree, whose checkbox is checked
     .show-password-btn            .tw-eye
     .form-register-submit         the dialog's submit button
     .terms-link .policy-link .login-text a   the three anchors we already have
     .error-email/-password/-terms  IT's own .field-error blocks, inserted
     .lang-list button             a hidden mirror of our language choice:
                                   IT sends the active button's text lowercased
     .modal__wrap .success-modal .disabled-modal #sso   static markup, index.html

   Three things IT's page has no reason to do, because it has one language and
   no pop-up on top of the page:
     * language: IT's buttons are .lang-list button. Ours is a menu of <li>, so
       a hidden .lang-list holds one <button> per language (text UA / RU / EN),
       the current one first and clicked whenever the language changes. IT's own
       click handler then does what it always does.
     * the pop-up is a native <dialog>, in the TOP LAYER: IT's modals are plain
       fixed boxes and would open behind it. The dialog is closed when one of
       them becomes active.
     * shell.js re-wires the three links on every language change and removes
       an href it has no value for. The hrefs IT set are remembered and put back.
   One more, in the consent box: IT toggles its state on a click on .terms-wrap,
   and a click on the <label> also clicks the checkbox, which would count twice.
   The label's own activation is cancelled and the checkbox is set from IT's
   state, which is the ".active" class IT toggles on .terms-wrap.

   The phone tab is removed (registration/email is the only route there is). */

(function () {
  'use strict';

  var dialog = document.getElementById('tw-signup');
  if (!dialog) return;

  function $(sel) { return dialog.querySelector(sel); }
  function addClass(sel, cls) {
    var el = $(sel);
    if (el) cls.split(' ').forEach(function (c) { el.classList.add(c); });
    return el;
  }

  /* ── the form, minus the phone tab ────────────────────────── */

  /* The registration API is registration/email. There is no phone route, so
     the tab goes. The email panel loses its tabpanel role: it would point at a
     tab that is gone. */
  ['.tw-tabs', '.tw-field[data-field="phone"]'].forEach(function (sel) {
    var el = $(sel);
    if (el) el.parentNode.removeChild(el);
  });
  var emailBox = $('.tw-field[data-field="email"]');
  if (emailBox) {
    emailBox.removeAttribute('role');
    emailBox.removeAttribute('aria-labelledby');
  }

  /* ── the hooks IT queries ─────────────────────────────────── */

  addClass('#tw-form', 'form-register');
  addClass('#tw-email', 'input-email');
  addClass('#tw-password', 'input-password');
  addClass('.tw-field[data-field="email"]', 'input-wrap');
  addClass('.tw-field[data-field="password"]', 'input-password-wrap');
  var terms = addClass('.tw-agree', 'terms-wrap active');
  addClass('.tw-eye', 'show-password-btn');
  addClass('.tw-cta[type="submit"]', 'form-register-submit');
  addClass('[data-tw-link="terms"]', 'terms-link');
  addClass('[data-tw-link="privacy"]', 'policy-link');
  addClass('.tw-foot', 'login-text');

  /* IT's three error blocks, markup as in their index.html: the block, an
     <img> (their stylesheet hides it) and the <span> main.js writes into. Each
     sits right after the box it belongs to, which is what IT's CSS expects. */
  function errorBlock(name) {
    var el = document.createElement('div');
    el.className = 'field-error error-' + name;
    el.innerHTML = '<img src="assets/img/it/error.svg" alt="error"><span></span>';
    return el;
  }
  [['.tw-field[data-field="email"]', 'email'],
   ['.tw-field[data-field="password"]', 'password'],
   ['.tw-agree', 'terms']].forEach(function (p) {
    var anchor = $(p[0]);
    if (anchor) anchor.parentNode.insertBefore(errorBlock(p[1]), anchor.nextSibling);
  });

  /* ── the consent box ──────────────────────────────────────── */

  if (terms) {
    var box = terms.querySelector('input[type="checkbox"]');
    terms.addEventListener('click', function (ev) {
      /* Registered before IT's listener, so it runs first. A link keeps its
         own click; anything else must not also activate the checkbox. */
      if (!(ev.target.closest && ev.target.closest('a'))) ev.preventDefault();
    });
    new MutationObserver(function () {
      /* After the click has finished: a cancelled checkbox click puts the old
         value back at the very end of the dispatch. */
      setTimeout(function () { box.checked = terms.classList.contains('active'); }, 0);
    }).observe(terms, { attributes: true, attributeFilter: ['class'] });
  }

  /* ── language: the buttons IT reads ───────────────────────── */

  (function () {
    var C = window.TW_CAMPAIGN || {};
    var codes = (C.languages || []).slice();
    var now = window.TWI18n ? TWI18n.current() : codes[0];
    codes.sort(function (a, b) { return (b === now) - (a === now); });   // current first
    var list = document.createElement('div');
    list.className = 'lang-list';
    list.hidden = true;
    codes.forEach(function (code) {
      var b = document.createElement('button');
      b.type = 'button';
      b.textContent = code.toUpperCase();
      list.appendChild(b);
    });
    document.body.appendChild(list);
    if (window.TW) TW.on('lang', function (code) {
      Array.prototype.forEach.call(list.children, function (b) {
        if (b.textContent === String(code).toUpperCase()) b.click();
      });
    });
  }());

  /* ── the three links survive a language change ────────────── */

  (function () {
    var kept = [];
    ['.terms-link', '.policy-link', '.login-text a'].forEach(function (sel) {
      var a = $(sel);
      if (!a) return;
      var rec = { a: a, href: null };
      kept.push(rec);
      new MutationObserver(function () {
        var h = a.getAttribute('href');
        if (h) rec.href = h;
      }).observe(a, { attributes: true, attributeFilter: ['href'] });
    });
    if (window.TW) TW.on('lang', function () {
      kept.forEach(function (rec) {
        if (rec.href && rec.a.getAttribute('href') !== rec.href) rec.a.setAttribute('href', rec.href);
      });
    });
  }());

  /* ── IT's modals open above a native <dialog> ─────────────── */

  ['.success-modal', '.modal__wrap', '.disabled-modal'].forEach(function (sel) {
    var el = document.querySelector(sel);
    if (!el) return;
    new MutationObserver(function () {
      if (el.classList.contains('active') && window.TWForm) TWForm.close();
    }).observe(el, { attributes: true, attributeFilter: ['class'] });
  });
}());
