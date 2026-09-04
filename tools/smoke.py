#!/usr/bin/env python3
"""
Headless smoke test. Loads every page in a real browser and asserts the things
a human notices in the first second and no text check can see.

Run by hand, from the project root:

    python tools/smoke.py

Needs Playwright and one Chromium:

    python -m pip install playwright
    python -m playwright install chromium

It serves the project itself on a loopback port, so nothing has to be running
first, and it never touches the network. Like tools/fonts.py and
tools/optimize.py this is NOT a build step -- the published site is the files
in this repo, and nothing here runs at deploy time.


WHY THIS FILE EXISTS
--------------------
Two silent visual bugs shipped to production in two days, and neither could
have been caught by reading the source.

The first was the hryvnia sign: absent from the fonts, drawn in a system
fallback, thin and narrow beside black italic digits. Nothing failed, because a
missing glyph still renders *something*. tools/fonts.py --check now guards it.

The second was this one. A `display: flex` on .fc-modal that was never scoped
to [open] left the CLOSED dialog in normal flow. Two symptoms, one cause: 650px
of apparent emptiness under the footer -- the dialog is transparent and
opacity: 0, so it reads as blank page -- and, because the close button was
being rendered, its `autofocus` fired at parse time and scrolled the page to
the bottom on load. The site opened at its own footer for a day and every text
check in CI was green.

So the assertions here are deliberately about geometry and not about markup:

  scrollY == 0                     the page opens where it was written to open
  scrollHeight <= footer bottom    nothing is left in flow past the last thing
                                   the visitor is meant to see
  the closed dialog is display:none, and its close button draws no box
  the console is clean            a 404 on an asset shows up here as an error

The footer assertion is the general one. It does not know about dialogs; it
catches anything at all that parks itself below the footer, which is the shape
this class of bug takes every time.

Both viewports are checked. The modal carries its own mobile rules --
width: min(504px, 100vw - 15px), max-height: calc(100svh - 32px) -- so a
recurrence there would size differently from a recurrence on desktop.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit('smoke: Playwright is not installed.\n'
             '  python -m pip install playwright\n'
             '  python -m playwright install chromium')

ROOT = Path(__file__).resolve().parent.parent

PAGES = ('index.html', 'ru.html', 'en.html')

# Desktop is the Figma frame width; mobile is the 375 frame the modal has its
# own rules for, in a viewport tall enough that 100svh means something.
VIEWPORTS = (('desktop', 1440, 900), ('mobile', 375, 812))


class QuietHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler logs every request to stderr. Nobody wants it."""

    def log_message(self, fmt, *args):
        pass


def serve(root):
    """Serve `root` on a loopback port the OS picks. Returns the base URL."""
    handler = partial(QuietHandler, directory=str(root))
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, 'http://127.0.0.1:%d' % httpd.server_address[1]


# Read in one pass in the page, after load. getClientRects() rather than
# offsetParent for the close button: offsetParent is null for a positioned
# element even when it is perfectly visible, and this button is sticky.
MEASURE = """() => {
  const footer = document.querySelector('.fc-footer');
  const dialog = document.getElementById('fc-signup');
  const close  = document.getElementById('fc-close');
  return {
    scrollY:       Math.round(window.scrollY),
    scrollHeight:  document.documentElement.scrollHeight,
    innerHeight:   window.innerHeight,
    footerBottom:  footer ? Math.ceil(footer.getBoundingClientRect().bottom + window.scrollY) : null,
    dialogFound:   !!dialog,
    dialogOpen:    dialog ? dialog.open : null,
    dialogDisplay: dialog ? getComputedStyle(dialog).display : null,
    closeDrawn:    close ? close.getClientRects().length > 0 : null,
  };
}"""


def check(page, url, errors):
    """Load one page and return its list of failure strings."""
    page.goto(url, wait_until='load')
    m = page.evaluate(MEASURE)
    bad = []

    if m['scrollY'] != 0:
        bad.append('opens scrolled to %dpx instead of the top -- something '
                   'below the fold is taking focus at load' % m['scrollY'])

    if m['footerBottom'] is None:
        bad.append('no .fc-footer on the page')
    else:
        # A page shorter than the viewport still reports the viewport height.
        allowed = max(m['footerBottom'], m['innerHeight']) + 1
        if m['scrollHeight'] > allowed:
            bad.append('%dpx of page below the footer: scrollHeight %d, footer '
                       'ends at %d -- something is still in flow down there'
                       % (m['scrollHeight'] - m['footerBottom'],
                          m['scrollHeight'], m['footerBottom']))

    if not m['dialogFound']:
        bad.append('no #fc-signup dialog on the page')
    elif m['dialogOpen']:
        bad.append('#fc-signup is open on load')
    else:
        if m['dialogDisplay'] != 'none':
            bad.append("closed #fc-signup computes display: %s, not none -- the "
                       "UA's dialog:not([open]) rule is being beaten by a class"
                       % m['dialogDisplay'])
        if m['closeDrawn']:
            bad.append('#fc-close draws a box while the dialog is closed, so '
                       'its autofocus can fire at load')

    bad.extend(errors)
    return bad, m


def main():
    httpd, base = serve(ROOT)
    failures = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for name, width, height in VIEWPORTS:
                context = browser.new_context(viewport={'width': width, 'height': height})
                page = context.new_page()

                # Attached once per context, cleared per page below, so a
                # message can never arrive before someone is listening.
                errors = []
                page.on('console', lambda msg: errors.append('console error: ' + msg.text)
                        if msg.type == 'error' else None)
                page.on('pageerror', lambda exc: errors.append('uncaught: %s' % exc))

                for html in PAGES:
                    errors.clear()
                    bad, m = check(page, '%s/%s' % (base, html), errors)
                    label = '%s @ %s' % (html, name)
                    if bad:
                        failures += len(bad)
                        for line in bad:
                            print('::error::%s: %s' % (label, line))
                    else:
                        print('ok  %-22s scrollY %d, %dpx tall, footer ends at '
                              '%d, dialog display: none'
                              % (label, m['scrollY'], m['scrollHeight'],
                                 m['footerBottom']))

                context.close()
        finally:
            browser.close()
            httpd.shutdown()

    if failures:
        print('\nsmoke: %d failure%s' % (failures, '' if failures == 1 else 's'))
        return 1
    print('\nsmoke: %d pages x %d viewports, all clean'
          % (len(PAGES), len(VIEWPORTS)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
