/* The IT platform connection -- this landing's own, NOT the template's.

   js/form.js, js/shell.js and the other shared files are never edited here, so
   everything the platform needs is attached from outside through the seams the
   template leaves open: form.onRegister in campaign.js, TW.on('lang'), and the
   DOM that js/shell.js has already built by the time this file runs (it is
   loaded after shell.js, which mounts the dialog synchronously in boot()).

   Platform connection = IT's template (owner, 2026-11-11). The requests, their
   headers, their order and the registration body are IT's reference landing
   (their _js/main.js, _js/api/resilve-recaptcha.js, _js/utils/url.js), step
   for step. A deviation needs the owner's AND IT's OK; the ones left are
   listed in the decision "Platform connection = IT's template" (topwin-lp
   skill) and are not on the request path, except where noted below.

   ── The flow (IT's) ──────────────────────────────────────────
   1. config.   Development (localhost, 127.0.0.1, or an origin containing
                https://land-crm) uses campaign.js § platform.dev when all three
                of its values are filled in: a TopWin dev landing that only IT
                can issue. Until then localhost and 127.0.0.1 take the demo path
                without a request, and land-crm reads config.json like
                production. Everywhere else config.json is fetched from the
                site root: { id, email_registration, landing }.
   2. landing.  GET config.landing with Content-Type and Accept
                application/json -> { data: { active, recaptcha_key, country,
                currency, promocode, rules, policy, login, redirect_link } }.
                Analytics first, then: active false: the "unavailable" card
                with support@top-win.com, and nothing else happens. Otherwise
                reCAPTCHA v3 api.js?render=<key> is loaded, and the Terms /
                Privacy / Login links are set to the API's URLs exactly as IT
                does (no host filter), with the page's query appended.
   3. ip.       GET https://api.ipify.org?format=json once at load, as IT does;
                the IP is kept and read at submit ("" if it has not come).
   4. submit.   The body, built like IT's:
                  { email, password, landing_id, language, currency, country,
                    promocode, receivePromos: true, clientIp, ...urlParams }
                every URL parameter spread LAST (so it can overwrite a field,
                as on IT's page), then grecaptcha.execute(key, {action:
                "register"}) sets "g-recaptcha-response" on it, then POST
                config.email_registration with Content-Type: application/json.
                `language` is the active language button's text lowercased,
                as IT sends it: ua, ru or en.
   5. success.  PENDING IT ANSWER (owner, 2026-11-11): the SSO hand-off below
                is kept as it was until IT says which is right.
                response.data.accessToken and response.data.redirectUrl.
                TopWin returns redirectUrl: the tracker mirror with modal=signIn.
                That URL is POSTed to <mirror>/api/welcome as tmpToken + redirect.
                Without redirectUrl, IT's path: <rules host>/api/welcome and
                redirect /{language}/{redirect_link}. The confirmation screen
                is never shown.

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
  var ipAddress = '';      // IT's registerFormState.ipAddress: filled by ipify at load
  var landing = null;      // { data, config, domain } once active
  var analyticsOn = false; // injectAnalytics runs once, even if the landing is retried
  var offShown = false;
  var busy = false;

  /* platform.dev counts only with all three values. The template ships it
     empty: TopWin has no dev landing yet, and another brand's landing must
     never stand in for one (decision 21 in the topwin-lp skill). */
  function devConfig() {
    var d = P.dev;
    return d && d.id && d.email_registration && d.landing ? d : null;
  }

  /* A machine of our own, as opposed to IT's land-crm staging host. */
  function isLocal() {
    return location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  }

  /* The links the landing API hands us go on the page as they come, like IT's
     page does. The TopWin host filter that stood here (isTopWinUrl) was
     removed on 2026-11-11: the owner decided the connection must be IT's, and
     IT applies the API's links without a check. What the API returns for a
     landing is IT's to keep right. */

  /* Resolves to the config object, or null when there is none to find. Only a
     404 on config.json means "nobody deployed one"; a network failure or a
     malformed file is a fault and rejects. */
  function loadConfig() {
    if (isDevelopment() && devConfig()) return Promise.resolve(devConfig());
    if (isLocal()) return Promise.resolve(null);   // no TopWin dev landing yet: the demo path
    if (configP) return configP;
    configP = fetch(P.configUrl || 'config.json')   // IT: fetch("config.json"), no options
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

  /* IT's addParamsToUrl(url, getQueryParams()): the page's raw query string,
     after "?" or "&". */
  function withQuery(href) {
    if (!href) return href;
    var q = location.search ? location.search.slice(1) : '';
    if (!q) return href;
    return href + (href.indexOf('?') < 0 ? '?' : '&') + q;
  }

  /* IT's getURLParams(): every parameter on the page URL, decoded, the last
     one winning when a name repeats. No whitelist: IT sends them all. */
  function urlParams() {
    var out = {};
    new URLSearchParams(location.search).forEach(function (value, key) { out[key] = value; });
    return out;
  }

  /* IT's language value: the active language button's text, lowercased. Our
     buttons show the internal code in capitals (UA, RU, EN), so this is ua,
     ru or en -- not the BCP-47 tag (uk) that <html lang> carries. */
  function language() {
    var code = window.TWI18n ? TWI18n.current() : '';
    return String(code || 'en').toLowerCase();
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
      s.src = 'https://www.google.com/recaptcha/api.js?render=' + key;   // IT's URL, verbatim
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
        method: 'GET',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }   // IT's API_HEADERS
      }).then(function (r) {
        if (!r.ok) throw new Error('landing: HTTP ' + r.status);
        return r.json();
      }).then(function (res) {
        var d = res && res.data;
        if (!d) throw new Error('landing: no data in the response');
        if (!analyticsOn) { analyticsOn = true; injectAnalytics(d); }   // before the active check, as IT does
        if (!d.active) { showOff(); return 'off'; }
        if (!d.recaptcha_key) throw new Error('landing: no recaptcha_key');

        /* IT's order: reCAPTCHA script, then the domain, then the links. */
        recaptchaP = loadRecaptcha(d.recaptcha_key);
        recaptchaP.catch(function () { /* reported at submit, where the visitor is */ });

        /* IT: registerFormState.domain = "https://" + new URL(data.rules).hostname */
        var domain = '';
        try { domain = 'https://' + new URL(d.rules).hostname; } catch (e) { /* no rules URL: no SSO target */ }
        landing = { data: d, config: cfg, domain: domain };

        applyLinks();
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
     IT pastes these into inline <script> text. Here the functions live in this
     file and only <script src> elements are appended; the same tags load.
     The IDs are the only thing that reaches code, so each one is checked
     before use. Not part of the registration request; left as it was (owner,
     2026-11-11: analytics injection stays ours). */

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

    /* TopWin's address is set in campaign.js. If it is emptied, the card has
       no address and its sentence does not end in "write to us:". */
    var mail = P.supportEmail || '';
    var el = document.createElement('dialog');
    el.className = 'tw-dialog pl-off';
    el.id = 'pl-off';
    el.setAttribute('aria-labelledby', 'pl-off-title');
    el.innerHTML =
      '<div class="tw-card">' +
      '<img class="tw-promo__logo" src="' + (C.brand || {}).logo + '" alt="">' +
      '<h2 class="tw-done__title" id="pl-off-title" data-i18n="pl.off.title"></h2>' +
      '<p class="tw-done__note" data-i18n="' + (mail ? 'pl.off.text' : 'pl.off.textNoMail') + '"></p>' +
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

  /* IT's call, made once at page load, not at submit: the IP is kept and the
     submit reads whatever is there, "" if ipify has not answered or failed. */
  function loadIp() {
    fetch('https://api.ipify.org?format=json')
      .then(function (r) { return r.json(); })
      .then(function (j) { ipAddress = (j && j.ip) || ''; })
      .catch(function (e) { console.warn('[platform] could not get the visitor IP:', e && e.message); });
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
     keep. tmpToken is a one-shot login ticket, not the password.
     When the API returns redirectUrl, welcome is posted to that mirror and
     redirect is the sign-in page. The CRM redirect_link is only the fallback.
     PENDING IT ANSWER (owner, 2026-11-11): IT's template has only the
     fallback path (<rules host>/api/welcome, /{lang}/{redirect_link}, and a
     button the visitor clicks). The owner asked IT which is right; until
     they answer, this stays as it was. The fallback's {lang} is IT's
     redirectLang, the same lowercased button text the body sends. */
  function sso(token, redirectUrl) {
    var action, redirect;
    if (redirectUrl) {
      var mirror = new URL(redirectUrl);
      action = mirror.origin + '/api/welcome';
      redirect = withQuery(redirectUrl);
    } else {
      var d = landing.data;
      var lang = language();
      var path = [lang, String(d.redirect_link || '').replace(/^\/+/, '')]
        .filter(Boolean).join('/');
      action = landing.domain + '/api/welcome';
      redirect = withQuery(landing.domain + '/' + path);
    }
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = action;
    form.enctype = 'application/x-www-form-urlencoded';
    form.hidden = true;
    [['tmpToken', token], ['redirect', redirect]].forEach(function (p) {
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

        /* IT's body, key for key and in IT's order, built before reCAPTCHA
           runs. The URL parameters are spread LAST, exactly as IT's
           `...params` -- so a parameter named like a field overwrites it, as
           it does on IT's page (owner, 2026-11-11: identical to IT).
           campaign.js form.hiddenFields is NOT sent: IT has no such thing. */
        var body = assign({
          email: document.getElementById('tw-email').value.trim(),
          password: document.getElementById('tw-password').value,
          landing_id: landing.config.id,
          language: language(),
          currency: landing.data.currency || null,
          country: landing.data.country || null,
          promocode: landing.data.promocode || null,
          receivePromos: true,
          clientIp: ipAddress
        }, urlParams());
        return recaptchaToken().then(function (token) {
          body['g-recaptcha-response'] = token;   // IT's executeRecaptcha: data["g-recaptcha-response"] = token
          return post(body);
        }).then(function (res) {
          var token = res && res.data && res.data.accessToken;
          var redirectUrl = res && res.data && res.data.redirectUrl;
          if (!token) throw new Error('registered, but no accessToken');
          if (!redirectUrl && !landing.domain) throw new Error('registered, but no redirectUrl or casino domain');
          if (window.TW) TW.track('form_success', { method: 'email' });
          sso(token, redirectUrl);          // busy stays on: the page is leaving
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
  /* IT starts ipify at load too, right after the config request. Not on the
     demo path (localhost without a dev landing): no request leaves a page
     that is not connected. */
  if (!(isLocal() && !devConfig())) loadIp();
}());
