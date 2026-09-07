/* Top Win registration dialog — behaviour.

   SHARED FILE. A campaign never edits this; tools/drift.py fails CI if it
   moves. What a campaign changes is in campaign.js: the offer, the five URLs,
   the endpoint, the hidden fields.

   The markup is built by js/shell.js and handed here through mount(). This
   file only ever sees a DOM that already exists, which is why there is no
   null-guarding maze below: mount() returns early once, and every handler
   after it can assume its element.

   ── The dialog is native ─────────────────────────────────────
   showModal() puts it in the TOP LAYER. That is not a style preference, it is
   what makes the card reusable: it renders identically over a fixed no-scroll
   stage, an artboard hero and an ordinary scrolling page, with no z-index
   negotiation with the campaign, and it cannot be trapped by an ancestor's
   overflow or transform. It also deletes about eighty lines of hand-written
   focus trap, inert bookkeeping, Escape handling and scroll locking that the
   previous landing had to carry and could not share, because its overlay was
   positioned inside a stage that only that page had.

   ── Where the data goes ──────────────────────────────────────
   Nowhere, by default. With form.endpoint empty and form.onRegister null the
   validated payload is logged and, if form.demoDone is on, the confirmation
   screen is walked anyway. The page is fully demoable before the platform
   exists, and it cannot silently half-ship: there is no state in which it
   looks wired and is not.

   The password is in the payload, because a registration hook without one is
   useless. That is also why form.endpoint must point at the operator's own
   TLS endpoint and nowhere else. */

(function () {
  'use strict';

  var C = window.TW_CAMPAIGN || {};
  var F = C.form || {};

  var PHONE_DIGITS = F.phoneDigits || 9;
  var PHONE_PREFIX = F.dialCode || '+380';
  var PASSWORD_MIN = F.passwordMin || 8;

  var EMAIL = /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i;

  var dialog, form, stepForm, stepDone;
  var tabs = [], panels = {};
  var mode = 'email';
  var opener = null;
  var mounted = false;

  function $(sel, root) { return (root || dialog).querySelector(sel); }
  function $$(sel, root) {
    return Array.prototype.slice.call((root || dialog).querySelectorAll(sel));
  }
  function t(key, vars) { return window.TWI18n ? TWI18n.t(key, vars) : key; }

  /* ── validation ───────────────────────────────────────────── */

  /* Ukrainian mobile numbers are nine digits behind +380, and visitors type
     them in three shapes. All three normalise to the same canonical value,
     because a number rejected for having the country code in it is a number
     the visitor typed correctly. */
  function phoneDigits() {
    var raw = $('#tw-phone').value.replace(/\D/g, '');
    var cc = PHONE_PREFIX.replace(/\D/g, '');
    if (cc && raw.indexOf(cc) === 0) raw = raw.slice(cc.length);      // 380XXXXXXXXX
    else if (raw.length === PHONE_DIGITS + 1 && raw[0] === '0') raw = raw.slice(1); // 0XXXXXXXXX
    return raw;
  }

  function value(name) {
    return name === 'phone' ? PHONE_PREFIX + phoneDigits() : $('#tw-email').value.trim();
  }

  var CHECK = {
    email:    function () { return EMAIL.test($('#tw-email').value.trim()); },
    phone:    function () { return phoneDigits().length === PHONE_DIGITS; },
    password: function () { return $('#tw-password').value.length >= PASSWORD_MIN; }
  };

  var ERR_KEY = { email: 'err.email', phone: 'err.phone', password: 'err.password' };

  function field(name) { return $('.tw-field[data-field="' + name + '"]'); }

  /* Two attributes and a message, in one place, so a field can never end up
     marked valid and invalid at once. `state` is 'valid' | 'invalid' | null. */
  function mark(name, state) {
    var el = field(name);
    var input = $('input', el);
    var err = $('.tw-err', el);

    if (state === 'valid') el.setAttribute('data-valid', ''); else el.removeAttribute('data-valid');
    if (state === 'invalid') el.setAttribute('data-invalid', ''); else el.removeAttribute('data-invalid');
    input.setAttribute('aria-invalid', String(state === 'invalid'));

    if (state === 'invalid') {
      err.textContent = t(ERR_KEY[name]);
      /* reset.css forces [hidden] { display: none !important } and display
         cannot be transitioned, so: unhide, let a frame pass, then add the
         class the transition runs on. The language menu does the same. */
      err.hidden = false;
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { err.classList.add('is-shown'); });
      });
    } else {
      err.classList.remove('is-shown');
      err.hidden = true;
      err.textContent = '';
    }
  }

  /* Live checking only ever ADDS the valid mark. A field is never turned red
     while the visitor is still typing it -- an email is invalid for most of
     the time it takes to write one, and saying so mid-word is scolding, not
     helping. Red arrives on blur, or on submit. */
  function live(name) {
    if (CHECK[name]()) mark(name, 'valid');
    else if (field(name).hasAttribute('data-invalid')) mark(name, null);
  }

  function grade(name) {
    var el = field(name);
    var input = $('input', el);
    if (!input.value) { mark(name, null); return true; }   // empty is not yet wrong
    var ok = CHECK[name]();
    mark(name, ok ? 'valid' : 'invalid');
    return ok;
  }

  /* Marks every field, then focuses the FIRST bad one only. role="alert" on
     the message announces it; the focus move is what locates it. One without
     the other leaves a screen-reader user told that something is wrong and
     not told where. */
  function validate() {
    var order = [mode, 'password'];
    var first = null;

    order.forEach(function (name) {
      var ok = CHECK[name]();
      mark(name, ok ? 'valid' : 'invalid');
      if (!ok && !first) first = name;
    });

    var agree = $('#tw-agree');
    if (!agree.checked) {
      agree.setAttribute('aria-invalid', 'true');
      if (!first) { agree.focus({ preventScroll: false }); return false; }
    } else {
      agree.setAttribute('aria-invalid', 'false');
    }

    if (first) { $('input', field(first)).focus({ preventScroll: false }); return false; }
    return agree.checked;
  }

  /* ── tabs ─────────────────────────────────────────────────── */

  function setMode(next) {
    if (next === mode) return;
    mode = next;
    tabs.forEach(function (tab) {
      tab.setAttribute('aria-selected', String(tab.getAttribute('data-mode') === mode));
    });
    Object.keys(panels).forEach(function (key) { panels[key].hidden = key !== mode; });
    /* The field that just left the screen keeps no error: its message would
       be announced by a live region the visitor can no longer see. */
    mark(next === 'email' ? 'phone' : 'email', null);
    $('input', panels[mode]).focus({ preventScroll: true });
  }

  /* ── submit ───────────────────────────────────────────────── */

  function payload() {
    var out = {
      method:     mode,
      contact:    value(mode),
      email:      mode === 'email' ? value('email') : '',
      phone:      mode === 'phone' ? value('phone') : '',
      password:   $('#tw-password').value,
      consent:    $('#tw-agree').checked,
      lang:       window.TWI18n ? TWI18n.tag() : document.documentElement.lang,
      bonus:      (C.offer || {}).code || '',
      landing_id: C.id || ''
    };
    var extra = F.hiddenFields || {}, k;
    for (k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) out[k] = extra[k];
    /* The campaign's own UTM block and whatever rode in on the landing URL,
       so a conversion can be attributed without a cookie. */
    var params = window.TW ? TW.params() : {};
    for (k in params) if (Object.prototype.hasOwnProperty.call(params, k)) out[k] = params[k];
    return out;
  }

  function formError(message) {
    var box = $('.tw-err[data-form-error]');
    box.textContent = message;
    box.hidden = false;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { box.classList.add('is-shown'); });
    });
  }

  function onSubmit(ev) {
    ev.preventDefault();
    if (!validate()) return;

    var data = payload();
    if (window.TW) TW.track('form_submit', { method: data.method });

    var send = null;
    if (typeof F.onRegister === 'function') send = F.onRegister(data);
    else if (F.endpoint) {
      send = fetch(F.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json().catch(function () { return null; });
      });
    }

    if (!send) {
      /* The shipped default. Loud in the console, invisible to the visitor,
         and impossible to mistake for a working integration. */
      console.info(
        '[' + (C.id || 'tw') + '] The form is valid but not wired to anything. ' +
        'Set form.endpoint (or form.onRegister) in campaign.js. Payload:', data);
      if (F.demoDone) showDone({ login: data.contact, password: data.password });
      return;
    }

    if (!send.then) send = Promise.resolve(send);
    send.then(function (res) {
      if (window.TW) TW.track('form_success', { method: data.method });
      showDone(res && (res.login || res.password)
        ? res
        : { login: data.contact, password: data.password });
    }, function () {
      formError(t('err.network'));
    });
  }

  /* ── the confirmation screen ──────────────────────────────── */

  /* The promo header stays; only the body below it swaps, so the dialog is
     never closed and reopened and the visitor never sees it flicker.

     Values go in with textContent, never innerHTML: they are whatever the
     visitor typed, or whatever an endpoint returned, and neither is trusted
     markup. */
  function showDone(res) {
    res = res || {};
    $('.tw-done__id').textContent = res.login || '';
    $('.tw-done__pw').textContent = res.password || '';

    stepForm.hidden = true;
    stepDone.hidden = false;
    if (window.TWI18n) TWI18n.apply(stepDone);

    /* Focus the heading so the swap is announced. It is tabindex="-1" and
       css/form.css removes its ring: a ring on a heading nobody clicked reads
       as a rendering fault. */
    $('.tw-done__title').focus({ preventScroll: true });
    if (window.TW) TW.emit('register', res);
  }

  function showForm() {
    stepDone.hidden = true;
    stepForm.hidden = false;
  }

  /* Clipboard first; the selection fallback is for a page opened over plain
     http or from a file, where navigator.clipboard is simply undefined.
     Someone will double-click the HTML. */
  function copy(button) {
    var text = $(button.getAttribute('data-copy')).textContent;
    var done = function () {
      button.classList.add('is-copied');
      button.setAttribute('aria-label', t('done.copied'));
      setTimeout(function () {
        button.classList.remove('is-copied');
        button.setAttribute('aria-label', t('done.copy'));
      }, 1600);
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { legacy(text, done); });
    } else {
      legacy(text, done);
    }
  }

  function legacy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { /* nothing to offer */ }
    document.body.removeChild(ta);
  }

  /* ── open / close ─────────────────────────────────────────── */

  function open() {
    if (!mounted || dialog.open) return;
    opener = document.activeElement;
    showForm();
    dialog.showModal();
    if (window.TW) TW.emit('formopen');
  }

  function close() {
    if (mounted && dialog.open) dialog.close();
  }

  /* ── mount ────────────────────────────────────────────────── */

  function mount(root) {
    dialog = root;
    if (!dialog) return;

    form = $('#tw-form');
    stepForm = $('[data-step="form"]');
    stepDone = $('[data-step="done"]');

    tabs = $$('.tw-tab');
    panels.email = $('.tw-field[data-field="email"]');
    panels.phone = $('.tw-field[data-field="phone"]');

    tabs.forEach(function (tab) {
      tab.addEventListener('click', function () { setMode(tab.getAttribute('data-mode')); });
    });

    ['email', 'phone', 'password'].forEach(function (name) {
      var input = $('input', field(name));
      input.addEventListener('input', function () { live(name); });
      input.addEventListener('blur', function () { grade(name); });
    });

    /* The field accepts the number in three shapes and the validator
       normalises all three, but the box still showed what was typed -- so a
       visitor who pasted 380931234567 read "+380 380931234567" and could not
       tell whether it had been understood. Written back on blur, once the
       number is complete, so nothing is rewritten mid-typing. */
    $('#tw-phone').addEventListener('blur', function () {
      var digits = phoneDigits();
      if (digits.length === PHONE_DIGITS) this.value = digits;
    });

    var eye = $('.tw-eye');
    eye.addEventListener('click', function () {
      var input = $('#tw-password');
      var shown = input.type === 'text';
      input.type = shown ? 'password' : 'text';
      eye.setAttribute('aria-pressed', String(!shown));
      eye.setAttribute('aria-label', t(shown ? 'field.reveal' : 'field.hide'));
      input.focus({ preventScroll: true });
    });

    $('#tw-agree').addEventListener('change', function () {
      this.setAttribute('aria-invalid', String(!this.checked));
    });

    form.addEventListener('submit', onSubmit);

    $$('[data-tw-close]').forEach(function (b) {
      b.addEventListener('click', function () { close(); });
    });

    $$('.tw-copy').forEach(function (b) {
      b.addEventListener('click', function () { copy(b); });
    });

    /* `close` fires for Escape and for the close button alike, so focus
       restoration lives here once rather than at every exit. */
    dialog.addEventListener('close', function () {
      if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
      opener = null;
      if (window.TW) TW.emit('formclose');
    });

    /* A click on the backdrop lands on the dialog element itself, never on
       anything inside the card. */
    dialog.addEventListener('click', function (ev) {
      if (ev.target === dialog) close();
    });

    mounted = true;
  }

  window.TWForm = {
    mount: mount,
    open: open,
    close: close,
    showDone: showDone,
    isOpen: function () { return !!(dialog && dialog.open); }
  };
}());
