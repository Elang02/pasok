#!/usr/bin/env python3
"""
Two questions, measured
=======================

1. Does a per-SKU event multiplier beat one shared multiplier?  (clean baseline)
2. Is there any learnable structure left that more model capacity could capture?

Run:  .venv/bin/python tools/forecast_ceiling.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
HORIZON = 90          # days held out at the end
PRE = 28              # days before an event used as its local baseline


def load() -> pd.DataFrame:
    sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
    sd["date"] = pd.to_datetime(sd["date"])
    return sd.sort_values(["sku", "date"])


def wape(actual: np.ndarray, pred: np.ndarray) -> float:
    m = np.isfinite(actual) & np.isfinite(pred)
    return float(np.abs(actual[m] - pred[m]).sum() / actual[m].sum())


# ---------------------------------------------------------------- 1. event test
def event_test(sd: pd.DataFrame) -> pd.DataFrame:
    """Uplift vs the 28 days BEFORE each event; train on earlier years, test the last."""
    ev = pd.read_csv(ROOT / "data/catalog/events.csv")
    ev["date"] = pd.to_datetime(ev["date"])

    # collapse to event spans: first and last day of each (event, year)
    ev["year"] = ev["date"].dt.year
    spans = ev.groupby(["event", "year"])["date"].agg(["min", "max"]).reset_index()

    wide = sd.pivot(index="date", columns="sku", values="sales").sort_index()
    out = []
    for r in spans.itertuples():
        before = wide.loc[r.min - pd.Timedelta(days=PRE): r.min - pd.Timedelta(days=1)]
        during = wide.loc[r.min:r.max]
        if len(before) < PRE or len(during) == 0:
            continue
        base = before.mean()
        lift = (during.mean() / base.replace(0, np.nan)).dropna()
        for sku, v in lift.items():
            if np.isfinite(v):
                out.append({"event": r.event, "year": r.year, "sku": sku, "uplift": float(v)})
    df = pd.DataFrame(out)

    print("=" * 78)
    print("1. PER-SKU vs SHARED EVENT MULTIPLIER  (train on earlier years, test the last)")
    print("=" * 78)
    print(f"{'event':10} {'years':>14} {'shared':>8} {'WAPE_shared':>12} "
          f"{'WAPE_perSKU':>12}  verdict")
    rows = []
    for e, g in df.groupby("event"):
        years = sorted(g.year.unique())
        if len(years) < 2:
            continue
        train, test = g[g.year < years[-1]], g[g.year == years[-1]]
        shared = float(train.groupby("sku")["uplift"].median().median())
        per_sku = train.groupby("sku")["uplift"].median()

        a = test["uplift"].to_numpy()
        ws = wape(a, np.full(len(test), shared))
        wp = wape(a, test["sku"].map(per_sku).fillna(shared).to_numpy())
        verdict = "shared wins" if ws < wp else "per-SKU wins"
        rows.append({"event": e, "shared": round(shared, 3), "wape_shared": round(ws, 4),
                     "wape_per_sku": round(wp, 4), "verdict": verdict})
        print(f"{e:10} {str(years):>14} {shared:>8.3f} {ws:>12.4f} {wp:>12.4f}  {verdict}")
    print()
    wins = sum(1 for r in rows if r["verdict"] == "shared wins")
    print(f"-> shared multiplier wins {wins}/{len(rows)} events out of sample")
    print()
    return pd.DataFrame(rows)


# ------------------------------------------------------- 2. estimator / capacity
def estimator_test(sd: pd.DataFrame) -> None:
    """Can more model capacity beat a one-week seasonal naive? Compare per SKU."""
    wide = sd.pivot(index="date", columns="sku", values="sales").sort_index().astype(float)
    test = wide.iloc[-HORIZON:]
    hist = wide.iloc[:-HORIZON]                    # everything before the holdout

    cands: dict[str, pd.DataFrame] = {}
    # what the pipeline uses as its control
    cands["snaive (t-7)"] = test.shift(7).fillna(hist.iloc[-7:].iloc[0]) if False else \
        pd.concat([hist.iloc[-7:], test]).shift(7).iloc[-HORIZON:]
    # seasonal means over 2, 4 and 8 weeks: more history, less noise
    for k in (2, 4, 8):
        stack = pd.concat([hist.iloc[-7 * k:], test])
        rolled = stack.rolling(7 * k, min_periods=7).mean().iloc[-HORIZON:]
        cands[f"seasonal_mean_{k}w"] = rolled

    print("=" * 78)
    print("2. DOES MORE CAPACITY BEAT THE ONE-WEEK SEASONAL NAIVE?")
    print("=" * 78)
    act = test.to_numpy().ravel()
    act = test
    print(f"{'estimator':18} {'pooled WAPE':>12} {'per-SKU median':>15} {'per-SKU p90':>12}")
    res = {}
    for name, pred in cands.items():
        p = pred.reindex_like(test)
        pooled = wape(test.to_numpy().ravel(), p.to_numpy().ravel())
        per = [wape(test[c].to_numpy(), p[c].to_numpy()) for c in test.columns]
        per = pd.Series(per).replace([np.inf, -np.inf], np.nan).dropna()
        res[name] = pooled
        print(f"{name:18} {pooled:>12.4f} {per.median():>15.4f} {per.quantile(.9):>12.4f}")

    print()
    cat = pd.read_csv(ROOT / "data/catalog/catalog.csv")
    vol = cat["volatility"]
    floor = float((vol * np.sqrt(2 / np.pi)).median())
    print(f"noise floor (median SKU, from the generator's volatility): {floor:.4f}")
    best = min(res, key=res.get)
    print(f"best estimator: {best} at pooled WAPE {res[best]:.4f}")
    print()
    print("Read this way: if every candidate lands within a hair of the floor, the error is")
    print("the generator's noise, and no amount of capacity removes it.")


if __name__ == "__main__":
    s = load()
    event_test(s)
    estimator_test(s)
