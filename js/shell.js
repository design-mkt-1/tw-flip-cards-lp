/* Top Win shell — builds the chrome, wires the seams, exposes window.TW.

   SHARED FILE. A campaign never edits this; tools/drift.py fails CI if it
   moves.

   ── Why the markup is here and not in index.html ─────────────
   There is no bundler in this repo and there will not be one: both landings
   this template replaces are plain files copied to GitHub Pages, and the team
   that integrates them reads HTML, not a build config. So the header, the
   footer and the registration dialog are template strings in this file, and
   index.html carries two empty mount points and a <main> the campaign owns.

   That is what makes them shared. The alternative — the same chrome pasted
   into every campaign's HTML — is exactly what produced two footers, two
   modals and no header at all across the last two pages.

   What it costs, stated plainly rather than defended:
     * the chrome needs JavaScript. Both existing landings are already dead
       without it (no game, no form), and the campaign hero is static HTML and
       still paints.
     * the header and footer are not in view-source. <title>, description and
       hreflang stay static in <head>, where a crawler reads them.
     * fetch('partials/header.html') was the obvious alternative and is dead
       on file://, which someone will use. A build step that inlines partials
       is the thing being avoided.

   Rejected for the same reason: server includes and Jekyll (both repos ship
   .nojekyll deliberately), and custom elements (the same innerHTML under a
   heavier lifecycle, plus a second thing to explain).

   ── Load order ───────────────────────────────────────────────
   campaign.js, strings.js, i18n.js, form.js, shell.js, campaign/main.js — all
   `defer`, which preserves source order and runs everything before
   DOMContentLoaded. That order IS the dependency graph. */

(function () {
  'use strict';

  var C = window.TW_CAMPAIGN || {};
  var LOC = window.TW_LOCALES || {};

  var readyQueue = [];
  var listeners = {};
  var booted = false;

  /* Params that rode in on the landing URL and are allowed through to the
     outbound click. Read once, at boot, because a campaign may replace the
     query string later (a mechanic writing history state) and the affiliate
     id must survive that. */
  var passed = (function () {
    var out = {};
    var q = new URLSearchParams(location.search);
    (C.passthrough || []).forEach(function (name) {
      var v = q.get(name);
      if (v) out[name] = v;
    });
    return out;
  }());

  function params() {
    var out = {}, k;
    var own = C.params || {};
    for (k in own) if (Object.prototype.hasOwnProperty.call(own, k)) out[k] = own[k];
    for (k in passed) if (Object.prototype.hasOwnProperty.call(passed, k)) out[k] = passed[k];
    return out;
  }

  /* links.<name> with params and passthrough appended, or null when it is not
     set. Null is meaningful: the caller leaves the anchor without an href
     rather than pointing it at "#". */
  function url(name) {
    var base = (C.links || {})[name];
    if (!base) return null;
    var all = params();
    var keys = Object.keys(all);
    if (!keys.length) return base;

    var joiner = base.indexOf('?') < 0 ? '?' : '&';
    var q = keys.map(function (k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(all[k]);
    }).join('&');
    return base + joiner + q;
  }

  /* ── analytics ────────────────────────────────────────────── */

  /* Nothing is injected and no third-party request is made unless an id is
     configured, which is why the CSP in index.html can ship as 'self'. If you
     set one of these you must also swap that meta — a meta policy cannot be
     written from script, and a CSP refusal appears only in the console. */
  function injectAnalytics() {
    var a = C.analytics || {};

    if (a.gtmId) {
      window.dataLayer = window.dataLayer || [];
      window.dataLayer.push({ 'gtm.start': Date.now(), event: 'gtm.js' });
      var g = document.createElement('script');
      g.async = true;
      g.src = 'https://www.googletagmanager.com/gtm.js?id=' + encodeURIComponent(a.gtmId);
      document.head.appendChild(g);
    }

    if (a.metaPixelId) {
      /* Meta's own snippet, transcribed rather than eval'd from a string, so
         script-src stays free of 'unsafe-inline'. */
      /* eslint-disable */
      !function (f, b, e, v, n, t, s) {
        if (f.fbq) return; n = f.fbq = function () {
          n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
        };
        if (!f._fbq) f._fbq = n; n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
        t = b.createElement(e); t.async = true; t.src = v;
        s = b.getElementsByTagName(e)[0]; s.parentNode.insertBefore(t, s);
      }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
      /* eslint-enable */
      window.fbq('init', a.metaPixelId);
      window.fbq('track', 'PageView');
    }
  }

  function track(event, props) {
    var a = C.analytics || {};
    var payload = props || {};
    payload.landing_id = C.id || '';
    payload.lang = window.TWI18n ? TWI18n.current() : '';
    var all = params(), k;
    for (k in all) if (Object.prototype.hasOwnProperty.call(all, k)) payload[k] = all[k];

    if (window.dataLayer) window.dataLayer.push(Object.assign({ event: event }, payload));
    if (window.fbq) window.fbq('trackCustom', event, payload);
    if (a.debug) console.info('[track]', event, payload);
  }

  /* ── events ───────────────────────────────────────────────── */

  function on(name, fn) { (listeners[name] = listeners[name] || []).push(fn); }

  function emit(name, data) {
    (listeners[name] || []).forEach(function (fn) {
      /* A campaign's own listener must not be able to strand the visitor in a
         half-open dialog, so a throw here is contained and reported. */
      try { fn(data); } catch (e) { console.error('[TW.on ' + name + ']', e); }
    });
  }

  /* ── markup ───────────────────────────────────────────────── */

  var ICON = {
    globe: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
           '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 2.5 15.4 0 18' +
           'M12 3c-2.5 2.6-2.5 15.4 0 18"/></svg>',
    caret: '<svg class="tw-lang__caret" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
           '<path d="m6 9 6 6 6-6"/></svg>',
    tick:  '<svg class="tw-langopt__check" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
           '<path d="m5 13 4 4 10-10"/></svg>',
    close: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
           'stroke-linecap="round" aria-hidden="true" focusable="false">' +
           '<path d="M6 6l12 12M18 6L6 18"/></svg>',
    copy:  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
           '<rect x="9" y="9" width="12" height="12" rx="2"/>' +
           '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    sound: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
           '<path class="tw-mute__spk" d="M4 9h4l5-4v14l-5-4H4z"/>' +
           '<g class="tw-mute__on"><path d="M16 9a4 4 0 0 1 0 6"/><path d="M18.5 6.5a8 8 0 0 1 0 11"/></g>' +
           '<g class="tw-mute__off"><path d="m16 9 5 6M21 9l-5 6"/></g></svg>'
  };

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function headerHTML() {
    var b = C.brand || {};
    var h = C.header || {};
    var langs = (C.languages || []).filter(function (code) { return LOC[code]; });

    var right = '';
    if (h.mute) {
      right += '<button class="tw-mute" type="button" aria-pressed="false" ' +
               'data-i18n-attr="aria-label:hdr.sound">' + ICON.sound + '</button>';
    }
    if (h.lang !== false && langs.length > 1) {
      /* Built from TW_LOCALES filtered by campaign.languages. The previous
         landing hand-wrote three <li> in its HTML, which is precisely the
         component edit that made adding a language a code change. */
      var options = langs.map(function (code) {
        var meta = LOC[code];
        return '<li class="tw-langopt" role="option" data-lang="' + esc(code) + '" ' +
               'aria-selected="false" tabindex="-1">' +
               '<img class="tw-langopt__flag" src="assets/img/icons/' + esc(meta.flag) + '" alt="">' +
               '<span class="tw-langopt__code">' + esc(code.toUpperCase()) + '</span>' +
               '<span class="tw-langopt__name">' + esc(meta.name) + '</span>' +
               ICON.tick + '</li>';
      }).join('');

      right += '<div class="tw-lang-wrap">' +
               '<button class="tw-lang" type="button" id="tw-lang-btn" aria-haspopup="listbox" ' +
               'aria-expanded="false" data-i18n-attr="aria-label:hdr.lang">' +
               ICON.globe + '<span class="tw-lang__code"></span>' + ICON.caret + '</button>' +
               '<ul class="tw-langmenu" role="listbox" aria-labelledby="tw-lang-btn" hidden>' +
               options + '</ul></div>';
    }

    return '<header class="tw-hdr">' +
           '<a class="tw-hdr__logo" data-tw-link="home" aria-label="' + esc(b.logoAlt || 'Top Win') + '">' +
           '<img src="' + esc(b.logo) + '" alt="' + esc(b.logoAlt || 'Top Win') + '" width="120" height="21">' +
           '</a>' +
           '<div class="tw-hdr__right">' + right + '</div>' +
           '</header>';
  }

  var PAY = {
    visa:       { file: 'pay-visa.svg',       alt: 'Visa',       cls: ' tw-ftr__mark--visa' },
    mastercard: { file: 'pay-mastercard.svg', alt: 'Mastercard', cls: ' tw-ftr__mark--mc' },
    tether:     { file: 'pay-tether.svg',     alt: 'Tether',     cls: '' },
    bitcoin:    { file: 'pay-bitcoin.svg',    alt: 'Bitcoin',    cls: '' }
  };

  function footerHTML() {
    var b = C.brand || {};
    var marks = (b.payments || []).filter(function (k) { return PAY[k]; }).map(function (k) {
      var p = PAY[k];
      return '<li class="tw-ftr__badge"><img class="tw-ftr__mark' + p.cls +
             '" src="assets/img/icons/' + p.file + '" alt="' + p.alt + '"></li>';
    }).join('');

    /* The DOM order is the mobile node's -- payments, then copyright. The wide
       arrangement restates its own order in CSS, so reading order and visual
       order match in both. */
    return '<footer class="tw-ftr">' +
           '<span class="tw-ftr__logo"><img src="' + esc(b.logo) + '" alt="" width="96" height="17"></span>' +
           '<div class="tw-ftr__pay">' +
           '<p class="tw-ftr__label" data-i18n="footer.pay"></p>' +
           '<ul class="tw-ftr__marks">' + marks + '</ul>' +
           '</div>' +
           '<p class="tw-ftr__copy" data-i18n="footer.copy"></p>' +
           '</footer>';
  }

  function fieldHTML(name, opts) {
    var F = C.form || {};
    var isPhone = name === 'phone';
    var lead = isPhone
      ? '<img class="tw-input__flag" src="' + esc(F.dialFlag) + '" alt="">' +
        '<span class="tw-input__prefix">' + esc(F.dialCode) + '</span>'
      : '';

    return '<div class="tw-field" data-field="' + name + '"' + (opts.attrs || '') + '>' +
           (opts.label ? '<span class="tw-label" data-i18n="' + opts.label + '"></span>' : '') +
           '<label class="tw-input' + (isPhone ? ' tw-input--phone' : '') + '">' +
           '<span class="tw-sr-only" data-i18n="' + opts.name + '"></span>' + lead +
           '<input id="tw-' + name + '" type="' + opts.type + '"' + (opts.extra || '') +
           ' data-i18n-attr="placeholder:' + opts.placeholder + '"' +
           ' aria-describedby="tw-err-' + name + '" aria-invalid="false">' +
           (opts.eye
             ? '<button class="tw-eye" type="button" aria-pressed="false" ' +
               'data-i18n-attr="aria-label:field.reveal">' +
               '<img src="assets/img/icons/eye.svg" alt=""></button>'
             : '') +
           '<span class="tw-ok"><img src="assets/img/icons/check.svg" alt=""></span>' +
           '</label>' +
           '<p class="tw-err" id="tw-err-' + name + '" role="alert" hidden></p>' +
           '</div>';
  }

  function dialogHTML() {
    var b = C.brand || {};
    var offer = C.offer || {};

    var promo =
      '<div class="tw-promo">' +
      '<img class="tw-promo__logo" src="' + esc(b.logo) + '" alt="' + esc(b.logoAlt || 'Top Win') + '">' +
      '<div class="tw-promo__head">' +
      '<p class="tw-promo__title" id="tw-promo-title" data-i18n="promo.title"></p>' +
      '<div class="tw-promo__offer">' +
      (offer.percent ? '<span class="tw-promo__pct" data-i18n="promo.pct"></span>' : '') +
      (offer.amount ? '<span class="tw-promo__sub" data-i18n="promo.amount"></span>' : '') +
      (offer.spins ? '<span class="tw-promo__sub" data-i18n="promo.spins"></span>' : '') +
      '</div></div></div>';

    /* Five nodes, not one string with markup in it, so a locale can move the
       links within the sentence. The sentence up to the first link is a real
       <label> for the box; the rest is not, because a click on either link
       would otherwise toggle the checkbox on its way to the anchor. */
    var consent =
      '<div class="tw-agree">' +
      '<input class="tw-agree__box" id="tw-agree" type="checkbox" checked ' +
      'aria-describedby="tw-agree-text" data-i18n-attr="aria-label:agree.aria">' +
      '<p class="tw-agree__text" id="tw-agree-text">' +
      '<label for="tw-agree" data-i18n="agree.pre"></label>' +
      '<a data-tw-link="terms" data-i18n="agree.terms"></a>' +
      '<span data-i18n="agree.mid"></span>' +
      '<a data-tw-link="privacy" data-i18n="agree.privacy"></a>' +
      '<span data-i18n="agree.post"></span>' +
      '</p></div>';

    var signup =
      '<div class="tw-step" data-step="form">' +
      '<div class="tw-tabs" role="tablist" data-i18n-attr="aria-label:tabs.label">' +
      '<button class="tw-tab" type="button" role="tab" id="tw-tab-email" data-mode="email" ' +
      'aria-selected="true" aria-controls="tw-panel-email" data-i18n="tab.email"></button>' +
      '<button class="tw-tab" type="button" role="tab" id="tw-tab-phone" data-mode="phone" ' +
      'aria-selected="false" aria-controls="tw-panel-phone" data-i18n="tab.phone"></button>' +
      '</div>' +
      '<div class="tw-fields">' +
      fieldHTML('email', {
        name: 'field.email', placeholder: 'field.email', type: 'email',
        extra: ' inputmode="email" autocomplete="email"',
        attrs: ' id="tw-panel-email" role="tabpanel" aria-labelledby="tw-tab-email"'
      }) +
      fieldHTML('phone', {
        name: 'field.phoneLabel', placeholder: 'field.phone', type: 'tel',
        extra: ' inputmode="tel" autocomplete="tel-national"',
        attrs: ' id="tw-panel-phone" role="tabpanel" aria-labelledby="tw-tab-phone" hidden'
      }) +
      fieldHTML('password', {
        name: 'field.password', label: 'field.password',
        placeholder: 'field.passwordHint', type: 'password',
        extra: ' autocomplete="new-password"', eye: true
      }) +
      '</div>' +
      consent +
      '<div class="tw-actions">' +
      '<button class="tw-cta" type="submit" data-i18n="cta.register"></button>' +
      '<p class="tw-err" data-form-error role="alert" hidden></p>' +
      '<p class="tw-foot"><span data-i18n="foot.have"></span> ' +
      '<a data-tw-link="login" data-i18n="foot.login"></a></p>' +
      '</div></div>';

    var cred = function (key, cls) {
      return '<div class="tw-cred"><dt data-i18n="' + key + '"></dt>' +
             '<dd class="' + cls + '"></dd>' +
             '<button class="tw-copy" type="button" data-copy=".' + cls + '" ' +
             'data-i18n-attr="aria-label:done.copy">' + ICON.copy + '</button></div>';
    };

    var done =
      '<div class="tw-step tw-done" data-step="done" hidden>' +
      '<hr class="tw-rule">' +
      '<h2 class="tw-done__title" tabindex="-1" data-i18n="done.title"></h2>' +
      '<dl class="tw-creds">' + cred('done.login', 'tw-done__id') +
      cred('done.password', 'tw-done__pw') + '</dl>' +
      '<p class="tw-done__note" data-i18n="done.note"></p>' +
      '<div class="tw-actions">' +
      '<a class="tw-cta" data-tw-link="cta" data-i18n="cta.website"></a>' +
      '</div></div>';

    return '<dialog class="tw-dialog" id="tw-signup" aria-labelledby="tw-promo-title">' +
           '<button class="tw-close" type="button" data-tw-close ' +
           'data-i18n-attr="aria-label:dialog.close">' + ICON.close + '</button>' +
           '<form class="tw-card" id="tw-form" novalidate>' +
           promo + signup + done +
           '</form></dialog>';
  }

  /* ── link wiring ──────────────────────────────────────────── */

  /* An unset link gets NO href, not href="#". A mark that takes focus, is
     announced as a link and then does nothing reads as a broken control; an
     element with no href is simply not a link, which is the honest state of a
     seam nobody has filled in yet. */
  function wireLinks(root) {
    Array.prototype.forEach.call(root.querySelectorAll('[data-tw-link]'), function (el) {
      var href = url(el.getAttribute('data-tw-link'));
      if (href) el.setAttribute('href', href);
      else el.removeAttribute('href');
    });
  }

  /* ── boot ─────────────────────────────────────────────────── */

  function mountSlot(name, html, show) {
    var slot = document.querySelector('[data-tw="' + name + '"]');
    if (!slot) return;
    if (show === false) { slot.remove(); return; }
    slot.outerHTML = html;
  }

  function boot() {
    if (booted) return;
    booted = true;

    var b = C.brand || {};
    if (b.themeColor) {
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', b.themeColor);
    }

    mountSlot('header', headerHTML(), (C.header || {}).show !== false);
    mountSlot('footer', footerHTML(), (C.footer || {}).show !== false);
    document.body.insertAdjacentHTML('beforeend', dialogHTML());

    if (window.TWForm) TWForm.mount(document.getElementById('tw-signup'));

    /* i18n last, so it renders markup that already exists. It also sets
       <html lang> to the real BCP-47 tag. */
    if (window.TWI18n) {
      TWI18n.init();
      TWI18n.onChange(function (code) {
        wireLinks(document);          // a locale can change nothing here, but a
        track('lang_change', { to: code });  // campaign hook might
        emit('lang', code);
      });
    }

    wireLinks(document);
    injectAnalytics();
    track('lp_view');

    readyQueue.forEach(function (fn) {
      try { fn(); } catch (e) { console.error('[TW.ready]', e); }
    });
    readyQueue = null;
  }

  window.TW = {
    config: C,
    t: function (key, vars) { return window.TWI18n ? TWI18n.t(key, vars) : key; },
    lang: function () { return window.TWI18n ? TWI18n.current() : ''; },
    setLang: function (code) { if (window.TWI18n) TWI18n.set(code); },
    url: url,
    params: params,
    openForm: function () { if (window.TWForm) TWForm.open(); },
    closeForm: function () { if (window.TWForm) TWForm.close(); },
    showDone: function (res) { if (window.TWForm) TWForm.showDone(res); },
    track: track,
    on: on,
    emit: emit,
    ready: function (fn) {
      if (readyQueue) readyQueue.push(fn);
      else fn();
    }
  };

  /* `defer` already guarantees the document is parsed, so this runs now
     rather than waiting for DOMContentLoaded -- which matters, because
     campaign/main.js is the next deferred script and its TW.ready() callbacks
     should run in the same tick, not a frame later. */
  boot();
}());
