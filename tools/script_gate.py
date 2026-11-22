#!/usr/bin/env python3
"""Check that the talk script fits the clock and quotes numbers the deck or the data can back.

Three questions, in order:

1. Does every section fit the seconds it is given, at a speakable pace?
2. Is every number in the spoken text a number that exists in the deck or in the artefacts?
3. Does the script still describe thirteen pages, or has the deck moved under it?

Run from the repository root: `.venv/bin/python tools/script_gate.py`
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "demo/TALK_SCRIPT.md"
DECK_JSON = ROOT / "demo/deck/deck_text.json"

# Sections hold a heading "## m:ss — Page N, title (Xs, about Y words)" and spoken text until "---".
HEAD = re.compile(
    r"^##\s+(\d+):(\d{2})\s+[—-]\s+Page\s+(\d+),\s*(.*?)\s*\((\d+)\s*s,\s*about\s*(\d+)\s*words\)"
)
NUMBER = re.compile(
    r"(?<![\w.])(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:\.\d+)?)"
    r"\s*(percent|times|days|units|SKUs|SKU|bn|billion|rupiah|receipts|holidays|outlets|spikes|"
    r"seconds|rows|points?|dollars)?"
)

PACE_MIN, PACE_MAX = 124, 158        # words a minute that still sound like speech
SLACK = 0.18                          # a section may run this much over or under its slot

# Numbers that exist only inside the page-7 capture, which is a picture, not text.
IN_PICTURE = {
    "7,500", "4,972", "3,340", "407", "98", "31", "18", "7", "6",
}

# Numbers that are spoken as words rather than digits.
WORDS = {
    "thirteen": 13, "six hundred": 600, "twelve": 12, "thousand": 1000,
    "hundred eighty-seven": 587, "five hundred": 500,
}


def spoken_words(spoken: str) -> int:
    """Words a speaker has to say: letters, and a number counts as one word however it is written."""
    letters = re.findall(r"[A-Za-z][A-Za-z'’-]*", spoken)
    numbers = re.findall(r"(?<![\w.])\d[\d.,]*", spoken)
    return len(letters) + len(numbers)


def sections(text: str) -> list[dict]:
    out, cur = [], None
    for line in text.splitlines():
        m = HEAD.match(line.strip())
        if m:
            cur = {
                "min": int(m.group(1)), "sec": int(m.group(2)), "page": int(m.group(3)),
                "title": m.group(4), "slot": int(m.group(5)), "claimed": int(m.group(6)), "body": [],
            }
            out.append(cur)
        elif line.strip() == "---":
            cur = None
        elif cur is not None:
            cur["body"].append(line)
    for s in out:
        spoken = " ".join(l.strip() for l in s["body"] if l.strip() and not l.startswith("*"))
        s["words"] = spoken_words(spoken)
        s["spoken"] = spoken
    return out


def deck_text() -> str:
    """The words on the slides, read straight out of the pptx the talk is given over."""
    deck = ROOT / "demo/deck/Pasok_DemoDay_2026.pptx"
    try:
        from pptx import Presentation
    except ImportError:
        return DECK_JSON.read_text() if DECK_JSON.exists() else ""
    if not deck.exists():
        return ""
    out: list[str] = []
    for slide in Presentation(str(deck)).slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    out += [cell.text for cell in row.cells]
    return "\n".join(out)


def deck_numbers() -> set[str]:
    raw = deck_text()
    if not raw:
        return set()
    found = set()
    for m in re.finditer(r"\d[\d.,]*", raw):
        found.add(m.group(0))
        found.add(m.group(0).replace(",", ""))
    return found


def data_numbers() -> set[str]:
    """Every number in the artefacts the deck was built from, as written and normalised."""
    seen = set()
    paths: list[Path] = []
    for pat in ("data/**/*.json", "data/**/*.csv", "simulation/*.json", "experiments/*.json"):
        paths += sorted(ROOT.glob(pat))
    for path in paths:
        if path.stat().st_size > 2_000_000:      # the sales and receipt dumps hold nothing a talk cites
            continue
        raw = path.read_text(errors="ignore")
        for m in re.finditer(r"-?\d[\d.,]*", raw):
            tok = m.group(0).rstrip(".,")
            seen.add(tok)
            seen.add(tok.replace(",", ""))
            try:
                val = float(tok.replace(",", ""))
            except ValueError:
                continue
            seen.add(f"{val:.2f}".rstrip("0").rstrip("."))
            seen.add(f"{val:.1f}".rstrip("0").rstrip("."))
            seen.add(f"{val:.0f}")
    return seen


def rewrite_doc(text: str, pace: int = 135) -> str:
    """Set every heading and the clock table from the words actually there, at a speakable pace."""
    lines = text.splitlines()
    rows: list[dict] = []
    clock = 0
    out: list[str] = []
    pending: list[dict] = []
    cur = None
    for line in lines:
        m = HEAD.match(line.strip())
        if m:
            cur = {"page": int(m.group(3)), "title": m.group(4), "body": []}
            pending.append(cur)
            out.append(line)                     # heading is rewritten in a second pass
            continue
        if line.strip() == "---":
            cur = None
        elif cur is not None:
            cur["body"].append(line)
        out.append(line)

    for sec in pending:
        spoken = " ".join(l.strip() for l in sec["body"] if l.strip())
        sec["words"] = spoken_words(spoken)
        sec["secs"] = max(20, 5 * math.ceil(sec["words"] / pace * 60 / 5))
        sec["start"] = clock
        clock += sec["secs"]

    # second pass: headings
    idx = 0
    for i, line in enumerate(out):
        if HEAD.match(line.strip()):
            sec = pending[idx]
            idx += 1
            out[i] = (f"## {sec['start'] // 60}:{sec['start'] % 60:02d} — Page {sec['page']}, "
                      f"{sec['title']} ({sec['secs']} s, about {sec['words']} words)")

    # third pass: the clock table between its header and the closing rule
    start_tbl = next(i for i, l in enumerate(out) if l.startswith("| Time | Page |"))
    end_tbl = next(i for i in range(start_tbl, len(out)) if out[i].strip() == "---")
    table = [
        out[start_tbl], out[start_tbl + 1],
        *[f"| {s['start'] // 60}:{s['start'] % 60:02d} | {s['page']} {s['title']} | {s['secs']} | "
          f"{s['words']} |" for s in pending],
        f"| {clock // 60}:{clock % 60:02d} | buffer | {900 - clock} | |",
        "",
    ]
    return "\n".join(out[:start_tbl] + table + out[end_tbl:]) + "\n"


def main() -> int:
    if "--rewrite" in sys.argv[1:]:
        before = SCRIPT.read_text()
        after = rewrite_doc(before)
        SCRIPT.write_text(after)
        print(f"rewrote {SCRIPT.name}: {len(before.split())} words in, {len(after.split())} out")

    text = SCRIPT.read_text()
    rows = sections(text)
    known = deck_numbers() | data_numbers()
    problems: list[str] = []
    total_words = sum(s["words"] for s in rows)

    print(f"{SCRIPT.name}: {len(rows)} sections, {total_words} spoken words")
    for s in rows:
        wpm = s["words"] / (s["slot"] / 60)
        drift = (s["words"] - s["claimed"]) / max(s["claimed"], 1)
        flag = ""
        if not PACE_MIN <= wpm <= PACE_MAX:
            flag = f"  <-- {wpm:.0f} words a minute"
            problems.append(f"page {s['page']}: {wpm:.0f} wpm does not fit {s['slot']} s")
        if abs(drift) > SLACK:
            flag += f"  (claims {s['claimed']} words, has {s['words']})"
            problems.append(f"page {s['page']}: {s['words']} words vs {s['claimed']} claimed")
        print(f"  {s['min']}:{s['sec']:02d}  page {s['page']:>2}  {s['words']:>3} words"
              f"  {wpm:>3.0f} wpm{flag}")

    pages = sorted(s["page"] for s in rows)
    if pages != list(range(1, len(pages) + 1)):
        problems.append(f"script pages are {pages}, not 1..{len(pages)}")

    unknown: list[str] = []
    for s in rows:
        for m in NUMBER.finditer(s["spoken"]):
            tok = m.group(1)
            unit = (m.group(2) or "").lower()
            if not unit:                     # a bare number is usually a page or a list item
                continue
            forms = {tok, tok.replace(",", ""), tok.replace(".", "")}
            if forms & (known | IN_PICTURE):
                continue
            unknown.append(f"page {s['page']}: {tok} {unit}")
    if unknown:
        print(f"\n{len(unknown)} numbers the deck and the artefacts cannot back:")
        for u in unknown[:20]:
            print("  " + u)
        problems.append(f"{len(unknown)} unbacked numbers")

    total_s = sum(s["slot"] for s in rows)
    print(f"\ntotal speaking time {total_s // 60}:{total_s % 60:02d} "
          f"({total_s} s for {total_words} words, {total_words / (total_s / 60):.0f} wpm)")
    if total_s > 900:
        problems.append(f"{total_s} s does not fit a fifteen-minute slot")

    if problems:
        print("\nthe script and the clock do not agree yet:")
        for p in problems:
            print("  - " + p)
        return 1
    print("\nevery section fits its slot, and every number it speaks is in the deck or the data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
