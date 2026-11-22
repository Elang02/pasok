"""Compare two replays on service and money, not on one headline number.

    .venv/bin/python tools/compare_replays.py data/sim/replay2026_v2 data/sim/replay2026_v3

Both worlds must cover the same calendar window; the tool trims to the overlap so a replay
that stopped early cannot look better by having less time to lose sales.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_RATE = 0.08
WACC = 0.12


def load(sim: Path) -> pd.DataFrame:
    s = pd.read_csv(sim / "world/stock_daily.csv", parse_dates=["date"])
    s["sku"] = s["sku"].astype(str)
    cost = pd.read_csv(ROOT / "data/catalog/catalog.csv")[["sku", "unit_cost_idr"]]
    s = s.merge(cost, on="sku", how="left")
    s["value"] = s["on_hand"].clip(lower=0) * s["unit_cost_idr"]
    return s


def summarise(s: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    w = s[(s["date"] >= start) & (s["date"] <= end)]
    daily = w.groupby("date").agg(
        value=("value", "sum"), sold=("sales", "sum"), lost=("lost_sales", "sum"),
        oos=("lost_sales", lambda x: int((x > 0).sum())),
    )
    days = len(daily)
    dem = daily["sold"].sum() + daily["lost"].sum()
    cogs = float((w["sales"] * w["unit_cost_idr"]).sum())
    avg_inv = float(daily["value"].mean())
    dio = avg_inv / (cogs / days) if cogs else float("nan")
    lost_value = float((w.loc[w["lost_sales"] > 0]
                        .assign(v=lambda d: d["lost_sales"] * d["unit_cost_idr"])["v"].sum()))
    out = {
        "days": days,
        "sold": int(daily["sold"].sum()),
        "lost": int(daily["lost"].sum()),
        "lost_pct": round(100 * daily["lost"].sum() / dem, 3) if dem else None,
        "oos_sku_days": int(daily["oos"].sum()),
        "avg_inventory_value_bn": round(avg_inv / 1e9, 1),
        "turns": round(cogs / avg_inv, 2) if avg_inv else None,
        "dio_days": round(dio, 1),
        "physical_carry_bn": round(avg_inv * PHYSICAL_RATE * days / 365 / 1e9, 1),
        "lost_margin_bn_10pct": round(lost_value * 0.10 / 1e9, 2),
    }
    for dpo in (30, 45, 60):
        financed = avg_inv * max(0.0, dio - dpo) / dio if dio else 0.0
        out[f"finance_bn_dpo{dpo}"] = round(financed * WACC * days / 365 / 1e9, 2)
    return out


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: compare_replays.py SIM_A SIM_B")
    a, b = (Path(x) for x in sys.argv[1:3])
    da, db = load(a), load(b)
    # Score the agent era, not the seeded prehistory both worlds carry.
    era = pd.Timestamp(sys.argv[3]) if len(sys.argv) > 3 else pd.Timestamp("2026-01-01")
    start = max(da["date"].min(), db["date"].min(), era)
    end = min(da["date"].max(), db["date"].max())
    rows = {a.name: summarise(da, start, end), b.name: summarise(db, start, end)}
    print(f"overlap {start.date()} .. {end.date()}")
    frame = pd.DataFrame(rows).T
    print(frame.to_string())
    delta = frame.loc[b.name] - frame.loc[a.name]
    print("\nB minus A:")
    print(delta.to_string())


if __name__ == "__main__":
    main()
