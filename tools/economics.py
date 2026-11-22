"""What the daily loop costs, with supplier terms in the model.

A distributor does not pay cash on delivery: it buys from the principal on terms and sells
to outlets on terms. So inventory cost has two parts, and only one of them is financing:

    physical carrying   storage at a published Jakarta rent per m3, handling per unit
                        sold, and damage as a share of value. Bottom-up, each line printed
                        with its own assumption, because "8 percent" answered nothing.
    financing           only the days the distributor itself funds. Cash conversion cycle
                        CCC = DIO + DSO - DPO. If DPO covers DIO and DSO, the principal
                        finances the stock and the financing line goes to zero.

Ordering cost and lost margin are reported the same way as before, with the margin printed
as a range because the catalogue carries cost, not selling price.

Run:
    .venv/bin/python tools/economics.py --sim data/sim/replay2026_v3
    .venv/bin/python tools/economics.py --dpo 30 45 60 --dso 30
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Physical carrying is bottom-up, not a flat percentage. The old 8%/yr was an assumption
# with no address; now storage comes from a published Jakarta rent, handling from a per-unit
# rate, damage from a shrink rate, and the three are reported separately.
WAREHOUSE_RENT_IDR_PER_M2_MONTH = 81_795   # Greater Jakarta, Q2 2026, Cushman & Wakefield
RACK_HEIGHT_M = 6.0                        # usable stacking height, assumption
HANDLING_IDR_PER_UNIT = 12                 # pick, pack, put-away per unit, assumption
DAMAGE_RATE_PER_YEAR = 0.004               # shrink and breakage, assumption
WACC = 0.12
ORDER_COST_IDR = 150_000
MARGINS = (0.08, 0.10, 0.12)
DPO_CHOICES = (30, 45, 60)
DSO_DEFAULT = 30


def calculate(sim: Path, days: int, dpo: int, dso: int) -> dict:
    stock = pd.read_csv(sim / "world/stock_daily.csv", parse_dates=["date"])
    cat = pd.read_csv(ROOT / "data/catalog/catalog.csv")[["sku", "unit_cost_idr"]]
    vol = pd.read_csv(ROOT / "data/warehouse/unit_volume.csv")[["sku", "m3_per_unit"]]
    stock["sku"] = stock["sku"].astype(str)
    vol["sku"] = vol["sku"].astype(str)
    stock = stock.merge(cat, on="sku", how="left").merge(vol, on="sku", how="left")
    if stock["unit_cost_idr"].isna().any():
        raise SystemExit("catalog is missing a unit cost for at least one SKU")

    # The world file carries the seeded history before the agent took over. Score only the
    # trailing window the replay actually decided, or the numbers mix two policies.
    end = stock["date"].max()
    start = end - pd.Timedelta(days=days - 1)
    stock = stock[(stock["date"] >= start) & (stock["date"] <= end)].copy()

    stock["inventory_value"] = stock["on_hand"].clip(lower=0) * stock["unit_cost_idr"]
    stock["occupied_m3"] = stock["on_hand"].clip(lower=0) * stock["m3_per_unit"].fillna(0.0)
    daily = stock.groupby("date").agg(
        inventory_value=("inventory_value", "sum"),
        occupied_m3=("occupied_m3", "sum"),
        sold=("sales", "sum"),
        lost=("lost_sales", "sum"),
    )
    n = len(daily)
    avg_inv = float(daily["inventory_value"].mean())
    cogs = float((stock["sales"] * stock["unit_cost_idr"]).sum())
    cogs_day = cogs / n if n else float("nan")
    dio = avg_inv / cogs_day if cogs_day else float("nan")

    ccc = dio + dso - dpo
    financed_days = max(0.0, dio - dpo)
    financed_value = avg_inv * (financed_days / dio) if dio else 0.0

    storage_per_m3_year = WAREHOUSE_RENT_IDR_PER_M2_MONTH * 12 / RACK_HEIGHT_M
    avg_m3 = float(daily["occupied_m3"].mean())
    storage_cost = avg_m3 * storage_per_m3_year * n / 365
    handling_cost = float(daily["sold"].sum()) * HANDLING_IDR_PER_UNIT
    damage_cost = avg_inv * DAMAGE_RATE_PER_YEAR * n / 365
    carrying_physical = storage_cost + handling_cost + damage_cost
    carrying_finance = financed_value * WACC * n / 365
    po_keys = set()
    for d in sorted(sim.glob("day-*")):
        f = d / "decisions.csv"
        if f.exists():
            dec = pd.read_csv(f)
            placed = dec[dec.get("guarded_order", 0) > 0]
            for _, row in placed.iterrows():
                po_keys.add((str(row.get("date", d.name)), row["principal_id"]))
    ordering = len(po_keys) * ORDER_COST_IDR

    lost_units = float(daily["lost"].sum())
    lost_at_cost = float((stock.loc[stock["lost_sales"] > 0]
                          .assign(v=lambda d: d["lost_sales"] * d["unit_cost_idr"])["v"].sum()))

    return {
        "sim": str(sim.relative_to(ROOT.resolve()) if str(sim).startswith(str(ROOT.resolve())) else sim),
        "days": n,
        "terms": {"dpo_days": dpo, "dso_days": dso},
        "assumptions": {
            "storage": {
                "rent_idr_per_m2_month": WAREHOUSE_RENT_IDR_PER_M2_MONTH,
                "rent_source": "Greater Jakarta warehouse rent, Q2 2026, Cushman & Wakefield",
                "rack_height_m": RACK_HEIGHT_M,
                "implied_idr_per_m3_year": round(storage_per_m3_year),
                "avg_occupied_m3": round(avg_m3),
            },
            "handling_idr_per_unit": HANDLING_IDR_PER_UNIT,
            "damage_rate_per_year": DAMAGE_RATE_PER_YEAR,
            "wacc": WACC,
            "order_cost_idr": ORDER_COST_IDR,
            "margins_tested": list(MARGINS),
            "margin_note": "gross margin is an assumption; the catalogue has cost, not price",
        },
        "working_capital": {
            "avg_inventory_value_idr": round(avg_inv),
            "cogs_idr": round(cogs),
            "turns_per_year": round(cogs / avg_inv, 2) if avg_inv else None,
            "dio_days": round(dio, 1),
            "dso_days": dso,
            "dpo_days": dpo,
            "ccc_days": round(ccc, 1),
            "financed_days": round(financed_days, 1),
            "financed_value_idr": round(financed_value),
        },
        "cost": {
            "physical_carrying_idr": round(carrying_physical),
            "physical_detail_idr": {
                "storage": round(storage_cost),
                "handling": round(handling_cost),
                "damage": round(damage_cost),
            },
            "financing_idr": round(carrying_finance),
            "ordering_idr": ordering,
            "total_idr": round(carrying_physical + carrying_finance + ordering),
        },
        "lost_demand": {
            "units": round(lost_units),
            "at_cost_idr": round(lost_at_cost),
            "margin_lost_idr": {f"{int(m*100)}pct": round(lost_at_cost * m) for m in MARGINS},
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", default=str(ROOT / "data/sim/replay2026_v3"))
    ap.add_argument("--out", default=str(ROOT / "data/agents/economics.json"))
    ap.add_argument("--days", type=int, default=284)
    ap.add_argument("--dpo", type=int, nargs="+", default=list(DPO_CHOICES))
    ap.add_argument("--dso", type=int, default=DSO_DEFAULT)
    a = ap.parse_args()

    scenarios = {f"dpo{int(d)}": calculate(Path(a.sim), a.days, int(d), a.dso) for d in a.dpo}
    out = {
        "note": "one entry per supplier-term scenario; the middle one is the working assumption",
        "scenarios": scenarios,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2))
    for name, s in scenarios.items():
        wc, c = s["working_capital"], s["cost"]
        print(f"{name}: DIO {wc['dio_days']}d CCC {wc['ccc_days']}d | physical Rp {c['physical_carrying_idr']/1e9:.1f}bn "
              f"| financing Rp {c['financing_idr']/1e9:.1f}bn | ordering Rp {c['ordering_idr']/1e6:.1f}M")


if __name__ == "__main__":
    main()
