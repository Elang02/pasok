#!/usr/bin/env python3
"""
Does per-SKU ML beat the pooled estimate for event multipliers?
==============================================================

The generator's true model (src/catalog/generate.py:198) is

    demand = base_s * weekday * event_mult * noise_s

where `event_mult` is ONE array for the whole catalog. So every SKU carries the SAME
event uplift; any per-SKU variation a model fits is noise.

Test the consequence. For each event, fit the uplift on the EARLIER occurrences and
predict the LAST one:

    Model A (pooled)  : one multiplier per event, estimated across all SKUs
    Model B (per-SKU) : one multiplier per SKU, estimated on the same train data

If B loses out-of-sample, the extra capacity is fitting noise, and "ML for per-SKU
event patterns" is buying variance, not signal.
"""
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ---- data: daily sales per SKU (the walk carries the same sales the catalog made)
sd = pd.read_csv(ROOT / "data/stock/stock_daily.csv", usecols=["date", "sku", "sales"])
sd["date"] = pd.to_datetime(sd["date"])
sd = sd.sort_values(["sku", "date"])

# ---- event table: the generator's own calendar
ev = pd.read_csv(ROOT / "data/catalog/events.csv")
ev["date"] = pd.to_datetime(ev["date"])

# ---- baseline: trailing 28-day mean of the same weekday, so weekday shape is out
sd["baseline"] = (sd.groupby("sku", observed=True)["sales"]
                    .transform(lambda s: s.rolling(28, min_periods=14).mean()))
sd = sd.dropna(subset=["baseline"])

# ---- label each day with its event
day_ev = ev.groupby("date")["event"].first()
sd["event"] = sd["date"].map(day_ev)
w = sd[sd["event"].notna()].copy()
w["uplift"] = w["sales"] / w["baseline"].replace(0, np.nan)
w = w.dropna(subset=["uplift"])

# ---- split occurrences per event by year
w["year"] = w["date"].dt.year
print("=== occurrences per event (years present) ===")
for e, g in w.groupby("event"):
    print(f"  {e:10} years: {sorted(g.year.unique())}")
print()

print(f"{'event':10} {'n_train':>8} {'n_test':>7} "
      f"{'pooled_mult':>11} {'wape_pooled':>11} {'wape_perSKU':>11}  verdict")
rows = []
for e, g in w.groupby("event"):
    years = sorted(g.year.unique())
    if len(years) < 2:
        print(f"  {e:10} skipped: only {len(years)} occurrence-year(s)")
        continue
    train, test = g[g.year < years[-1]], g[g.year == years[-1]]
    if len(train) == 0 or len(test) == 0:
        continue

    # Model A: one multiplier for all SKUs, median of the per-SKU lifts
    pooled = float(train.groupby("sku")["uplift"].median().median())

    # Model B: per-SKU multiplier, falls back to pooled where unseen
    per_sku = train.groupby("sku")["uplift"].median()
    test = test.copy()
    test["pred_pooled"] = pooled
    test["pred_per_sku"] = test["sku"].map(per_sku).fillna(pooled)

    def wape(actual, pred):
        m = actual.notna() & pred.notna()
        return float((actual[m] - pred[m]).abs().sum() / actual[m].sum())

    wa, wb = wape(test["uplift"], test["pred_pooled"]), wape(test["uplift"], test["pred_per_sku"])
    verdict = "pooled wins" if wa < wb else "per-SKU wins"
    rows.append({"event": e, "n_train": train.sku.nunique(), "n_test": test.sku.nunique(),
                 "pooled_mult": round(pooled, 3), "wape_pooled": round(wa, 4),
                 "wape_per_sku": round(wb, 4), "verdict": verdict})
    print(f"{e:10} {train.sku.nunique():>8} {test.sku.nunique():>7} "
          f"{pooled:>11.3f} {wa:>11.4f} {wb:>11.4f}  {verdict}")

print()
print("=== the true multiplier is shared: spread of the FITTED per-SKU lift around it ===")
for e, g in w.groupby("event"):
    per = g.groupby(["year", "sku"])["uplift"].mean().groupby("year").agg(["mean", "std"])
    print(f"  {e:10} within-year SD of per-SKU lift: "
          + ", ".join(f"{int(y)}:{r['std']:.3f}" for y, r in per.iterrows()))
print()
print("Since the generator applies ONE multiplier per day, that SD is pure noise.")
