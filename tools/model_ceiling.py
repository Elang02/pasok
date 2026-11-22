#!/usr/bin/env python3
"""
Estimators and the per-SKU ceiling — with NO lookahead.
=======================================================

Every forecast at day t may only use data strictly before t. Anything else leaks and
flatters the score, so each candidate is shifted explicitly.
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
H = 90

sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
sd["date"] = pd.to_datetime(sd["date"])
wide = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)

test = wide.iloc[-H:]
hist = wide.iloc[:-H]
full = wide                                     # for rolling, then shift(1)


def wape(a, p):
    m = np.isfinite(a) & np.isfinite(p)
    return float(np.abs(a[m] - p[m]).sum() / a[m].sum())


def pred_from_rolling(k: int) -> pd.DataFrame:
    """mean of the k days strictly before t (shift(1) kills the leak)."""
    return full.rolling(k, min_periods=max(2, k // 2)).mean().shift(1).iloc[-H:]


def pred_from_ewma(hl: float) -> pd.DataFrame:
    return full.ewm(halflife=hl, min_periods=2).mean().shift(1).iloc[-H:]


def pred_snaive(k: int) -> pd.DataFrame:
    """same weekday k weeks back: y[t-k*7]."""
    return full.shift(k * 7).iloc[-H:]


cands: dict[str, pd.DataFrame] = {"snaive_1w": pred_snaive(1)}
for k in (7, 10, 14, 21, 28):
    cands[f"mean_{k}d"] = pred_from_rolling(k)
for hl in (3, 7, 14, 21):
    cands[f"ewma_{hl}"] = pred_from_ewma(hl)

print("=" * 80)
print("4. ESTIMATORS (no lookahead) AND THE ORACLE CEILING")
print("=" * 80)
scores, pooled = {}, {}
for name, p in cands.items():
    p = p.reindex_like(test)
    per = pd.Series({c: wape(test[c].to_numpy(), p[c].to_numpy()) for c in test.columns})
    scores[name] = per
    pooled[name] = wape(test.to_numpy().ravel(), p.to_numpy().ravel())
    print(f"{name:12} pooled {pooled[name]:.4f}   per-SKU median {per.median():.4f}")

S = pd.DataFrame(scores)                    # index = sku, columns = estimator
best_global = min(pooled, key=pooled.get)
oracle = S.min(axis=1)

print()
print(f"best single estimator : {best_global}  (pooled {pooled[best_global]:.4f}, "
      f"per-SKU median {S[best_global].median():.4f})")
print(f"ORACLE per-SKU choice : per-SKU median {oracle.median():.4f}   <- needs hindsight")
gain = S[best_global].median() - oracle.median()
print(f"-> absolute value of per-SKU model choice: {gain:.4f} WAPE "
      f"({100 * gain / S[best_global].median():.1f}% relative, and unattainable)")

print()
print("estimator each SKU prefers (oracle):")
print(S.idxmin(axis=1).value_counts().to_string())

# ---------------- is the leftover weekday structure already in the estimator?
print()
print("=" * 80)
print("5. RESIDUAL BY WEEKDAY: flat mean vs seasonal naive")
print("=" * 80)
CAT = pd.read_csv(ROOT / "data/catalog/catalog.csv")
vol = CAT["volatility"]
floor = float((vol * np.sqrt(2 / np.pi)).median())
print(f"noise floor from the generator's own volatility (median SKU): {floor:.4f}")
print()
for name in ("snaive_1w", "mean_14d", "mean_28d"):
    p = cands[name].reindex_like(test)
    rel = ((test - p) / p.replace(0, np.nan)).stack().rename("rel").reset_index()
    rel["dow"] = rel["date"].dt.dayofweek
    dow = rel.groupby("dow").rel.mean()
    print(f"{name:12} residual by weekday: " + " ".join(f"{v:+.3f}" for v in dow.values))
    print(f"{'':12} spread {dow.std():.4f}  |  residual sd {rel.rel.std():.4f}")
