"""
Pasok — Stock Position agent
============================

Builds the inventory ledger the Decision Agent reasons over. The generator never wrote
stock, so this agent reconstructs it the way a real system would: it reads the sales
history and the receiving records, runs a replenishment walk, and reports the position
at a snapshot date.

What it produces
----------------
data/stock/stock_daily.csv       daily per SKU: on_hand, in_transit, arrivals, sales,
                                 lost_sales, ordered
data/stock/position_snapshot.csv one row per SKU at the snapshot date: the sellable
                                 figure, days of cover, and the two risk flags
data/stock/position_summary.json run summary + verification numbers

Discipline: this agent reads ONLY sales + catalog + receiving (ERP-style exports). It
never reads events.csv or any generator intent. That is what makes the downstream
decision defensible: the agent learns from history, not from the answer key.

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/stock_position.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
PREP = ROOT / "data" / "prep"
# PASOK_STOCK moves the world this step reads and writes, so a day of the
# simulation writes into its own directory instead of over the real snapshot.
OUT = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))

SEED = 20261008
VELOCITY_WINDOW = 28        # days, rolling mean for velocity
SAFETY_DAYS = 7             # safety stock in days of cover
REVIEW_PERIOD = 7           # order review cadence (weekly)
OPENING_COVER_DAYS = 30     # opening stock = 30 days of early velocity
CONFIRM_DELAY = 7           # days an order sits as an OPEN PO before it is in transit
                            # (principal confirmation window = one review cycle)


def snapshot_date() -> pd.Timestamp:
    """The day the world is at. PASOK_AS_OF moves it back, so the loop can be run as of
    any day the sales history covers, which is what makes a day by day simulation possible.
    """
    as_of = os.environ.get("PASOK_AS_OF")
    """The last day of the generated sales window.

    Read from the data instead of hardcoded, so extending the window moves the
    whole demo with it. When this was a literal the console kept answering from
    28 December 2025 even after the sales data ran to October 2026.
    """
    idx = pd.read_parquet(PREP / "daily_by_sku.parquet").index
    last = pd.to_datetime(idx).max()
    if as_of:
        want = pd.Timestamp(as_of)
        return min(last, want)
    return last


SNAPSHOT = snapshot_date()


def load_daily() -> pd.DataFrame:
    """Daily network sales per SKU from the fast parquet cache.

    build_prep.py writes the date as the index, so accept either shape: the
    index, or a `date` column from a cache written by an older build.
    """
    d = pd.read_parquet(PREP / "daily_by_sku.parquet")
    if "date" in d.columns:
        d = d.set_index("date")
    d.index = pd.to_datetime(d.index)
    return d.sort_index()


def principal_lead_times() -> tuple[dict, dict, dict]:
    """Learned lead time per principal from receiving records.

    Returns (mean, sd, p90). The MEAN drives the simulated arrival, because a delivery
    arrives when it arrives. The P90 drives the TRIGGER, because the order has to be
    placed early enough that a bad-tail delivery still lands before the shelf empties.
    Using the mean for both is what let cover run to zero between reviews.
    """
    rec = pd.read_csv(CAT / "receiving.csv")
    mean = rec.groupby("principal_id")["actual_lead_d"].mean().round().astype(int).to_dict()
    sd = rec.groupby("principal_id")["actual_lead_d"].std().fillna(1.0).to_dict()
    p90 = rec.groupby("principal_id")["actual_lead_d"].quantile(0.90).round(0).to_dict()
    return mean, sd, p90


def simulate_sku(sales: np.ndarray, lead_days: int, rng: np.random.Generator,
                 lead_trigger_days: float | None = None):
    """Inventory walk for one SKU. Returns arrays over the same horizon.

    `lead_days` is the expected arrival lag (the learned mean). `lead_trigger_days` is the
    cover the review fires at; it is the learned p90 so that a delivery in the slow tail
    still lands before the shelf empties. Defaults to `lead_days` for callers that pass one
    number.

    Order lifecycle (proposal line 18): everything ordered but not yet arrived is
    outstanding. A placed order is labelled an OPEN PO for the first CONFIRM_DELAY
    days (awaiting principal confirmation) and IN TRANSIT afterwards. Both count
    toward sellable; the walk itself is unchanged, so the order dynamics do not move
    with the labelling choice.
    """
    trig = float(lead_days if lead_trigger_days is None else lead_trigger_days)
    n = len(sales)
    vel = pd.Series(sales).rolling(VELOCITY_WINDOW, min_periods=7).mean().to_numpy()
    vel = np.where(np.isnan(vel), sales[:VELOCITY_WINDOW].mean() if n > 0 else 0.0, vel)

    on_hand = np.zeros(n)
    in_transit = np.zeros(n)
    open_po = np.zeros(n)
    arrivals = np.zeros(n)
    ordered = np.zeros(n)
    lost = np.zeros(n)

    # opening stock (carried into the walk below)
    opening = vel[0] * OPENING_COVER_DAYS if n else 0.0

    # outstanding orders: (placed_day, arrival_day, units)
    outstanding: list[list[float]] = []

    for t in range(n):
        # carry yesterday's shelf forward (this was the bug: every day started at 0)
        on_hand[t] = on_hand[t - 1] if t > 0 else opening

        # arrivals land first (they were ordered lead_days ago)
        landed = [o for o in outstanding if o[1] == t]
        for _, _, q in landed:
            on_hand[t] += q
            arrivals[t] += q
        outstanding = [o for o in outstanding if o[1] != t]

        # sales deplete (never below zero; shortfall = lost sales)
        want = sales[t]
        sold = min(want, on_hand[t])
        lost[t] = want - sold
        on_hand[t] -= sold

        # split outstanding: recent placements = open PO, older = in transit
        open_po[t] = sum(q for day, _, q in outstanding if t - day < CONFIRM_DELAY)
        in_transit[t] = sum(q for day, _, q in outstanding if t - day >= CONFIRM_DELAY)

        # weekly review: order when cover falls below the TRIGGER cover (lead p90 + safety)
        if t % REVIEW_PERIOD == 0:
            cover = on_hand[t] / vel[t] if vel[t] > 0 else 999.0
            if cover < (trig + SAFETY_DAYS):
                target = vel[t] * (trig + REVIEW_PERIOD + SAFETY_DAYS + OPENING_COVER_DAYS / 2)
                qty = max(0.0, target - on_hand[t] - open_po[t] - in_transit[t])
                if qty > 0:
                    # jitter the arrival by a couple of days, seeded
                    eta = t + max(1, lead_days + int(rng.integers(-1, 3)))
                    outstanding.append([t, eta, qty])
                    ordered[t] = qty

    # closing split includes anything not yet landed
    open_po[-1] = sum(q for day, _, q in outstanding if (n - 1) - day < CONFIRM_DELAY)
    in_transit[-1] = sum(q for day, _, q in outstanding if (n - 1) - day >= CONFIRM_DELAY)
    return on_hand, in_transit, open_po, arrivals, ordered, lost, vel, opening


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    sales_wide = load_daily()
    skus = list(sales_wide.columns)
    dates = sales_wide.index
    print(f"loaded {len(skus)} SKUs x {len(dates)} days")

    catalog = pd.read_csv(CAT / "catalog.csv").set_index("sku")
    lead_mean, _, lead_p90 = principal_lead_times()

    frames = []
    snaps = []
    for sku in skus:
        y = sales_wide[sku].to_numpy(dtype=float)
        pid = catalog.loc[sku, "principal_id"]
        lead = int(lead_mean.get(pid, 10))
        trig = float(lead_p90.get(pid, lead))
        oh, it, opo, arr, oq, lost, vel, opening = simulate_sku(y, lead, rng, trig)

        frames.append(pd.DataFrame({
            "date": dates, "sku": sku, "sales": y.astype(int),
            "on_hand": oh, "in_transit": it, "open_po": opo, "arrivals": arr,
            "ordered": oq, "lost_sales": lost,
        }))
        frames[-1]["opening_units"] = round(float(opening), 1)

        # snapshot at the last day
        v = vel[-1] if len(vel) else 0.0
        # proposal line 18: on-hand + in-transit + open purchase orders
        sellable = oh[-1] + it[-1] + opo[-1]
        cover = (sellable / v) if v > 0 else float("inf")
        sl_months = float(catalog.loc[sku, "shelf_life_months"])
        snaps.append({
            "sku": sku,
            "principal_id": pid,
            "on_hand_units": round(float(oh[-1]), 1),
            "in_transit_units": round(float(it[-1]), 1),
            "open_po_units": round(float(opo[-1]), 1),
            "sellable_units": round(float(sellable), 1),
            "velocity_units_day": round(float(v), 2),
            "days_of_cover": round(float(cover), 1) if np.isfinite(cover) else None,
            "lead_time_days": lead,
            "lead_trigger_days": trig,
            "shelf_life_days": int(sl_months * 30),
            "below_reorder": bool(cover < (lead + SAFETY_DAYS)),
            "expiry_risk": bool(np.isfinite(cover) and cover * 1.0 > sl_months * 30),
            "lost_sales_total": int(np.sum(lost)),
        })

    daily = pd.concat(frames, ignore_index=True)
    daily["sku"] = daily["sku"].astype("category")
    daily.to_csv(OUT / "stock_daily.csv", index=False)

    snap = pd.DataFrame(snaps)
    # the decision agent needs to know which day this is a snapshot OF. Without
    # this column it has to guess, and a wrong guess makes every horizon answer
    # talk about the wrong season.
    snap["snapshot"] = str(SNAPSHOT.date()) if hasattr(SNAPSHOT, "date") else str(SNAPSHOT)
    snap.to_csv(OUT / "position_snapshot.csv", index=False)

    # ---- verification ----
    neg = int((daily["on_hand"] < -1e-6).sum())
    # walk invariant per SKU: opening + arrivals - sales - lost = closing
    check = daily.groupby("sku", observed=True).agg(
        sales=("sales", "sum"), arr=("arrivals", "sum"),
        lost=("lost_sales", "sum"), oh_end=("on_hand", "last"),
        oh_first=("on_hand", "first"), ord=("ordered", "sum"))
    check["recon"] = check["oh_first"] + check["arr"] - check["sales"] + check["lost"] - check["oh_end"]

    summary = {
        "n_skus": int(len(snap)),
        "n_days": int(len(dates)),
        "snapshot_date": str(dates[-1].date()),
        "negative_on_hand_rows": neg,
        "max_abs_recon_error": float(check["recon"].abs().max()),
        "below_reorder": int(snap["below_reorder"].sum()),
        "expiry_risk": int(snap["expiry_risk"].sum()),
        "lost_sales_total": int(snap["lost_sales_total"].sum()),
        "sellable_composition": {
            "on_hand_total": float(snap["on_hand_units"].sum()),
            "in_transit_total": float(snap["in_transit_units"].sum()),
            "open_po_total": float(snap["open_po_units"].sum()),
            "sellable_total": float(snap["sellable_units"].sum()),
            "skus_with_open_po": int((snap["open_po_units"] > 0).sum()),
            "skus_with_in_transit": int((snap["in_transit_units"] > 0).sum()),
        },
        "days_of_cover": {
            "p10": float(np.nanpercentile(snap["days_of_cover"].replace([np.inf], np.nan).dropna(), 10)),
            "median": float(np.nanmedian(snap["days_of_cover"].replace([np.inf], np.nan).dropna())),
            "p90": float(np.nanpercentile(snap["days_of_cover"].replace([np.inf], np.nan).dropna(), 90)),
        },
        "median_velocity": float(snap["velocity_units_day"].median()),
    }
    (OUT / "position_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
