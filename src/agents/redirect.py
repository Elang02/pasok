"""
Pasok — Branch-Depot Redirect (GSD 06-02)
==========================================

Closes two proposal claims:

  line 20: the Decision Agent may "redirect excess to a branch depot".
  line 16: when demand undershoots the curve, positions flip to expiry-risk flags
           "with transfers or markdowns proposed while value remains".

Detection
---------
A SKU holds excess when its days of cover run past the Decision Agent's own cover
target (cover_days_target) — i.e. more stock than the plan asked for. Expiry risk
(shelf life shorter than the cover horizon) forces a markdown instead of a transfer.

Action
------
  TRANSFER  -> move the excess to the branch depot (city) where the same SKU sells
               fastest, if it can outlive the transfer horizon
  MARKDOWN  -> shelf life too short to wait; propose a markdown while value remains
  HOLD      -> excess exists but no depot can absorb it usefully

Outputs
-------
data/orders/redirect_decisions.csv    one row per excess SKU
data/orders/branch_depot_ledger.csv   one row per proposed transfer
data/orders/redirect_summary.json      counts + value protected

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/redirect.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "orders"
CAT = ROOT / "data" / "catalog"
STK = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))  # PASOK_STOCK = hari yang disimulasikan
AG = ROOT / "data" / "agents"

TRANSFER_DAYS = 14        # how many days of depot demand one transfer should cover
MIN_EXCESS_DAYS = 5       # ignore trivial overage
CENTRAL = "DC-Central"


def main() -> int:
    pos = pd.read_csv(STK / "position_snapshot.csv")
    dec = pd.read_csv(AG / "decisions.csv")[["sku", "cover_days_target", "principal_id"]]
    cat = pd.read_csv(CAT / "catalog.csv")[["sku", "unit_cost_idr", "shelf_life_months"]]
    city = pd.read_csv(CAT / "sku_city_demand.csv")

    df = pos.merge(dec, on="sku", how="left", suffixes=("", "_dec")).merge(cat, on="sku", how="left")
    df["principal_id"] = df["principal_id_dec"].fillna(df["principal_id"])
    df["excess_days"] = df["days_of_cover"] - df["cover_days_target"]
    df["shelf_life_days"] = df["shelf_life_months"] * 30.0
    excess = df[df["excess_days"] > MIN_EXCESS_DAYS].copy()

    # per SKU: depot = city with the largest historical demand for that SKU
    city_tot = city.groupby("sku")["units"].sum().rename("sku_units")
    top = city.sort_values("units", ascending=False).groupby("sku").head(1).set_index("sku")
    city["share"] = city["units"] / city["sku"].map(city_tot)
    daily = city.copy()
    daily["daily_units"] = daily["units"] / 1092.0        # 1092 days of history

    rows, ledger = [], []
    for _, r in excess.iterrows():
        sku = r["sku"]
        excess_units = max(0.0, r["excess_days"] * r["velocity_units_day"])
        excess_value = excess_units * r["unit_cost_idr"]
        depot_city = top.loc[sku, "city"] if sku in top.index else None
        depot_daily = 0.0
        if depot_city is not None:
            m = daily[(daily["sku"] == sku) & (daily["city"] == depot_city)]
            depot_daily = float(m["daily_units"].iloc[0]) if len(m) else 0.0

        # shelf life against the horizon this excess would sit for
        can_wait = r["shelf_life_days"] > (r["days_of_cover"] + TRANSFER_DAYS)

        if not can_wait:
            action = "MARKDOWN"
            qty = 0.0
            reason = (f"shelf life {r['shelf_life_days']:.0f}d vs cover {r['days_of_cover']:.1f}d "
                      f"+ transfer {TRANSFER_DAYS}d — markdown while value remains")
        elif depot_daily > 0 and depot_city is not None:
            qty = float(min(excess_units, depot_daily * TRANSFER_DAYS))
            action = "TRANSFER"
            reason = (f"excess {r['excess_days']:.1f}d over target; {depot_city} sells "
                      f"{depot_daily:.1f} u/day — move {qty:.0f}u to branch depot")
        else:
            action, qty = "HOLD", 0.0
            reason = "excess held: no branch depot demand for this SKU"

        rows.append({
            "sku": sku, "principal_id": r["principal_id"], "action": action,
            "days_of_cover": round(float(r["days_of_cover"]), 2),
            "cover_days_target": float(r["cover_days_target"]),
            "excess_days": round(float(r["excess_days"]), 2),
            "excess_units": round(excess_units, 1),
            "excess_value_idr": round(excess_value, 0),
            "depot_city": depot_city or "",
            "transfer_qty": round(qty, 1),
            "value_protected_idr": round(qty * r["unit_cost_idr"], 0),
            "reason": reason,
        })
        if action == "TRANSFER":
            ledger.append({
                "transfer_id": f"TR-{len(ledger)+1:04d}",
                "sku": sku, "from_depot": CENTRAL, "to_depot": depot_city,
                "qty": round(qty, 1), "unit_cost_idr": int(r["unit_cost_idr"]),
                "value_idr": round(qty * r["unit_cost_idr"], 0),
                "rationale": reason,
            })

    rd = pd.DataFrame(rows)
    lg = pd.DataFrame(ledger)
    rd.to_csv(OUT / "redirect_decisions.csv", index=False)
    lg.to_csv(OUT / "branch_depot_ledger.csv", index=False)

    summary = {
        "excess_skus": int(len(rd)),
        "by_action": rd["action"].value_counts().to_dict() if len(rd) else {},
        "depots_used": int(rd.loc[rd["action"] == "TRANSFER", "depot_city"].nunique()) if len(rd) else 0,
        "excess_value_at_risk_idr": float(rd["excess_value_idr"].sum()) if len(rd) else 0.0,
        "value_protected_idr": float(rd["value_protected_idr"].sum()) if len(rd) else 0.0,
        "transfers": int(len(lg)),
        "transfer_value_idr": float(lg["value_idr"].sum()) if len(lg) else 0.0,
        "min_excess_days_threshold": MIN_EXCESS_DAYS,
    }
    (OUT / "redirect_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    assert rd["sku"].is_unique, "duplicate SKU in redirect decisions"
    assert (rd["excess_days"] > MIN_EXCESS_DAYS).all(), "row below excess threshold slipped in"
    if len(lg):
        assert set(lg["sku"]).issubset(set(rd.loc[rd["action"] == "TRANSFER", "sku"])), "ledger has non-transfer SKU"
        assert abs(lg["value_idr"].sum() - rd.loc[rd["action"] == "TRANSFER", "value_protected_idr"].sum()) < 1.0, \
            "ledger value does not reconcile with decisions"
        assert (lg["qty"] > 0).all(), "zero-qty transfer"
    print(f"\nVERIFICATION PASS: {len(rd)} excess SKUs, {len(lg)} transfers, "
          f"IDR {summary['value_protected_idr']:,.0f} protected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
