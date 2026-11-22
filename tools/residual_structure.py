#!/usr/bin/env python3
"""Is there learnable structure left in the residual of the best simple estimator?"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
sd["date"] = pd.to_datetime(sd["date"])
wide = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)

# the best simple estimator found: 2-week seasonal mean
pred = wide.rolling(14, min_periods=7).mean().shift(1)
resid = (wide - pred).dropna(how="all")
resid = resid.loc["2024-01-01":]
pred = pred.loc[resid.index]

print("=" * 74)
print("3. IS THERE STRUCTURE LEFT IN THE RESIDUAL?")
print("=" * 74)

# a) autocorrelation of the residual
r = resid.mean(axis=1)              # pooled across SKUs
ac = [r.autocorr(lag=k) for k in range(1, 15)]
print("residual autocorrelation (lag 1..14), pooled across SKUs:")
print("  " + " ".join(f"{v:+.3f}" for v in ac))
print(f"  max |ac|: {max(abs(v) for v in ac):.3f}")

# b) does a weekday or month effect survive?
res = resid.stack().rename("r").reset_index()
res["dow"] = res["date"].dt.dayofweek
res["month"] = res["date"].dt.month
rel = (resid / pred).stack().rename("rel").reset_index()
rel["dow"] = rel["date"].dt.dayofweek
rel["month"] = rel["date"].dt.month

print("\nmean relative residual by weekday (0=Mon):")
print("  " + "  ".join(f"{d}:{rel[rel.dow == d].rel.mean():+.3f}" for d in range(7)))
print("mean relative residual by month:")
print("  " + "  ".join(f"{m}:{rel[rel.month == m].rel.mean():+.3f}" for m in range(1, 13)))
print(f"\nspread across weekday means: {rel.groupby('dow').rel.mean().std():.4f}")
print(f"spread across month   means: {rel.groupby('month').rel.mean().std():.4f}")
print(f"overall residual sd        : {rel.rel.std():.4f}")
print()
print("A model can only exploit systematic differences across a feature. If the spread")
print("across weekday/month means is a small fraction of the residual sd, the residual is")
print("noise and there is no pattern left to learn from that feature.")
