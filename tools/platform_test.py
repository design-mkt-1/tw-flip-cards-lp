#!/usr/bin/env python3
"""
Headless test of IT's registration code (js/it/) on this page, against a stub.

    python -I tools/platform_test.py </dev/null

Same needs and same rules as tools/smoke.py: Playwright and one Chromium, the
project served from a loopback port, and NOT ONE real request -- the platform
API, ipify, Google and the fingerprint CDN are answered by
tools/platform_stub.py, and anything else that leaves the page fails the run.

Decision 25 (owner, 2026-11-12): registration and connection are IT's
test6637.zip, 1:1. So this test checks two things.

  1. The copy is IT's. js/it/*, css/it/* and assets/img/it/* are compared by
     hash with the files in IT's archive (newline-normalised). main.js is IT's
     flip_cards (1).zip version (SSO from the registration response's
     `redirectUrl`) byte for byte; form-text.js differs in the lines that give
     UA and RU IT's English, proven by undoing the change and hashing again.
  2. The page behaves as IT's does, in ua / ru / en:
       config / landing      development branch (127.0.0.1): TEMP_CONFIG, landing 8;
                             a production origin: config.json first, then its landing
       IT's request          body keys and ORDER, `language` = button text lowercased,
                             headers, request order, fingerprint script loaded
       validation            IT's English messages
       success               IT's success modal (their texts, their check icon),
                             the pop-up closed, NOTHING posted until its button is
                             clicked, then #sso POST. With `redirectUrl` in the response:
                             origin(redirectUrl)/api/welcome; without it, the
                             fallback <rules host>/api/welcome
       errors                the raw server message in the email error; the exact
                             reCAPTCHA string opens IT's error modal (a near miss does
                             not); a browser-side reCAPTCHA failure opens it too
       landing off           IT's page-disabled modal, mailto support@top-win.com
       analytics             IT's analytics.js from the landing response
       adapter               consent toggles once per click, eye toggles once, the
                             three links survive a language change, no phone tab
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote_plus
import hashlib
import json
import re
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent))
import platform_stub as stubmod

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit('platform_test: Playwright is not installed.\n'
             '  python -m pip install playwright\n'
             '  python -m playwright install chromium')

ROOT = Path(__file__).resolve().parent.parent

LANGS = ['ua', 'ru', 'en']
SUPPORT = 'support@top-win.com'
OTHER_SUPPORT = 'support@' + 'jack' + '-' + 'pot' + '.com'      # IT's sample address, never ours
OTHER_BRAND = re.compile('jack' + r'[-_ .]?' + 'pot', re.I)

# IT's own English text (their _js/enums/form-text.js, EN), on all three languages.
IT_TEXT = {
    'required': 'This field is required.',
    'mail': 'Please enter a valid email address',
    'pw_min': 'Password must be at least 8 characters long.',
    'terms': 'Please confirm your agreement with the terms.',
    'ok_title': 'Congratulations!',
    'ok_text': "Your registration is complete. Welcome to the winners' circle.",
    'ok_btn': 'Go to the site',
    'rc_text': ('Unfortunately, we were unable to verify your identity. '
                'Please try registering using a different browser or device.'),
    'disabled_title': 'Page disabled',
    'disabled_text': 'The page you are looking for appears to be disabled',
}
# Addendum 2026-11-12 to decision 25: the register button's two labels follow the
# page language (the landing's own cta.register / cta.loading); all else is IT's.
BTN = {'ua': ('ЗАРЕЄСТРУВАТИСЬ', 'Завантаження…'),
       'ru': ('ЗАРЕГИСТРИРОВАТЬСЯ', 'Загрузка…'),
       'en': ('REGISTER', 'Loading…')}
RC_EXACT = 'reCAPTCHA verification failed. Please try again.'
TAKEN = 'Email already registered. Please use a different email or login.'

BODY_KEYS = ['email', 'password', 'landing_id', 'language', 'currency', 'country', 'promocode',
             'receivePromos', 'clientIp', 'lang', 'g-recaptcha-response']

# sha256 of IT's files in test6637.zip (main.js: flip_cards (1).zip, 2026-11-13),
# newline-normalised; repo path -> hash.
IT_ORIGINAL = {
    'js/it/main.js':
        'b9a61fd0e4369529396fa2096b1025edcf7cf053c93ca0d79591058c0aac3646',
    'js/it/analytics.js':
        '391649c5d48a9f12217ef63bbcc9864b8537d40e0b4d4c65e0ecbcc6c06d5e55',
    'js/it/enums/enums.js':
        'eaa527cb5827b0674645a9373f0ee3e9908efbd056bca2a01eaf6aa07cbc0ef0',
    'js/it/enums/api.js':
        '469ed7ea2aefac927404bc8a2453294bc304140473d13296a087396ea3ed7c3f',
    'js/it/enums/form-text.js':
        '21a7fb7f00f48f6ce45baa6d292d340561e47715300689ac1958c61e36685c2e',
    'js/it/api/resilve-recaptcha.js':
        '6b005e8796cb22b6bac0e53e7f972342ab8d36830c4e636de961e3585ee2a24a',
    'js/it/utils/url.js':
        '6a5beab0b21dac60f3454e4b07f83e8b9d321d5cce9d249e919bc228d773db59',
    'js/it/utils/form-validations.js':
        'feaf5a30b4fefa2e15091a5307400c411199d2a4c4d3a1bcaf26f205580a3724',
    'css/it/success-modal.css':
        'b57c182c1e5eaef14e5a8ee4b4f15d91d145278807809db007d979c847ea4114',
    'css/it/reg-modal-error.css':
        '9fa852b0aba9c18d17b358d7b8dbeb4df896abcfd84dbc11fa55c739d2e22350',
    'css/it/disabled-modal.css':
        'bdeb2e4ecf1823434817e20eb7c2ec41177da643765b7e986e844cbc14e19efc',
    'assets/img/it/check-success.svg':
        '59381efcc37e1c47529767fb8f85708e028bc394b5f4c03522f55c6f13c51c2b',
    'assets/img/it/error.svg':
        'f91a997bc70e6517eb957ca0399bb4b6078957f3b86c8347653075a345e049e7',
    'assets/img/it/mail.svg':
        '6253a46b2f1b85fb9c91fbb3d1afae0b4b107ec2a564016dd1433aebc7e54a39',
    'assets/img/it/logo.svg':
        '61978fbd35a3d0ae0197ef8ecd0924c231870bce987a5a7fe1aa27c0e4a9c083',
}
# form-text.js minus the lines that give UA and RU IT's English, and main.js
# with the support address put back, must equal IT's original.
FORM_TEXT_MARK = '\n// TopWin, decision 25'


def sha(text):
    return hashlib.sha256(text.replace('\r\n', '\n').encode('utf-8')).hexdigest()


def read(rel):
    return (ROOT / rel).read_bytes().decode('utf-8')


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve():
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, 'http://127.0.0.1:%d' % httpd.server_address[1]


class Run:
    """One page in one fresh context, with its own stub state.
    mode 'dev'  : http://127.0.0.1 -- IT's development branch, TEMP_CONFIG
    mode 'prod' : stubmod.SITE     -- config.json first, main.js starts at once"""

    def __init__(self, browser, base, mode='dev', viewport=(1440, 900), **state):
        self.base = base
        self.mode = mode
        self.state = stubmod.new_state(**state)
        self.ctx = browser.new_context(viewport={'width': viewport[0], 'height': viewport[1]})
        stubmod.install(self.ctx, self.state, [base] if mode == 'dev' else [])
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on('console', lambda m: self.errors.append('console error: ' + m.text)
                     if m.type == 'error' and 'Failed to load resource' not in m.text else None)
        self.page.on('pageerror', lambda e: self.errors.append('uncaught: %s' % e))

    def open(self, lang='en', ready='recaptcha'):
        origin = self.base if self.mode == 'dev' else stubmod.SITE
        self.page.goto(origin + '/index.html?lang=' + lang, wait_until='load')
        if ready == 'recaptcha':
            self.wait(lambda: 'recaptcha_js' in self.state['order'])
            self.page.wait_for_function('typeof grecaptcha !== "undefined"', timeout=8000)
        elif ready == 'landing':
            self.wait(lambda: 'landing' in self.state['order'])
            self.settle(300)
        return self

    def wait(self, cond, timeout=8000):
        for _ in range(timeout // 50):
            if cond():
                return True
            self.page.wait_for_timeout(50)
        return False

    def settle(self, ms=300):
        self.page.wait_for_timeout(ms)

    def fill(self, email='player@example.com', password='Sup3rSecret!'):
        p = self.page
        if not p.evaluate('document.getElementById("tw-signup").open'):
            p.evaluate('TWForm.open()')
            p.wait_for_selector('#tw-signup[open]')
        p.fill('#tw-email', email)
        p.fill('#tw-password', password)

    def submit(self, **kw):
        self.fill(**kw)
        self.page.click('.tw-cta[type="submit"]')

    def active(self, sel):
        return self.page.evaluate('s => !!document.querySelector(s) && '
                                  'document.querySelector(s).classList.contains("active")', sel)

    def text(self, sel):
        return self.page.evaluate('s => document.querySelector(s).textContent', sel)

    def dialog_open(self):
        return self.page.evaluate('document.getElementById("tw-signup").open')

    def close(self):
        self.ctx.close()


def main():
    httpd, base = serve()
    results = []

    def check(name, ok, detail=''):
        results.append((name, bool(ok), detail))
        print(('ok   ' if ok else 'FAIL ') + name + ('' if ok else '  -> ' + str(detail)), flush=True)

    # ── 1. the copy is IT's ───────────────────────────────────────
    for rel, want in IT_ORIGINAL.items():
        got = read(rel)
        if rel == 'js/it/main.js':
            check('copy: ' + rel + ' = IT\'s flip_cards (1).zip version, byte for byte',
                  sha(got) == want and got.count(SUPPORT) == 2,
                  'hash differs or the support address is not on exactly two lines')
        elif rel == 'js/it/enums/form-text.js':
            head = got.replace('\r\n', '\n')
            head = head[:head.index(FORM_TEXT_MARK)].rstrip('\n') + '\n'
            check('copy: ' + rel + ' = IT\'s, plus the UA / RU lines',
                  sha(head) == want and 'LANG_TEXTS.UA = {...LANG_TEXTS.EN};' in got
                  and 'LANG_TEXTS.RU = {...LANG_TEXTS.EN};' in got, 'hash differs')
        else:
            check('copy: ' + rel + ' = IT\'s, byte for byte', sha(got) == want, 'hash differs')
    main_js = read('js/it/main.js')
    check('copy: main.js names only support@top-win.com, never IT\'s sample address',
          OTHER_SUPPORT not in main_js and SUPPORT in main_js)
    html = read('index.html')
    check('page: no Content-Security-Policy, as IT\'s index.html has none',
          'Content-Security-Policy' not in html.replace('No Content-Security-Policy', ''))
    check('page: FingerprintJS 3.3.3 loaded as a plain script before IT\'s main.js module',
          html.find('fingerprintjs@3.3.3/dist/fp.min.js"></script>') > 0
          and html.find('fp.min.js') < html.find('<script type="module" src="js/it/main.js">'))
    check('page: nothing of ours left in the registration path',
          not (ROOT / 'js' / 'it' / 'platform.js').exists()
          and 'TWPlatform' not in read('campaign.js') and 'TWPlatform' not in read('js/platform.js'))

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            # ── 2. the happy path, in every language ──────────────
            for lang in LANGS:
                r = Run(browser, base).open(lang)
                st = r.state
                tag = '[%s] ' % lang
                order = st['order']
                check(tag + 'dev: IT\'s TEMP_CONFIG -- GET landing/8, then reCAPTCHA api.js',
                      st['landing_urls'] and st['landing_urls'][0].endswith('/api/jp/landing/8')
                      and order.index('landing') < order.index('recaptcha_js'), str(order))
                check(tag + 'ipify requested once, at load', order.count('ipify') == 1, str(order))
                check(tag + 'landing GET: JSON headers',
                      st['landing_gets'][0].get('accept') == 'application/json'
                      and st['landing_gets'][0].get('content-type') == 'application/json'
                      and st['landing_gets'][0]['method'] == 'GET', str(st['landing_gets']))
                check(tag + 'reCAPTCHA script: render=<key>, verbatim',
                      st['recaptcha_src'] == ['https://www.google.com/recaptcha/api.js?render=STUB-SITE-KEY'],
                      str(st['recaptcha_src']))
                check(tag + 'FingerprintJS script requested', len(st['fingerprint']) == 1, str(st['fingerprint']))
                links = r.page.evaluate("""() => ({
                    terms: document.querySelector('.terms-link').getAttribute('href'),
                    policy: document.querySelector('.policy-link').getAttribute('href'),
                    login: document.querySelector('.login-text a').getAttribute('href') })""")
                check(tag + 'links: rules / policy / login as the API gives them, page query appended',
                      links == {'terms': stubmod.CASINO + '/uk/rules?lang=' + lang,
                                'policy': stubmod.CASINO + '/uk/privacy?lang=' + lang,
                                'login': stubmod.CASINO + '/uk/login?lang=' + lang}, str(links))
                r.submit()
                check(tag + 'success modal opens (IT\'s)', r.wait(lambda: r.active('.success-modal'), 6000))
                body = st['registered'][0] if st['registered'] else {}
                check(tag + 'POST body: IT\'s keys in IT\'s order, g-recaptcha-response last',
                      list(body) == BODY_KEYS, str(list(body)))
                check(tag + 'POST body: values (landing_id 8, language = button text lowercased)',
                      body.get('landing_id') == 8 and body.get('language') == lang
                      and body.get('currency') == 'UAH' and body.get('country') == 'UA'
                      and body.get('promocode') == 'PROMO-X' and body.get('receivePromos') is True
                      and body.get('clientIp') == '203.0.113.7' and body.get('lang') == lang
                      and body.get('g-recaptcha-response') == 'STUB-TOKEN:STUB-SITE-KEY:register'
                      and body.get('email') == 'player@example.com', str(body))
                raw = st['register_raw'][0] if st['register_raw'] else {'headers': {}, 'body': '', 'method': ''}
                check(tag + 'POST: method, Content-Type, compact JSON, no other headers of ours',
                      raw['method'] == 'POST' and raw['headers'].get('content-type') == 'application/json'
                      and raw['body'] == json.dumps(body, separators=(',', ':'), ensure_ascii=False)
                      and st['register_urls'][0].endswith('/api/jp/registration/email'), str(raw))
                texts = r.page.evaluate("""() => ({
                    title: document.querySelector('.success-modal__title').textContent,
                    text: document.querySelector('.success-modal__text').textContent,
                    btn: document.querySelector('.success-modal__btn').textContent,
                    icon: document.querySelector('.success-modal__icon-inner img').getAttribute('src'),
                    shown: getComputedStyle(document.querySelector('.success-modal')).display })""")
                check(tag + 'success modal: IT\'s English text, IT\'s check icon, on screen',
                      texts == {'title': IT_TEXT['ok_title'], 'text': IT_TEXT['ok_text'],
                                'btn': IT_TEXT['ok_btn'], 'icon': 'assets/img/it/check-success.svg',
                                'shown': 'flex'}, str(texts))
                check(tag + 'the pop-up is closed behind it', not r.dialog_open())
                check(tag + 'button label after the request is the page-language register label',
                      r.page.evaluate('document.querySelector(".form-register-submit").textContent')
                      == BTN[lang][0], r.page.evaluate('document.querySelector(".form-register-submit").textContent'))
                r.settle(300)
                check(tag + 'NOTHING is posted to the casino before the button is clicked', not st['sso'], str(st['sso']))
                action = r.page.evaluate('document.getElementById("sso").getAttribute("action")')
                check(tag + 'redirectUrl absent: #sso action = <rules host>/api/welcome (fallback)', action == stubmod.CASINO + '/api/welcome', action)
                r.page.click('.success-modal__btn')
                check(tag + 'the button submits #sso', r.wait(lambda: bool(st['sso']), 6000))
                want = ('tmpToken=TMP-TOKEN-123&redirect=' +
                        quote_plus('%s/%s/lobby?lang=%s' % (stubmod.CASINO, lang, lang), safe=''))
                check(tag + 'SSO POST: tmpToken and redirect = host/<lang>/<redirect_link>?<page query>',
                      st['sso'] and st['sso'][0]['method'] == 'POST'
                      and st['sso'][0]['url'] == stubmod.CASINO + '/api/welcome'
                      and st['sso'][0]['body'] == want, str(st['sso']))
                check(tag + 'console clean, nothing left the page', not r.errors and not st['leaks'],
                      str(r.errors + st['leaks']))
                r.close()

            # ── 2b. SSO from IT's `redirectUrl` (flip_cards (1).zip, 2026-11-13) ──
            for lang in LANGS:
                ru = stubmod.PLATFORM + '/uk/deposit?src=x'
                r = Run(browser, base, register_json={'data': {'accessToken': 'TMP-TOKEN-123',
                                                              'redirectUrl': ru}}).open(lang)
                st = r.state
                tag = '[%s] redirectUrl present: ' % lang
                r.submit()
                check(tag + 'success modal opens', r.wait(lambda: r.active('.success-modal'), 6000))
                r.settle(300)
                action = r.page.evaluate('document.getElementById("sso").getAttribute("action")')
                check(tag + '#sso action = origin(redirectUrl)/api/welcome, not the rules host',
                      action == stubmod.PLATFORM + '/api/welcome', action)
                fields = r.page.evaluate('''() => [...document.querySelectorAll("#sso input")]
                    .map(i => [i.name, i.value])''')
                want_redirect = '%s&lang=%s' % (ru, lang)
                check(tag + 'tmpToken is set and the redirect field = redirectUrl (+ page query)',
                      ['tmpToken', 'TMP-TOKEN-123'] in fields and ['redirect', want_redirect] in fields,
                      str(fields))
                check(tag + 'NOTHING is posted before the button is clicked', not st['sso'], str(st['sso']))
                r.page.click('.success-modal__btn')
                check(tag + 'the button submits #sso', r.wait(lambda: bool(st['sso']), 6000))
                want = 'tmpToken=TMP-TOKEN-123&redirect=' + quote_plus(want_redirect, safe='')
                check(tag + 'SSO POST: platform origin, tmpToken and redirect',
                      st['sso'] and st['sso'][0]['method'] == 'POST'
                      and st['sso'][0]['url'] == stubmod.PLATFORM + '/api/welcome'
                      and st['sso'][0]['body'] == want, str(st['sso']))
                check(tag + 'console clean, nothing left the page', not r.errors and not st['leaks'],
                      str(r.errors + st['leaks']))
                r.close()

            # ── 3. validation: IT's messages, in English whatever the language ──
            for lang in ('ua', 'en'):
                r = Run(browser, base).open(lang)
                tag = '[%s] ' % lang
                r.submit(email='', password='')
                r.settle(150)
                check(tag + 'empty form: IT\'s "required" under both fields',
                      r.text('.error-email span') == IT_TEXT['required']
                      and r.text('.error-password span') == IT_TEXT['required']
                      and r.active('.error-email') and r.active('.error-password')
                      and not r.state['registered'])
                r.fill(email='bad', password='abc')
                r.page.click('.tw-cta[type="submit"]')
                r.settle(150)
                check(tag + 'bad email / short password: IT\'s two messages',
                      r.text('.error-email span') == IT_TEXT['mail']
                      and r.text('.error-password span') == IT_TEXT['pw_min'])
                r.page.fill('#tw-email', 'a@b.co')
                check(tag + 'typing hides the email error and marks the box valid',
                      not r.active('.error-email') and 'valid' in
                      r.page.get_attribute('.tw-field[data-field="email"]', 'class'))
                r.close()

            r = Run(browser, base).open('en')
            box = '#tw-agree'
            r.page.evaluate('TWForm.open()')
            r.page.wait_for_selector('#tw-signup[open]')
            check('consent: starts accepted (IT\'s state is true)', r.page.is_checked(box) and r.active('.terms-wrap'))
            r.page.click('label[for="tw-agree"]')
            r.settle(100)
            check('consent: one click on the sentence = one toggle (off)',
                  not r.page.is_checked(box) and not r.active('.terms-wrap'))
            r.fill()
            r.page.click('.tw-cta[type="submit"]')
            r.settle(150)
            check('consent off: IT\'s message, nothing posted',
                  r.text('.error-terms span') == IT_TEXT['terms'] and r.active('.error-terms')
                  and not r.state['registered'])
            r.page.click(box)
            r.settle(100)
            check('consent: one click on the box = one toggle (on), message gone',
                  r.page.is_checked(box) and r.active('.terms-wrap') and not r.active('.error-terms'))
            r.page.click('.tw-eye')
            t1 = r.page.get_attribute('#tw-password', 'type')
            r.page.click('.tw-eye')
            t2 = r.page.get_attribute('#tw-password', 'type')
            check('eye: toggles once per click', (t1, t2) == ('text', 'password'), (t1, t2))
            check('card: no phone tab, no phone field',
                  r.page.locator('.tw-tabs').count() == 0 and r.page.locator('#tw-phone').count() == 0)
            r.page.evaluate("TW.setLang('ru')")
            r.settle(200)
            links = r.page.evaluate("""() => [document.querySelector('.terms-link').getAttribute('href'),
                document.querySelector('.policy-link').getAttribute('href'),
                document.querySelector('.login-text a').getAttribute('href')]""")
            check('links survive a language change',
                  links == [stubmod.CASINO + '/uk/rules?lang=en', stubmod.CASINO + '/uk/privacy?lang=en',
                            stubmod.CASINO + '/uk/login?lang=en'], str(links))
            r.page.click('.tw-cta[type="submit"]')
            r.wait(lambda: bool(r.state['registered']))
            check('language switched after load -> body.language follows (ru)',
                  r.state['registered'] and r.state['registered'][0]['language'] == 'ru',
                  str(r.state['registered']))
            r.close()

            # ── 4. errors: the raw server text, IT's exact match ─────
            def failing(register_json, status=400, lang='en', **kw):
                r = Run(browser, base, register_status=status, register_json=register_json, **kw).open(lang)
                r.fill()
                r.page.evaluate('''() => { const b = document.querySelector(".form-register-submit");
                    window.__labels = [b.textContent];
                    new MutationObserver(() => window.__labels.push(b.textContent))
                        .observe(b, {childList: true, characterData: true, subtree: true}); }''')
                r.page.click('.tw-cta[type="submit"]')
                r.wait(lambda: bool(r.state['registered']))
                r.settle(300)
                return r

            r = failing({'errors': [TAKEN]})
            check('error: the raw server message is the email error, nothing translated',
                  r.text('.error-email span') == TAKEN and r.active('.error-email')
                  and not r.active('.modal__wrap') and not r.active('.success-modal'), r.text('.error-email span'))
            for blang in LANGS:
                rb = r if blang == 'en' else failing({'errors': [TAKEN]}, lang=blang)
                got = rb.page.evaluate('(() => { const b = document.querySelector(".form-register-submit");'
                                       ' return [!b.disabled, b.textContent, window.__labels]; })()')
                check('error [%s]: button usable again, label = page-language register label' % blang,
                      got[0] and got[1] == BTN[blang][0], str(got))
                check('error [%s]: the loading label was the page-language one' % blang,
                      BTN[blang][1] in got[2], str(got))
                if rb is not r:
                    rb.close()
            check('error: no SSO, console shows no uncaught error',
                  not r.state['sso'] and not any(e.startswith('uncaught') for e in r.errors), str(r.errors))
            r.close()

            r = failing({'errors': ['Something unexpected happened']})
            check('error: any other server message is shown as it came',
                  r.text('.error-email span') == 'Something unexpected happened')
            r.close()

            r = failing({'errors': [RC_EXACT]})
            check('reCAPTCHA (server, exact string): IT\'s modal + "reCAPTCHA verification failed."',
                  r.active('.modal__wrap') and r.text('.error-email span') == 'reCAPTCHA verification failed.'
                  and r.text('.modal__text') == IT_TEXT['rc_text'] and not r.dialog_open(),
                  r.text('.error-email span'))
            r.close()

            r = failing({'errors': [RC_EXACT.lower()]})
            check('reCAPTCHA near miss (other case): no modal -- IT matches the exact string',
                  not r.active('.modal__wrap') and r.text('.error-email span') == RC_EXACT.lower())
            r.close()

            r = Run(browser, base, recaptcha_ok=False).open('en')
            r.submit()
            ok = r.wait(lambda: r.active('.modal__wrap'), 6000)
            r.settle(200)
            check('reCAPTCHA (browser): IT\'s modal, nothing posted', ok and not r.state['registered']
                  and r.text('.modal__text') == IT_TEXT['rc_text'])
            r.close()

            r = Run(browser, base, register_abort=True).open('en')
            r.submit()
            r.wait(lambda: r.active('.error-email'), 6000)
            check('network failure: the browser\'s own message in the email error, no modal',
                  r.active('.error-email') and r.text('.error-email span') != '' and not r.active('.modal__wrap'),
                  r.text('.error-email span'))
            r.close()

            # ── 5. landing off ─────────────────────────────────────
            for lang in LANGS:
                r = Run(browser, base, active=False).open(lang, ready='landing')
                r.settle(300)
                info = r.page.evaluate("""() => ({
                    on: document.querySelector('.disabled-modal').classList.contains('active'),
                    title: document.querySelector('.disabled-modal h2').textContent,
                    text: document.querySelector('.disabled-modal .title-content span').textContent,
                    href: document.querySelector('.mail-link').getAttribute('href'),
                    mail: document.querySelector('.mail-link').textContent,
                    all: document.body.innerText + document.documentElement.outerHTML })""")
                check('[%s] landing off: IT\'s "Page disabled" modal, support@top-win.com' % lang,
                      info['on'] and info['title'] == IT_TEXT['disabled_title']
                      and info['text'] == IT_TEXT['disabled_text']
                      and info['href'] == 'mailto:' + SUPPORT and info['mail'] == SUPPORT, str(info)[:200])
                check('[%s] landing off: IT\'s sample address and the other brand appear nowhere on the page' % lang,
                      OTHER_SUPPORT not in info['all'] and not OTHER_BRAND.search(info['all']))
                check('[%s] landing off: reCAPTCHA is not loaded' % lang, not r.state['recaptcha_src'])
                r.close()

            # ── 6. analytics: IT's analytics.js on the landing response ──
            r = Run(browser, base, analytics_google='G-TEST12345', analytics_yandex=12345,
                    gtm_tag='GTM-TEST123').open('en')
            r.settle(300)
            reqs = ' '.join(r.state['analytics_requests'])
            check('analytics: GA, Yandex and GTM load from the landing response',
                  'googletagmanager.com/gtag/js?id=G-TEST12345' in reqs
                  and 'mc.yandex.ru/metrika/tag.js' in reqs and 'gtm.js?id=GTM-TEST123' in reqs, reqs)
            check('analytics: window.ym, window.dataLayer and the GTM noscript iframe exist',
                  r.page.evaluate('typeof ym === "function" && Array.isArray(dataLayer) && '
                                  '!!document.querySelector("noscript iframe[src*=\'ns.html?id=GTM-TEST123\']") || '
                                  'document.body.firstElementChild.tagName === "NOSCRIPT"'))
            check('analytics: console clean', not r.errors, str(r.errors))
            r.close()
            r = Run(browser, base).open('en')
            r.settle(200)
            check('analytics: a landing with none loads none', not r.state['analytics_requests'])
            r.close()

            # ── 7. a production origin: config.json first ──────────
            cfg = {'id': 3, 'email_registration': stubmod.API + '/api/jp/registration/email',
                   'landing': stubmod.API + '/api/jp/landing/3'}
            r = Run(browser, base, mode='prod', config=cfg).open('en')
            r.submit()
            r.wait(lambda: r.active('.success-modal'), 6000)
            order = r.state['order']
            check('prod: config.json, then GET its landing, then reCAPTCHA (ipify fires at once, as in IT)',
                  order.index('config') < order.index('landing') < order.index('recaptcha_js')
                  and r.state['landing_urls'] == [cfg['landing']], str(order))
            check('prod: landing_id and endpoint come from config.json',
                  r.state['registered'] and r.state['registered'][0]['landing_id'] == 3
                  and r.state['register_urls'] == [cfg['email_registration']], str(r.state['registered']))
            check('prod: success modal; console clean, nothing leaked', r.active('.success-modal')
                  and not r.errors and not r.state['leaks'], str(r.errors + r.state['leaks']))
            r.close()

            r = Run(browser, base, mode='prod', config=None).open('en', ready=None)
            r.settle(800)
            check('prod: no config.json -> IT\'s page does nothing else (no landing, no registration)',
                  r.state['order'].count('landing') == 0 and not r.state['registered']
                  and not any(e.startswith('uncaught') for e in r.errors), str(r.state['order'] + r.errors))
            r.close()
        finally:
            browser.close()
            httpd.shutdown()

    failed = [r for r in results if not r[1]]
    if failed:
        print('\nplatform_test: %d of %d failed' % (len(failed), len(results)))
        return 1
    print('\nplatform_test: %d checks, all ok (IT test6637 registration 1:1, ua / ru / en)' % len(results))
    return 0


if __name__ == '__main__':
    sys.exit(main())
