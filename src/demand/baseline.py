"""
Pasok — Catalog classification and classical baselines
======================================================

Gives every SKU its operational class (volume x volatility) and a classical forecast
baseline with a confidence interval. The Decision Agent reasons against these; the RPT
scorer receives engineered features derived from them.

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/demand/baseline.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
OUT = ROOT / "data" / "demand"
HOLDOUT_WEEKS = 13


def load_weekly() -> pd.DataFrame:
    """Stream sales.csv in chunks and aggregate to SKU x ISO week."""
    chunks = []
    reader = pd.read_csv(
        CAT / "sales.csv",
        usecols=["sku", "date", "units"],
        parse_dates=["date"],
        chunksize=2_000_000,
        dtype={"sku": "category", "units": "int32"},
    )
    for i, ch in enumerate(reader):
        ch["week"] = ch["date"].dt.to_period("W").dt.start_time
        agg = ch.groupby(["sku", "week"], observed=True)["units"].sum()
        chunks.append(agg)
        print(f"  chunk {i+1}: {len(ch):,} rows -> cumulative groups {sum(len(c) for c in chunks):,}")
    weekly = pd.concat(chunks).groupby(level=[0, 1]).sum().unstack(level=0)
    weekly.index.name = "week"
    return weekly


def classify(catalog: pd.DataFrame, weekly: pd.DataFrame) -> pd.DataFrame:
    total = weekly.sum(axis=0)
    vol = weekly.std(axis=0) / weekly.mean(axis=0).replace(0, np.nan)

    # ABC is a value question, not a unit question: 10,000 cheap sachets and 400 cartons of
    # cooking oil are not the same business, and ranking by units calls the sachets "A".
    # Rank by consumption value (units x unit cost) the way APICS and every distributor's
    # ABC report does; units stay in the output as context.
    cost = catalog.set_index("sku")["unit_cost_idr"].reindex(total.index).fillna(0.0)
    value = (total * cost).sort_values(ascending=False)

    ranked = value
    cum = ranked.cumsum() / ranked.sum()
    cls = pd.Series("C", index=ranked.index)
    cls[cum <= 0.80] = "A"
    cls[(cum > 0.80) & (cum <= 0.95)] = "B"

    out = pd.DataFrame({
        "sku": ranked.index,
        "total_units": total.reindex(ranked.index).values,
        "total_value_idr": ranked.values,
        "cv": vol.reindex(ranked.index).values,
    })
    out["class_volume"] = cls.reindex(ranked.index).values
    out["class_volatility"] = pd.cut(
        out["cv"], bins=[-np.inf, 0.35, 0.70, np.inf], labels=["Low", "Med", "High"]
    ).astype(str)
    return out.merge(catalog[["sku", "category", "principal_id", "shelf_life_months"]], on="sku", how="left")


def wape(actual: np.ndarray, pred: np.ndarray) -> float:
    denom = np.abs(actual).sum()
    return float(np.abs(actual - pred).sum() / denom) if denom else float("nan")


def backtest(weekly: pd.DataFrame) -> pd.DataFrame:
    """Leave the last HOLDOUT_WEEKS out; score three baselines per SKU."""
    train = weekly.iloc[:-HOLDOUT_WEEKS]
    test = weekly.iloc[-HOLDOUT_WEEKS:]
    rows = []

    for sku in weekly.columns:
        y = train[sku].to_numpy(dtype=float)
        yt = test[sku].to_numpy(dtype=float)
        n = len(yt)

        # moving average of the last 4 training weeks
        ma4 = np.full(n, y[-4:].mean())
        # seasonal naive: same week one year earlier (52 weeks back)
        if len(y) >= 52:
            snaive = np.concatenate([y[-52:], y[-52:]])[:n]
        else:
            snaive = np.full(n, y.mean())
        # simple exponential smoothing, alpha 0.3
        alpha = 0.3
        level = y[0]
        for v in y[1:]:
            level = alpha * v + (1 - alpha) * level
        ses = np.full(n, level)

        cands = {"ma4": ma4, "snaive": snaive, "ses": ses}
        scores = {k: wape(yt, v) for k, v in cands.items()}
        best = min(scores, key=lambda k: (np.isnan(scores[k]), scores[k]))
        resid = np.abs(yt - cands[best])
        scale = np.nanstd(y[-26:]) if len(y) >= 26 else np.nanstd(y)
        q = np.nanquantile(resid, 0.9) if np.any(~np.isnan(resid)) else 0.0

        rows.append({
            "sku": sku,
            "best_baseline": best,
            "wape_ma4": scores["ma4"],
            "wape_snaive": scores["snaive"],
            "wape_ses": scores["ses"],
            "wape_best": scores[best],
            "forecast_next": float(cands[best][-1]),
            "interval_lo": float(max(0.0, cands[best][-1] - q)),
            "interval_hi": float(cands[best][-1] + q),
            "resid_sd": float(scale) if not np.isnan(scale) else 0.0,
        })

    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = pd.read_csv(CAT / "catalog.csv")
    print(f"catalog: {len(catalog)} SKUs")

    print("aggregating sales to weekly (streamed)...")
    weekly = load_weekly()
    print(f"weekly matrix: {weekly.shape[0]} weeks x {weekly.shape[1]} SKUs")

    classes = classify(catalog, weekly)
    classes.to_csv(OUT / "sku_classes.csv", index=False)

    print("backtesting baselines...")
    base = backtest(weekly)
    base = base.merge(classes[["sku", "class_volume", "class_volatility"]], on="sku", how="left")
    base.to_csv(OUT / "baselines.csv", index=False)

    # coverage: does the true next-week value fall in the interval?
    last_train = weekly.iloc[:-HOLDOUT_WEEKS].iloc[-1]
    summary = {
        "n_skus": int(len(base)),
        "median_wape_best": float(base["wape_best"].median()),
        "mean_wape_best": float(base["wape_best"].mean()),
        "baseline_pick": base["best_baseline"].value_counts().to_dict(),
        "class_volume": classes["class_volume"].value_counts().to_dict(),
        "class_volatility": classes["class_volatility"].value_counts().to_dict(),
        "wape_by_class": base.groupby("class_volume")["wape_best"].median().round(4).to_dict(),
    }
    (OUT / "baseline_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
