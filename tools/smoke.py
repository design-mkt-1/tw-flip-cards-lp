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

Then it plays the game, which is the second thing no text check can see. The
campaign requires the visitor to go 3 of 3: whichever cards they turn, all
three land the top prize (CONFIG.alwaysWin, js/flip.js). Nothing else in CI
touches game logic -- parity compares tags, fonts.py compares glyphs -- so a
regression that quietly restored the old hunt, or that promoted the attribute
without the visible prize, would go green through all of it. That is the same
shape as both bugs above: nothing fails, it is just wrong.

play() picks three cards that were BUILT AS LOSERS and turns them. Choosing
losers on purpose is what makes the assertion mean something -- three fixed
positions would be three real winners about once in eighty runs, and the test
would pass for the wrong reason. It checks the rendered prize text and not only
data-prize, for the reason the hryvnia taught: attribute state passes while the
pixels are wrong.
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


class Skipped(Exception):
    """The game check does not apply to how the game is currently configured."""


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


# The cards the visitor is meant to be able to win with: everything the deck
# built as a losing tier. There are always six.
PICK_LOSERS = """() => {
  const api = window.TWFlip;
  if (!api) return null;
  return {
    winPrizeId: api.config.winPrizeId,
    winTarget:  api.config.winTarget,
    alwaysWin:  api.config.alwaysWin,
    losers: [...document.querySelectorAll('.fc-cell')]
      .filter(c => c.dataset.prize !== api.config.winPrizeId)
      .map(c => c.dataset.pos),
  };
}"""

# Read after the win sequence has run. The prize TEXT as well as the attribute:
# data-prize can say p250k over a card still drawing 25.000.
PLAYED = """(positions) => {
  const api  = window.TWFlip;
  const top  = api.config.deck.find(p => p.id === api.config.winPrizeId);
  const grid = document.getElementById('fc-grid');
  const dlg  = document.getElementById('fc-signup');
  const cells = positions.map(p => document.querySelector('.fc-cell[data-pos="' + p + '"]'));
  return {
    found:    api.state.found,
    expected: top.pct,
    prizes:   cells.map(c => c.dataset.prize),
    marked:   cells.map(c => 'win' in c.dataset),
    faces:    cells.map(c => c.dataset.face),
    texts:    cells.map(c => {
      const el = c.querySelector('.fc-prize__pct');
      return el ? el.textContent : null;
    }),
    winFaces: cells.map(c => 'winFace' in c.dataset),
    pipsOn:   document.querySelectorAll('#fc-progress .fc-pip[data-on]').length,
    pipsAll:  document.querySelectorAll('#fc-progress .fc-pip').length,
    phase:      grid ? (grid.dataset.phase || null) : null,
    dialogOpen: dlg ? dlg.open : null,

    // The cards nobody turned. They open too, showing the losing tiers.
    rest: [...document.querySelectorAll('.fc-cell')]
      .filter(c => !('win' in c.dataset))
      .map(c => ({
        pos:     c.dataset.pos,
        prize:   c.dataset.prize,
        face:    c.dataset.face,
        winFace: 'winFace' in c.dataset,
      })),
  };
}"""


def play(page):
    """Turn three cards built as losers. All three must win. Returns failures."""
    bad = []
    pick = page.evaluate(PICK_LOSERS)

    if pick is None:
        return ['window.TWFlip is not exposed, so the game cannot be played']
    if not pick['alwaysWin']:
        # Not a failure. The switch is marketing's to flip; say so and stop,
        # rather than assert the campaign's rules against the other game.
        # Raised, not printed, so the ok line below cannot go on claiming
        # "3 of 3" for a run that never checked it.
        raise Skipped('CONFIG.alwaysWin is off')

    need = pick['winTarget']
    if len(pick['losers']) < need:
        return ['only %d cards were built as losers, need %d to prove the '
                'promotion happens' % (len(pick['losers']), need)]

    # From the END of the board, deliberately. buildGrid marks the first few
    # cards with data-win-face so both face images are fetched at load, and
    # turning those would exercise only half of it: the attribute is supposed
    # to move ONTO cards that had none and OFF the ones the visitor left. Take
    # the tail and both halves are under test.
    positions = pick['losers'][-need:]
    for pos in positions:
        page.click('.fc-cell[data-pos="%s"] .fc-card' % pos)

    try:
        page.wait_for_function(
            'window.TWFlip.state.found === window.TWFlip.config.winTarget',
            timeout=5000)
        page.wait_for_function(
            '() => document.getElementById("fc-signup").open', timeout=5000)
        # The rest of the board opens on a stagger after that.
        page.wait_for_function(
            '() => [...document.querySelectorAll(".fc-cell")]'
            '.every(c => c.dataset.face === "front")', timeout=5000)
    except Exception:
        pass  # Measure anyway: the numbers below say more than the timeout does.

    m = page.evaluate(PLAYED, positions)
    where = ', '.join(positions)

    if m['found'] != need:
        bad.append('turned %d cards at positions %s and the game counted %d '
                   'wins, not %d -- the visitor did not go %d of %d'
                   % (need, where, m['found'], need, need, need))

    for i, pos in enumerate(positions):
        if m['prizes'][i] != pick['winPrizeId']:
            bad.append('card %s was built as a loser and stayed %s after being '
                       'turned -- it was not promoted to %s'
                       % (pos, m['prizes'][i], pick['winPrizeId']))
        elif m['texts'][i] != m['expected']:
            bad.append('card %s says data-prize=%s but draws %r, not %r -- the '
                       'attribute was promoted and the visible prize was not'
                       % (pos, m['prizes'][i], m['texts'][i], m['expected']))
        if not m['marked'][i]:
            bad.append('card %s has no data-win, so it gets no ring, no bloom '
                       'and no shine' % pos)
        if not m['winFaces'][i]:
            bad.append('card %s has no data-win-face, so it draws the plain '
                       'face art while claiming the top prize' % pos)
        if m['faces'][i] != 'front':
            bad.append('card %s did not turn: data-face is %s'
                       % (pos, m['faces'][i]))

    if m['pipsOn'] != need:
        bad.append('%d of %d progress pips lit after %d wins'
                   % (m['pipsOn'], m['pipsAll'], need))
    if m['phase'] != 'reveal':
        bad.append('#fc-grid never reached data-phase="reveal" (it is %r), so '
                   'the board never reacted to the win' % m['phase'])
    if not m['dialogOpen']:
        bad.append('#fc-signup did not open after the third win -- the visitor '
                   'reaches no form')

    # The six nobody turned. They open showing what the deck built them as.
    # data-win-face has to have come off any that were carrying it for the
    # preload, or a 50.000 card draws the top prize's orange frame -- a bug
    # that is invisible for as long as those cards stay face down.
    for c in m['rest']:
        if c['face'] != 'front':
            bad.append('card %s never opened at the reveal: data-face is %s'
                       % (c['pos'], c['face']))
        if c['prize'] == pick['winPrizeId']:
            bad.append('card %s was not turned by the visitor and still shows '
                       'the top prize -- only the cards they pick get promoted'
                       % c['pos'])
        if c['winFace']:
            bad.append('card %s draws the top prize\'s orange frame while '
                       'showing %s -- data-win-face was left on a card the '
                       'visitor never turned' % (c['pos'], c['prize']))

    return bad


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

    # The console errors are NOT folded in here. play() runs after this on the
    # same page, and anything it throws has to land in the same list.
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
                    played = '3 of 3'
                    try:
                        bad.extend(play(page))
                    except Skipped as why:
                        played = 'game not played (%s)' % why
                    bad.extend(errors)
                    label = '%s @ %s' % (html, name)
                    if bad:
                        failures += len(bad)
                        for line in bad:
                            print('::error::%s: %s' % (label, line))
                    else:
                        print('ok  %-22s scrollY %d, %dpx tall, footer ends at '
                              '%d, dialog display: none, %s'
                              % (label, m['scrollY'], m['scrollHeight'],
                                 m['footerBottom'], played))

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
