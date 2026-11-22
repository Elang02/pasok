#!/usr/bin/env python
"""Measure what the policy does, and set it beside numbers from outside this repo.

The five proposal targets are written against "current practice". This repo has no record of
that practice: every candidate baseline here is a replay of data this repo generated itself, so
comparing the agent against it measures the generator, not the policy. This tool therefore
reports absolute outcomes and puts each one beside a published benchmark, which a judge can
check without trusting our own data.

Usage
-----
    .venv/bin/python tools/outcome_measure.py --replay replay2026_v28
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "data" / "sim"
OUT = ROOT / "data" / "agents" / "outcomes.json"

WINDOW = (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-11"))

BENCHMARKS = {
    "fill": {
        "value": 0.92,
        "label": "retail shelf availability: about 8% of items out of stock on a store visit",
        "source": "Corsten & Gruen, out-of-stock rates; GMA 8.3% in physical stores",
        "url": "https://www.semanticscholar.org/paper/bad6469da2fd41a7d787d4b4b4b43b996f5eb68c",
    },
    "dio_days": {
        "value": 56.67,
        "label": "PT Indofood CBP days of inventory, 2025 (43.73 in 2016)",
        "source": "Feranika dkk., Jurnal Manajemen Terapan dan Keuangan 15(3), 2026",
        "url": "https://online-journal.unja.ac.id/mankeu/article/view/60238",
    },
    "shrink_pct_sales": {
        "value": 0.0270,
        "label": "supermarket shrink, 2.70% of sales (range 1.76-3.10%)",
        "source": "National Supermarket Shrink Survey",
        "url": "http://wheresmyshrink.com/executivesummary.html",
    },
}


def load(replay: str) -> dict[str, pd.DataFrame]:
    d = SIM / replay
    if not (d / "world" / "stock_daily.csv").exists():
        raise SystemExit(f"{d} has no stock_daily.csv")
    stock = pd.read_csv(d / "world" / "stock_daily.csv", parse_dates=["date"])
    stock = stock[(stock["date"] >= WINDOW[0]) & (stock["date"] <= WINDOW[1])].copy()
    classes = pd.read_csv(ROOT / "data" / "demand" / "sku_classes.csv")[["sku", "class_volume"]]
    catalog = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")[["sku", "unit_cost_idr"]]
    stock = stock.merge(classes, on="sku", how="left").merge(catalog, on="sku", how="left")
    days = (WINDOW[1] - WINDOW[0]).days + 1
    months = days / 30.44
    # expiry is logged per review day, not per SKU: days.csv carries expired_units
    days_csv = pd.read_csv(d / "days.csv", parse_dates=["day"])
    days_csv = days_csv[(days_csv["day"] >= WINDOW[0]) & (days_csv["day"] <= WINDOW[1])]
    return {"stock": stock, "days": days_csv, "months": months, "name": replay}


def measure(sim: dict[str, pd.DataFrame]) -> dict:
    stock, months = sim["stock"], sim["months"]
    out: dict[str, dict] = {}

    for cls in ("A", "B", "C"):
        s = stock[stock["class_volume"] == cls]
        sold = float(s["sales"].sum())
        lost = float(s["lost_sales"].sum())
        out[f"fill_{cls}"] = {
            "value": round(sold / (sold + lost), 4) if sold + lost else None,
            "unit": "share of demand served",
            "n_skus": int(s["sku"].nunique()),
        }
        # an incident is a SKU-month in which the shelf ran dry
        s = s.assign(month=s["date"].dt.to_period("M"))
        dry = s[s["lost_sales"] > 0].groupby(["sku", "month"]).size().reset_index()
        out[f"stockout_{cls}_per_month"] = {
            "value": round(len(dry) / months, 1),
            "unit": "SKU-months with demand lost, per month",
        }
        s = s.assign(held_value=s["on_hand"] * s["unit_cost_idr"])
        out[f"inventory_{cls}_idr"] = {
            "value": round(float(s.groupby("date")["held_value"].sum().mean()), 0),
            "unit": "average stock on hand, rupiah",
        }

    units = float(sim["days"]["expired_units"].sum())
    stock = stock.assign(held_value=stock["on_hand"] * stock["unit_cost_idr"])
    cogs = float((stock["sales"] * stock["unit_cost_idr"]).sum())
    # Value the write-off with each SKU's own cost. The earlier version multiplied total units by
    # the catalogue's average cost, which flatters the number when the expired items are the cheap
    # ones (one-month bread), and it disagreed with expired.csv by nearly half.
    exp_path = ROOT / "data" / "sim" / str(sim.get("name", "")) / "expired.csv"
    value = None
    if exp_path.exists():
        exp = pd.read_csv(exp_path)
        if "qty" in exp.columns and "sku" in exp.columns:
            _cat = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")[["sku", "unit_cost_idr"]]
            exp = exp.merge(_cat, on="sku", how="left")
            value = float((exp["qty"] * exp["unit_cost_idr"].fillna(0.0)).sum())
    if value is None:
        value = units * (cogs / max(1.0, float(stock["sales"].sum())))
    out["expiry_units_per_month"] = {"value": round(units / months, 0), "unit": "units, per month"}
    out["expiry_idr_per_month"] = {"value": round(value / months, 0), "unit": "rupiah, per month"}
    out["expiry_pct_of_cogs"] = {
        "value": round(value / cogs, 4) if cogs else None,
        "unit": "share of cost of goods sold",
    }
    daily_value = stock.groupby("date")["held_value"].sum()
    out["inventory_idr"] = {"value": round(float(daily_value.mean()), 0), "unit": "average, rupiah"}
    out["dio_days"] = {
        "value": round(float(daily_value.mean()) / (cogs / len(daily_value)), 1) if cogs else None,
        "unit": "days of inventory",
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", default="replay2026_v28")
    args = ap.parse_args()

    sim = load(args.replay)
    outcomes = measure(sim)

    # where a benchmark exists, say whether we are on the better side of it
    checks = {
        "fill_A": ("fill", "higher"),
        "fill_B": ("fill", "higher"),
        "fill_C": ("fill", "higher"),
        "dio_days": ("dio_days", "lower"),
        "expiry_pct_of_cogs": ("shrink_pct_sales", "lower"),
    }
    board = []
    for key, (bench, better) in checks.items():
        b = BENCHMARKS[bench]
        ours = outcomes[key]["value"]
        if ours is None:
            ok = None
        elif better == "higher":
            ok = ours >= b["value"]
        else:
            ok = ours <= b["value"]
        board.append({
            "metric": key,
            "ours": ours,
            "unit": outcomes[key]["unit"],
            "benchmark": b["value"],
            "benchmark_label": b["label"],
            "benchmark_source": b["source"],
            "benchmark_url": b["url"],
            "better_than_benchmark": ok,
        })

    payload = {
        "replay": args.replay,
        "window": f"{WINDOW[0].date()}..{WINDOW[1].date()}",
        "outcomes": outcomes,
        "against_published": board,
        "note": (
            "No manual-policy baseline is used: this repo has no record of the distributor's "
            "current practice, so a comparison against a replay we generated would measure the "
            "generator. Published benchmarks stand in for the outside world."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))

    print(f"replay {args.replay}  window {payload['window']}")
    print(f"{'metric':24} {'ours':>12} {'benchmark':>12}  better?")
    for r in board:
        ours = "n/a" if r["ours"] is None else f"{r['ours']:,.4g}"
        print(f"{r['metric']:24} {ours:>12} {r['benchmark']:>12}  {r['better_than_benchmark']}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
