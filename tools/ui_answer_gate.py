#!/usr/bin/env python
"""
Pasok — answer gate: the buyer never reads machine output, jargon or filler.

The pages are checked by `ui_lang_gate.py`. This one checks what the agent SAYS, which
is a different surface: the six answers are built in `pasok_answers.py` and the panel's
recommendations come from a model, so a page-level pass cannot see either.

Contract: `docs/PLAIN_LANGUAGE.md`.

Run
---
    cd <repo root>
    .venv/bin/python tools/ui_answer_gate.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pasok_answers as ans  # noqa: E402

# A stored value leaked to the reader. Every one of these was seen in a real answer.
LEAKS = [
    (re.compile(r"\bnan\b", re.I), "a missing value printed as nan"),
    (re.compile(r"\bNone\b"), "a Python None printed"),
    (re.compile(r"->|<-|=>"), "an arrow instead of a sentence"),
    (re.compile(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b"), "a stored code (HOLD_ONE_CYCLE)"),
    (re.compile(r"\b(OTIF|WAPE)\b"), "an abbreviation the buyer must translate"),
    (re.compile(r"\*\*Rationale\.\*\*"), "the machine key instead of 'Why:'"),
    (re.compile(r"\d[\d,.]*\s?u\b"), "a unit suffix (17521.3u)"),
    (re.compile(r"\bx\d+\.\d+"), "a multiplier (x1.40)"),
    (re.compile(r"\b(AUTO_ISSUED|FULL|PARTIAL|ESCALATED)\b"), "an acceptance value"),
    (re.compile(r"[\u2014\u2013]"), "an em dash or en dash"),
    (re.compile(r";[ \t]+[A-Za-z]"), "a semicolon in prose"),
    # A labelled zero the reader cannot act on. "Value of the stock that runs out: IDR 0"
    # was a real line in the stockout answer: the stock does run out, and the zero only
    # meant none of it runs out before the next delivery.
    (re.compile(r"(?::|\bis\b)\s*(?:IDR|Rp)\s*0\b"), "a zero that tells the reader nothing"),
]

# An answer has to carry what the question asked for. These are requirements, not bans:
# the answer to "what is the nearest event" was an event name with no date anywhere in it.
REQUIREMENTS = [
    ("an event question",
     lambda name: "event" in name,
     [(re.compile(r"\b\d{1,2} \w+ \d{4}\b"), "no date, and an event without a date "
                                                 "is not an answer"),
      (re.compile(r"\b\d+ days?\b"), "no distance in days from this snapshot")]),
    ("a stock question",
     lambda name: "runs out" in name,
     [(re.compile(r"\bIDR [\d,]+\b"), "nothing the reader can attach a cost to")]),
]

# The proposal uses these words and the judges know them. An answer body may not, because
# the answer is what a buyer reads. Labels on a figure are fine, sentences are not.
JARGON = [
    (re.compile(r"\bguardrail", re.I), "say 'order rule'"),
    (re.compile(r"\bvelocity\b", re.I), "say 'sells per day'"),
    (re.compile(r"\bsellable\b", re.I), "say 'available now'"),
    (re.compile(r"\bdays of cover\b", re.I), "say 'days of stock left'"),
    (re.compile(r"\blead( | )?(p90|time)\b", re.I), "say 'delivery time'"),
    (re.compile(r"\bamplification\b", re.I), "say 'how much orders swing'"),
    (re.compile(r"\buplift\b", re.I), "say 'times normal'"),
    (re.compile(r"\bexception queue\b", re.I), "say 'SKUs waiting for a person'"),
    (re.compile(r"\bescalat", re.I), "say 'waiting for a person'"),
    (re.compile(r"\bauto-issued\b", re.I), "say 'placed without a person'"),
    (re.compile(r"\bpeak multiplier\b", re.I), "say 'times normal at peak'"),
]

# An answer that says one of these is not real information.
FILLER = [
    (re.compile(r"(?:^|[.!?]\s)(So|Thus|Therefore)[, ]"), "a filler connective that opens a sentence"),
    (re.compile(r"\bin conclusion\b|\boverall,\b|\bit is worth noting\b", re.I), "filler"),
    (re.compile(r"\bas an AI\b|\bI (think|believe)\b", re.I), "the assistant talking about itself"),
]

CASES = [
    ("network summary", lambda: ans.summary()),
    ("SKU waiting for a person", lambda: ans.exceptions()),
    ("runs out within a week", lambda: ans.stockout_within_a_week()),
    ("spike within a month", lambda: ans.spike_within_a_month()),
    ("why SKU0536", lambda: ans.sku_decision("SKU0536")),
    ("a SKU with no decision", lambda: ans.sku_decision("SKU9999")),
    ("order PO-0001", lambda: ans.order_status("PO-0001")),
    ("an order that is not there", lambda: ans.order_status("PO-0349")),
    ("the nearest event", lambda: ans.event_impact("")),
    ("a named event", lambda: ans.event_impact("Lebaran")),
    ("an event we do not know", lambda: ans.event_impact("Waisak")),
    ("supplier reliability", lambda: ans.supplier_reliability()),
    ("forecast accuracy", lambda: ans.forecast_accuracy()),
]


def main() -> int:
    bad = 0
    for name, fn in CASES:
        try:
            text = fn() or ""
        except Exception as e:  # a crash is a finding, not a stack trace for the reader
            print(f"FAIL  {name}: raised {type(e).__name__}: {e}")
            bad += 1
            continue
        for group, rules in (("leak", LEAKS), ("jargon", JARGON), ("filler", FILLER)):
            for rx, why in rules:
                for m in rx.finditer(text):
                    a = max(0, m.start() - 45)
                    b = min(len(text), m.end() + 45)
                    ctx = text[a:b].replace("\n", " ")
                    print(f"FAIL  {name} [{group}] {why}\n      ...{ctx}...")
                    bad += 1
        if len(text.strip()) < 20:
            print(f"FAIL  {name}: the answer is empty")
            bad += 1
        for label, applies, rules in REQUIREMENTS:
            if not applies(name):
                continue
            for rx, why in rules:
                if not rx.search(text):
                    print(f"FAIL  {name} [{label}] {why}")
                    bad += 1
    # The nearest event has to be the nearest one. The answer defaulted to Lebaran, which
    # is the fifth nearest at 156 days, while Christmas sat 72 days away.
    cal = ans._event_calendar()
    if cal:
        near = cal[0]
        t = ans.event_impact("")
        if near["event"] not in t or f"{near['date']:%d %B %Y}" not in t:
            print(f"FAIL  the nearest event: the calendar says {near['event']} on "
                  f"{near['date']:%d %B %Y}, and the answer does not")
            bad += 1
    print("-" * 72)
    if bad:
        print(f"{bad} finding(s): the reader is seeing machine output, jargon or filler")
        return 1
    print(f"all {len(CASES)} answers read as plain language about real numbers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
