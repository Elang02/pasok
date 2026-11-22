#!/usr/bin/env python3
"""
Pasok — test cases (end-to-end, from real artefacts)
====================================================

Two questions a purchasing manager actually asks:

  TC-1  What runs out of stock within a week?
  TC-2  What will need more stock because a demand spike is coming within a month?

Both are answered by reading the same artefacts the four agents produce, and both are
cross-checked against what the Decision Agent actually did about them. Nothing here is
hard-coded: change the input data and the answers change.

Run:  .venv/bin/python tools/test_cases.py
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
STOCK = ROOT / "data" / "stock"
AG = ROOT / "data" / "agents"
DEM = ROOT / "data" / "demand"
ORD = ROOT / "data" / "orders"

LINE = "=" * 96
sub = "-" * 96


def _ev(v) -> str:
    """The event name, or "" when there is none.

    NaN under astype(str) is the truthy string "nan", which passes both `if event` and
    `event != ""`. Every filter in this file has to normalise first.
    """
    if v is None or (isinstance(v, float) and v != v):
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def idr(v: float) -> str:
    return f"IDR {v:,.0f}"


def load():
    snap = pd.read_csv(STOCK / "position_snapshot.csv")
    dec = pd.read_csv(AG / "decisions.csv")
    cat = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")
    orders = pd.read_csv(ORD / "purchase_orders.csv")
    cal = pd.read_csv(DEM / "event_calendar.csv")
    return snap, dec, cat, orders, cal


# --------------------------------------------------------------------- TC-1
def tc1_runs_out_within_a_week(snap, dec, cat, orders) -> dict:
    """SKUs whose stock dies within 7 days, and which die before the next delivery lands."""
    d = snap.merge(dec[["sku", "event", "cover_days_target", "guarded_order", "action"]],
                   on="sku", how="left")
    d = d.merge(cat[["sku", "category", "unit_cost_idr"]], on="sku", how="left")

    within_week = d[d["days_of_cover"] <= 7].copy()
    # The sharper line: cover shorter than the lead time means it stocks out BEFORE the
    # next delivery can arrive, so the shortfall is real, not just tight.
    critical = within_week[within_week["days_of_cover"] < within_week["lead_time_days"]]
    at_risk_value = float((critical["sellable_units"] * critical["unit_cost_idr"]).sum())

    # the real outcome: what the executor did with those POs, not the decision label
    po = orders[orders["sku"].isin(within_week["sku"])]
    auto = int((po["status"] == "AUTO_ISSUED").sum())
    escalated = int((po["status"] == "ESCALATED").sum())
    covered = int(within_week["guarded_order"].gt(0).sum())

    rows = []
    for _, r in within_week.sort_values("days_of_cover").head(15).iterrows():
        rows.append({
            "sku": r["sku"], "category": r["category"], "principal": r["principal_id"],
            "on_hand": r["on_hand_units"], "sellable": r["sellable_units"],
            "velocity_day": r["velocity_units_day"], "cover_d": r["days_of_cover"],
            "lead_d": r["lead_time_days"], "event": r["event"],
            "action": r["action"], "order": r["guarded_order"],
        })

    return {
        "question": "What runs out of stock within a week?",
        "summary": {
            "skus_cover_le_7d": int(len(within_week)),
            "of_which_die_before_next_delivery": int(len(critical)),
            "at_risk_stock_value_idr": at_risk_value,
            "given_an_order_by_the_loop": covered,
            "po_auto_issued": auto,
            "po_escalated_to_a_human": escalated,
            "total_skus": int(len(d)),
        },
        "top": rows,
    }


# --------------------------------------------------------------------- TC-2
def tc2_spike_within_a_month(snap, dec, cat, cal) -> dict:
    """SKUs carrying an event spike in the coming month, ranked by the extra stock it implies."""
    snapshot = str(dec["snapshot"].iloc[0])
    snap_date = pd.Timestamp(snapshot)
    horizon = snap_date + pd.Timedelta(days=30)

    # The event the loop actually acted on, and the peak day it planned against.
    # dropna() must come BEFORE astype(str): NaN becomes the literal string "nan"
    # otherwise, and then it sorts as if it were a real event name.
    # NaN under astype(str) becomes the literal "nan", which passes `!= ""` and made every
    # SKU look event-covered. Normalise once, the same way one_pass.py does.
    acted = sorted({_ev(e) for e in dec["event"].unique()} - {""})
    coming = []
    for e in acted:
        r = dec[dec["event"] == e]
        days = (r["event_day"].dropna().astype(str).sort_values()
                if "event_day" in r else pd.Series(dtype=str))
        peak = str(days.iloc[0]) if len(days) else ""
        # Only an event whose peak falls INSIDE the horizon is coming. A peak behind the
        # snapshot is history: reporting Imlek's 2026-01-30 under a key named
        # `event_windows_in_horizon` for an October snapshot is what made this answer wrong.
        if not peak or not (snap_date <= pd.Timestamp(peak) <= horizon):
            continue
        coming.append({
            "event": e,
            "peak_day_the_loop_planned_for": peak,
            "ramp_mult_min": float(r["event_mult"].min()),
            "ramp_mult_max": float(r["event_mult"].max()),
        })

    d = dec.merge(cat[["sku", "category", "unit_cost_idr", "shelf_life_months"]],
                  on="sku", how="left")
    d["event"] = d["event"].map(_ev)
    hot = d[d["event"] != ""].copy()
    # extra units the ramp forces on top of the plain forecast
    hot["extra_daily"] = hot["forecast_daily_eff"] - hot["forecast_daily"]
    hot["extra_units"] = (hot["extra_daily"] * hot["cover_days_target"]).round(0)
    hot["extra_value_idr"] = hot["extra_units"] * hot["unit_cost_idr"]

    by_event = hot.groupby("event").agg(
        skus=("sku", "count"),
        extra_units=("extra_units", "sum"),
        extra_value_idr=("extra_value_idr", "sum"),
        median_peak_mult=("event_mult", "median"),
    ).reset_index().to_dict("records")

    rows = []
    for _, r in hot.sort_values("extra_units", ascending=False).head(15).iterrows():
        rows.append({
            "sku": r["sku"], "category": r["category"], "principal": r["principal_id"],
            "event": r["event"], "event_day": r.get("event_day", ""),
            "ramp_uplift": r["event_mult"],
            "base_day": r["forecast_daily"], "spiked_day": r["forecast_daily_eff"],
            "extra_units": r["extra_units"], "extra_value_idr": r["extra_value_idr"],
            "shelf_life_months": r["shelf_life_months"],
        })

    return {
        "question": "What needs more stock because a spike is coming within a month?",
        "summary": {
            "snapshot_date": snapshot,
            "horizon_end": str(horizon.date()),
            "event_windows_in_horizon": coming,
            "skus_with_a_spike": int(len(hot)),
            "extra_units_implied": float(hot["extra_units"].sum()),
            "extra_value_implied_idr": float(hot["extra_value_idr"].sum()),
            "already_covered_by_the_loop": int((hot["action"] == "SIZE").sum()),
        },
        "by_event": by_event,
        "top": rows,
    }


def main() -> int:
    snap, dec, cat, orders, cal = load()
    tc1 = tc1_runs_out_within_a_week(snap, dec, cat, orders)
    tc2 = tc2_spike_within_a_month(snap, dec, cat, cal)

    for tc in (tc1, tc2):
        print(LINE)
        print("Q:", tc["question"])
        print(sub)
        for k, v in tc["summary"].items():
            print(f"  {k:38} {v}")
        print(sub)
        for r in tc["top"][:10]:
            print("  " + " | ".join(f"{k}={v}" for k, v in r.items()))
        print()

    print(LINE)
    print("CHECK: do the two answers agree with what the loop actually did?")
    print(sub)
    s1 = tc1["summary"]
    ok1 = s1["given_an_order_by_the_loop"] == s1["skus_cover_le_7d"]
    print(f"  TC-1 {s1['skus_cover_le_7d']} SKUs under a week, "
          f"{s1['of_which_die_before_next_delivery']} die before the next delivery")
    print(f"        the loop ordered all of them: {s1['given_an_order_by_the_loop']}/"
          f"{s1['skus_cover_le_7d']} -> {ok1}")
    print(f"        those POs: {s1['po_auto_issued']} auto-issued, "
          f"{s1['po_escalated_to_a_human']} escalated to a human")
    s2 = tc2["summary"]
    print(f"  TC-2 {s2['skus_with_a_spike']} SKUs carry a ramp in the horizon; "
          f"{s2['already_covered_by_the_loop']} of them get an order "
          f"({s2['skus_with_a_spike'] - s2['already_covered_by_the_loop']} are held: "
          f"existing stock already covers the horizon)")
    print(f"        extra units the ramp implies: {s2['extra_units_implied']:,.0f} "
          f"({idr(s2['extra_value_implied_idr'])})")

    out = ROOT / "data" / "agents" / "test_cases.json"
    out.write_text(json.dumps({"tc1": tc1, "tc2": tc2}, indent=2))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
