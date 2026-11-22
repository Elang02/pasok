#!/usr/bin/env python3
"""
Does the ML gain change decisions, not just the error number?
============================================================

The loop stocks out when it forecasts BELOW realised demand. So the metric that matters is
the under-forecast: how often, and by how much, the forecast sits under the actual.
"""
from __future__ import annotations

import pathlib
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
H, N_JOBS = 90, 2

sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
sd["date"] = pd.to_datetime(sd["date"])
wide = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype("float32")
test, cv = wide.iloc[-H:], wide.rolling(7, min_periods=4).mean().shift(1).iloc[-H:]

idx = wide.index
F = {f"lag{k}": wide.shift(k) for k in (1, 7, 14, 28)}
F["roll7"] = wide.rolling(7, min_periods=3).mean().shift(1)
F["roll28"] = wide.rolling(28, min_periods=10).mean().shift(1)


def tile(v):
    return pd.DataFrame(np.tile(np.asarray(v, dtype="float32")[:, None], (1, wide.shape[1])),
                        index=idx, columns=wide.columns)


day = idx.day.to_numpy()
F["dow"] = tile(idx.dayofweek.to_numpy())
F["month"] = tile(idx.month.to_numpy())
F["is_payday"] = tile(((day >= 25) & (day <= 28)) | (day == 1) | (day == 2))
F["seasonal_month_index"] = (wide.groupby(wide.index.month).transform("mean") / wide.mean()).astype("float32")


def st(df):
    s = df.stack().rename("v")
    s.index = s.index.set_names(["date", "sku"])
    return s.to_frame().reset_index()


feats = list(F)
long = st(wide).rename(columns={"v": "sales"})
for n in feats:
    long = long.merge(st(F[n]).rename(columns={"v": n}), on=["date", "sku"], how="left")
long = long.dropna(subset=["lag28", "roll28"])
tr, te = long[long["date"] < test.index[0]], long[long["date"] >= test.index[0]]

m = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.06, num_leaves=63,
                      min_child_samples=50, subsample=0.8, subsample_freq=1,
                      colsample_bytree=0.8, random_state=7, n_jobs=N_JOBS, verbose=-1)
m.fit(tr[feats], tr["sales"])
pred = pd.Series(m.predict(te[feats]), index=pd.MultiIndex.from_arrays(
    [te["date"], te["sku"].astype(str)]))
piv = pred.unstack("sku").reindex_like(test)

print("=" * 80)
print("8. UNDER-FORECAST — the regime that causes stockouts")
print("=" * 80)
print(f"{'forecaster':22} {'under-rate':>11} {'median short%':>14} {'>30% short':>11} {'worst 1%':>10}")
for name, p in (("classical mean_7d", cv), ("lightgbm global", piv)):
    a, v = test.to_numpy().ravel(), p.to_numpy().ravel()
    ok = np.isfinite(a) & np.isfinite(v) & (a > 0)
    a, v = a[ok], v[ok]
    short = np.clip((a - v) / a, 0, None)          # 0 when forecast >= actual
    und = short > 0
    print(f"{name:22} {und.mean():>11.1%} {np.median(short[und]):>14.1%} "
          f"{(short > 0.30).mean():>11.1%} {np.quantile(short, 0.99):>10.1%}")

print()
print("=" * 80)
print("9. THE 11 SELLABLE=0 SKUs — would ML have called the surge?")
print("=" * 80)
zero = pd.read_csv(ROOT / "data/stock/position_snapshot.csv")
zero = zero[zero.sellable_units == 0]["sku"].tolist()
last6 = test.iloc[-6:]
cv_last, ml_last = cv.iloc[-6:], piv.iloc[-6:]
print(f"{'sku':9} {'realised':>9} {'classical':>10} {'ML':>9} {'cl short':>9} {'ML short':>9}")
tot_c = tot_m = 0
for sku in zero:
    a = last6[sku].sum()
    c = cv_last[sku].sum()
    v = ml_last[sku].sum()
    sc, sm = max(0, (a - c) / a), max(0, (a - v) / a)
    tot_c += sc * a
    tot_m += sm * a
    print(f"{sku:9} {a:>9,.0f} {c:>10,.0f} {v:>9,.0f} {sc:>8.1%} {sm:>8.1%}")
print(f"\nunit shortfall, classical: {tot_c:,.0f}   |   ML: {tot_m:,.0f}")
