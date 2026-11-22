#!/usr/bin/env python3
"""
Pasok: UI system gate
=====================

A gate for the shape of the console, not its wording and not its data. It exists
because the four console pages drifted apart in ways nobody chose: one content box
was 980px wide, another 860, two were 1080, so switching tabs slid the page 110px
sideways. One page carried a bare `nav { }` rule that restyled the shared masthead,
one padded its own header, one put the masthead inside the content box so the header
changed width when you left the page. All of it passed every other check.

Static, so it runs anywhere (no browser, no server):

  1. every console page links the one shared stylesheet
  2. no page sets its own max-width on `.wrap` or `.sheet`
  3. the masthead is not nested inside the content container
  4. no bare element selectors that reach outside their page (`nav {`, `header {`)
  5. one font request per page, and it is the shared one
  6. no light-theme leftovers (the console is a dark ground now)
  7. no old faces left behind (Newsreader, Switzer)

Run:  .venv/bin/python tools/ui_system_gate.py [web]
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

CONSOLE = ["chat.html", "orders.html", "receiving.html", "health.html",
           "transfers.html", "suppliers.html", "geography.html", "catalog.html", "panel.html",
           "loop.html"]   # chat.html is at "/"
SHARED_SHEET = "/pasok.css"
SHARED_FACES = ("Bricolage Grotesque", "IBM Plex Mono")
DEAD_FACES = ("Newsreader", "Switzer", "Fraunces", "JetBrains")
# element selectors that leak out of a page and restyle the shared chrome
BARE_LEAKS = re.compile(r"^\s*(nav|header|footer|body|html)\s*(?:,|\{)", re.M)
LIGHT_LEFTOVERS = re.compile(r"oklch\(\s*(?:9[0-9]|8[0-9]|7[0-9])\s*%|#(?:fff|ffffff|fefefe|f7f7f7)\b", re.I)
OWN_WIDTH = re.compile(r"\.(wrap|sheet)[^{]*\{[^}]*max-width", re.S)

failures: list[str] = []


def style_block(html: str) -> str:
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S))


def check(path: pathlib.Path, root: pathlib.Path) -> None:
    name = path.name
    html = path.read_text()
    css = style_block(html)

    if SHARED_SHEET not in html:
        failures.append(f"{name}: does not link {SHARED_SHEET}")

    if OWN_WIDTH.search(css):
        failures.append(f"{name}: sets its own max-width on .wrap or .sheet, "
                        "which is how the content edges stopped lining up")

    head = html.find('<header class="masthead"')
    content = min([i for i in (html.find('<main class="sheet"'), html.find('<div class="wrap"'))
                   if i >= 0] or [-1])
    if head < 0:
        failures.append(f"{name}: no shared masthead")
    elif content >= 0 and head > content:
        failures.append(f"{name}: the masthead sits inside the content container, "
                        "so the header changes width when you leave this page")

    for m in BARE_LEAKS.finditer(css):
        failures.append(f"{name}: bare `{m.group(1)}` selector in the page stylesheet "
                        "restyles the shared chrome")

    links = re.findall(r'<link[^>]+fonts\.googleapis\.com[^>]*rel="stylesheet"', html)
    if len(links) != 1:
        failures.append(f"{name}: {len(links)} font requests, expected 1")
    # the request writes the face with a plus, so normalise before matching
    requested = " ".join(links).replace("+", " ")
    for face in SHARED_FACES:
        if face not in requested:
            failures.append(f"{name}: font request is missing {face}")
    for face in DEAD_FACES:
        if face in html:
            failures.append(f"{name}: still references the retired face {face}")

    left = LIGHT_LEFTOVERS.findall(css)
    if left:
        failures.append(f"{name}: {len(left)} light-theme leftover(s) in the page stylesheet")


def main(argv: list[str]) -> int:
    target = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT / "web"
    targets = [target / n for n in CONSOLE] if target.is_dir() else [target]

    print("UI system gate")
    print("-" * 72)
    for path in targets:
        if not path.exists():
            failures.append(f"{path}: missing")
            continue
        before = len(failures)
        check(path, target)
        print(f"  {'ok  ' if len(failures) == before else 'FAIL'} {path.name}")

    sheet = target / "pasok.css"
    if sheet.exists():
        css = sheet.read_text()
        for token in ("--page-width", "--color-paper", "--color-accent", "--font-body"):
            if token not in css:
                failures.append(f"pasok.css: {token} is not declared")
        if ".sheet," not in css or ".wrap" not in css:
            failures.append("pasok.css: .sheet and .wrap are not declared together")

    print("-" * 72)
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print("  -", f)
        return 1
    print("one sheet, one container, one face, one masthead: the console is consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
