#!/usr/bin/env python3
"""
What multiple of normal sales does the GUARDRAIL actually allow?
===============================================================

Elang's correction: the credit line should follow NORMAL sales, times the GUARDRAIL's own
bound, not the calendar's event multiplier. So measure the guardrail's bound instead of
assuming one.

Method: for every SKU, take the order the guardrails actually let through (`guarded_order`
in decisions.csv) and divide its value by that SKU's normal monthly sales value (event days
removed). That ratio IS the guardrail's realised multiple. Percentiles of it bound the line.

Run: .venv/bin/python tools/guardrail_multiple.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
CAT, STK, ORD, AG, DEM = R / "data/catalog", R / "data/stock", R / "data/orders", R / "data/agents", R / "data/demand"


def main() -> int:
    cat = pd.read_csv(CAT / "catalog.csv")[["sku", "principal_id", "unit_cost_idr", "credit_limit_idr"]]
    dec = pd.read_csv(AG / "decisions.csv")[["sku", "guarded_order", "forecast_daily", "event", "event_mult"]]
    sd = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales"])
    sd["date"] = pd.to_datetime(sd["date"])
    ev = pd.read_csv(CAT / "events.csv")
    ev["date"] = pd.to_datetime(ev["date"])

    # ---- normal monthly sales value, event days removed
    sd["is_event"] = sd["date"].isin(set(ev["date"]))
    norm = sd[~sd["is_event"]].groupby("sku")["sales"].mean().rename("normal_units_day")
    d = cat.merge(norm, on="sku").merge(dec, on="sku")
    d["normal_month_value"] = d["normal_units_day"] * 30 * d["unit_cost_idr"]
    d["order_value"] = d["guarded_order"] * d["unit_cost_idr"]
    d["ratio"] = d["order_value"] / d["normal_month_value"].replace(0, np.nan)

    print("=" * 84)
    print("1. THE GUARDRAIL'S REALISED MULTIPLE OF NORMAL MONTHLY SALES")
    print("=" * 84)
    r = d["ratio"].dropna()
    print(f"  orders with a positive size: {len(r)} of {len(d)}")
    print(f"  median {r.median():.2f}x   p75 {r.quantile(.75):.2f}x   p90 {r.quantile(.90):.2f}x   "
          f"p99 {r.quantile(.99):.2f}x   max {r.max():.2f}x")
    print()
    print("  split by whether the order carried an event ramp:")
    for lbl, sub in (("with event", d[d["event"].astype(str).str.len() > 0]),
                     ("no event", d[d["event"].astype(str).str.len() == 0])):
        s = sub["ratio"].dropna()
        if len(s):
            print(f"    {lbl:12} n={len(s):>4}  median {s.median():.2f}x  p90 {s.quantile(.9):.2f}x  max {s.max():.2f}x")

    print()
    print("=" * 84)
    print("2. THE GUARDRAIL CONSTANTS, AND WHAT EACH ONE BOUNDS")
    print("=" * 84)
    print("  EWMA_ALPHA 0.15  smooths the forecast (EWMA) before sizing      -> not a size cap")
    print("  DAMP 0.5         damps the change against the previous order    -> not a size cap")
    print("  CAP_K 2.5        order <= forecast + 2.5 sigma                  -> THE size cap")
    print("  cap_level        median guarded order level x 1.2               -> per-SKU ceiling")
    print()
    print("  So the only rule that caps HOW BIG an order can be is CAP_K, applied to the")
    print("  forecast plus its own error spread. Its realised multiple of normal sales is the")
    print("  ratio measured above.")

    print()
    print("=" * 84)
    print("3. THREE CANDIDATE RULES, MEDIAN LIMIT ACROSS 600 SKUs")
    print("=" * 84)
    GUARD = float(np.ceil(r.quantile(0.99)))          # the measured guardrail bound
    print(f"  guardrail bound measured at p99: {GUARD:.0f}x normal sales")
    print()
    for lbl, mult in (("now in the file (event multiplier 3.2)", 3.2),
                      ("guardrail bound (measured)", GUARD)):
        line = d["normal_month_value"] * mult
        print(f"  {lbl:38} median line Rp{line.median():>16,.0f}")
    print(f"  {'one replenishment cycle x 1.28':38} median line "
          f"Rp{float((pd.read_csv(STK/'position_snapshot.csv')['velocity_units_day']*10*d['unit_cost_idr']*1.28).median()):>16,.0f}")

    print()
    print("=" * 84)
    print("4. DOES THE GUARDRAIL BOUND MAKE THE CREDIT CHECK BINDING?")
    print("=" * 84)
    po = pd.read_csv(ORD / "purchase_orders.csv")
    d["limit_guard"] = d["normal_month_value"] * GUARD
    m = po.merge(d[["sku", "normal_month_value", "limit_guard", "ratio"]], on="sku", how="left")
    over = m["value_idr"] > m["limit_guard"]
    print(f"  orders above the guardrail-bounded line: {int(over.sum())} of {len(m)}")
    print(f"  their ratio distribution: median {m.loc[over, 'ratio'].median():.2f}x  "
          f"max {m.loc[over, 'ratio'].max():.2f}x")
    if over.sum():
        print()
        print("  biggest offenders (order value vs the line):")
        w = m[over].nlargest(5, "value_idr")[["po_id", "sku", "value_idr", "limit_guard", "ratio"]]
        w["value_jt"] = (w["value_idr"] / 1e6).round(0)
        w["limit_jt"] = (w["limit_guard"] / 1e6).round(0)
        print(w[["po_id", "sku", "value_jt", "limit_jt", "ratio"]].to_string(index=False))

    print()
    print("Read: if the guardrail bounds the order, the line derived from the SAME bound can")
    print("only be breached by an order the guardrail itself let through above it. Those are")
    print("the lines where the two rules disagree, and they are the honest exceptions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
