#!/usr/bin/env python3
"""
A real ML model against the classical estimators, same test window.
===================================================================

Global LightGBM across all 600 SKUs, fed the features that actually exist here: lags,
weekday, month, payday week, and the known event multiplier. Same held-out 90 days.

Built on the WIDE frame (1092 x 600) so every feature is a vectorised shift/rolling,
then stacked once. The per-SKU pandas-lambda version was the thing that timed out.
"""
from __future__ import annotations

import pathlib
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
H = 90
N_JOBS = 2                      # leave room; the box has 4 vCPU and hermes needs them

sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
sd["date"] = pd.to_datetime(sd["date"])
wide = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype("float32")
print(f"wide frame: {wide.shape[0]} days x {wide.shape[1]} SKUs")

test = wide.iloc[-H:]
cv = wide.rolling(7, min_periods=4).mean().shift(1)          # classical baseline


def wape(a, p):
    m = np.isfinite(a) & np.isfinite(p)
    return float(np.abs(a[m] - p[m]).sum() / a[m].sum())


# ---------------- features, all vectorised on the wide frame
F: dict[str, pd.DataFrame] = {}
for k in (1, 7, 14, 28):
    F[f"lag{k}"] = wide.shift(k)
for k in (7, 28):
    F[f"roll{k}"] = wide.rolling(k, min_periods=max(3, k // 3)).mean().shift(1)

idx = wide.index
F["dow"] = pd.DataFrame(np.tile(idx.dayofweek.to_numpy()[:, None], (1, wide.shape[1])),
                        index=idx, columns=wide.columns).astype("float32")
F["month"] = pd.DataFrame(np.tile(idx.month.to_numpy()[:, None], (1, wide.shape[1])),
                          index=idx, columns=wide.columns).astype("float32")
day = idx.day.to_numpy()
pay = (((day >= 25) & (day <= 28)) | (day == 1) | (day == 2)).astype("float32")
F["is_payday"] = pd.DataFrame(np.tile(pay[:, None], (1, wide.shape[1])),
                              index=idx, columns=wide.columns)

ev = pd.read_csv(ROOT / "data/catalog/events.csv")
ev["date"] = pd.to_datetime(ev["date"])
em = ev.groupby("date")["factor"].max().reindex(idx).fillna(1.0).astype("float32")
F["event_mult"] = pd.DataFrame(np.tile(em.to_numpy()[:, None], (1, wide.shape[1])),
                               index=idx, columns=wide.columns)

FEATS = list(F)
print(f"features: {FEATS}")

# stack once: long = (days x skus) rows
def stack(df: pd.DataFrame, name_col="sku") -> pd.DataFrame:
    s = df.stack().rename("v")
    s.index = s.index.set_names(["date", name_col])
    return s.to_frame().reset_index()


long = stack(wide.rename(columns={c: c for c in wide.columns}), "sku").rename(columns={"v": "sales"})
for name, df in F.items():
    long = long.merge(stack(df, "sku").rename(columns={"v": name}), on=["date", "sku"], how="left")
long = long.dropna(subset=["lag28", "roll28"])
long["sku"] = long["sku"].astype("category")

tr = long[long["date"] < test.index[0]]
te = long[long["date"] >= test.index[0]]
print(f"train rows {len(tr):,} | test rows {len(te):,}")

model = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.06, num_leaves=63,
                          min_child_samples=50, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.8, random_state=7, n_jobs=N_JOBS, verbose=-1)
model.fit(tr[FEATS], tr["sales"], categorical_feature=[])

pred = pd.Series(model.predict(te[FEATS]), index=pd.MultiIndex.from_arrays(
    [te["date"], te["sku"].astype(str)]))
piv = pred.unstack("sku").reindex_like(test)

print()
print("=" * 80)
print("6. LIGHTGBM (global, 600 SKUs) vs CLASSICAL, SAME 90-DAY TEST WINDOW")
print("=" * 80)
for name, p in (("mean_7d (classical)", cv), ("lightgbm (global)", piv)):
    p = p.reindex_like(test)
    pooled = wape(test.to_numpy().ravel(), p.to_numpy().ravel())
    per = pd.Series({c: wape(test[c].to_numpy(), p[c].to_numpy()) for c in test.columns})
    print(f"{name:22} pooled {pooled:.4f}   per-SKU median {per.median():.4f}   "
          f"p90 {per.quantile(.9):.4f}")

cat = pd.read_csv(ROOT / "data/catalog/catalog.csv")
floor = float((cat["volatility"] * np.sqrt(2 / np.pi)).median())
print(f"\nnoise floor (generator volatility, median SKU): {floor:.4f}")
print()
imp = pd.Series(model.feature_importances_, index=FEATS).sort_values(ascending=False)
print("feature importance (split count):")
print(imp.to_string())
