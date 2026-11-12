#!/usr/bin/env python3
"""
Headless test of js/platform.js against a stubbed IT platform.

    python tools/platform_test.py

Same needs and same rules as tools/smoke.py: Playwright and one Chromium, the
project served from a loopback port, and NOT ONE real request -- the platform
API, ipify and Google are all answered by tools/platform_stub.py, and anything
else that leaves the page fails the run.

campaign.js ships platform.dev = IT's TEMP_CONFIG (decision 24), a host on the
network that must never be reached from a test, and platform.supportEmail =
support@top-win.com. Each run injects stubmod.DEV as platform.dev before
campaign.js is read, so every flow talks to the stub; the runs that test the
empty values or campaign.js's own values say so (the latter answers that host
from the stub, it never reaches the network).

It walks the scenarios a visitor can actually hit:

  inactive landing   the "unavailable" card, in every language, nothing else;
                     support@top-win.com, a mailto and the full "write to us:"
                     sentence; an emptied address -> no mailto, no "write to us"
  no dev landing     localhost with platform.dev empty -> demo, no request
  any host's links   rules / policy / login are applied as the API gives them,
                     with no host filter, as IT's template does
  IT's request       the POST body is IT's key for key and IN IT'S ORDER
                     (email, password, landing_id, language, currency, country,
                     promocode, receivePromos, clientIp, ...every URL param,
                     g-recaptcha-response), headers are IT's (landing GET:
                     Content-Type + Accept application/json; POST: Content-Type
                     application/json), the order is IT's (landing GET,
                     api.js?render=<key>, ipify at load, then the POST), and
                     `language` is IT's code: ua, ru, en
  success modal     after registering, a TopWin dialog in ua/ru/en: focus on the
                     dialog's button (>= 24px), Escape does not dismiss it, and
                     NOTHING is posted until the button is clicked
  SSO                the button submits the hidden POST to <rules host>/api/welcome
                     (tmpToken, redirect = host/lang/redirect_link + page query);
                     the done screen (with the password) is never shown
  email taken        its own message in every language, button usable again
  reCAPTCHA failure  from the server and from the browser: its own message in
                     the form AND a separate modal (ua/ru/en) with a close button
  network failure    the template's generic line
  loading state      the button is disabled while the request is in flight
  hiddenFields       not sent: IT's body has no such thing
  production config  no config.json -> demo path; a config.json -> used
  the card           the phone tab is gone, the links come from the landing
  analytics          GA, Yandex and GTM load from the landing response, as IT's
                     LP does: valid IDs load, invalid ones are skipped, none
                     loads nothing, an inactive landing still loads them, demo
                     loads nothing, and the console shows no CSP refusal
  redirectUrl        ignored: the hand-off goes to the rules host even when the
                     answer carries one; no casino domain -> the generic line
                     and nothing posted
  campaign.js dev    the file's own platform.dev works end to end (answered by
                     the stub), with landing id 8
  no CSP             index.html has no Content-Security-Policy, as IT's has none
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

# Read by the page as TW_CAMPAIGN is assigned: campaign.js's own values stay,
# the keys given here replace theirs in TW_CAMPAIGN.platform.
INJECT = '''(() => {
  const over = %s;
  let c;
  Object.defineProperty(window, 'TW_CAMPAIGN', {
    configurable: true,
    get() { return c; },
    set(v) { c = v; if (v) { v.platform = Object.assign(v.platform || {}, over); } }
  });
})();'''

SUPPORT = 'support@top-win.com'
WITHMAIL = {'ua': 'Реєстрація зараз закрита. Спробуйте пізніше або напишіть нам:',
            'ru': 'Регистрация сейчас закрыта. Попробуйте позже или напишите нам:',
            'en': 'Registration is closed right now. Please try again later or write to us:'}
NOMAIL = {'ua': 'Реєстрація зараз закрита. Спробуйте пізніше.',
          'ru': 'Регистрация сейчас закрыта. Попробуйте позже.',
          'en': 'Registration is closed right now. Please try again later.'}

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

# The two modals' texts, as the owner reviewed them (decision 24).
MODAL = {
    'ua': {'ok_title': 'Вітаємо!',
           'ok_text': 'Реєстрацію завершено. Ласкаво просимо до кола переможців.',
           'ok_btn': 'Перейти на сайт',
           'rc_text': 'На жаль, нам не вдалося підтвердити вашу особу. Спробуйте зареєструватися в іншому браузері або на іншому пристрої.',
           'close': 'Закрити'},
    'ru': {'ok_title': 'Поздравляем!',
           'ok_text': 'Регистрация завершена. Добро пожаловать в круг победителей.',
           'ok_btn': 'Перейти на сайт',
           'rc_text': 'К сожалению, нам не удалось подтвердить вашу личность. Попробуйте зарегистрироваться в другом браузере или на другом устройстве.',
           'close': 'Закрыть'},
    'en': {'ok_title': 'Congratulations!',
           'ok_text': "Your registration is complete. Welcome to the winners' circle.",
           'ok_btn': 'Go to the site',
           'rc_text': 'Unfortunately, we were unable to verify your identity. Please try registering using a different browser or device.',
           'close': 'Close'},
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

    def __init__(self, browser, base, platform=None, **state):
        self.base = base
        self.state = stubmod.new_state(**state)
        self.ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
        over = {} if platform == 'own' else {'dev': stubmod.DEV}
        if platform != 'own':
            over.update(platform or {})
        self.ctx.add_init_script(INJECT % json.dumps(over))
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

    def finish(self):
        """Registration succeeded: click the success modal's button and wait
        for the casino stub to load, which is the SSO POST arriving."""
        self.page.wait_for_selector('#pl-ok[open] .pl-modal__btn', timeout=6000)
        self.page.click('#pl-ok .pl-modal__btn')
        self.page.wait_for_function(SSO_DONE, timeout=6000)

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
                mailhref = r.page.get_attribute('.pl-off__mail', 'href')
                mailtext = r.page.inner_text('.pl-off__mail').strip()
                note = r.page.inner_text('#pl-off .tw-done__note').strip()
                check('inactive, %s: card shown in that language' % lang,
                      text.lower() == MESSAGES[lang]['off'].lower(), text)
                check('inactive, %s: mailto:%s, shown as that address' % (lang, SUPPORT),
                      mailhref == 'mailto:' + SUPPORT and mailtext == SUPPORT, '%s | %s' % (mailhref, mailtext))
                check('inactive, %s: the full sentence, ending in "write to us:"' % lang,
                      note == WITHMAIL[lang], note)
                r.page.keyboard.press('Escape')
                r.settle(200)
                check('inactive, %s: Escape does not dismiss it' % lang,
                      r.page.evaluate('document.getElementById("pl-off").open'))
                check('inactive, %s: no reCAPTCHA, no registration' % lang,
                      not r.page.evaluate('!!window.grecaptcha') and not r.state['registered'])
                check('inactive, %s: nothing leaked, console clean' % lang,
                      not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
                r.close()

            # ── inactive landing with the support address emptied: the fallback ──
            for lang in ('ua', 'ru', 'en'):
                r = Run(browser, base, active=False, platform={'supportEmail': ''}).open('lang=' + lang)
                r.page.wait_for_selector('#pl-off[open]', timeout=4000)
                mails = r.page.locator('.pl-off__mail').count()
                note = r.page.inner_text('#pl-off .tw-done__note').strip()
                check('inactive, %s, empty address: no mailto' % lang, mails == 0, str(mails))
                check('inactive, %s, empty address: no "write to us"' % lang, note == NOMAIL[lang], note)
                r.close()

            # ── inactive landing with another support address set ──
            r = Run(browser, base, active=False, platform={'supportEmail': 'help@example.invalid'}).open('lang=en')
            r.page.wait_for_selector('#pl-off[open]', timeout=4000)
            mail = r.page.get_attribute('.pl-off__mail', 'href')
            note = r.page.inner_text('#pl-off .tw-done__note').strip()
            check('inactive, address set: mailto that address', mail == 'mailto:help@example.invalid', str(mail))
            check('inactive, address set: the sentence asks to write', note.endswith(':'), note)
            r.close()

            # ── localhost with no dev landing: the demo path, nothing sent ──
            r = Run(browser, base, platform={'dev': {'id': None, 'email_registration': '', 'landing': ''}})
            r.open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_selector('[data-step="done"]:not([hidden])', timeout=4000)
            check('no dev landing: demo path, no landing GET, no registration',
                  not r.state['landing_gets'] and not r.state['registered'],
                  str(r.state['landing_gets']) + str(r.state['registered']))
            check('no dev landing: nothing left the page, console clean',
                  not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
            r.close()

            # ── links from the landing on any host: applied as IT does, no filter ──
            r = Run(browser, base, foreign_links=True)
            r.open('lang=en')
            r.settle()
            links = r.page.evaluate("""() => ({
                terms: document.querySelector('[data-tw-link="terms"]').getAttribute('href'),
                privacy: document.querySelector('[data-tw-link="privacy"]').getAttribute('href'),
                login: document.querySelector('[data-tw-link="login"]').getAttribute('href'),
            })""")
            want_links = {'terms': stubmod.FOREIGN + '/uk/rules?lang=en',
                          'privacy': stubmod.FOREIGN + '/uk/privacy?lang=en',
                          'login': stubmod.FOREIGN + '/uk/login?lang=en'}
            check('any host: rules / policy / login applied as the API gives them (IT: no filter)',
                  links == want_links, str(links))
            r.close()

            # ── IT's request: body key for key and in order, headers, order ──
            r = Run(browser, base).open('lang=ua&click_id=CLK1&sub1=S1&evil=1')
            r.settle()
            r.page.evaluate("TW_CAMPAIGN.form.hiddenFields = {email: 'hacked', landing_id: 'hacked', extra: 'no'}")
            r.fill_and_submit()
            r.page.wait_for_selector('#pl-ok[open] .pl-modal__btn', timeout=6000)
            r.settle(600)
            m = r.page.evaluate("""() => {
                const d = document.getElementById('pl-ok'), b = d.querySelector('.pl-modal__btn');
                const rect = b.getBoundingClientRect();
                return { focusOnBtn: document.activeElement === b, open: d.open, modal: d.matches(':modal'),
                         label: document.getElementById(d.getAttribute('aria-labelledby')).textContent,
                         desc: document.getElementById(d.getAttribute('aria-describedby')).textContent,
                         btn: b.textContent.trim(), h: rect.height, w: rect.width,
                         raw: /pl[.](ok|rc)[.]/.test(d.textContent) };
            }""")
            check('success modal: opened as a modal, focus on its button',
                  m['open'] and m['modal'] and m['focusOnBtn'], str(m))
            check('success modal: button is at least 24px', m['h'] >= 24 and m['w'] >= 24, str(m))
            check('success modal: title (aria-labelledby) and text (aria-describedby) in Ukrainian',
                  m['label'] == MODAL['ua']['ok_title'] and m['desc'] == MODAL['ua']['ok_text']
                  and m['btn'] == MODAL['ua']['ok_btn'] and not m['raw'], str(m))
            r.page.keyboard.press('Escape')
            r.settle(200)
            check('success modal: Escape does not dismiss it', r.page.evaluate('document.getElementById("pl-ok").open'))
            check('success modal: the registration form is closed behind it',
                  not r.page.evaluate('document.getElementById("tw-signup").open'))
            check('success modal: NOTHING is posted to the casino before the button is clicked',
                  not r.state['sso'] and r.page.title() != 'casino stub', str(r.state['sso']))
            r.page.click('#pl-ok .pl-modal__btn')
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            body = r.state['registered'][0] if r.state['registered'] else {}
            # IT's main.js: { email, password, landing_id, language, currency,
            # country, promocode, receivePromos: true, clientIp, ...params },
            # then resilve-recaptcha.js sets data["g-recaptcha-response"].
            want = [('email', 'player@example.com'), ('password', 'Sup3rSecret!'),
                    ('landing_id', stubmod.DEV['id']), ('language', 'ua'), ('currency', 'UAH'),
                    ('country', 'UA'), ('promocode', 'PROMO-X'), ('receivePromos', True),
                    ('clientIp', '203.0.113.7'),
                    ('lang', 'ua'), ('click_id', 'CLK1'), ('sub1', 'S1'), ('evil', '1'),
                    ('g-recaptcha-response', 'STUB-TOKEN:STUB-SITE-KEY:register')]
            check('IT body: keys in IT\'s order, URL params spread last, then g-recaptcha-response',
                  list(body.keys()) == [k for k, _ in want], str(list(body.keys())))
            check('IT body: every value is IT\'s', list(body.items()) == want, str(list(body.items())))
            check('IT body: hiddenFields is not sent', 'extra' not in body and body.get('email') != 'hacked', str(body))
            raw = r.state['register_raw'][0] if r.state['register_raw'] else {}
            check('IT POST: method POST, Content-Type application/json, body is JSON.stringify(data)',
                  raw.get('method') == 'POST'
                  and raw.get('headers', {}).get('content-type') == 'application/json'
                  and raw.get('body') == json.dumps(dict(want), separators=(',', ':'), ensure_ascii=False),
                  str(raw))
            g = r.state['landing_gets']
            check('IT landing GET: method GET, Content-Type + Accept application/json',
                  len(g) == 1 and g[0].get('method') == 'GET' and g[0].get('accept') == 'application/json'
                  and g[0].get('content-type') == 'application/json', str(g))
            check('IT reCAPTCHA: api.js?render=<recaptcha_key>, once',
                  r.state['recaptcha_src'] == ['https://www.google.com/recaptcha/api.js?render=STUB-SITE-KEY'],
                  str(r.state['recaptcha_src']))
            check('IT reCAPTCHA: executed with the API key and action "register"',
                  body.get('g-recaptcha-response') == 'STUB-TOKEN:STUB-SITE-KEY:register')
            order = r.state['order']
            pos = {k: order.index(k) if k in order else -1 for k in ('landing', 'recaptcha_js', 'ipify', 'register')}
            check('IT order: landing GET -> api.js -> POST; ipify once, before the POST',
                  -1 not in pos.values() and pos['landing'] < pos['recaptcha_js'] < pos['register']
                  and pos['ipify'] < pos['register'] and order.count('ipify') == 1
                  and order.count('register') == 1, str(order))
            sso = r.state['sso']
            fields = parse_qs(sso[0]['body']) if sso else {}
            check('success: exactly one POST to <casino>/api/welcome',
                  len(sso) == 1 and sso[0]['method'] == 'POST'
                  and sso[0]['url'] == stubmod.CASINO + '/api/welcome', str(sso))
            check('success: tmpToken is the accessToken', fields.get('tmpToken') == ['TMP-TOKEN-123'], str(fields))
            check('success: redirect is <casino>/<IT lang>/<redirect_link>?<page query>',
                  fields.get('redirect') == [stubmod.CASINO + '/ua/lobby?lang=ua&click_id=CLK1&sub1=S1&evil=1'],
                  str(fields.get('redirect')))
            check('success: the password is not in the SSO post',
                  bool(sso) and 'Sup3rSecret' not in sso[0]['body'])
            check('success: only the stubbed origins were contacted, console clean',
                  not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
            r.close()

            # ── IT's language codes: the active language button, lowercased ──
            for lang in ('ua', 'ru', 'en'):
                r = Run(browser, base).open('lang=' + lang)
                r.settle()
                btn = r.page.evaluate("() => { const c = document.querySelector('.tw-lang__code');"
                                      " return c ? c.textContent.trim() : ''; }")
                r.fill_and_submit()
                r.finish()
                sent = r.state['registered'][0].get('language') if r.state['registered'] else None
                check('IT language, %s: button says %s, body sends %r' % (lang, lang.upper(), lang),
                      sent == lang and btn == lang.upper(), '%r / button %r' % (sent, btn))
                r.close()
            r = Run(browser, base).open('lang=en')
            r.settle()
            r.page.evaluate("TW.setLang('ru')")
            r.settle(150)
            r.fill_and_submit()
            r.finish()
            sent = r.state['registered'][0].get('language') if r.state['registered'] else None
            check('IT language: a switch to RU sends "ru"', sent == 'ru', str(sent))
            r.close()

            r = Run(browser, base).open('landing_id=999&promocode=URLCODE')
            r.settle()
            r.fill_and_submit()
            r.finish()
            body = r.state['registered'][0] if r.state['registered'] else {}
            check('IT body: a URL param named like a field overwrites it, as on IT\'s page',
                  body.get('landing_id') == '999' and body.get('promocode') == 'URLCODE'
                  and list(body.keys())[:9] == ['email', 'password', 'landing_id', 'language', 'currency',
                                                'country', 'promocode', 'receivePromos', 'clientIp'],
                  str(body))
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
            r.finish()
            r.settle(500)
            check('success: the confirmation screen (login + password) is never shown',
                  len(r.state['sso']) == 1 and not seen, str(seen))
            r.close()

            # ── success modal text in every language ──
            for lang in ('ua', 'ru', 'en'):
                r = Run(browser, base).open('lang=' + lang)
                r.settle()
                r.fill_and_submit()
                r.page.wait_for_selector('#pl-ok[open] .pl-modal__btn', timeout=6000)
                got = r.page.evaluate("""() => ({
                    t: document.getElementById('pl-ok-title').textContent,
                    x: document.getElementById('pl-ok-text').textContent,
                    b: document.querySelector('#pl-ok .pl-modal__btn').textContent.trim() })""")
                check('success modal, %s: the reviewed title, text and button' % lang,
                      got == {'t': MODAL[lang]['ok_title'], 'x': MODAL[lang]['ok_text'],
                              'b': MODAL[lang]['ok_btn']}, str(got))
                check('success modal, %s: console clean, nothing leaked' % lang,
                      not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
                r.close()

            # ── redirectUrl is ignored: IT's template does not read it ──
            r = Run(browser, base, redirect_url=stubmod.MIRROR + '/uk?modal=signIn').open('lang=ua&click_id=CLK1&sub1=S1')
            r.settle()
            r.fill_and_submit()
            r.finish()
            sso = r.state['sso']
            fields = parse_qs(sso[0]['body']) if sso else {}
            check('redirectUrl ignored: one POST, to <rules host>/api/welcome, not the mirror',
                  len(sso) == 1 and sso[0]['url'] == stubmod.CASINO + '/api/welcome', str(sso))
            check('redirectUrl ignored: redirect is <host>/ua/lobby + the page query',
                  fields.get('redirect') == [stubmod.CASINO + '/ua/lobby?lang=ua&click_id=CLK1&sub1=S1'],
                  str(fields.get('redirect')))
            r.close()

            # ── the button submits once, however many clicks ──
            r = Run(browser, base).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_selector('#pl-ok[open] .pl-modal__btn', timeout=6000)
            r.page.dblclick('#pl-ok .pl-modal__btn')
            r.page.wait_for_function(SSO_DONE, timeout=6000)
            r.settle(300)
            check('success modal: a double click posts to the casino once', len(r.state['sso']) == 1, str(r.state['sso']))
            r.close()

            # No casino domain (the landing has no rules URL): nothing to hand off to.
            r = Run(browser, base, casino_rules=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('no casino domain: the generic line, no success modal',
                  r.form_error() == MESSAGES['en']['network'] and not r.page.locator('#pl-ok').count(),
                  r.form_error())
            check('no casino domain: nothing posted to any welcome',
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
                check('email taken, %s: no modal, only the form line' % lang,
                      not r.page.locator('#pl-rc').count() and not r.page.locator('#pl-ok').count())
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
                r.page.wait_for_selector('#pl-rc[open]', timeout=4000)
                r.settle(500)
                rc = r.page.evaluate("""() => {
                    const d = document.getElementById('pl-rc'), b = d.querySelector('.pl-modal__btn');
                    return { modal: d.matches(':modal'), focusOnBtn: document.activeElement === b,
                             text: document.getElementById(d.getAttribute('aria-labelledby')).textContent,
                             btn: b.textContent.trim(), h: b.getBoundingClientRect().height,
                             ok: !!document.getElementById('pl-ok') }; }""")
                check('recaptcha modal, %s: a separate modal, reviewed text, focus on its button' % lang,
                      rc['modal'] and rc['focusOnBtn'] and rc['text'] == MODAL[lang]['rc_text']
                      and rc['btn'] == MODAL[lang]['close'] and not rc['ok'], str(rc))
                check('recaptcha modal, %s: its button is at least 24px' % lang, rc['h'] >= 24, str(rc))
                r.page.click('#pl-rc .pl-modal__btn')
                r.settle(300)
                check('recaptcha modal, %s: the button closes it, nothing posted to the casino, form usable' % lang,
                      not r.page.evaluate('document.getElementById("pl-rc").open')
                      and not r.state['sso'] and not r.page.is_disabled('.tw-cta[type="submit"]'))
                r.close()

            r = Run(browser, base, recaptcha_ok=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('recaptcha fails in the browser: its message, nothing posted',
                  r.form_error() == MESSAGES['en']['recaptcha'] and not r.state['registered'], r.form_error())
            r.page.wait_for_selector('#pl-rc[open]', timeout=4000)
            check('recaptcha fails in the browser: the modal opens too',
                  r.page.inner_text('#pl-rc-text').strip() == MODAL['en']['rc_text'])
            r.page.evaluate("TW.setLang('ru')")
            r.settle(150)
            check('error message follows a language switch',
                  r.form_error() == MESSAGES['ru']['recaptcha'], r.form_error())
            check('recaptcha modal follows a language switch',
                  r.page.inner_text('#pl-rc-text').strip() == MODAL['ru']['rc_text'])
            r.close()

            r = Run(browser, base, register_abort=True).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.page.wait_for_function(ERROR_SHOWN, timeout=5000)
            check('network failure: the template\'s generic line',
                  r.form_error() == MESSAGES['en']['network'], r.form_error())
            check('network failure: button usable again, no modal',
                  not r.page.is_disabled('.tw-cta[type="submit"]') and not r.page.locator('#pl-rc, #pl-ok').count())
            r.close()

            r = Run(browser, base, ipify_ok=False).open('lang=en')
            r.settle()
            r.fill_and_submit()
            r.finish()
            check('ipify down: registration still goes, clientIp is ""',
                  r.state['registered'] and r.state['registered'][0].get('clientIp') == '')
            r.close()

            # ── campaign.js's own platform.dev (IT's TEMP_CONFIG), end to end ──
            # No override: the file's values are read. Their host is added to the
            # stub's list, so it is answered locally and nothing reaches the network.
            text = (ROOT / 'campaign.js').read_text(encoding='utf-8')
            block = text[text.index('dev: {'):]
            block = block[:block.index('}')]
            own_id = re.search(r"id:\s*(\d+)", block)
            own_reg = re.search(r"email_registration:\s*'([^']+)'", block)
            own_land = re.search(r"landing:\s*'([^']+)'", block)
            check('campaign.js dev: id 8, registration/email and landing/8 on one https host',
                  bool(own_id and own_reg and own_land) and own_id.group(1) == '8'
                  and own_reg.group(1).endswith('/api/jp/registration/email')
                  and own_land.group(1).endswith('/api/jp/landing/8')
                  and urlparse(own_reg.group(1)).netloc == urlparse(own_land.group(1)).netloc
                  and urlparse(own_land.group(1)).scheme == 'https', block)
            if own_land:
                u = urlparse(own_land.group(1))
                stubmod.APIS = stubmod.APIS + ('%s://%s' % (u.scheme, u.netloc),)
                try:
                    r = Run(browser, base, platform='own').open('lang=en')
                    r.settle()
                    r.fill_and_submit()
                    r.finish()
                    check('campaign.js dev: landing GET, registration POST with landing_id 8, SSO only after the click',
                          r.state['order'].count('landing') == 1 and r.state['registered']
                          and r.state['registered'][0].get('landing_id') == 8 and len(r.state['sso']) == 1,
                          str(r.state['order']))
                    check('campaign.js dev: only stubbed origins contacted, console clean',
                          not r.state['leaks'] and not r.errors, str(r.state['leaks'] + r.errors))
                    r.close()
                finally:
                    stubmod.APIS = (stubmod.PROD_API,)

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
            r.finish()
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

            # ── no CSP: IT's index.html has none (owner, 2026-11-11) ──
            html = (ROOT / 'index.html').read_text(encoding='utf-8')
            check('no CSP: index.html has no Content-Security-Policy meta, as IT\'s has none',
                  not re.search(r'http-equiv=["\']?Content-Security-Policy', html, re.I))
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
