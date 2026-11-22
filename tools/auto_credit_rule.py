#!/usr/bin/env python3
"""
The auto-order credit rule Elang specified
==========================================

    auto credit ceiling = (normal-month sales, no event) x (max guardrail multiplier)

Two things to establish from data before wiring it in:

  1. what "max guardrail multiplier" actually is here, since the pipeline has no explicit
     constant for it
  2. what "normal-month sales, no event" is, measured by excluding event windows

Run: .venv/bin/python tools/auto_credit_rule.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT, STK, ORD, DEM = ROOT / "data/catalog", ROOT / "data/stock", ROOT / "data/orders", ROOT / "data/demand"
AUTO_LIMIT = 200_000_000


def main() -> int:
    print("=" * 88)
    print("1. WHAT IS THE MAXIMUM MULTIPLIER THE GUARDRAIL WOULD ALLOW?")
    print("=" * 88)
    ramps = pd.read_csv(DEM / "sku_ramps.csv")
    ev = pd.read_csv(CAT / "events.csv")
    ev["date"] = pd.to_datetime(ev["date"])
    peak_learned = ramps["peak_mult"]
    peak_true = ev.groupby(["event", ev["date"].dt.year])["factor"].max()
    print("learned peak multiplier per SKU-event (sku_ramps.csv, 3000 rows):")
    print(f"  median {peak_learned.median():.2f}   p90 {peak_learned.quantile(.9):.2f}   "
          f"p99 {peak_learned.quantile(.99):.2f}   max {peak_learned.max():.2f}")
    print()
    print("the generator's own peak factor per event-year (the truth):")
    print(f"  median {peak_true.median():.2f}   p90 {peak_true.quantile(.9):.2f}   "
          f"max {peak_true.max():.2f}")
    print()
    print("the pipeline's guardrail constants (decision.py):")
    print("  EWMA_ALPHA 0.15 (forecast smoothing), DAMP 0.5 (order damping),")
    print("  CAP_K 2.5 (variance cap: order <= forecast + 2.5 sigma)")
    print("  -> there is NO explicit maximum-multiplier constant. The defensible reading of")
    print("     'the max multiplier the guardrail allows' is the largest peak the learned")
    print("     ramps actually carry, i.e. p99 rounded up.")

    MAX_MULT = float(np.ceil(peak_learned.quantile(0.99)))
    print(f"\n  MAX_MULT chosen = {MAX_MULT:.0f}")

    # ---------- 2. normal-month sales, excluding event windows
    print()
    print("=" * 88)
    print("2. NORMAL-MONTH SALES (event days removed)")
    print("=" * 88)
    sd = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales"])
    sd["date"] = pd.to_datetime(sd["date"])
    cat = pd.read_csv(CAT / "catalog.csv")[["sku", "principal_id", "unit_cost_idr", "credit_limit_idr"]]

    ev_days = set(ev["date"])
    sd["is_event"] = sd["date"].isin(ev_days)
    print(f"event days in the walk: {sd['is_event'].sum() // 600} of {sd['date'].nunique()} "
          f"calendar days ({sd['is_event'].mean():.1%} of rows)")

    norm = sd[~sd["is_event"]].groupby("sku")["sales"].mean().rename("normal_units_day")
    evt = sd[sd["is_event"]].groupby("sku")["sales"].mean().rename("event_units_day")
    d = cat.merge(norm, on="sku").merge(evt, on="sku")
    d["normal_month_idr"] = d["normal_units_day"] * 30 * d["unit_cost_idr"]
    d["event_month_idr"] = d["event_units_day"] * 30 * d["unit_cost_idr"]

    # ---------- 3. the rule
    d["limit_new"] = (d["normal_month_idr"] * MAX_MULT).round(-5)
    print()
    print(f"limit = normal_month_idr x {MAX_MULT:.0f}")
    print(f"  min    {d['limit_new'].min():,.0f}")
    print(f"  median {d['limit_new'].median():,.0f}")
    print(f"  max    {d['limit_new'].max():,.0f}")
    print()
    print("compare the three candidate rules, median across 600 SKUs:")
    snap = pd.read_csv(STK / "position_snapshot.csv")[["sku", "velocity_units_day"]]
    rec = pd.read_csv(CAT / "receiving.csv")
    lead_p90 = rec.groupby("principal_id")["actual_lead_d"].quantile(0.9)
    dd = cat.merge(snap, on="sku")
    dd["lead_p90"] = dd["principal_id"].map(lead_p90)
    cycle = dd["velocity_units_day"] * dd["lead_p90"] * dd["unit_cost_idr"]
    print(f"  current file (random round numbers) : {pd.read_csv(CAT/'catalog.csv').credit_limit_idr.median():>18,.0f}")
    print(f"  1.28 x one replenishment cycle      : {float((1.28*cycle).median()):>18,.0f}")
    print(f"  normal month x {MAX_MULT:.0f}                       : {d['limit_new'].median():>18,.0f}")

    # ---------- 4. what it does to the split
    print()
    print("=" * 88)
    print("3. THE AUTO / ESCALATE SPLIT UNDER THE NEW RULE")
    print("=" * 88)
    po = pd.read_csv(ORD / "purchase_orders.csv")
    m = po.merge(d[["sku", "credit_limit_idr", "limit_new"]], on="sku", how="left")
    sw = set(pd.read_csv(ORD / "supplier_switch_proposals.csv")["from_principal"])

    def split(col: str, flag: bool) -> tuple[int, int]:
        ok = (m["value_idr"] <= AUTO_LIMIT) & (m["value_idr"] <= m[col])
        if flag:
            ok &= ~m["principal_id"].isin(sw)
        return int(ok.sum()), int((~ok).sum())

    print(f"{'':46} {'auto':>7} {'escalated':>11}")
    for label, col in (("today (random round numbers)", "credit_limit_idr"),
                       (f"normal month x {MAX_MULT:.0f}", "limit_new")):
        for flag, fl in ((True, "+ switch flag on"), (False, "+ switch flag off")):
            a, e = split(col, flag)
            print(f"{label + ' ' + fl:46} {a:>7} {e:>11}")

    # is the new rule binding at all?
    m["over_new"] = m["value_idr"] > m["limit_new"]
    m["over_value"] = m["value_idr"] > AUTO_LIMIT
    print()
    print(f"orders above the new credit ceiling : {int(m['over_new'].sum())}")
    print(f"orders above the Rp200M signing line: {int(m['over_value'].sum())}")
    print(f"orders above BOTH                    : {int((m['over_new'] & m['over_value']).sum())}")
    print()
    print("Read: if 'above the signing line' is much larger than 'above the new ceiling', the")
    print("binding constraint is the policy threshold, not the credit rule, and no credit rule")
    print("can lift the auto count past that line.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
