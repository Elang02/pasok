#!/usr/bin/env python3
"""
Credit limits: are they sized to the goods?
===========================================

Elang's point: a credit limit should scale with how fast a SKU turns over, not be a flat
pick from four round numbers. Measure the gap, then show what a demand-proportional limit
would do to the auto/escalation split.

Run: .venv/bin/python tools/credit_sizing.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT = ROOT / "data/catalog"
STK = ROOT / "data/stock"
ORD = ROOT / "data/orders"
AG = ROOT / "data/agents"

AUTO_LIMIT = 200_000_000
ZMULT = 1.28          # 90% service, same constant the Decision Agent uses
LEAD_FALLBACK = 10    # days


def main() -> int:
    cat = pd.read_csv(CAT / "catalog.csv")
    snap = pd.read_csv(STK / "position_snapshot.csv")[["sku", "velocity_units_day", "lead_time_days"]]
    rec = pd.read_csv(CAT / "receiving.csv")
    lead_p90 = rec.groupby("principal_id")["actual_lead_d"].quantile(0.9).round(0)

    d = cat.merge(snap, on="sku", how="left")
    d["lead_p90"] = d["principal_id"].map(lead_p90).fillna(LEAD_FALLBACK)

    # ---------- 1. the current limits have nothing to do with the goods
    d["need_cycle_idr"] = d.velocity_units_day * d.lead_p90 * d.unit_cost_idr
    d["ratio"] = d.credit_limit_idr / d.need_cycle_idr.replace(0, np.nan)

    print("=" * 84)
    print("1. THE CURRENT CREDIT LIMIT vs WHAT ONE NORMAL CYCLE ACTUALLY COSTS")
    print("=" * 84)
    print(f"limits in the file: {sorted(cat.credit_limit_idr.unique())}")
    print(f"correlation(limit, units sold per day): {d.credit_limit_idr.corr(d.velocity_units_day):+.3f}")
    print(f"median limit / (cycle need)           : {d.ratio.median():.2f}x")
    print(f"SKUs where the limit cannot cover ONE cycle: {(d.ratio < 1).sum()} of {len(d)}")
    print()
    show = ["sku", "category", "velocity_units_day", "lead_p90", "unit_cost_idr",
            "need_cycle_idr", "credit_limit_idr", "ratio"]
    print("worst five:")
    print(d.nsmallest(5, "ratio")[show].round(2).to_string(index=False))
    print()
    print("best five:")
    print(d.nlargest(5, "ratio")[show].round(2).to_string(index=False))

    # ---------- 2. what a demand-proportional limit would be
    d["limit_proposed"] = (ZMULT * d.need_cycle_idr).round(-5)
    print()
    print("=" * 84)
    print("2. A LIMIT SIZED TO DEMAND (median cycle need x 1.28, rounded to 100k)")
    print("=" * 84)
    print(f"proposed: min {d.limit_proposed.min():,.0f}  median {d.limit_proposed.median():,.0f}  "
          f"max {d.limit_proposed.max():,.0f}")
    print(f"for comparison, today's: min {cat.credit_limit_idr.min():,.0f}  "
          f"median {cat.credit_limit_idr.median():,.0f}  max {cat.credit_limit_idr.max():,.0f}")

    # ---------- 3. what that does to the auto/escalation split
    po = pd.read_csv(ORD / "purchase_orders.csv")
    m = po.merge(d[["sku", "credit_limit_idr", "limit_proposed"]], on="sku", how="left")

    def split(limit_col: str) -> tuple[int, int]:
        ok = (m["value_idr"] <= AUTO_LIMIT) & (m["value_idr"] <= m[limit_col])
        return int(ok.sum()), int((~ok).sum())

    now = split("credit_limit_idr")
    then = split("limit_proposed")
    print()
    print("=" * 84)
    print("3. THE AUTO / ESCALATE SPLIT, UNDER EACH SET OF LIMITS")
    print("=" * 84)
    print(f"{'':34} {'auto':>8} {'escalated':>11} {'auto share':>12}")
    for label, r in (("today's flat limits", now), ("demand-sized limits", then)):
        print(f"{label:34} {r[0]:>8} {r[1]:>11} {r[0]/sum(r):>11.1%}")

    # how many are held back by value alone once credit stops biting
    still = m[(m["value_idr"] > m["limit_proposed"]) | (m["value_idr"] > AUTO_LIMIT)]
    by_value = (still["value_idr"] > AUTO_LIMIT).sum()
    print()
    print(f"with demand-sized limits, {len(still)} still escalated; "
          f"{by_value} of those because the order is above the Rp200M signing line")
    print()
    print("Read: the credit limit is per-SKU trade credit, so it shrinks with the SKU. The")
    print("Rp200M signing line is a policy threshold, so it does not. The two are different")
    print("things and only one of them was mis-sized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
