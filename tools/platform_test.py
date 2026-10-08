#!/usr/bin/env python3
"""
Headless test of js/platform.js against a stubbed IT platform.

    python tools/platform_test.py

Same needs and same rules as tools/smoke.py: Playwright and one Chromium, the
project served from a loopback port, and NOT ONE real request -- jack-pot.tech,
ipify and Google are all answered by tools/platform_stub.py, and anything else
that leaves the page fails the run.

It walks the scenarios a visitor can actually hit:

  inactive landing   the "unavailable" card, in every language, nothing else
  success + SSO      registration body, then the hidden POST to the casino,
                     and the done screen (with the password) never shown
  email taken        its own message in every language, button usable again
  reCAPTCHA failure  from the server and from the browser, its own message
  network failure    the template's generic line
  loading state      the button is disabled while the request is in flight
  body safety        a field hiddenFields tries to set cannot overwrite email,
                     landing_id or the rest
  production config  no config.json -> demo path; a config.json -> used
  the card           the phone tab is gone, the links come from the landing
  analytics          GA, Yandex and GTM load from the landing response, as IT's
                     LP does: valid IDs load, invalid ones are skipped, none
                     loads nothing, an inactive landing still loads them, demo
                     loads nothing, and the console shows no CSP refusal
  redirectUrl        TopWin's redirectUrl: the hand-off goes to its mirror, with
                     the page query; no redirectUrl and no casino domain -> the
                     generic line and nothing posted
  CSP                the production API is in connect-src
  badge              the reCAPTCHA badge is hidden, as IT's LP hides it
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import re
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_stub as stubmod

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit('platform_test: Playwright is not installed.\n'
             '  python -m pip install playwright\n'
             '  python -m playwright install chromium')

ROOT = Path(__file__).resolve().parent.parent

MESSAGES = {
    'ua': {'exists': 'Цей email уже зареєстровано. Увійдіть в акаунт',
           'recaptcha': 'Не вдалося пройти перевірку безпеки. Спробуйте ще раз',
           'network': 'Не вдалося надіслати. Спробуйте ще раз',
           'off': 'Сторінка тимчасово недоступна'},
    'ru': {'exists': 'Этот email уже зарегистрирован. Войдите в аккаунт',
           'recaptcha': 'Не удалось пройти проверку безопасности. Попробуйте ещё раз',
           'network': 'Не удалось отправить. Попробуйте ещё раз',
           'off': 'Страница временно недоступна'},
    'en': {'exists': 'This email is already registered. Please log in',
           'recaptcha': 'The security check failed. Please try again',
           'network': 'Could not send. Please try again',
           'off': 'This page is temporarily unavailable'},
}

ERROR_SHOWN = ('() => { const b = document.querySelector(".tw-err[data-form-error]");'
               ' return !b.hidden && b.textContent; }')
SSO_DONE = '() => document.title === "casino stub"'


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, 'http://127.0.0.1:%d' % httpd.server_address[1]


class Run:
    """One page in one fresh context, with its own stub state."""

    def __init__(self, browser, base, **state):
        self.base = base
        self.state = stubmod.new_state(**state)
        self.ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
        stubmod.install(self.ctx, self.state, [base])
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on('console', lambda m: self.errors.append('console error: ' + m.text)
                     if m.type == 'error' else None)
        self.page.on('pageerror', lambda e: self.errors.append('uncaught: %s' % e))

    def open(self, query='lang=en'):
        self.page.goto(self.base + '/index.html?' + query, wait_until='load')
        return self

    def settle(self, ms=400):
        self.page.wait_for_timeout(ms)

    def fill_and_submit(self, email='player@example.com', password='Sup3rSecret!'):
        p = self.page
        p.evaluate('TWForm.open()')
        p.wait_for_selector('#tw-signup[open]')
        p.fill('#tw-email', email)
        p.fill('#tw-password', password)
        p.click('.tw-cta[type="submit"]')

    def form_error(self):
        return self.page.evaluate(
            '() => { const b = document.querySelector(".tw-err[data-form-error]");'
            ' return b.hidden ? "" : b.textContent; }')

    def close(self):
        self.ctx.close()


def main():
    httpd, base = serve()
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail)); print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '  -> ' + detail), flush=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            # ── the card: no phone tab, links from the landing, right headers ──
            r = Run(browser, base).open()
            r.settle()
            card = r.page.evaluate("""() => ({
                tabs:  !!document.querySelector('.tw-tabs'),
                phone: !!document.getElementById('tw-phone'),
                terms: document.querySelector('[data-tw-link="terms"]').getAttribute('href'),
                login: document.querySelector('[data-tw-link="login"]').getAttribute('href'),
            })""")
            check('card: phone tab and phone field are gone', not card['tabs'] and not card['phone'], str(card))
            check('card: terms link comes from the landing, with the page query',
                  card['terms'] == stubmod.CASINO + '/uk/rules?lang=en', card['terms'])
            check('card: login link comes from the landing',
                  card['login'] == stubmod.CASINO + '/uk/login?lang=en', card['login'])
            g = r.state['landing_gets']
            check('card: landing GET sent once with JSON headers',
                  len(g) == 1 and g[0].get('accept') == 'application/json'
                  and g[0].get('content-type') == 'application/json', str(g))
            r.page.evaluate("TW.setLang('ru')")
            r.settle(150)
            href = r.page.get_attribute('[data-tw-link="terms"]', 'href')
            check('card: terms link survives a language switch',
                  href == stubmod.CASINO + '/uk/rules?lang=en', str(href))
            check('card: nothing left the page, console clean',
                  not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
            r.close()

            # ── inactive landing ──
            for lang in ('ua', 'ru', 'en'):
                r = Run(browser, base, active=False).open('lang=' + lang)
                r.page.wait_for_selector('#pl-off[open]', timeout=4000)
                text = r.page.inner_text('#pl-off-title')
                mail = r.page.get_attribute('.pl-off__mail', 'href')
                check('inactive, %s: card shown in that language' % lang,
                      text.lower() == MESSAGES[lang]['off'].lower(), text)
                check('inactive, %s: mailto support' % lang, mail == 'mailto:support@jack-pot.com', str(mail))
                r.page.keyboard.press('Escape')
                r.settle(200)
                check('inactive, %s: Escape does not dismiss it' % lang,
                      r.page.evaluate('document.getElementById("pl-off").open'))
                check('inactive, %s: no reCAPTCHA, no registration' % lang,
                      not r.page.evaluate('!!window.grecaptcha') and not r.state['registered'])
                check('inactive, %s: nothing leaked, console clean' % lang,
                      not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
                r.close()

            # ── success + SSO ──
            r = Run(browser, base).open('lang=ua&click_id=CLK1&sub1=S1&evil=1')
            r.settle()
            r.page.evaluate("TW_CAMPAIGN.form.hiddenFields = {email: 'hacked', landing_id: 'hacked', extra: 'ok'}")
            r.fill_and_submit()
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            body = r.state['registered'][0] if r.state['registered'] else {}
            want = {'email': 'player@example.com', 'password': 'Sup3rSecret!', 'landing_id': 8,
                    'language': 'uk', 'currency': 'UAH', 'country': 'UA', 'promocode': 'PROMO-X',
                    'receivePromos': True, 'clientIp': '203.0.113.7',
                    'g-recaptcha-response': 'STUB-TOKEN:STUB-SITE-KEY:register',
                    'click_id': 'CLK1', 'sub1': 'S1', 'extra': 'ok'}
            wrong = {k: (body.get(k), v) for k, v in want.items() if body.get(k) != v}
            check('success: registration body is IT\'s, field for field', not wrong, str(wrong))
            check('success: reCAPTCHA ran with the API key and action "register"',
                  body.get('g-recaptcha-response') == want['g-recaptcha-response'])
            check('success: a URL param outside the whitelist is not sent', 'evil' not in body, str(body))
            sso = r.state['sso']
            fields = parse_qs(sso[0]['body']) if sso else {}
            check('success: exactly one POST to <casino>/api/welcome',
                  len(sso) == 1 and sso[0]['method'] == 'POST'
                  and sso[0]['url'] == stubmod.CASINO + '/api/welcome', str(sso))
            check('success: tmpToken is the accessToken', fields.get('tmpToken') == ['TMP-TOKEN-123'], str(fields))
            check('success: redirect is <casino>/<lang>/<redirect_link>?<page query>',
                  fields.get('redirect') == [stubmod.CASINO + '/uk/lobby?lang=ua&click_id=CLK1&sub1=S1&evil=1'],
                  str(fields.get('redirect')))
            check('success: the password is not in the SSO post',
                  bool(sso) and 'Sup3rSecret' not in sso[0]['body'])
            check('success: only the stubbed origins were contacted, console clean',
                  not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
            r.close()

            # The confirmation screen shows the password the visitor just typed.
            # The page is replaced by the casino within milliseconds, so a
            # screenshot would never catch it: an observer reports to the test
            # through a binding that survives the navigation.
            r = Run(browser, base)
            seen = []
            r.ctx.expose_function('reportDone', lambda: seen.append(1))
            r.ctx.add_init_script("""
              document.addEventListener('DOMContentLoaded', () => {
                const done = document.querySelector('[data-step="done"]');
                if (!done) return;
                new MutationObserver(() => { if (!done.hidden) window.reportDone(); })
                  .observe(done, { attributes: true, attributeFilter: ['hidden'] });
              });""")
            r.open()
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            r.settle(500)
            check('success: the confirmation screen (login + password) is never shown',
                  len(r.state['sso']) == 1 and not seen, str(seen))
            r.close()

            # ── success with redirectUrl (TopWin): the hand-off goes to its mirror ──
            r = Run(browser, base, redirect_url=stubmod.MIRROR + '/uk?modal=signIn').open('lang=ua&click_id=CLK1&sub1=S1')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            sso = r.state['sso']
            fields = parse_qs(sso[0]['body']) if sso else {}
            check('redirectUrl: one POST to <mirror>/api/welcome',
                  len(sso) == 1 and sso[0]['method'] == 'POST'
                  and sso[0]['url'] == stubmod.MIRROR + '/api/welcome', str(sso))
            check('redirectUrl: tmpToken is the accessToken', fields.get('tmpToken') == ['TMP-TOKEN-123'], str(fields))
            check('redirectUrl: redirect is the redirectUrl plus the page query',
                  fields.get('redirect') == [stubmod.MIRROR + '/uk?modal=signIn&lang=ua&click_id=CLK1&sub1=S1'],
                  str(fields.get('redirect')))
            check('redirectUrl: only the stubbed origins were contacted, console clean',
                  not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
            r.close()

            # No redirectUrl and no casino domain: nothing to hand off to.
            r = Run(browser, base, casino_rules=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('no redirectUrl, no casino domain: the generic line',
                  r.form_error() == MESSAGES['en']['network'], r.form_error())
            check('no redirectUrl, no casino domain: nothing posted to any welcome',
                  not r.state['sso'], str(r.state['sso']))
            r.close()

            # ── errors, in every language ──
            for lang in ('ua', 'ru', 'en'):
                r = Run(browser, base, register_status=400,
                        register_json={'errors': ['Email already registered. Please use a different email or login.']}
                        ).open('lang=' + lang)
                r.settle()
                r.fill_and_submit()
                r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
                check('email taken, %s: its own message' % lang,
                      r.form_error() == MESSAGES[lang]['exists'], r.form_error())
                check('email taken, %s: button usable again, no SSO' % lang,
                      not r.page.is_disabled('.tw-cta[type="submit"]') and not r.state['sso'])
                # Chromium logs the stub's own HTTP 400 as a console error; that
                # one is expected and nothing else is.
                other = [e for e in r.errors if 'Failed to load resource' not in e]
                check('email taken, %s: no other console error, nothing leaked' % lang,
                      not other and not r.state['leaks'], str(other + r.state['leaks']))
                r.close()

                r = Run(browser, base, register_status=400,
                        register_json={'errors': ['reCAPTCHA verification failed. Please try again.']}
                        ).open('lang=' + lang)
                r.settle()
                r.fill_and_submit()
                r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
                check('recaptcha refused by the server, %s: its own message' % lang,
                      r.form_error() == MESSAGES[lang]['recaptcha'], r.form_error())
                r.close()

            r = Run(browser, base, recaptcha_ok=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('recaptcha fails in the browser: its message, nothing posted',
                  r.form_error() == MESSAGES['en']['recaptcha'] and not r.state['registered'], r.form_error())
            r.page.evaluate("TW.setLang('ru')")
            r.settle(150)
            check('error message follows a language switch',
                  r.form_error() == MESSAGES['ru']['recaptcha'], r.form_error())
            r.close()

            r = Run(browser, base, register_abort=True).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('network failure: the template\'s generic line',
                  r.form_error() == MESSAGES['en']['network'], r.form_error())
            check('network failure: button usable again', not r.page.is_disabled('.tw-cta[type="submit"]'))
            r.close()

            r = Run(browser, base, ipify_ok=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            check('ipify down: registration still goes, clientIp is ""',
                  r.state['registered'] and r.state['registered'][0].get('clientIp') == '')
            r.close()

            # ── loading state: the registration request is never answered ──
            r = Run(browser, base).open('lang=en')
            r.settle()
            r.ctx.route(stubmod.API + '/api/jp/registration/email', lambda route: None)
            r.fill_and_submit()
            r.settle(600)
            check('loading: submit is disabled and aria-busy while waiting',
                  r.page.is_disabled('.tw-cta[type="submit"]')
                  and r.page.get_attribute('.tw-cta[type="submit"]', 'aria-busy') == 'true')
            r.ctx.unroute_all(behavior='ignoreErrors')   # let go of the request left hanging
            r.close()

            # ── production: config.json is fetched from the site root ──
            def prod(config, **state):
                r = Run(browser, base, **state)

                def route(rt):
                    u = urlparse(rt.request.url)
                    if u.path.endswith('/config.json'):
                        if config is None:
                            return rt.fulfill(status=404, body='no')
                        return rt.fulfill(status=200, content_type='application/json', body=json.dumps(config))
                    return rt.continue_(url=base + u.path + ('?' + u.query if u.query else ''))

                r.ctx.route('http://lp.stub.test/**', route)
                r.page.goto('http://lp.stub.test/index.html?lang=en', wait_until='load')
                r.settle()
                return r

            r = prod(None)
            r.fill_and_submit()
            r.page.wait_for_selector('[data-step="done"]:not([hidden])', timeout=4000)
            check('production, no config.json: demo path, nothing sent',
                  not r.state['registered'] and not r.state['landing_gets'])
            r.close()

            cfg = {'id': 42, 'email_registration': stubmod.API + '/api/jp/registration/email',
                   'landing': stubmod.API + '/api/jp/landing/42'}
            r = prod(cfg)
            r.fill_and_submit()
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            check('production, config.json present: its id is the landing_id',
                  r.state['registered'] and r.state['registered'][0].get('landing_id') == 42)
            r.close()

            # ── analytics, as IT's LP loads them from the landing response ──
            GTAG_URL = 'https://www.googletagmanager.com/gtag/js?id=G-ABC123'
            YM_URL = 'https://mc.yandex.ru/metrika/tag.js'
            GTM_URL = 'https://www.googletagmanager.com/gtm.js?id=GTM-ABC123'
            GOOD = {'analytics_google': 'G-ABC123', 'analytics_yandex': 12345678, 'gtm_tag': 'GTM-ABC123'}

            r = Run(browser, base, **GOOD).open()
            r.settle(600)
            tags = r.page.evaluate("""() => ({
                gtagConfig: (window.dataLayer || []).some(e => e && e[0] === 'config' && e[1] === 'G-ABC123'),
                gtmStart: (window.dataLayer || []).some(e => e && e.event === 'gtm.js' && 'gtm.start' in e),
                ymInit: ((window.ym && window.ym.a) || []).some(a => a[0] === 12345678 && a[1] === 'init'),
                scripts: Array.from(document.querySelectorAll('script[src]')).map(s => s.src),
            })""")
            requested = r.state['analytics_requests']
            check('analytics, valid IDs: gtag, tag.js and gtm.js are loaded',
                  GTAG_URL in requested and YM_URL in requested and GTM_URL in requested
                  and GTAG_URL in tags['scripts'] and YM_URL in tags['scripts'] and GTM_URL in tags['scripts'],
                  str(requested))
            check('analytics, valid IDs: dataLayer has the gtag config and the gtm.start event',
                  tags['gtagConfig'] and tags['gtmStart'], str(tags))
            check('analytics, valid IDs: the ym queue has the init call', tags['ymInit'], str(tags))
            csp = [e for e in r.errors if 'Content Security Policy' in e or 'Refused to' in e]
            check('analytics, valid IDs: no CSP refusal, nothing leaked, console clean',
                  not csp and not r.state['leaks'] and not r.errors, str(csp + r.state['leaks'] + r.errors))
            r.close()

            r = Run(browser, base, analytics_google='G-x"><script>', analytics_yandex='12a', gtm_tag='GTM-abc')
            warns = []
            r.page.on('console', lambda m: warns.append(m.text) if m.type == 'warning' else None)
            r.open()
            r.settle(600)
            bad = r.page.evaluate("""() => ({
                scripts: Array.from(document.querySelectorAll('script[src]')).map(s => s.src),
                ym: typeof window.ym, gtag: typeof window.gtag,
            })""")
            injected = [x for x in bad['scripts'] if 'googletagmanager' in x or 'mc.yandex' in x or 'G-x' in x]
            check('analytics, invalid IDs: no script is injected for any of them',
                  not injected and not r.state['analytics_requests'] and bad['ym'] == 'undefined'
                  and bad['gtag'] == 'undefined', str(injected + r.state['analytics_requests']))
            check('analytics, invalid IDs: each one is skipped with a console warning',
                  sum('skipped an invalid' in w for w in warns) == 3, str(warns))
            r.close()

            r = Run(browser, base).open()
            r.settle(600)
            none = r.page.evaluate("""() => ({
                gtag: typeof window.gtag, ym: typeof window.ym, dataLayer: typeof window.dataLayer,
            })""")
            check('analytics, no IDs: nothing is injected',
                  not r.state['analytics_requests'] and none == {'gtag': 'undefined', 'ym': 'undefined', 'dataLayer': 'undefined'},
                  str(none) + str(r.state['analytics_requests']))
            r.close()

            r = Run(browser, base, active=False, **GOOD).open()
            r.page.wait_for_selector('#pl-off[open]', timeout=4000)
            r.settle(300)
            requested = r.state['analytics_requests']
            check('analytics, inactive landing: the tags are injected anyway',
                  GTAG_URL in requested and YM_URL in requested and GTM_URL in requested, str(requested))
            r.close()

            r = prod(None, **GOOD)
            r.fill_and_submit()
            r.page.wait_for_selector('[data-step="done"]:not([hidden])', timeout=4000)
            check('analytics, demo mode (no config.json): nothing is injected',
                  not r.state['analytics_requests'], str(r.state['analytics_requests']))
            r.close()

            # ── the reCAPTCHA badge is hidden, as IT's LP hides it ──
            r = Run(browser, base).open()
            r.settle()
            badge = r.page.evaluate("""() => {
                const b = document.createElement('div');
                b.className = 'grecaptcha-badge';
                document.body.appendChild(b);
                const cs = getComputedStyle(b);
                return [cs.opacity, cs.pointerEvents];
            }""")
            check('badge: .grecaptcha-badge is opacity 0 and takes no pointer events',
                  badge == ['0', 'none'], str(badge))
            r.close()

            # ── CSP: the production API is allowed in connect-src ──
            html = (ROOT / 'index.html').read_text(encoding='utf-8')
            connect = re.search(r"connect-src ('self'[^;]*);", html).group(1).split()
            check('CSP: connect-src has the production API, right after self',
                  connect[:2] == ["'self'", stubmod.PROD_API], str(connect))
        finally:
            browser.close()
            httpd.shutdown()

    failed = [x for x in results if not x[1]]
    for name, ok, detail in results:
        print(('ok   ' if ok else '::error::FAIL ') + name + ('' if ok or not detail else '  -> ' + detail))
    print('\nplatform_test: %d checks, %d failed' % (len(results), len(failed)))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
