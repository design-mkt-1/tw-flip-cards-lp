"""A stand-in for everything js/platform.js talks to, for the two browser tests.

Not one real request is ever sent to the platform API, ipify or Google: the
browser is intercepted before the network and every one of those origins is
answered from here. Any OTHER non-local request is aborted and recorded in
state['leaks'], so a test can assert the page asked for nothing it should not.

index.html has no CSP (IT's template has none, owner 2026-11-11), so nothing
is refused by the browser before interception.
"""

import json

# The production API. The stub answers it; every request to it is
# intercepted and none reaches it.
PROD_API = 'https://api2-land-prod.top-win.promo'
API = PROD_API
APIS = (PROD_API,)
# What the tests put in campaign.js § platform.dev, which ships IT's own dev
# config (decision 24), a real host. Injected by platform_test.py and smoke.py
# so the page never calls it.
DEV = {'id': 7,
       'email_registration': API + '/api/jp/registration/email',
       'landing': API + '/api/jp/landing/7'}
# Shaped like the live casino host topwin-bet.club, on the reserved .test TLD
# so it never resolves.
CASINO = 'https://casino.topwin-bet.test'
# A host that is not TopWin's. Since 2026-11-11 the page applies the landing's
# links as IT's template does, with no host filter, so these are applied too.
FOREIGN = 'https://casino.example.invalid'
# A mirror the registration answer may carry as redirectUrl. The page ignores it
# (decision 24); its /api/welcome is answered so a test can prove nothing is posted there.
MIRROR = 'https://mirror.example'
# The analytics hosts js/platform.js loads from the landing response. They are
# answered with an empty script, so nothing reaches Google or Yandex.
ANALYTICS = (
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
        'landing_delay': 0,
        'register_status': 200,
        'register_json': {'data': {'accessToken': 'TMP-TOKEN-123'}},
        'redirect_url': None,  # set: the registration answer also carries data.redirectUrl
        'casino_rules': True,  # False: the landing has no rules URL, so there is no casino domain
        'foreign_links': False,  # True: rules / policy / login point to a host that is not TopWin's
        'register_abort': False,
        'recaptcha_ok': True,
        'ipify_ok': True,
        'registered': [],     # parsed JSON bodies sent to the registration API
        'register_raw': [],   # {headers, body, method}: the request exactly as sent
        'order': [],          # 'landing' | 'recaptcha_js' | 'ipify' | 'register', in arrival order
        'recaptcha_src': [],  # every api.js URL the page asked for
        'sso': [],            # {url, body} of every POST to the casino
        'landing_gets': [],   # headers of every GET landing
        'leaks': [],          # anything else that left the page
        'analytics_google': None,   # IDs the landing response carries; None = absent
        'analytics_yandex': None,
        'gtm_tag': None,
        'analytics_requests': [],   # every URL answered by the analytics stub
    }
    state.update(over)
    return state


def landing_json(state):
    casino = FOREIGN if state['foreign_links'] else CASINO
    return {'data': {
        'active': state['active'],
        'recaptcha_key': 'STUB-SITE-KEY',
        'country': 'UA',
        'currency': 'UAH',
        'promocode': 'PROMO-X',
        'rules': casino + '/uk/rules' if state['casino_rules'] else '',
        'policy': casino + '/uk/privacy',
        'login': casino + '/uk/login',
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

        if any(url.startswith(p) for p in local_prefixes):
            return route.continue_()

        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=CORS)

        if any(url.startswith(a + '/api/jp/landing/') for a in APIS):
            state['landing_gets'].append(dict(req.headers, method=req.method))
            state['order'].append('landing')
            return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                 body=json.dumps(landing_json(state)))

        if any(url.startswith(a + '/api/jp/registration/email') for a in APIS):
            if state['register_abort']:
                return route.abort()
            state['registered'].append(json.loads(req.post_data or '{}'))
            state['register_raw'].append({'headers': req.headers, 'body': req.post_data or '',
                                          'method': req.method})
            state['order'].append('register')
            payload = state['register_json']
            if state['redirect_url']:
                payload = {'data': dict(payload['data'], redirectUrl=state['redirect_url'])}
            return route.fulfill(status=state['register_status'], headers=CORS,
                                 content_type='application/json',
                                 body=json.dumps(payload))

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

        if url.startswith(CASINO + '/api/welcome') or url.startswith(MIRROR + '/api/welcome'):
            state['sso'].append({'url': url, 'body': req.post_data or '',
                                 'method': req.method})
            return route.fulfill(status=200, content_type='text/html',
                                 body='<!doctype html><title>casino stub</title>')

        if any(url.startswith(p) for p in ANALYTICS):
            state['analytics_requests'].append(url)
            return route.fulfill(status=200, content_type='application/javascript', body='')

        state['leaks'].append('%s %s' % (req.method, url))
        return route.abort()

    context.route('**/*', handler)
