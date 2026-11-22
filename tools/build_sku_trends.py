"""Per-SKU trend facts, so "how is this SKU moving" is a stored answer, not a guess.

Reads the 2023-2026 sales history and the v2 catalogue, and writes:

  data/demand/sku_trends.csv   one row per SKU
  data/demand/trend_summary.json

Metrics are deliberately simple and explainable to a buyer:

  units_12m, value_12m      last 52 weeks
  yoy_pct                   last 52 weeks vs the 52 before
  slope_pct_month           OLS on log monthly units, last 18 months, in percent/month
  cv_monthly                std/mean of monthly units, the volatility the buffer uses
  peak_month                calendar month with the highest average units
  trend_label               growing / flat / declining, from slope and yoy together

Run: .venv/bin/python tools/build_sku_trends.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SALES = ROOT / "data" / "catalog" / "sales.csv"
CATALOG = ROOT / "data" / "catalog" / "catalog.csv"
OUT = ROOT / "data" / "demand"


def main() -> int:
    sales = pd.read_csv(SALES, parse_dates=["date"])
    catalog = pd.read_csv(CATALOG)[["sku", "category", "unit_cost_idr"]]

    sales["month"] = sales["date"].dt.to_period("M")
    monthly = sales.groupby(["sku", "month"], as_index=False)["units"].sum()
    monthly["month_ts"] = monthly["month"].dt.to_timestamp()

    last_day = sales["date"].max()
    start_12m = last_day - pd.Timedelta(days=364)
    start_prev = start_12m - pd.Timedelta(days=364)

    recent = sales[sales["date"] > start_12m].groupby("sku")["units"].sum()
    prior = sales[(sales["date"] > start_prev) & (sales["date"] <= start_12m)].groupby("sku")["units"].sum()

    rows = []
    for sku, g in monthly.groupby("sku"):
        g = g.sort_values("month_ts")
        tail18 = g[g["month_ts"] >= last_day - pd.DateOffset(months=18)]
        y = np.log1p(tail18["units"].to_numpy(dtype=float))
        x = np.arange(len(y), dtype=float)
        slope = float(np.polyfit(x, y, 1)[0]) if len(y) >= 6 else 0.0
        slope_pct = (np.exp(slope) - 1.0) * 100.0
        u12 = float(recent.get(sku, 0.0))
        u_prev = float(prior.get(sku, 0.0))
        yoy = (u12 / u_prev - 1.0) * 100.0 if u_prev > 0 else np.nan
        mu, sd = float(g["units"].mean()), float(g["units"].std(ddof=0))
        cv = sd / mu if mu > 0 else np.nan
        by_month = g.assign(m=g["month_ts"].dt.month).groupby("m")["units"].mean()
        peak = int(by_month.idxmax()) if len(by_month) else 0
        # Label answers "bigger or smaller than last year"; momentum answers "is the
        # recent direction different from that". Mixing the two produced SKUs that grew
        # 1.6% year on year and were still called declining.
        if np.isfinite(yoy) and yoy > 5:
            label = "growing"
        elif np.isfinite(yoy) and yoy < -5:
            label = "declining"
        else:
            label = "flat"
        if slope_pct > 0.5:
            momentum = "accelerating"
        elif slope_pct < -0.5:
            momentum = "slowing"
        else:
            momentum = "steady"
        rows.append({
            "sku": sku,
            "units_12m": u12,
            "yoy_pct": round(yoy, 2) if np.isfinite(yoy) else None,
            "slope_pct_month": round(slope_pct, 3),
            "cv_monthly": round(cv, 3) if np.isfinite(cv) else None,
            "peak_month": peak,
            "trend_label": label,
            "momentum": momentum,
        })

    trends = pd.DataFrame(rows).merge(catalog, on="sku", how="left")
    trends["value_12m"] = trends["units_12m"] * trends["unit_cost_idr"]
    trends = trends[["sku", "category", "units_12m", "value_12m", "yoy_pct",
                     "slope_pct_month", "cv_monthly", "peak_month", "trend_label", "momentum"]]
    trends.to_csv(OUT / "sku_trends.csv", index=False)

    summary = {
        "window": {"last_day": str(last_day.date()), "months": int(monthly["month"].nunique())},
        "skus": int(len(trends)),
        "label_counts": trends["trend_label"].value_counts().to_dict(),
        "momentum_counts": trends["momentum"].value_counts().to_dict(),
        "yoy_median_pct": round(float(trends["yoy_pct"].median()), 2),
        "yoy_positive_share": round(float((trends["yoy_pct"] > 0).mean()), 3),
        "cv_median": round(float(trends["cv_monthly"].median()), 3),
        "peak_month_mode": int(trends["peak_month"].mode().iloc[0]),
        "by_category": trends.groupby("category").agg(
            skus=("sku", "count"),
            value_12m=("value_12m", "sum"),
            median_yoy=("yoy_pct", "median"),
        ).round(2).reset_index().to_dict(orient="records"),
    }
    (OUT / "trend_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"{summary['skus']} SKUs, {summary['window']['months']} months")
    print("labels", summary["label_counts"])
    print("median YoY %", summary["yoy_median_pct"], "| positive share", summary["yoy_positive_share"])
    print(trends.sort_values("value_12m", ascending=False).head(5)[
        ["sku", "category", "units_12m", "value_12m", "yoy_pct", "trend_label"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
