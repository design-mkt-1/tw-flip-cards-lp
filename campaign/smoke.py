"""The mechanic's own browser check, run by tools/smoke.py after its nine.

tools/smoke.py proves the SHELL works: the bars mounted, TW.openForm() opens
the dialog, no dead link, no untranslated key. It cannot know what this
campaign's win condition is, so it calls check() once per viewport and language
and lets it assert the rest.

Three things, all of which broke at least once in this landing's history:

  1. nine cards are built, face down, and each carries a real accessible name
     -- not the prize, which would give the game away before it is turned;
  2. turning three opens the registration card BY ITSELF, and the board goes
     to its reveal phase with the other six face up;
  3. dismissing the card leaves the claim button as the way back in. It was
     `display: none` until the win, so if the win never marked it the visitor
     who pressed Escape had no route to the form at all.
"""


def check(page, viewport, lang):
    tag = f"[{viewport} {lang}]"

    cells = page.locator(".cmp-cell")
    assert cells.count() == 9, f"{tag} the board built {cells.count()} cards, not 9"
    assert page.locator('.cmp-cell[data-face="back"]').count() == 9, \
        f"{tag} a card started face up"

    # The name is the position, never the prize. It also has to be translated:
    # an unresolved key here is a card that announces "card.back".
    name = page.eval_on_selector(
        '.cmp-cell[data-pos="1"] [data-role="label"]', "el => el.textContent.trim()")
    assert name and "card." not in name, f"{tag} card 1 announces {name!r}"

    # 1, 2, 3 — and the third opens the dialog on its own.
    for pos in (1, 2, 3):
        page.click(f'.cmp-cell[data-pos="{pos}"] .cmp-card')
        page.wait_for_timeout(120)

    assert page.evaluate("CMPCards.found()") == 3, f"{tag} the three turns did not count"

    page.wait_for_function("() => document.getElementById('tw-signup').open", timeout=10000)
    assert page.eval_on_selector("#cmp-grid", "el => el.dataset.phase") == "reveal", \
        f"{tag} the board did not go to its reveal phase"
    # The six open in a stagger that outlasts the dialog by design — the last
    # one lands about 80ms after the card is on screen — so this waits for the
    # sweep rather than sampling it mid-flight.
    page.wait_for_function(
        "() => !document.querySelector('.cmp-cell[data-face=\"back\"]')", timeout=5000)

    # Escape closes it, and the claim button is the way back in.
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    assert page.eval_on_selector("#cmp-claim", "el => getComputedStyle(el).display") != "none", \
        f"{tag} the claim button is still hidden after the win"

    page.click("#cmp-claim")
    page.wait_for_function("() => document.getElementById('tw-signup').open", timeout=5000)
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)
