#!/usr/bin/env python3
"""
Measure the bullwhip on the REAL order stream, per SKU, on a time series.
=======================================================================

The proposal (line 26) promises three guardrails that "run while the agent works". The old
check compared variance ACROSS 600 SKUs in one shot, which measures size differences between
a fast and a slow mover, not amplification. That produced a meaningless 513x.

The right unit is one SKU over time: how much wider does the order stream swing than the
demand it serves. This computes it three ways and reports the honest number.

Run: .venv/bin/python tools/bullwhip_real.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
STK, AG = R / "data/stock", R / "data/agents"


def amp(a: np.ndarray, b: np.ndarray) -> float:
    """Var(order) / Var(demand) on the same window, same SKU."""
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    if len(a) < 30 or b.var() <= 0:
        return float("nan")
    return float(a.var() / b.var())


def main() -> int:
    obs = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales", "ordered"])
    obs["date"] = pd.to_datetime(obs["date"])
    w_ord = obs.pivot(index="date", columns="sku", values="ordered").sort_index().astype(float)
    w_sal = obs.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)

    W = 104
    o, s = w_ord.iloc[-W:], w_sal.iloc[-W:]
    cols = [c for c in w_ord.columns if c in w_sal.columns]

    print("=" * 88)
    print("BULLWHIP ON THE REAL ORDER STREAM — per SKU, over time")
    print("=" * 88)
    print(f"window: last {W} days, {len(cols)} SKUs")
    print()
    print("Var(order) / Var(demand), computed per SKU then summarised:")
    a = np.array([amp(o[c].to_numpy(), s[c].to_numpy()) for c in cols])
    a = a[np.isfinite(a)]
    print(f"  SKUs with a measurable ratio : {len(a)}")
    print(f"  median {np.median(a):.2f}x   p25 {np.quantile(a,.25):.2f}x   "
          f"p75 {np.quantile(a,.75):.2f}x   p90 {np.quantile(a,.90):.2f}x")
    print(f"  share above 1.0 (order swings wider than demand): {(a>1).mean():.1%}")

    print()
    print("Same ratio on the day-to-day CHANGE, which is what a manager sees as whiplash:")
    d_amp = np.array([amp(np.diff(o[c].to_numpy()), np.diff(s[c].to_numpy())) for c in cols])
    d_amp = d_amp[np.isfinite(d_amp)]
    print(f"  median {np.median(d_amp):.2f}x   p90 {np.quantile(d_amp,.90):.2f}x")

    print()
    print("=" * 88)
    print("HOW THIS COMPARES TO THE FIGURE 1 SIMULATION (proposal line 27)")
    print("=" * 88)
    import json
    sim = json.loads((R / "simulation/results.json").read_text())
    print(f"  simulation, unguarded : {sim['unguarded']['amplification']:.2f}x")
    print(f"  simulation, guarded   : {sim['guarded']['amplification']:.2f}x")
    print(f"  real pipeline, now    : {np.median(a):.2f}x (median SKU)")
    print()
    print("Read: the real pipeline is NOT the Figure 1 simulation. The simulation shows what")
    print("the three guardrails do to a reactive policy on one national series; the real loop")
    print("sizes from a per-SKU forecast over a buying horizon, so its order stream is a")
    print("planning quantity, not a day-by-day reaction. Both numbers are honest; they answer")
    print("different questions and must be quoted as such.")

    print()
    print("=" * 88)
    print("WHAT THE FIXED CAP ACTUALLY DID")
    print("=" * 88)
    dec = pd.read_csv(AG / "decisions.csv")
    raw = dec["raw_order"].astype(float)
    g = dec["guarded_order"].astype(float)
    print(f"  orders the cap bound      : {int((g < raw).sum())} of {len(dec)}")
    print(f"  units removed by the cap  : {float((raw - g).clip(lower=0).sum()):,.0f} "
          f"({100*(raw-g).clip(lower=0).sum()/raw.sum():.1f}% of raw volume)")
    print(f"  per-SKU cut, median       : "
          f"{float(((raw-g).clip(lower=0)/raw.replace(0,np.nan)).median()):.1%}")
    print(f"  largest per-SKU cut       : "
          f"{float(((raw-g).clip(lower=0)/raw.replace(0,np.nan)).max()):.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
