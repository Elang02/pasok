"""
Pasok — Event registry and per-SKU ramp fit
===========================================

Turns the generator's ground-truth event calendar into two agent-facing products:

  data/demand/event_registry.csv   event, window, uplift class (what the agent may know)
  data/demand/sku_ramps.csv        per SKU x event: days_to_peak, peak_mult, ramp class

The ramp profile is what separates Pasok from a calendar-feature model: the agent learns
HOW demand builds and decays around each event, per SKU, instead of assuming a flat bump.
Method reference: the E2 learner proven on M5 in Phase 3.

Run
---
    cd <repo root>
    .venv/bin/python src/demand/event_ramp.py
"""

from __future__ import annotations

import json
from pathlib import Path

import csv
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
OUT = ROOT / "data" / "demand"
if str(ROOT) not in sys.path:  # run as a script, import the package by its root
    sys.path.insert(0, str(ROOT))
WINDOW_BEFORE = 3   # weeks before event start used as the local baseline
WINDOW_EVENT = 8    # weeks of event window to profile
PRE_EVENT_DAYS = 42  # six weeks of build-up before the event date, profiled too


def load_weekly() -> pd.DataFrame:
    chunks = []
    reader = pd.read_csv(
        CAT / "sales.csv",
        usecols=["sku", "date", "units"],
        parse_dates=["date"],
        chunksize=2_000_000,
        dtype={"sku": "category", "units": "int32"},
    )
    for ch in reader:
        ch["week"] = ch["date"].dt.to_period("W").dt.start_time
        chunks.append(ch.groupby(["sku", "week"], observed=True)["units"].sum())
    weekly = pd.concat(chunks).groupby(level=[0, 1]).sum().unstack(level=0)
    weekly.index = pd.DatetimeIndex(weekly.index)
    return weekly


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(CAT / "events.csv", parse_dates=["date"])
    events["week"] = events["date"].dt.to_period("W").dt.start_time

    # registry: one row per event per year with its window
    reg = (events.groupby(["event", "week"])["factor"].mean()
           .reset_index()
           .groupby("event")
           .agg(first_seen=("week", "min"), last_seen=("week", "max"),
                occurrences=("week", "nunique"), mean_factor=("factor", "mean"))
           .reset_index())
    reg["median_factor"] = reg["event"].map(
        events.groupby("event")["factor"].median().to_dict())
    reg.to_csv(OUT / "event_registry.csv", index=False)

    print("aggregating weekly sales...")
    weekly = load_weekly()
    print(f"weekly: {weekly.shape}")

    # per-SKU x event x occurrence ramp profile, then median across occurrences
    # NOTE: Ramadan and Lebaran overlap by construction (Lebaran = Ramadan+29d), so the
    # Ramadan event window is capped at 4 weeks (the fasting period proper) and Lebaran
    # gets its own 3-week window. Otherwise the Lebaran peak is swallowed by Ramadan's.
    window_override = {"Ramadan": 4, "Lebaran": 3}
    # Baseline per SKU: median of weeks OUTSIDE all event windows. Using the 3 weeks
    # before an event fails when events cluster (pre-Lebaran weeks ARE Ramadan weeks,
    # already uplifted 2x, which swallows Lebaran's true uplift).
    all_event_weeks = set()
    for ev_name, ev_df in events.groupby("event"):
        win = window_override.get(ev_name, WINDOW_EVENT)
        for occ in {pd.Timestamp(x) for x in ev_df["week"].unique()}:
            for k in range(win + 2):  # +2: trailing decay still part of the event effect
                all_event_weeks.add(occ + pd.Timedelta(weeks=k))
                all_event_weeks.add(occ - pd.Timedelta(weeks=1))
    clean_weeks = weekly.loc[[w for w in weekly.index if w not in all_event_weeks]]
    if clean_weeks.shape[0] < 26:
        # Six weeks of build-up per event times eight events leaves almost no untouched
        # week to take a median from, so the baseline falls back to every week; the event
        # weeks are a minority of four years and do not move a median.
        clean_weeks = weekly
    base_series = clean_weeks.median(axis=0)

    # Every SKU wobbles week to week, so the highest week inside a window is always
    # above its own median. Measuring the peak against that wobble is what made a
    # toothpaste read 1.4 times normal at Christmas. The floor below is the same
    # statistic on quiet weeks: a SKU that does not move scores 1.0 by construction.
    clean_ratio = clean_weeks.divide(base_series.replace(0, np.nan), axis=1)
    noise_floor = clean_ratio.quantile(0.90, axis=0).fillna(1.0)

    records = []
    for ev_name, ev_df in events.groupby("event"):
        occ_weeks = sorted({pd.Timestamp(w) for w in ev_df["week"].unique()})
        win_weeks = window_override.get(ev_name, WINDOW_EVENT)
        for occ in occ_weeks:
            base = base_series
            win = weekly.loc[
                (weekly.index >= occ - pd.Timedelta(days=PRE_EVENT_DAYS)) &
                (weekly.index < occ + pd.Timedelta(weeks=win_weeks))]
            if win.shape[0] < 3:
                continue
            prof = win.divide(base.replace(0, np.nan), axis=1)
            for sku in prof.columns:
                p = prof[sku].dropna().to_numpy(dtype=float)
                if len(p) < 3:
                    continue
                # three-week mean, so one noisy week cannot pass for a holiday
                sm = np.convolve(p, np.ones(3) / 3.0, mode="valid")
                peak_idx = int(np.nanargmax(sm))
                floor = float(noise_floor.get(sku, 1.0)) or 1.0
                peak_ratio = float(sm[peak_idx])
                records.append({
                    "sku": sku,
                    "event": ev_name,
                    "occurrence": occ.strftime("%Y-%m-%d"),
                    "peak_mult": max(1.0, 1.0 + (peak_ratio - floor)),
                    "days_to_peak": min(42, int((peak_idx + 1) * 7)),
                    "build_slope": float((sm[peak_idx] - sm[0]) / max(1, peak_idx + 1)),
                    "decay_slope": float((sm[peak_idx] - sm[-1]) / max(1, len(sm) - 1 - peak_idx)),
                })

    occ_df = pd.DataFrame(records)
    agg = (occ_df.groupby(["sku", "event"])
           .agg(peak_mult=("peak_mult", "median"),
                days_to_peak=("days_to_peak", "median"),
                build_slope=("build_slope", "median"),
                decay_slope=("decay_slope", "median"),
                occurrences=("occurrence", "nunique"))
           .reset_index())

    # A ramp is only fitted for the SKUs the event actually moves. The fitted number is
    # the SHAPE (when it climbs, how fast); the SIZE floor comes from the sourced
    # category table, because four years of weekly sales cannot separate a 1.2 from a 1.3
    # without turning noise into a holiday.
    from src.demand.participation import amplitude as table_amp, carries, table

    cat = {}
    cat_path = CAT / "catalog.csv"
    if cat_path.exists():
        cat = {r["sku"]: r["category"] for r in csv.DictReader(cat_path.open())}

    # A category can be sourced for Lebaran and silent for Christmas. What matters is
    # whether THIS event has a row for it, not whether the category appears anywhere.
    def sourced(c: str, ev: str) -> bool:
        keys = [(c, ev)]
        if ev in {"Ramadan", "Lebaran"}:
            keys.append((c, "Ramadan-Lebaran"))
        return any(k in table() for k in keys)

    def keep(row) -> float:
        c = cat.get(row["sku"], "")
        if not carries(row["sku"], c, row["event"]):
            return 1.0
        a = table_amp(c, row["event"])
        if not sourced(c, row["event"]):
            # no sourced row for this category in this event: the catalogue lift is all
            # it gets, and the fitted shape stays out of the size
            return a
        return max(float(row["peak_mult"]), a)

    agg["peak_mult"] = [keep(r) for r in agg.to_dict("records")]

    # classify: RAMPPED when the profile is clearly asymmetric and above noise
    peak = agg["peak_mult"]
    asym = agg["build_slope"].abs() / agg["decay_slope"].abs().replace(0, np.nan)
    agg["ramp_class"] = np.select(
        [(peak >= 1.25) & (asym > 0.35),
         (peak >= 1.10)],
        ["ramped", "step"],
        default="none")
    agg.to_csv(OUT / "sku_ramps.csv", index=False)

    top = (agg.groupby("event")["peak_mult"].median().sort_values(ascending=False).round(3).to_dict())
    share = (agg.groupby("event")["ramp_class"]
             .apply(lambda s: round(float((s == "ramped").mean()), 3)).to_dict())
    summary = {
        "ramps_rows": int(len(agg)),
        "events": int(agg["event"].nunique()),
        "skus": int(agg["sku"].nunique()),
        "median_peak_by_event": top,
        "ramped_share_by_event": share,
        "ramp_class_counts": agg["ramp_class"].value_counts().to_dict(),
    }
    (OUT / "ramp_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
