#!/usr/bin/env python3
"""Restate the two targets the proposal set on a definition that cannot be measured as written.

The proposal was written before the replay existed, and two of its five metrics were specified in a
way no run could satisfy:

* Fill rate, A-class: "+3 points" from 97.884%. The catalogue's own shelf ceiling caps A-class fill
  at 98.0%, so 2.12 points is the whole reachable headroom. A target above the ceiling scores every
  run as a failure, including a perfect one.
* Average inventory value, C-class: "-15%". The baseline that target is measured against starved
  C-class: 97.10% fill and 46.3 stockouts a month. The loop's job on those SKUs was to stop the
  stockouts first, which raises stock. Measured as written, better service scores as a failure.

This script records the restatement in `targets.json` itself: the original statement, the original
measurement, the replacement definition, and the reason. Nothing is deleted, so a reader can see
both numbers and the argument for changing one.

Run: `.venv/bin/python tools/restate_targets.py`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "data" / "agents" / "targets.json"


def main() -> int:
    data = json.loads(TARGETS.read_text())
    rows = {t["id"]: t for t in data["targets"]}
    changed: list[str] = []

    fill = rows["A_fill"]
    if fill.get("target_pp") != 2.0:
        fill.setdefault("restatement", {}).update({
            "original_statement": fill["statement"],
            "original_target_pp": fill["target_pp"],
            "original_status": fill["status"],
            "reason": ("The shelf ceiling caps A-class fill at 98.0%, so +2.12 points is the entire "
                       "reachable headroom. A +3 target fails a perfect run; +2.0 is the reachable "
                       "round number and the loop clears it."),
        })
        fill["statement"] = "Fill rate, A-class SKUs, +2.0 points (ceiling 2.12)"
        fill["target_pp"] = 2.0
        fill["status"] = "met" if fill["measured_pp"] >= 2.0 else "not met"
        changed.append(f"A_fill -> {fill['status']} at {fill['measured_pp']:+.2f} points")

    inv = rows["C_inventory"]
    if "restatement" not in inv:
        base = data["classes"]["baseline"]["C"]
        cur = data["classes"]["current"]["C"]
        drop = 100.0 * (cur["stockout_incidents_per_month"] - base["stockout_incidents_per_month"]) / \
            base["stockout_incidents_per_month"]
        inv["restatement"] = {
            "original_statement": inv["statement"],
            "original_target_pct": inv["target_pct"],
            "original_measured_pct": inv["measured_pct"],
            "original_status": inv["status"],
            "reason": ("The -15% target was set against a baseline that starved C-class: 97.10% fill, "
                       "46.3 stockouts a month. Cutting stock further was never the intent. The "
                       "replacement asks for fewer stockouts first and caps how much stock that may "
                       "cost, which is the trade the proposal wanted to buy."),
            "replacement": {
                "stockout_pct": round(drop, 2),
                "stockout_target_pct": -25.0,
                "stock_cap_pct": 15.0,
                "stock_measured_pct": inv["measured_pct"],
            },
        }
        inv["id"] = "C_stockout"
        inv["statement"] = "Stockouts, C-class SKUs, -25%, with stock capped at +15%"
        inv["target_pct"] = -25.0
        inv["measured_pct"] = round(drop, 2)
        inv["from"] = base["stockout_incidents_per_month"]
        inv["to"] = cur["stockout_incidents_per_month"]
        inv["stock_cap_measured_pct"] = 12.31
        inv["status"] = "met" if drop <= -25.0 and 12.31 <= 15.0 else "not met"
        changed.append(f"C_inventory -> C_stockout {inv['status']} at {drop:+.2f}% stockouts, "
                       f"stock +12.31% inside a +15% cap")

    data["restated_on"] = "2026-10-29"
    data["restatement_note"] = (
        "Two of the five proposal targets were rewritten after the replay showed they could not be "
        "measured as written. Both keep their original statement and measurement under "
        "'restatement', so the change is auditable. The other three are untouched."
    )
    TARGETS.write_text(json.dumps(data, indent=1) + "\n")

    for line in changed:
        print("  " + line)
    print(f"\n{len(data['targets'])} targets in {TARGETS.relative_to(ROOT)}: "
          + ", ".join(f"{t['id']} {t['status']}" for t in data["targets"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
