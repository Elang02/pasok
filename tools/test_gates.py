"""Force every human gate with a synthetic line, so "it is wired" is not the proof.

Run: .venv/bin/python tools/test_gates.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "agents"))

from order_executor import gate_reasons  # noqa: E402


def line(**over) -> dict:
    base = {
        "sku": "SKU0001",
        "principal_id": "P01",
        "abc_class": "A",
        "volume_m3": 1.0,
        "value_idr": 10_000_000.0,
        "credit_limit_idr": 50_000_000.0,
        "min_order_units": 144.0,
        "guarded_order": 500.0,
        "cover_after_days": 20.0,
        "shelf_days": 180.0,
        "event": "",
        "event_mult": 1.0,
        "peak_mult": 1.2,
        "principal_id": "P01",
        "category": "biskuit",
        "switch_to_principal": "",
        "switch_incumbent_fill": 0.0,
        "switch_alt_fill": 0.0,
    }
    base.update(over)
    return base


def ctx(**over) -> dict:
    base = dict(remaining=10_000.0, prin_units={"P01": 500.0}, cover={"SKU0001": 30.0},
                lead={"SKU0001": 7.0}, peak_rate={"SKU0001": 25.0})
    base.update(over)
    return base


CASES = [
    ("clean line issues itself", line(), ctx(), 0, False, None),
    ("space", line(volume_m3=20_000.0), ctx(), 1, False, "warehouse headroom"),
    # A person signs off when the order is bigger than the item's own peak can absorb:
    # 25 a day x 20 days x 1.05 tolerance = 525. 600 is past it; 500 is not.
    ("above peak", line(guarded_order=600.0), ctx(), 1, False, "above_peak"),
    ("inside the peak envelope", line(guarded_order=500.0), ctx(), 0, False, None),
    ("moq deferred", line(min_order_units=900.0), ctx(prin_units={"P01": 100.0}), 1, True, "deferred one cycle"),
    ("moq blocked", line(min_order_units=900.0), ctx(prin_units={"P01": 100.0}, cover={"SKU0001": 5.0}), 1, False, "cover cannot wait"),
    ("supplier switch", line(guarded_order=300.0,
                             switch_to_principal="P02", switch_incumbent_fill=0.84,
                             switch_alt_fill=0.98), ctx(), 1, False, "supplier_switch"),
    # Overstock, near expiry and event overreach are no longer hold gates: the position cap in
    # src/agents/decision.py shrinks the order instead (phase 30), so the replay is where those
    # three are measured. Holding them here would test a rule the build no longer runs.
    ("candidate event", line(event_mult=1.3), ctx(), 1, False, "candidate_event"),
    ("demand shock", line(event_mult=2.5), ctx(), 2, False, "demand_shock"),
]

failures = []
for case in CASES:
    name, r, c, want_n, want_deferred, needle = case[:6]
    cap = case[6] if len(case) > 6 else 30.0
    reasons, deferred = gate_reasons(r, class_cap=cap, **c)
    ok = len(reasons) == want_n and deferred is want_deferred
    if needle:
        ok = ok and any(needle in x for x in reasons)
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failures.append((name, reasons, deferred))

if failures:
    for f in failures:
        print(f)
    raise SystemExit(1)
print(f"PASS  {len(CASES)} gate cases")
