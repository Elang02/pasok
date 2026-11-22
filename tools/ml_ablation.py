#!/usr/bin/env python3
"""
Ablation: is the ML gain real, or is it the leaked event table?
==============================================================

The pipeline's discipline (src/agents/stock_position.py docstring): the agents never read
events.csv or any generator intent. So a model that gets `event_mult` is cheating relative
to the build. This runs the honest version and measures the gap.
"""
from __future__ import annotations

import pathlib
import time
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


def wape(a, p):
    m = np.isfinite(a) & np.isfinite(p)
    return float(np.abs(a[m] - p[m]).sum() / a[m].sum())


def per_sku(p):
    return pd.Series({c: wape(test[c].to_numpy(), p[c].to_numpy()) for c in test.columns})


idx = wide.index
F: dict[str, pd.DataFrame] = {}
for k in (1, 7, 14, 28):
    F[f"lag{k}"] = wide.shift(k)
for k in (7, 28):
    F[f"roll{k}"] = wide.rolling(k, min_periods=max(3, k // 3)).mean().shift(1)


def tile(v, name, dtype="float32"):
    return pd.DataFrame(np.tile(np.asarray(v, dtype=dtype)[:, None], (1, wide.shape[1])),
                        index=idx, columns=wide.columns)


day = idx.day.to_numpy()
F["dow"] = tile(idx.dayofweek.to_numpy(), "dow")
F["month"] = tile(idx.month.to_numpy(), "month")
F["is_payday"] = tile(((day >= 25) & (day <= 28)) | (day == 1) | (day == 2), "pay")

# the "learned" event signal the pipeline could legitimately hold: the registry's learned
# multipliers, which are derived from history, not from the generator's table
reg = pd.read_csv(ROOT / "data/demand/event_registry.csv")
events = pd.read_csv(ROOT / "data/catalog/events.csv")
events["date"] = pd.to_datetime(events["date"])
print("recoverable-event proxy: monthly seasonal index learned from the SKU's own history")
month_idx = wide.groupby(wide.index.month).transform("mean") / wide.mean()
F["seasonal_month_index"] = month_idx.astype("float32")

HONEST = [k for k in F if k != "event_mult"]
LEAK = ["event_mult"]


def build(feats: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    def st(df):
        s = df.stack().rename("v")
        s.index = s.index.set_names(["date", "sku"])
        return s.to_frame().reset_index()
    long = st(wide).rename(columns={"v": "sales"})
    for n in feats:
        long = long.merge(st(F[n]).rename(columns={"v": n}), on=["date", "sku"], how="left")
    long = long.dropna(subset=["lag28", "roll28"])
    return long[long["date"] < test.index[0]], long[long["date"] >= test.index[0]]


def fit_eval(feats: list[str], label: str):
    t0 = time.time()
    tr, te = build(feats)
    m = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.06, num_leaves=63,
                          min_child_samples=50, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.8, random_state=7, n_jobs=N_JOBS, verbose=-1)
    m.fit(tr[feats], tr["sales"])
    pred = pd.Series(m.predict(te[feats]), index=pd.MultiIndex.from_arrays(
        [te["date"], te["sku"].astype(str)]))
    piv = pred.unstack("sku").reindex_like(test)
    per = per_sku(piv)
    pooled = wape(test.to_numpy().ravel(), piv.to_numpy().ravel())
    dt = time.time() - t0
    print(f"{label:34} pooled {pooled:.4f}  per-SKU median {per.median():.4f}  "
          f"p90 {per.quantile(.9):.4f}   [{dt:.0f}s]")
    return per


print()
print("=" * 92)
print("7. ABLATION — same test window, same model family")
print("=" * 92)
base = per_sku(cv)
print(f"{'classical mean_7d':34} pooled {wape(test.to_numpy().ravel(), cv.to_numpy().ravel()):.4f}"
      f"  per-SKU median {base.median():.4f}  p90 {base.quantile(.9):.4f}")

honest = fit_eval(HONEST, "lightgbm, legit features only")

# the leak model: add the generator's own event factor
F["event_mult"] = tile(
    events.groupby("date")["factor"].max().reindex(idx).fillna(1.0).to_numpy(), "em")
leaked = fit_eval(HONEST + LEAK, "lightgbm + generator event_mult (LEAK)")

print()
print(f"legit ML gain over classical : {100 * (base.median() - honest.median()) / base.median():.1f}% relative")
print(f"extra gain if we cheated      : {100 * (honest.median() - leaked.median()) / honest.median():.1f}% relative")
