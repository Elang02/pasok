#!/usr/bin/env python3
"""
Pasok: UI truth gate
====================

A page is allowed to print a number only if that number is on disk. This gate reads
the served HTML and asserts every figure agrees with the artefact it claims to
describe. It exists because four pages spent a week saying "rekaman 28 Desember 2025"
while the pipeline had moved to 2026-10-11, and the demo page quoted 137 orders after
the loop had issued 145.

What it checks, per page:

  1. every data-fig value equals `web/figures.py` FIG[key]
  2. the masthead line equals the artefact's snapshot line
  3. no placeholder survived (`<!--SNAPSHOT-->`, `<!--LEARN_BARS-->`)
  4. no unresolved `data-fig` key (a typo would silently keep the stale literal)
  5. one type system per page: exactly one Google Fonts stylesheet
  6. one masthead, and none of the stray `class="nav"` the loop page used to carry

Run:  .venv/bin/python tools/ui_truth_gate.py            # against the live server
      .venv/bin/python tools/ui_truth_gate.py --port 8090
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "web"))

import figures                                                    # noqa: E402

CONSOLE_PAGES = ["/", "/orders", "/catalog", "/receiving", "/health", "/transfers", "/suppliers",
                 "/geography", "/panel", "/loop"]   # the console is the front door at "/"
DEMO_PAGE = "/demo"

FIG_RE = re.compile(r'data-fig="(?P<key>[a-z0-9_]+)"[^>]*>(?P<txt>[^<]*)<')
FONT_LINK_RE = re.compile(r'<link[^>]+fonts\.googleapis\.com[^>]*rel="stylesheet"')
PLACEHOLDER_RE = re.compile(r"<!--(SNAPSHOT|SNAPSHOT_SHORT|LEARN_BARS)-->")
STALE_DATE_RE = re.compile(r"28 Desember 2025")

failures: list[str] = []
checked = 0


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=15) as fh:
        return fh.read().decode("utf-8", "replace")


def check_page(name: str, html: str, is_demo: bool) -> None:
    global checked

    for m in PLACEHOLDER_RE.finditer(html):
        failures.append(f"{name}: placeholder {m.group(0)} survived to the response")

    if STALE_DATE_RE.search(html):
        failures.append(f"{name}: carries the stale date '28 Desember 2025'")

    fonts = FONT_LINK_RE.findall(html)
    if len(fonts) != 1:
        failures.append(f"{name}: {len(fonts)} Google Fonts stylesheets, expected 1")

    if not is_demo:
        line = figures.snapshot_line()
        if line not in html:
            failures.append(f"{name}: masthead is not '{line}'")
        mastheads = html.count('class="masthead"')
        if mastheads != 1:
            failures.append(f"{name}: {mastheads} mastheads, expected 1")
        if 'class="nav"' in html:
            failures.append(f'{name}: stray class="nav" outside the shared masthead')

    figs = FIG_RE.findall(html)
    if is_demo and not figs:
        failures.append(f"{name}: no data-fig values at all, the page is unbound again")

    for key, txt in figs:
        checked += 1
        want = figures.FIG.get(key)
        if want is None:
            failures.append(f"{name}: data-fig={key!r} is not a known figure")
        elif txt != want:
            failures.append(f"{name}: data-fig={key!r} shows {txt!r}, artefact says {want!r}")

    if is_demo and 'data-ui' in html and re.search(r'class="bar', html) is None:
        failures.append(f"{name}: the bars block is empty")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    base = f"http://{args.host}:{args.port}"

    print(f"UI truth gate against {base}")
    print(f"  artefact snapshot line: {figures.snapshot_line()}")
    print("-" * 72)

    for path in CONSOLE_PAGES + [DEMO_PAGE]:
        url = base + path
        try:
            html = get(url)
        except (urllib.error.URLError, OSError) as exc:
            failures.append(f"{path}: unreachable ({exc})")
            print(f"  FAIL {path:8s} unreachable")
            continue
        before = len(failures)
        check_page(path, html, path == DEMO_PAGE)
        status = "ok  " if len(failures) == before else "FAIL"
        print(f"  {status} {path:8s} {len(html):>7,} bytes")

    print("-" * 72)
    if failures:
        print(f"{len(failures)} problem(s):")
        for f in failures:
            print("  -", f)
        return 1
    print(f"all pages agree with the artefacts ({checked} figures checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
