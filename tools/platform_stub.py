"""A stand-in for everything IT's registration code (js/it/) talks to, for the
two browser tests.

Not one real request is ever sent to the platform API, ipify, Google or the
fingerprint CDN: the browser is intercepted before the network and every one of
those is answered from here. Any OTHER non-local request is aborted and
recorded in state['leaks'], so a test can assert the page asked for nothing it
should not.

The API is matched by PATH (/api/jp/landing/<id>, /api/jp/registration/email),
on any host. IT's own dev host sits in js/it/enums/enums.js and is the only
place tools/brands.py lets it be named, so it is not named here: whichever host
a page is configured with, the stub answers it.

Two ways to open the page:
  * http://127.0.0.1:<port>/   IT's development branch (TEMP_CONFIG, landing 8,
                               main.js starts one second late)
  * SITE (http://lp.test/)     a production-like origin: the files come from
                               disk through the stub, config.json comes from
                               state['config'] (404 when it is None), and
                               main.js starts at once
"""

import json
import mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The production API host of config.example.json: never reached, always answered.
API = 'https://api2-land-prod.top-win.promo'
# A production-like origin that does not resolve; the stub serves it from ROOT.
SITE = 'http://lp.test'
# Shaped like the live casino host topwin-bet.club, on the reserved .test TLD.
CASINO = 'https://casino.topwin-bet.test'
# Where the backend's `redirectUrl` points (IT flip_cards, 2026-11-13): the real
# platform origin, which differs from the `rules` host above.
PLATFORM = 'https://platform.topwin-bet.test'
# The analytics and fingerprint hosts. Answered with an empty script.
FINGERPRINT = 'https://cdn.jsdelivr.net/npm/@fingerprintjs/fingerprintjs@3.3.3/'
EMPTY_SCRIPT_HOSTS = (
    'https://www.googletagmanager.com/',
    'https://www.google-analytics.com/',
    'https://mc.yandex.ru/',
    'https://mc.yandex.com/',
)
CORS = {
    'access-control-allow-origin': '*',
    'access-control-allow-headers': '*',
    'access-control-allow-methods': 'GET, POST, OPTIONS',
}

RECAPTCHA_JS = """
window.grecaptcha = {
  ready: function (f) { f(); },
  execute: function (key, opts) {
    return %s;
  }
};
"""


def new_state(**over):
    state = {
        'active': True,
        'register_status': 200,
        # Add 'redirectUrl': <url> to data to take IT's redirectUrl path; without
        # it main.js falls back to the rules host + /<lang>/<redirect_link>.
        'register_json': {'data': {'accessToken': 'TMP-TOKEN-123'}},
        'casino_rules': True,   # False: the landing has no rules URL
        'register_abort': False,
        'recaptcha_ok': True,
        'ipify_ok': True,
        'config': None,         # SITE only: the config.json body; None = 404
        'registered': [],       # parsed JSON bodies sent to the registration API
        'register_raw': [],     # {headers, body, method}: the request as sent
        'landing_urls': [],     # every GET landing URL
        'register_urls': [],    # every POST registration URL
        'order': [],            # 'config' | 'landing' | 'recaptcha_js' | 'ipify' | 'register'
        'recaptcha_src': [],    # every api.js URL the page asked for
        'sso': [],              # {url, body, method} of every POST to the casino
        'landing_gets': [],     # headers of every GET landing
        'fingerprint': [],      # every request to the fingerprint CDN
        'leaks': [],            # anything else that left the page
        'analytics_google': None,
        'analytics_yandex': None,
        'gtm_tag': None,
        'analytics_requests': [],
    }
    state.update(over)
    return state


def landing_json(state):
    return {'data': {
        'active': state['active'],
        'recaptcha_key': 'STUB-SITE-KEY',
        'country': 'UA',
        'currency': 'UAH',
        'promocode': 'PROMO-X',
        'rules': CASINO + '/uk/rules' if state['casino_rules'] else '',
        'policy': CASINO + '/uk/privacy',
        'login': CASINO + '/uk/login',
        'redirect_link': 'lobby',
        'analytics_google': state['analytics_google'],
        'analytics_yandex': state['analytics_yandex'],
        'gtm_tag': state['gtm_tag'],
    }}


def install(context, state, local_prefixes):
    """Route everything on `context`. `local_prefixes` are the URLs that are
    allowed through untouched (the loopback server of the test)."""

    def handler(route):
        req = route.request
        url = req.url
        path = url.split('?', 1)[0]

        if any(url.startswith(p) for p in local_prefixes):
            return route.continue_()

        if url.startswith(SITE + '/'):
            rel = path[len(SITE) + 1:] or 'index.html'
            if rel == 'config.json':
                state['order'].append('config')
                if state['config'] is None:
                    return route.fulfill(status=404, body='not found')
                return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                     body=json.dumps(state['config']))
            f = ROOT / rel
            if not f.is_file() or ROOT not in f.resolve().parents:
                return route.fulfill(status=404, body='not found')
            return route.fulfill(status=200, body=f.read_bytes(),
                                 content_type=mimetypes.guess_type(f.name)[0] or 'application/octet-stream')

        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=CORS)

        if '/api/jp/landing/' in path:
            state['landing_gets'].append(dict(req.headers, method=req.method))
            state['landing_urls'].append(url)
            state['order'].append('landing')
            return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                 body=json.dumps(landing_json(state)))

        if path.endswith('/api/jp/registration/email'):
            if state['register_abort']:
                return route.abort()
            state['registered'].append(json.loads(req.post_data or '{}'))
            state['register_raw'].append({'headers': req.headers, 'body': req.post_data or '',
                                          'method': req.method})
            state['register_urls'].append(url)
            state['order'].append('register')
            return route.fulfill(status=state['register_status'], headers=CORS,
                                 content_type='application/json',
                                 body=json.dumps(state['register_json']))

        if url.startswith('https://www.google.com/recaptcha/api.js'):
            state['recaptcha_src'].append(url)
            state['order'].append('recaptcha_js')
            result = ('Promise.resolve("STUB-TOKEN:" + key + ":" + opts.action)' if state['recaptcha_ok']
                      else 'Promise.reject(new Error("stub"))')
            return route.fulfill(status=200, content_type='application/javascript',
                                 body=RECAPTCHA_JS % result)

        if url.startswith('https://api.ipify.org'):
            state['order'].append('ipify')
            if not state['ipify_ok']:
                return route.abort()
            return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                 body='{"ip":"203.0.113.7"}')

        if url.startswith(CASINO + '/api/welcome') or url.startswith(PLATFORM + '/api/welcome'):
            state['sso'].append({'url': url, 'body': req.post_data or '',
                                 'method': req.method})
            return route.fulfill(status=200, content_type='text/html',
                                 body='<!doctype html><title>casino stub</title>')

        if url.startswith(FINGERPRINT):
            state['fingerprint'].append(url)
            return route.fulfill(status=200, content_type='application/javascript', body='')

        if any(url.startswith(p) for p in EMPTY_SCRIPT_HOSTS):
            state['analytics_requests'].append(url)
            return route.fulfill(status=200, content_type='application/javascript', body='')

        state['leaks'].append('%s %s' % (req.method, url))
        return route.abort()

    context.route('**/*', handler)
