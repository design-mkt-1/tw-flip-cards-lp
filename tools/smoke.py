#!/usr/bin/env python3
"""Drive the page in a real browser and fail on the things text checks cannot see.

Generalised from tw-flip-cards-lp/tools/smoke.py, which earned four of the
assertions below the hard way. They are kept because both bugs they exist for
are template-wide, not campaign-specific.

Serves the repo from a loopback SimpleHTTPRequestHandler on a random port, so
nothing here needs a build, a deploy, or the network.

Run:
    python -m pip install playwright && python -m playwright install chromium
    python tools/smoke.py
    python tools/smoke.py --headed        # watch it

A campaign adds its own assertions in campaign/smoke.py, exposing
`def check(page, viewport, lang):`. This file imports it if it exists and
calls it once per viewport per language.
"""

import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

# Windows consoles still default to cp1252, and these tools report Ukrainian
# and Russian copy back to the user. Without this the report itself crashes on
# the first Cyrillic character -- which turns a real finding into a traceback.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent

VIEWPORTS = [("desktop", 1440, 900), ("mobile", 375, 812)]

# Ignore-list for console noise a campaign is entitled to produce. The
# unwired-form notice is the template's own and is deliberately loud.
CONSOLE_OK = ("not wired to anything",)


def serve():
    class Quiet(socketserver.TCPServer):
        allow_reuse_address = True

        def handle_error(self, request, client_address):
            pass

    class Silent(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    server = Quiet(("127.0.0.1", 0),
                   functools.partial(Silent, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def languages():
    """The campaign's own list, read out of campaign.js without running it."""
    text = (ROOT / "campaign.js").read_text(encoding="utf-8")
    start = text.find("languages:")
    if start < 0:
        return ["ua"]
    chunk = text[start:text.find("]", start)]
    return [bit.strip().strip("'\"") for bit in chunk.split("[")[1].split(",") if bit.strip()]


class Failures(list):
    def check(self, condition, message):
        if not condition:
            self.append(message)


def run_page(page, where, lang, fails):
    tag = f"[{where} {lang}]"

    # 1. The shell mounted. Proves js/shell.js ran and index.html still has
    #    its two mount points -- the one thing a campaign can break in a file
    #    it is allowed to edit.
    for sel, what in ((".tw-hdr", "header"), (".tw-ftr", "footer")):
        box = page.locator(sel).bounding_box()
        fails.check(box and box["width"] > 0 and box["height"] > 0,
                    f"{tag} the {what} did not mount ({sel} has no box)")

    # 2. The page opens where it was written to open.
    fails.check(page.evaluate("window.scrollY") == 0, f"{tag} the page did not open at the top")

    # 3. Nothing is left in flow below the footer. Deliberately not
    #    dialog-aware: it catches anything that parks itself under the last
    #    thing the visitor is meant to see.
    over = page.evaluate("""() => {
        const f = document.querySelector('.tw-ftr');
        const bottom = f ? f.getBoundingClientRect().bottom + window.scrollY : 0;
        return document.documentElement.scrollHeight
             - Math.max(bottom, window.innerHeight);
    }""")
    fails.check(over <= 1, f"{tag} {over}px of page sits below the footer")

    # 4. The closed dialog computes display:none, so the UA's own
    #    `dialog:not([open])` rule is not being beaten by a class. When it was,
    #    the page carried 650px of apparent emptiness and an autofocus that
    #    scrolled to the footer.
    fails.check(
        page.eval_on_selector("#tw-signup", "el => getComputedStyle(el).display") == "none",
        f"{tag} the closed dialog is not display:none")

    # 5. No unresolved key. Catches a campaign that added a string in one
    #    locale and forgot another: the fallback chain ends at the key itself.
    unresolved = page.evaluate("""() => [...document.querySelectorAll('[data-i18n]')]
        .filter(el => el.textContent.trim() === el.getAttribute('data-i18n'))
        .map(el => el.getAttribute('data-i18n'))""")
    fails.check(not unresolved, f"{tag} untranslated key(s): {', '.join(unresolved)}")

    # 6. No dead links. An unset seam leaves NO href; href="#" is a control
    #    that takes focus, is announced as a link and then does nothing.
    dead = page.evaluate("""() => [...document.querySelectorAll('a[href]')]
        .filter(a => { const h = a.getAttribute('href'); return !h || h === '#'; })
        .map(a => a.className || a.textContent.trim().slice(0, 24))""")
    fails.check(not dead, f"{tag} dead link(s) with href=\"#\": {', '.join(dead)}")

    # 7. The dialog works: opens, takes focus, Escape closes it, focus returns.
    page.evaluate("TW.openForm()")
    page.wait_for_timeout(350)
    fails.check(page.eval_on_selector("#tw-signup", "el => el.open"),
                f"{tag} TW.openForm() did not open the dialog")
    fails.check(page.evaluate(
        "document.getElementById('tw-signup').contains(document.activeElement)"),
        f"{tag} focus did not move into the open dialog")

    # 8. The language survives the dialog. i18n.apply(root) exists precisely
    #    because this class of bug is real.
    others = [c for c in page.evaluate("TW.config.languages") if c != lang]
    if others:
        page.evaluate(f"TW.setLang('{others[0]}')")
        page.wait_for_timeout(120)
        fails.check(page.inner_text(".tw-promo__title").strip() != "",
                    f"{tag} the promo block emptied after a language change")
        page.evaluate(f"TW.setLang('{lang}')")

    page.keyboard.press("Escape")
    page.wait_for_timeout(350)
    fails.check(not page.eval_on_selector("#tw-signup", "el => el.open"),
                f"{tag} Escape did not close the dialog")

    # 9. Every tap target is at least 24x24. WCAG 2.2 target size (minimum).
    small = page.evaluate("""() => [...document.querySelectorAll(
        'a[href], button, input, [role=option], [role=tab]')]
        .filter(el => { const r = el.getBoundingClientRect();
                        return r.width > 0 && (r.width < 24 || r.height < 24); })
        .map(el => (el.className || el.tagName) + ` ${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)}`)""")
    fails.check(not small, f"{tag} tap target(s) under 24px: {'; '.join(small)}")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("smoke: playwright is not installed.\n"
              "  python -m pip install playwright\n"
              "  python -m playwright install chromium", file=sys.stderr)
        return 1

    campaign_check = None
    campaign_smoke = ROOT / "campaign" / "smoke.py"
    if campaign_smoke.is_file():
        sys.path.insert(0, str(ROOT / "campaign"))
        import smoke as campaign_module          # noqa: E402
        campaign_check = getattr(campaign_module, "check", None)

    server, port = serve()
    fails = Failures()
    langs = languages()
    headed = "--headed" in sys.argv[1:]

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        for where, w, h in VIEWPORTS:
            for lang in langs:
                page = browser.new_page(viewport={"width": w, "height": h})
                noise = []
                page.on("console", lambda m, n=noise: n.append(f"{m.type}: {m.text}")
                        if m.type in ("error", "warning") else None)
                page.on("pageerror", lambda e, n=noise: n.append(f"pageerror: {e}"))

                page.goto(f"http://127.0.0.1:{port}/index.html?lang={lang}")
                page.wait_for_timeout(500)

                run_page(page, where, lang, fails)
                if campaign_check:
                    campaign_check(page, where, lang)

                real = [n for n in noise if not any(ok in n for ok in CONSOLE_OK)]
                fails.check(not real, f"[{where} {lang}] console: {' | '.join(real)}")
                page.close()
        browser.close()

    server.shutdown()

    if fails:
        print(f"smoke: {len(fails)} failure(s)\n")
        for f in fails:
            print("  " + f)
        return 1

    print(f"smoke: {len(VIEWPORTS)} viewport(s) x {len(langs)} language(s), all clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
