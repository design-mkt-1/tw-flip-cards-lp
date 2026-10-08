/* The IT platform connection -- this landing's own, NOT the template's.

   js/form.js, js/shell.js and the other shared files are never edited here, so
   everything the platform needs is attached from outside through the seams the
   template leaves open: form.onRegister in campaign.js, TW.on('lang'), and the
   DOM that js/shell.js has already built by the time this file runs (it is
   loaded after shell.js, which mounts the dialog synchronously in boot()).

   It follows IT's reference landing step for step (their _js/main.js), so their
   deploy drops in: same config shape, same two requests, same body, same SSO.

   ── The flow ─────────────────────────────────────────────────
   1. config.   Development (localhost, 127.0.0.1, or an origin containing
                https://land-crm) uses campaign.js § platform.dev, which is IT's
                TEMP_CONFIG. Everywhere else config.json is fetched from the
                site root: { id, email_registration, landing }.
   2. landing.  GET config.landing -> { data: { active, recaptcha_key, country,
                currency, promocode, rules, policy, login, redirect_link } }.
                active false: the "unavailable" card, and nothing else happens.
                Otherwise the Terms / Privacy / Login links come from the API
                and reCAPTCHA v3 is loaded with the key the API gave us.
   3. submit.   reCAPTCHA token, visitor IP, then POST config.email_registration.
   4. success.  response.data.accessToken goes to <casino>/api/welcome as a
                hidden form POST (tmpToken + redirect), and the visitor lands on
                the platform already logged in. The confirmation screen of the
                template is never shown: it exists to display a login and a
                password, and here there is nothing to display.

   ── What form.js does with what we return ────────────────────
   onRegister's result is awaited. Resolve -> showDone() with the credentials.
   Reject -> the generic "could not send" line. So:
     * success  -> a promise that NEVER settles. The page is navigating away;
                   resolving would flash the done screen, and the password the
                   visitor just typed, for the length of the redirect.
     * a message we have our own words for (email taken, reCAPTCHA) -> written
                   into the form's error line here, then also never settles.
     * anything else -> reject, and the template's generic line shows.
     * no config.json at all (404) -> resolve with nothing: the template's demo
                   path, the confirmation screen with what was typed, and a
                   console warning. Invisible to the visitor, impossible to
                   mistake for a working integration in the console.

   The password is in the request body. config.email_registration must be the
   operator's own TLS endpoint and nowhere else, same as form.endpoint. */

(function () {
  'use strict';

  var C = window.TW_CAMPAIGN || {};
  var P = C.platform || {};
  var F = C.form || {};

  var dialog = document.getElementById('tw-signup');

  function t(key) { return window.TWI18n ? TWI18n.t(key) : key; }
  function assign(target) {
    for (var i = 1; i < arguments.length; i++) {
      var src = arguments[i] || {};
      for (var k in src) if (Object.prototype.hasOwnProperty.call(src, k)) target[k] = src[k];
    }
    return target;
  }

  /* ── the form, minus the phone tab ────────────────────────── */

  /* The registration API is registration/email. There is no phone route, so
     the tab goes. The template has no option for it (checked: nothing in
     shell.js or form.js reads one), and form.js is not ours to edit, so the
     nodes are removed after the shell built them. form.js stays in 'email'
     mode because nothing is left to click that would change it. The email
     panel loses its tabpanel role: it would point at a tab that is gone. */
  function dropPhone() {
    if (!dialog) return;
    ['.tw-tabs', '.tw-field[data-field="phone"]'].forEach(function (sel) {
      var el = dialog.querySelector(sel);
      if (el) el.parentNode.removeChild(el);
    });
    var email = dialog.querySelector('.tw-field[data-field="email"]');
    if (email) {
      email.removeAttribute('role');
      email.removeAttribute('aria-labelledby');
    }
  }

  /* ── config and landing ───────────────────────────────────── */

  /* IT's own test: their staging host, or a developer's machine. */
  function isDevelopment() {
    return location.origin.indexOf('https://land-crm') === 0 ||
           location.hostname === 'localhost' ||
           location.hostname === '127.0.0.1';
  }

  var configP = null;
  var landingP = null;
  var recaptchaP = null;
  var landing = null;      // { data, config, domain } once active
  var analyticsOn = false; // injectAnalytics runs once, even if the landing is retried
  var offShown = false;
  var busy = false;

  /* Resolves to the config object, or null when there is none to find. Only a
     404 on config.json means "nobody deployed one"; a network failure or a
     malformed file is a fault and rejects. */
  function loadConfig() {
    if (isDevelopment() && P.dev) return Promise.resolve(P.dev);
    if (configP) return configP;
    configP = fetch(P.configUrl || 'config.json', { cache: 'no-store' })
      .then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error('config.json: HTTP ' + r.status);
        return r.json();
      })
      .then(function (cfg) {
        if (cfg === null) return null;
        if (!cfg || !cfg.id || !cfg.email_registration || !cfg.landing) {
          throw new Error('config.json needs { id, email_registration, landing }');
        }
        return cfg;
      });
    configP.catch(function () { configP = null; });   // a fault is retried at submit
    return configP;
  }

  function withQuery(href) {
    if (!href) return href;
    var q = location.search ? location.search.slice(1) : '';
    if (!q) return href;
    return href + (href.indexOf('?') < 0 ? '?' : '&') + q;
  }

  /* The links are set on the anchors and set AGAIN on a language change:
     shell.js re-runs wireLinks() on every switch and, for a link whose
     campaign.js value is empty, removes the href it finds. TW.on('lang') fires
     after that, so ours wins. */
  function applyLinks() {
    if (!landing) return;
    var map = { terms: landing.data.rules, privacy: landing.data.policy, login: landing.data.login };
    Object.keys(map).forEach(function (name) {
      if (!map[name]) return;     // keep whatever campaign.js links.* gave it
      Array.prototype.forEach.call(document.querySelectorAll('[data-tw-link="' + name + '"]'), function (a) {
        a.setAttribute('href', withQuery(map[name]));
      });
    });
  }

  function loadRecaptcha(key) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = 'https://www.google.com/recaptcha/api.js?render=' + encodeURIComponent(key);
      s.async = true;
      s.onload = function () { resolve(); };
      s.onerror = function () { reject(new Error('recaptcha script did not load')); };
      document.body.appendChild(s);
    });
  }

  /* Resolves to 'demo' | 'off' | 'ready'. Rejects on any fault. */
  function loadLanding() {
    if (landingP) return landingP;
    landingP = loadConfig().then(function (cfg) {
      if (!cfg) return 'demo';
      return fetch(cfg.landing, {
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }
      }).then(function (r) {
        if (!r.ok) throw new Error('landing: HTTP ' + r.status);
        return r.json();
      }).then(function (res) {
        var d = res && res.data;
        if (!d) throw new Error('landing: no data in the response');
        if (!analyticsOn) { analyticsOn = true; injectAnalytics(d); }   // before the active check, as IT does
        if (!d.active) { showOff(); return 'off'; }
        if (!d.recaptcha_key) throw new Error('landing: no recaptcha_key');

        var domain = '';
        try { domain = 'https://' + new URL(d.rules).hostname; } catch (e) { /* no SSO target */ }
        landing = { data: d, config: cfg, domain: domain };

        applyLinks();
        recaptchaP = loadRecaptcha(d.recaptcha_key);
        recaptchaP.catch(function () { /* reported at submit, where the visitor is */ });
        return 'ready';
      });
    });
    landingP.catch(function (e) {
      console.warn('[platform] could not load the landing:', e && e.message);
      landingP = null;                // the next submit tries again
    });
    return landingP;
  }

  /* ── analytics, as IT's LP does it (their _js/analytics.js) ─
     IT pastes these into inline <script> text. Our CSP has no 'unsafe-inline',
     so that text would be blocked silently. Here the functions live in this
     file and only <script src> elements are appended. The IDs are the only
     thing that reaches code, so each one is checked before use. */

  var ID_PATTERN = {
    google: /^(G-[A-Z0-9]+|UA-\d+-\d+)$/,
    yandex: /^\d+$/,
    gtm:    /^GTM-[A-Z0-9]+$/
  };

  /* The ID as a string when it is valid for its kind, otherwise null. */
  function checkId(kind, id) {
    if (id === undefined || id === null || id === '') return null;
    var s = String(id);
    if (ID_PATTERN[kind].test(s)) return s;
    console.warn('[platform] skipped an invalid ' + kind + ' analytics ID');
    return null;
  }

  function appendScript(src) {
    var s = document.createElement('script');
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
  }

  function injectAnalytics(d) {
    try {
      var ga = checkId('google', d.analytics_google);
      if (ga) {
        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag('js', new Date());
        window.gtag('config', ga);
        appendScript('https://www.googletagmanager.com/gtag/js?id=' + ga);
        console.log('Google Analytics (' + ga + ') added');
      }

      var ym_id = checkId('yandex', d.analytics_yandex);
      if (ym_id) {
        /* Yandex's own queue stub: calls made before tag.js loads are kept in ym.a. */
        window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
        window.ym.l = 1 * new Date();
        appendScript('https://mc.yandex.ru/metrika/tag.js');
        window.ym(Number(ym_id), 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true });
        console.log('Yandex Metrika (' + ym_id + ') added');
      }

      var gtm = checkId('gtm', d.gtm_tag);
      if (gtm) {
        window.dataLayer = window.dataLayer || [];
        window.dataLayer.push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
        appendScript('https://www.googletagmanager.com/gtm.js?id=' + gtm);
        console.log('Google Tag Manager (' + gtm + ') added');
      }
    } catch (e) {
      console.error('[platform] analytics failed:', e && e.message);
    }
  }

  /* ── the "unavailable" card ───────────────────────────────── */

  /* Built from the template's own classes, so it is the same card. Not
     dismissible: there is nothing behind it to go back to. */
  function showOff() {
    if (offShown) return;
    offShown = true;
    if (window.TWForm) TWForm.close();

    var mail = P.supportEmail || '';
    var el = document.createElement('dialog');
    el.className = 'tw-dialog pl-off';
    el.id = 'pl-off';
    el.setAttribute('aria-labelledby', 'pl-off-title');
    el.innerHTML =
      '<div class="tw-card">' +
      '<img class="tw-promo__logo" src="' + (C.brand || {}).logo + '" alt="">' +
      '<h2 class="tw-done__title" id="pl-off-title" data-i18n="pl.off.title"></h2>' +
      '<p class="tw-done__note" data-i18n="pl.off.text"></p>' +
      (mail ? '<a class="pl-off__mail" href="mailto:' + mail + '"></a>' : '') +
      '</div>';
    var a = el.querySelector('.pl-off__mail');
    if (a) a.textContent = mail;
    document.body.appendChild(el);
    if (window.TWI18n) TWI18n.apply(el);

    el.addEventListener('cancel', function (ev) { ev.preventDefault(); });
    el.addEventListener('close', function () { if (offShown) el.showModal(); });
    el.showModal();
  }

  /* ── submit ───────────────────────────────────────────────── */

  function formBox() { return dialog.querySelector('.tw-err[data-form-error]'); }

  function clearError() {
    var box = formBox();
    box.classList.remove('is-shown');
    box.hidden = true;
    box.textContent = '';
    box.removeAttribute('data-i18n');
  }

  /* data-i18n, not a one-off textContent: a visitor who switches language with
     the message on screen gets it re-rendered by i18n.apply() like any other
     string. clearError() takes the attribute off again so the template's own
     generic line, which is written with textContent, is never overwritten by a
     stale key. */
  function showError(key) {
    var box = formBox();
    box.setAttribute('data-i18n', key);
    box.textContent = t(key);
    box.hidden = false;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { box.classList.add('is-shown'); });
    });
  }

  function setBusy(on) {
    busy = on;
    var btn = dialog.querySelector('.tw-cta[type="submit"]');
    if (!btn) return;
    btn.disabled = on;
    if (on) btn.setAttribute('aria-busy', 'true'); else btn.removeAttribute('aria-busy');
  }

  /* IT's call, with a ceiling: a slow third party must not hold a registration
     hostage. Empty string on any failure, as theirs does. */
  function clientIp() {
    var ctl = typeof AbortController === 'function' ? new AbortController() : null;
    var timer = setTimeout(function () { if (ctl) ctl.abort(); }, 3000);
    return fetch('https://api.ipify.org?format=json', ctl ? { signal: ctl.signal } : {})
      .then(function (r) { return r.json(); })
      .then(function (j) { return (j && j.ip) || ''; })
      .catch(function () { return ''; })
      .then(function (ip) { clearTimeout(timer); return ip; });
  }

  function recaptchaToken() {
    return recaptchaP.then(function () {
      return new Promise(function (resolve, reject) {
        if (!window.grecaptcha) return reject(new Error('grecaptcha missing'));
        grecaptcha.ready(function () {
          grecaptcha.execute(landing.data.recaptcha_key, { action: 'register' })
            .then(function (token) {
              if (token) resolve(token); else reject(new Error('empty token'));
            }, reject);
        });
      });
    }).catch(function (e) {
      var err = new Error('recaptcha: ' + (e && e.message));
      err.key = 'err.recaptcha';
      throw err;
    });
  }

  /* The server speaks English strings in { errors: [msg] }. Matched loosely --
     IT compares the reCAPTCHA one for equality, which breaks the day somebody
     rewords it -- and anything unrecognised is left to the template's generic
     line, with the original in the console for whoever debugs it. */
  function classify(message) {
    var m = String(message || '').toLowerCase();
    if (m.indexOf('recaptcha') >= 0) return 'err.recaptcha';
    if (m.indexOf('already registered') >= 0 || m.indexOf('already exists') >= 0) return 'err.exists';
    return null;
  }

  function post(body) {
    return fetch(landing.config.email_registration, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (r) {
      if (r.ok) return r.json();
      return r.json().catch(function () { return null; }).then(function (j) {
        var msg = j && j.errors && j.errors[0];
        var err = new Error(msg ? String(msg) : 'HTTP ' + r.status);
        err.key = classify(msg);
        throw err;
      });
    });
  }

  /* A real form POST, because that is what /api/welcome takes and because the
     token must travel in a body, never in a URL that history and referrers
     keep. tmpToken is a one-shot login ticket, not the password. */
  function sso(token, lang) {
    var d = landing.data;
    var path = [lang, String(d.redirect_link || '').replace(/^\/+/, '')]
      .filter(Boolean).join('/');
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = landing.domain + '/api/welcome';
    form.enctype = 'application/x-www-form-urlencoded';
    form.hidden = true;
    [['tmpToken', token], ['redirect', withQuery(landing.domain + '/' + path)]].forEach(function (p) {
      var input = document.createElement('input');
      input.type = 'hidden';
      input.name = p[0];
      input.value = p[1];
      form.appendChild(input);
    });
    document.body.appendChild(form);
    form.submit();
  }

  function register() {
    if (busy) return new Promise(function () {});
    setBusy(true);
    clearError();

    return new Promise(function (resolve, reject) {
      loadLanding().then(function (state) {
        if (state === 'demo') {
          console.warn('[platform] config.json not found: this build is not connected to the platform.');
          setBusy(false);
          resolve(null);     // form.js walks the confirmation screen with what was typed
          return null;
        }
        if (state === 'off') { setBusy(false); return null; }       // the card says why

        return recaptchaToken().then(function (token) {
          return clientIp().then(function (ip) {
            /* Everything we do not own goes FIRST, so a URL parameter or a
               hiddenFields entry named email or landing_id can never
               overwrite a real field. The values come from the inputs and
               from i18n, not from `payload`: form.js has already merged
               hiddenFields and the params ONTO that object, over its own
               fields, so reading email from it would read the overwrite. */
            var body = assign({}, F.hiddenFields, window.TW ? TW.params() : {}, {
              email: document.getElementById('tw-email').value.trim(),
              password: document.getElementById('tw-password').value,
              landing_id: landing.config.id,
              language: window.TWI18n ? TWI18n.tag() : document.documentElement.lang,
              currency: landing.data.currency || null,
              country: landing.data.country || null,
              promocode: landing.data.promocode || null,
              receivePromos: true,
              clientIp: ip,
              'g-recaptcha-response': token
            });
            return post(body);
          });
        }).then(function (res) {
          var token = res && res.data && res.data.accessToken;
          if (!token || !landing.domain) throw new Error('registered, but no accessToken or no casino domain');
          if (window.TW) TW.track('form_success', { method: 'email' });
          sso(token, window.TWI18n ? TWI18n.tag() : document.documentElement.lang);          // busy stays on: the page is leaving
        });
      }).catch(function (err) {
        console.warn('[platform] registration failed:', err && err.message);
        setBusy(false);
        if (err && err.key) { showError(err.key); return; }   // ours: never settles
        reject(err);
      });
    });
  }

  /* ── public ───────────────────────────────────────────────── */

  window.TWPlatform = { register: register };

  dropPhone();
  if (window.TW) TW.on('lang', applyLinks);

  /* Started at load, not at the first submit: an inactive landing must show
     its card before the visitor plays a game they cannot finish. */
  loadLanding().catch(function () { /* warned above */ });
}());
