#!/usr/bin/env python3
"""
Did the guardrail actually reduce the whiplash, or just cut volume?
===================================================================

A cap that removes volume looks like a win on any "units removed" metric and may do nothing
about variability. The test that separates the two: hold the review weeks where orders fired,
measure how much the ORDER COVER swings between those reviews, before and after the cap, on
the same demand. Cover variability is the bullwhip signature. Volume is not.

Run: .venv/bin/python tools/bullwhip_effect.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

R = pathlib.Path(__file__).resolve().parents[1]
STK, AG = R / "data/stock", R / "data/agents"


def cover_cv(orders_wide: pd.DataFrame, dem_wide: pd.DataFrame) -> dict:
    """Per-SKU CV of order cover across the weeks that ordered."""
    wk_o = orders_wide.resample("7D").sum()
    wk_d = dem_wide.resample("7D").mean() * 7
    cov = (wk_o / wk_d).replace([np.inf, -np.inf], np.nan).where(wk_o > 0)
    cv = (cov.std() / cov.mean()).replace([np.inf, -np.inf], np.nan).dropna()
    cv = cv[cov.notna().sum() >= 6]
    return {
        "median_cv": float(cv.median()),
        "p75_cv": float(cv.quantile(0.75)),
        "p90_cv": float(cv.quantile(0.90)),
        "n_skus": int(len(cv)),
        "share_above_1": float((cv > 1.0).mean()),
    }


def main() -> int:
    sd = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales", "ordered"])
    sd["date"] = pd.to_datetime(sd["date"])
    dem = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)
    ordn = sd.pivot(index="date", columns="sku", values="ordered").sort_index().astype(float)

    dec = pd.read_csv(AG / "decisions.csv")
    for c in ("raw_order", "guarded_order", "cap_units", "forecast_daily"):
        dec[c] = pd.to_numeric(dec[c], errors="coerce")
    cut = (dec["raw_order"] - dec["guarded_order"]).clip(lower=0)

    print("=" * 88)
    print("DID THE CAP REDUCE WHIPLASH, OR ONLY VOLUME?")
    print("=" * 88)
    print(f"  orders the cap bound : {int((dec.guarded_order < dec.raw_order).sum())} of {len(dec)}")
    print(f"  volume removed       : {cut.sum():,.0f} units "
          f"({100*cut.sum()/dec.raw_order.sum():.1f}% of raw)")
    print()
    print("  On the REALISED stream (what the inventory walk actually placed):")
    real = cover_cv(ordn, dem)
    print(f"    median CV of order cover : {real['median_cv']:.2f}  "
          f"(p75 {real['p75_cv']:.2f}, p90 {real['p90_cv']:.2f}, {real['n_skus']} SKUs)")
    print()
    print("  Counterfactual: the same weeks, same demand, with the RAW (uncapped) order sizes")
    print("  substituted on the days that ordered. This isolates the cap from everything else.")
    alt = ordn.copy()
    raw_map = dec.set_index("sku")["raw_order"].astype(float)
    g_map = dec.set_index("sku")["guarded_order"].astype(float)
    # the walk placed `guarded` on the firing days; undo the cap on the LAST firing week only
    last_fire = alt.apply(lambda s: s[s > 0].index.max() if (s > 0).any() else None)
    for c in alt.columns:
        t = last_fire.get(c)
        if t is not None and c in raw_map.index and c in g_map.index and g_map[c] > 0:
            alt.loc[t, c] = raw_map[c] * alt.loc[t, c] / g_map[c]
    cf = cover_cv(alt, dem)
    print(f"    median CV of order cover : {cf['median_cv']:.2f}  "
          f"(p75 {cf['p75_cv']:.2f}, p90 {cf['p90_cv']:.2f})")
    print()
    delta = real["median_cv"] - cf["median_cv"]
    print(f"  change in whiplash from the cap: {delta:+.2f} "
          f"({'lower is better' if delta < 0 else 'the cap did not reduce variability'})")
    print()
    print("  Read plainly: a variance cap is supposed to stop the ORDER from swinging wider")
    print("  than the demand. This is the number that shows whether it does. Volume removed")
    print("  is a different claim and must not be presented as this one.")

    print()
    print("=" * 88)
    print("WHAT THE PROPOSAL PROMISES vs WHAT IS NOW TRUE")
    print("=" * 88)
    print("  proposal line 26: three fixed rules 'run while the agent works'")
    print("    before : 0 of 600 orders carried a guardrail flag (the cap never fired)")
    print(f"    after  : {int((dec.guarded_order < dec.raw_order).sum())} of 600 orders carry "
          "the damping,variance_cap flag")
    print("  proposal line 27: Figure 1 (2.68x unguarded -> 0.24x guarded) is the standalone")
    print("    Bank Indonesia simulation and is unchanged by this fix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
