"""A stand-in for everything js/platform.js talks to, for the two browser tests.

Not one real request is ever sent to jack-pot.tech, ipify or Google: the
browser is intercepted before the network and every one of those origins is
answered from here. Any OTHER non-local request is aborted and recorded in
state['leaks'], so a test can assert the page asked for nothing it should not.

The CSP in index.html is still enforced by the browser before interception, so
a missing origin in it shows up as a console error exactly as it would live.
"""

import json

API = 'https://api2-land-dev.jack-pot.tech'
CASINO = 'https://casino.stub.test'
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
        'register_abort': False,
        'recaptcha_ok': True,
        'ipify_ok': True,
        'registered': [],     # parsed JSON bodies sent to the registration API
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
    return {'data': {
        'active': state['active'],
        'recaptcha_key': 'STUB-SITE-KEY',
        'country': 'UA',
        'currency': 'UAH',
        'promocode': 'PROMO-X',
        'rules': CASINO + '/uk/rules',
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

        if any(url.startswith(p) for p in local_prefixes):
            return route.continue_()

        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=CORS)

        if url.startswith(API + '/api/jp/landing/'):
            state['landing_gets'].append(req.headers)
            return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                 body=json.dumps(landing_json(state)))

        if url.startswith(API + '/api/jp/registration/email'):
            if state['register_abort']:
                return route.abort()
            state['registered'].append(json.loads(req.post_data or '{}'))
            return route.fulfill(status=state['register_status'], headers=CORS,
                                 content_type='application/json',
                                 body=json.dumps(state['register_json']))

        if url.startswith('https://www.google.com/recaptcha/api.js'):
            result = ('Promise.resolve("STUB-TOKEN:" + key + ":" + opts.action)' if state['recaptcha_ok']
                      else 'Promise.reject(new Error("stub"))')
            return route.fulfill(status=200, content_type='application/javascript',
                                 body=RECAPTCHA_JS % result)

        if url.startswith('https://api.ipify.org'):
            if not state['ipify_ok']:
                return route.abort()
            return route.fulfill(status=200, headers=CORS, content_type='application/json',
                                 body='{"ip":"203.0.113.7"}')

        if url.startswith(CASINO + '/api/welcome'):
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
