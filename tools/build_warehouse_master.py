"""
Pasok — Warehouse master data (space is a physical constraint, so it needs numbers)
==================================================================================

The order policy cannot decide whether an order fits the building from skirt size
alone. It needs two inputs:

1. How much space one selling unit takes.
   Real deployments read this from the item master: carton length x width x height and
   units per carton. This catalogue does not carry dimensions, only the pack string
   ("250ml", "5 x 75g"), so the volume is derived from the pack and multiplied by a
   stated packaging factor: cartons, void fill and the fact that a pallet of 250ml cups
   is not 100% product. 1.25 is the assumption, written down where anyone can check it.

2. How much space the building actually offers.
   Derived from the record rather than invented: the 95th percentile of the committed
   footprint (on hand + in transit + open PO) across the three years in
   data/stock/stock_daily.csv. A distributor builds for its busiest weeks, so the p95
   over three years is the size the building had to be. During a Lebaran build the
   footprint can exceed it, and that is exactly when a human decides on overflow.

Outputs
-------
data/warehouse/unit_volume.csv   sku, pack, litres_per_unit, m3_per_unit
data/warehouse/capacity.json     usable_m3, derivation, assumptions

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python tools/build_warehouse_master.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "data" / "catalog"
STOCK = ROOT / "data" / "stock"
OUT = ROOT / "data" / "warehouse"

PACKAGING_FACTOR = 1.25


def unit_litres(pack: object) -> float:
    s = str(pack).lower()
    mult = 1
    m2 = re.match(r"(\d+)\s*x\s*", s)
    if m2:
        mult = int(m2.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg)", s)
    if not m:
        return 0.0
    qty = float(m.group(1))
    return (qty / 1000 if m.group(2) in ("ml", "g") else qty) * mult


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cat = pd.read_csv(CAT / "catalog_view.csv")[["sku", "pack", "product_form"]]
    cat["litres_per_unit"] = [unit_litres(p) for p in cat["pack"]]
    cat["m3_per_unit"] = (cat["litres_per_unit"] * PACKAGING_FACTOR / 1000).round(6)
    cat[["sku", "pack", "litres_per_unit", "m3_per_unit"]].to_csv(OUT / "unit_volume.csv", index=False)

    daily = pd.read_csv(STOCK / "stock_daily.csv", parse_dates=["date"])
    daily = daily.merge(cat[["sku", "m3_per_unit"]], on="sku", how="left")
    daily["m3"] = (daily["on_hand"] + daily["in_transit"] + daily["open_po"]) * daily["m3_per_unit"]
    per_day = daily.groupby("date")["m3"].sum()
    usable = float(per_day.quantile(0.95))

    payload = {
        "usable_m3": round(usable, 0),
        "derivation": "95th percentile of committed footprint (on hand + in transit + open PO) "
                      "over the record in data/stock/stock_daily.csv",
        "record_days": int(len(per_day)),
        "footprint_mean_m3": round(float(per_day.mean()), 0),
        "footprint_max_m3": round(float(per_day.max()), 0),
        "footprint_max_date": str(per_day.idxmax().date()),
        "packaging_factor": PACKAGING_FACTOR,
        "assumptions": [
            "unit volume parsed from the pack string; cartons and void fill carried as a 1.25 factor",
            "the building is sized to the 95th percentile of the years in the record",
            "rack height, aisle share and pallet stacking are inside that percentile, not modelled separately",
        ],
    }
    (OUT / "capacity.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    print(f"\nunit_volume.csv: {len(cat)} SKUs, median {cat['m3_per_unit'].median():.5f} m3 per unit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
