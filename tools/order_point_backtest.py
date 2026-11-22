#!/usr/bin/env python3
"""
When to order, per supplier: measured against what actually arrived.
===================================================================

The order point is `lead_p90 + REVIEW_DAYS + buffer`. This scores it honestly two ways:

  CHEAP TEST   we watch the SKU every day and re-measure on the day it actually needs
               ordering, but we are not allowed to solve for the order point.
  HONEST TEST  we only look on the weekly review day, so we can be blind for up to
               6 days, and we then ask: would we have fired in time to have the stock
               land the day before it runs out?

Run: .venv/bin/python tools/order_point_backtest.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT, STK, AG = ROOT / "data/catalog", ROOT / "data/stock", ROOT / "data/agents"
RNG = np.random.default_rng(20261010)


def main() -> int:
    rec = pd.read_csv(CAT / "receiving.csv", parse_dates=["order_date"])
    snap = pd.read_csv(STK / "position_snapshot.csv")[["sku", "velocity_units_day", "lead_time_days"]]
    daily = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales", "on_hand"])
    daily["date"] = pd.to_datetime(daily["date"])

    # ---------- 1. the lead-time table, learned from receipts
    g = rec.groupby("principal_id")["actual_lead_d"]
    tab = pd.DataFrame({
        "n": g.size(),
        "p50": g.quantile(0.50).round(1),
        "p90": g.quantile(0.90).round(1),
        "mean": g.mean().round(2),
        "sd": g.std().round(2),
    })
    spread = (tab["p90"] - tab["p50"]).sort_values(ascending=False)
    print("=" * 88)
    print("1. LEAD TIME PER SUPPLIER, LEARNED FROM THE RECEIPTS (receiving.csv)")
    print("=" * 88)
    print(tab.to_string())
    print()
    print("the buffer the loop adds comes from the SPREAD, not the mean:")
    print(f"  widest  spread: {spread.index[0]} at {(spread.iloc[0]):.1f} days "
          f"(p90 {tab.loc[spread.index[0], 'p90']} vs p50 {tab.loc[spread.index[0], 'p50']})")
    print(f"  tightest spread: {spread.index[-1]} at {(spread.iloc[-1]):.1f} days")

    # ---------- 2. how long one delivery actually lasts
    cat = pd.read_csv(CAT / "catalog.csv")[["sku", "principal_id"]]
    d = cat.merge(snap, on="sku")
    d["lead_p90"] = d["principal_id"].map(tab["p90"])
    print()
    print("=" * 88)
    print("2. THE ORDER POINT (lead_p90 + weekly review + buffer)")
    print("=" * 88)
    dd = d.groupby("principal_id").agg(skus=("sku", "size"), lead_p90=("lead_p90", "first"))
    # the buffer the loop actually uses: lead spread (p90-p50) blended with forecast error,
    # at 90% service (z=1.28), floored at 2 days. decision.py principal_buffer().
    err_days = pd.Series({p: 2.5 for p in tab.index})            # typical forecast error in days
    for pid in tab.index:
        s = rec.loc[rec.principal_id == pid, "actual_lead_d"]
        err_days[pid] = float(np.ceil(1.28 * np.sqrt((s.std(ddof=1) / 1.0) ** 2 / max(1, len(s)))))
    dd["lead_p50"] = dd.index.map(tab["p50"])
    dd["lead_var"] = (dd["lead_p90"] - dd["lead_p50"]).clip(lower=0)
    dd["forecast_err_d"] = dd.index.map(err_days)
    dd["buffer_days"] = np.maximum(2, np.ceil(1.28 * np.sqrt(
        dd["lead_var"] ** 2 + dd["forecast_err_d"] ** 2) / 1.28).astype(int))
    dd["order_point_days"] = (dd["lead_p90"] + 7 + dd["buffer_days"]).round(0)
    dd["stockout_days"] = (dd["lead_p90"] + 7)
    print(dd.to_string())
    print()
    print("Read: `stockout_days` is the danger window. Past it, the order lands after the")
    print("shelf is already empty. The buffer sits on top for lead-time spread.")

    # ---------- 3. cheap test: measure on the exact day a reorder is needed
    print()
    print("=" * 88)
    print("3. CHEAP TEST — reorder point hit exactly, does it land before the shelf empties?")
    print("=" * 88)
    res = []
    for pid, gg in rec.groupby("principal_id"):
        lead = gg["actual_lead_d"].to_numpy(dtype=float)
        p90 = np.percentile(lead, 90)
        # simulate: place an order the day on_hand crosses p90 worth of demand
        sub = daily[daily["sku"].isin(d[ d.principal_id == pid ]["sku"])]
        for sku, h in sub.groupby("sku"):
            h = h.sort_values("date")
            oh, sal = h["on_hand"].to_numpy(), h["sales"].to_numpy()
            vel = max(1.0, np.median(sal))
            trig = np.where(oh <= vel * p90)[0]
            if len(trig) == 0:
                continue
            t = trig[0]
            eta = t + RNG.choice(lead)        # a lead time drawn from what that supplier does
            # did the shelf hold until the order could land?
            empty = np.where(oh <= 0)[0]
            if len(empty) == 0:
                res.append({"pid": pid, "sku": sku, "ok": True})
            else:
                res.append({"pid": pid, "sku": sku, "ok": eta <= empty[0]})
    r = pd.DataFrame(res)
    ok = r.groupby("pid")["ok"].mean()
    print(f"overall: {r['ok'].mean():.1%} of reorders landed before the shelf emptied")
    print("worst suppliers:")
    print(ok.sort_values().head(4).round(3).to_string())

    # ---------- 4. honest test: you only get to look on the review day
    print()
    print("=" * 88)
    print("4. HONEST TEST — decision made only on the weekly review day")
    print("=" * 88)
    print("A SKU entered the danger window up to 6 days before we could act. If the trip")
    print("across that gap plus the supplier's p90 exceeds the cover, the order is late.")
    gap = 6
    late = ((gap + dd["lead_p90"]) > dd["order_point_days"]).sum()
    print(f"per-supplier check (gap {gap} days > buffer):")
    dd["blind_gap"] = gap
    dd["gap_plus_lead"] = dd["blind_gap"] + dd["lead_p90"]
    dd["covered"] = dd["gap_plus_lead"] <= dd["order_point_days"]
    print(dd[["skus", "lead_p90", "order_point_days", "gap_plus_lead", "covered"]].to_string())
    print()
    print(f"suppliers where the blind gap is NOT covered by the buffer: "
          f"{int((~dd['covered']).sum())} of {len(dd)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
