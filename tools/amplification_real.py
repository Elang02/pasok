#!/usr/bin/env python3
"""
Measure amplification on the REAL order stream, correctly.
==========================================================

`tools/bullwhip_real.py` reported a median of 94x Var(order)/Var(demand) per SKU. That number
is an ARTEFACT and must not be quoted.

Why: this pipeline does not order every day. Orders fire on a weekly review, so on ~94.5% of
days the order is exactly zero and on ~5.5% it is a large replenishment. Var(order)/Var(demand)
on such a stream measures the sparsity of the ordering cadence, not amplification. Any
periodic restock policy scores huge on that ratio, including a perfect one.

The defensible measure compares like with like. Amplification is about the SIZE of an order
relative to the demand it has to cover, and about whether that relationship is stable. So:

  1. order cover: units ordered / units of demand the order has to span. A stable cover near
     the target means no amplification.
  2. review-to-review variability of that cover. If the cover jumps around, the policy is
     reacting to noise, and THAT is the bullwhip signature.
  3. correlation of the order with the LAST review's demand change (the classic upstream
     signature: order grows when recent demand grew).

Run: .venv/bin/python tools/amplification_real.py
"""
from __future__ import annotations

import json
import pathlib

import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
STK, AG, DEM = R / "data/stock", R / "data/agents", R / "data/demand"


def main() -> int:
    obs = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales", "ordered"])
    obs["date"] = pd.to_datetime(obs["date"])
    w_ord = obs.pivot(index="date", columns="sku", values="ordered").sort_index().astype(float)
    w_sal = obs.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)

    print("=" * 90)
    print("1. THE CADENCE, AND WHY Var(order)/Var(demand) IS THE WRONG TOOL HERE")
    print("=" * 90)
    frac = (w_ord > 0).mean().mean()
    print(f"  days carrying an order     : {frac:.1%}")
    print(f"  days at exactly zero       : {1-frac:.1%}")
    print("  A weekly-review restock policy is mostly zeros. Variance ratios on such a stream")
    print("  measure the cadence, not amplification, so they are not reported as bullwhip.")

    print()
    print("=" * 90)
    print("2. ORDER COVER: HOW MANY DAYS OF DEMAND ONE ORDER BUYS")
    print("=" * 90)
    # per-order cover, not a lifetime ratio: only look at the weeks that actually ordered
    wk_ord = w_ord.resample("7D").sum()
    wk_dem = w_sal.resample("7D").mean() * 7
    per_order_cover = (wk_ord / wk_dem).replace([np.inf, -np.inf], np.nan)
    per_order_cover = per_order_cover.where(wk_ord > 0)
    c = per_order_cover.stack().dropna()
    print(f"  orders measured: {len(c)} review weeks across {len(wk_ord.columns)} SKUs")
    print(f"  median {c.median():.1f} days   p10 {c.quantile(.10):.1f}   "
          f"p90 {c.quantile(.90):.1f}   max {c.max():.1f}")
    print("  For comparison, the sizing horizon in decision.py is lead p90 + review + buffer,")
    print("  so a cover clustered near that horizon means orders track the plan, not the noise.")

    print()
    print("=" * 90)
    print("3. REVIEW-TO-REVIEW VARIABILITY OF THAT COVER (the bullwhip signature)")
    print("=" * 90)
    # resample each SKU's order stream to its own review weeks
    cov_rows = []
    for c in w_ord.columns:
        o, s = w_ord[c], w_sal[c]
        vel = s.rolling(28, min_periods=7).mean()
        wk = o.resample("7D").sum()
        wk_vel = s.resample("7D").mean()
        cv = (wk / (wk_vel * 7)).replace([np.inf, -np.inf], np.nan).dropna()
        cv = cv[cv > 0]
        if len(cv) >= 6:
            cov_rows.append({"sku": c, "mean_cover": cv.mean(), "cv": cv.std() / cv.mean()})
    cv_df = pd.DataFrame(cov_rows)
    print(f"  SKUs with >=6 review weeks carrying an order: {len(cv_df)}")
    print(f"  coefficient of variation of order cover: median {cv_df['cv'].median():.2f}   "
          f"p75 {cv_df['cv'].quantile(.75):.2f}   p90 {cv_df['cv'].quantile(.90):.2f}")
    print("  A CV near 0 means each review orders the same amount of cover, i.e. no whiplash.")
    print("  A high CV means the order size swings with recent noise.")

    print()
    print("=" * 90)
    print("4. DOES THE ORDER CHASE LAST WEEK'S NOISE? (classic upstream signature)")
    print("=" * 90)
    rows = []
    for c in w_ord.columns[:200]:
        o, s = w_ord[c].resample("7D").sum(), w_sal[c].resample("7D").mean()
        if len(o) < 12 or o.std() == 0:
            continue
        d = s.pct_change().replace([np.inf, -np.inf], np.nan)
        m = o.notna() & d.notna()
        if m.sum() >= 12:
            r = float(np.corrcoef(o[m].to_numpy(), d[m].to_numpy())[0, 1])
            if np.isfinite(r):
                rows.append(r)
    if rows:
        r = np.array(rows)
        print(f"  correlation(order size, last week's demand change), median over "
              f"{len(r)} SKUs: {np.median(r):+.2f}")
        print(f"  share positively correlated (chasing): {(r > 0.2).mean():.1%}")
        print("  Near zero or negative means the order does not chase short-term noise.")

    print()
    print("=" * 90)
    print("5. WHAT THE FIXED CAP DID")
    print("=" * 90)
    dec = pd.read_csv(AG / "decisions.csv")
    raw, g = dec["raw_order"].astype(float), dec["guarded_order"].astype(float)
    cut = (raw - g).clip(lower=0)
    print(f"  orders the cap bound     : {int((g < raw).sum())} of {len(dec)}")
    print(f"  units removed            : {cut.sum():,.0f} ({100*cut.sum()/raw.sum():.1f}% of raw)")
    print(f"  median per-SKU cut       : {(cut/raw.replace(0, np.nan)).median():.1%}")
    print(f"  largest per-SKU cut      : {(cut/raw.replace(0, np.nan)).max():.1%}")
    print()
    print("  NOTE for the report: an 83% cut is large and needs its own explanation. It says")
    print("  the raw sizing asked for far more than the per-SKU forecast plus 2.5 sigma ever")
    print("  justified. That is the guardrail doing its job, and it is also a signal to check")
    print("  the raw sizing rather than celebrate the cut.")

    print()
    print("=" * 90)
    print("6. HONEST POSITION FOR THE DEMO")
    print("=" * 90)
    sim = json.loads((R / "simulation/results.json").read_text())
    print(f"  Figure 1 simulation (proposal line 27), on the Bank Indonesia retail index:")
    print(f"    unguarded {sim['unguarded']['amplification']:.2f}x  ->  guarded "
          f"{sim['guarded']['amplification']:.2f}x")
    print(f"    inventory {sim['unguarded']['avg_inventory']:.0f} -> "
          f"{sim['guarded']['avg_inventory']:.0f} units, "
          f"fill {sim['unguarded']['fill_rate']:.4f} -> {sim['guarded']['fill_rate']:.4f}")
    print("  Real pipeline: the cap now binds on "
          f"{int((g < raw).sum())} of {len(dec)} orders, which is the claim the proposal")
    print("  actually makes (\"three fixed decision rules that run while the agent works\").")
    print("  The amplification number for the real loop is NOT comparable to Figure 1 and is")
    print("  reported as cover variability, not as a variance ratio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
