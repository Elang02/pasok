"""Which SKUs carry an event, and which sleep through it.

A holiday does not lift a whole catalogue. The category table
(`data/demand/category_event_amplitude.csv`) says which categories move in which event
and what share of each category's SKUs actually carries the lift; the hash below turns
that share into a stable set of SKUs, so the same names appear on the page, in the answer
and in the replay.

The generator uses this to build sales, the ramp learner uses it to decide whose ramp is
worth fitting, and the console uses it to say how many SKUs move instead of "600".

Run nothing here; import it.
"""

from __future__ import annotations

import csv
import hashlib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "data" / "demand" / "category_event_amplitude.csv"

LEBARAN = {"Ramadan", "Lebaran", "Ramadan-Lebaran"}


@lru_cache(maxsize=1)
def table() -> dict[tuple[str, str], tuple[float, float]]:
    """(category, event) -> (amplitude, share)."""
    if not TABLE.exists():
        return {}
    out = {}
    for r in csv.DictReader(TABLE.open()):
        amp = float(r.get("amplitude") or 1.0)
        share = float(r.get("share") or 1.0)
        out[(r["category"].strip(), r["event"].strip())] = (amp, share)
    return out


def _keys(category: str, event: str):
    yield category, event
    if event in LEBARAN:
        yield category, "Ramadan-Lebaran"
    yield "default", event
    if event in LEBARAN:
        yield "default", "Ramadan-Lebaran"


def amplitude(category: str, event: str) -> float:
    for key in _keys(category, event):
        if key in table():
            return table()[key][0]
    return 1.0


def share(category: str, event: str) -> float:
    for key in _keys(category, event):
        if key in table():
            return table()[key][1]
    return 0.0


def carries(sku: str, category: str, event: str) -> bool:
    """True when this SKU is one of the ones the event actually moves."""
    frac = share(category, event)
    if frac <= 0.0 or amplitude(category, event) <= 1.0:
        return False
    if frac >= 1.0:
        return True
    h = int(hashlib.sha256(f"{sku}|{event}".encode()).hexdigest()[:8], 16) % 1000
    return h / 1000.0 < frac
