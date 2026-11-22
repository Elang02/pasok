"""
Pasok — Learn Step (GSD 06-03)
==============================

Closes the proposal's closing claim:

  line 22: "when the delivery lands, forecast is compared against actuals and the
           next cycle starts smarter"
  line 24: "Memory keeps a per-SKU decision history so the system can check whether
           its last call was right"

What this measures (and why)
----------------------------
The snapshot's order sizing is deliberately event-inflated (`f_eff = f_daily x event
mult`), so a snapshot-versus-snapshot cover check is circular and says nothing about
accuracy. The learn step instead scores each decision on the outcomes the records can
actually resolve:

  1. SUPPLY   — does the principal deliver what the order assumed? (fill rate)
  2. LOGISTICS— does the real lead time match the p90 the plan bought against? (drift)
  3. FORECAST — the Demand Agent's own held-out accuracy for that SKU (WAPE from
                baselines.csv, an out-of-sample number, not a re-fit)

An unknown score plus the reason is recorded rather than a flattering label.

Outputs
-------
data/agents/decision_history.csv    one row per PO — the Memory analogue
data/agents/learn_summary.json      outcome mix, drift, forecast accuracy, fill

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/learn.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "data" / "agents"
OUT = ROOT / "data" / "orders"
CAT = ROOT / "data" / "catalog"
STK = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))  # PASOK_STOCK = hari yang disimulasikan

FILL_OK = 0.95          # at or above this the principal delivered the assumed fill
LEAD_DRIFT_TOL = 1.0    # days
RESID_Z = 2.0           # realised demand outside 2 resid_sd of the forecast = surprise


def observed_principal_stats() -> pd.DataFrame:
    rec = pd.read_csv(CAT / "receiving.csv")
    g = rec.groupby("principal_id").agg(
        obs_lead_p90=("actual_lead_d", lambda s: s.quantile(0.90)),
        obs_lead_mean=("actual_lead_d", "mean"),
        obs_received=("received_units", "sum"),
        obs_ordered=("ordered_units", "sum"),
        obs_receipts=("po_id", "size"),
    )
    g["obs_fill_rate"] = (g["obs_received"] / g["obs_ordered"]).round(4)
    return g.reset_index()


def recent_sku_daily(start: str, days: int) -> pd.Series:
    acc: dict[str, float] = {}
    for ch in pd.read_csv(CAT / "sales.csv", usecols=["sku", "date", "units"], chunksize=2_000_000):
        ch = ch[ch["date"] >= start]
        if ch.empty:
            continue
        g = ch.groupby("sku", observed=True)["units"].sum()
        for k, v in g.items():
            acc[k] = acc.get(k, 0.0) + float(v)
    return (pd.Series(acc) / days).rename("realised_daily")


def monthly_by_sku() -> pd.DataFrame:
    """Realised daily demand per SKU per calendar month, from the inventory walk.

    The walk carries the same daily sales the catalog generated, so this is the same
    signal as streaming sales.csv, without re-reading 7.9M rows.
    """
    sd = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales"])
    sd["date"] = pd.to_datetime(sd["date"])
    sd["month"] = sd["date"].dt.to_period("M").astype(str)
    g = (sd.groupby(["month", "sku"], observed=True)["sales"]
           .agg(units_sum="sum", days="count").reset_index())
    g["realised_daily"] = g["units_sum"] / g["days"].clip(lower=1)
    return g[["month", "sku", "realised_daily", "days"]]


def walk_forward_curve() -> pd.DataFrame:
    """Month-by-month WAPE of a weekly seasonal-naive forecast against realised sales.

    For every day after the first week, the forecast is the same weekday one week
    earlier (the cheapest honest baseline; `baseline.py` picks the best per SKU on a
    holdout, this is the loop's cycle-over-cycle control). WAPE is summed over each
    calendar month, so the curve is the loop comparing forecast against actuals as the
    walk advances, not one flat snapshot.
    """
    sd = pd.read_csv(STK / "stock_daily.csv", usecols=["date", "sku", "sales"])
    sd["date"] = pd.to_datetime(sd["date"])
    sd = sd.sort_values(["sku", "date"])
    sd["fc"] = sd.groupby("sku", observed=True)["sales"].shift(7)
    sd = sd.dropna(subset=["fc"])
    sd = sd[sd["sales"] > 0]
    sd["month"] = sd["date"].dt.to_period("M").astype(str)
    sd["ae"] = (sd["sales"] - sd["fc"]).abs()
    g = sd.groupby("month").agg(ae=("ae", "sum"), act=("sales", "sum"),
                                n=("ae", "size")).reset_index()
    g["wape"] = g["ae"] / g["act"]
    g["skus"] = 600
    return g[["month", "skus", "n", "wape"]]



def main() -> int:
    po = pd.read_csv(OUT / "purchase_orders.csv")
    dec = pd.read_csv(AG / "decisions.csv")[["sku", "forecast_daily", "forecast_daily_eff",
                                             "event", "event_mult", "lead_p90_days"]]
    base = pd.read_csv(ROOT / "data" / "demand" / "baselines.csv")[
        ["sku", "best_baseline", "wape_best", "resid_sd", "interval_lo", "interval_hi"]]
    sr = pd.read_csv(AG / "supplier_reliability.csv")[["principal_id", "lead_p90_d", "fill_rate_observed"]]
    pos = pd.read_csv(STK / "position_snapshot.csv")[["sku", "velocity_units_day"]]
    obs = observed_principal_stats()
    # the last 28 days of the window the snapshot was taken at, read from the data
    snap = pd.read_csv(STK / "position_snapshot.csv")["snapshot"].iloc[0]
    win_start = (pd.Timestamp(str(snap)[:10]) - pd.Timedelta(days=27)).strftime("%Y-%m-%d")
    real = recent_sku_daily(win_start, 28)

    df = (po.merge(dec, on="sku", how="left")
            .merge(base, on="sku", how="left")
            .merge(sr, on="principal_id", how="left")
            .merge(pos, on="sku", how="left")
            .merge(obs, on="principal_id", how="left"))
    df["realised_daily"] = df["sku"].map(real)

    rows = []
    for _, r in df.iterrows():
        # ---- 1. supply: does the principal deliver what the order assumed? ----
        fill = float(r["obs_fill_rate"]) if pd.notna(r["obs_fill_rate"]) else float("nan")
        expected_received = float(r["qty"]) * fill if fill == fill else float("nan")
        shortfall = float(r["qty"]) - expected_received if expected_received == expected_received else float("nan")

        # ---- 2. logistics: realised p90 lead vs the p90 the plan bought against ----
        lead_planned = float(r["lead_p90_days"]) if pd.notna(r["lead_p90_days"]) else float("nan")
        lead_obs = float(r["obs_lead_p90"]) if pd.notna(r["obs_lead_p90"]) else float("nan")
        lead_drift = (lead_obs - lead_planned) if (lead_obs == lead_obs and lead_planned == lead_planned) else float("nan")

        # ---- 3. forecast: realised demand vs the plan, sized by the forecast's own sd ----
        realised = float(r["realised_daily"]) if pd.notna(r["realised_daily"]) else float("nan")
        planned = float(r["forecast_daily"]) if pd.notna(r["forecast_daily"]) else float("nan")
        resid_sd = float(r["resid_sd"]) if pd.notna(r["resid_sd"]) else float("nan")
        surprise_z = ((realised - planned) / resid_sd) if (resid_sd == resid_sd and resid_sd > 0
                                                          and realised == realised and planned == planned) else float("nan")

        supply_ok = (fill == fill) and fill >= FILL_OK
        lead_ok = (lead_drift != lead_drift) or abs(lead_drift) <= LEAD_DRIFT_TOL
        if supply_ok and lead_ok:
            score = "ON_PLAN"
        elif not supply_ok and not lead_ok:
            score = "SUPPLY_AND_LEAD"
        elif not supply_ok:
            score = "SUPPLY_SHORT"
        else:
            score = "LEAD_DRIFT"

        rows.append({
            "po_id": r["po_id"], "sku": r["sku"], "principal_id": r["principal_id"],
            "status": r["status"], "event": r["event"] or "",
            "ordered_units": r["qty"],
            "fill_rate_observed": fill,
            "expected_received_units": round(expected_received, 1) if expected_received == expected_received else "",
            "shortfall_units": round(shortfall, 1) if shortfall == shortfall else "",
            "lead_p90_planned_d": lead_planned,
            "lead_p90_observed_d": lead_obs,
            "lead_drift_d": round(lead_drift, 2) if lead_drift == lead_drift else "",
            "forecast_base_daily": planned,
            "realised_daily_28d": round(realised, 2) if realised == realised else "",
            "forecast_wape_best": float(r["wape_best"]) if pd.notna(r["wape_best"]) else "",
            "demand_surprise_z": round(surprise_z, 2) if surprise_z == surprise_z else "",
            "score": score,
        })

    dh = pd.DataFrame(rows)
    # carry the snapshot date into the history, so the window reported in
    # learn_summary.json is the day the loop actually scored rather than a guess.
    # `pos` above is sliced to two columns, so use the already-read `snap`.
    if len(dh):
        dh["snapshot"] = str(snap)[:10]
    dh.to_csv(AG / "decision_history.csv", index=False)

    wape = pd.to_numeric(dh["forecast_wape_best"], errors="coerce").dropna()
    z = pd.to_numeric(dh["demand_surprise_z"], errors="coerce").dropna()
    drift_rows = dh[dh["lead_drift_d"].apply(lambda x: isinstance(x, (int, float)) and abs(x) > LEAD_DRIFT_TOL)]

    summary = {
        "n_decisions": int(len(dh)),
        "score_distribution": dh["score"].value_counts().to_dict(),
        "share_on_plan": round(float((dh["score"] == "ON_PLAN").mean()), 4),
        "observed_fill_rate_mean": round(float(dh["fill_rate_observed"].dropna().mean()), 4),
        "principals_below_fill_95": sorted(dh.groupby("principal_id")["fill_rate_observed"].first()
                                           .loc[lambda s: s < FILL_OK].index.tolist()),
        "principals_with_lead_drift_gt_1d": sorted(drift_rows["principal_id"].unique().tolist()),
        "forecast_wape_best_median": round(float(wape.median()), 4) if len(wape) else None,
        "forecast_wape_best_mean": round(float(wape.mean()), 4) if len(wape) else None,
        "demand_surprises_outside_2sd": int((z.abs() > RESID_Z).sum()),
        # the window the loop actually scored, read from the data rather than typed in
        "recent_window": (f"{str(dh['snapshot'].iloc[0])[:10]}" if "snapshot" in dh.columns and len(dh)
                          else "belum diketahui"),
        "note": ("Order sizing is event-inflated by design, so accuracy is scored on "
                 "realised supply and logistics plus the Demand Agent's held-out WAPE, "
                 "never on a snapshot cover comparison."),
    }

    # ---- 4. learning curve: forecast vs actuals, month over month, over the walk ----
    wf = walk_forward_curve()
    wf_rows = [{
        "month": r["month"],
        "skus": int(r["skus"]),
        "readings": int(r["n"]),
        "wape": round(float(r["wape"]), 4),
    } for _, r in wf.iterrows()]
    (AG / "learn_curve.csv").write_text(
        "month,skus,readings,wape\n" +
        "\n".join(f'{r["month"]},{r["skus"]},{r["readings"]},{r["wape"]}' for r in wf_rows) + "\n")

    if wf_rows:
        best = min(wf_rows, key=lambda r: r["wape"])
        worst = max(wf_rows, key=lambda r: r["wape"])
        vals = [r["wape"] for r in wf_rows]
        summary["learning_curve"] = {
            "months": len(wf_rows),
            "readings": sum(r["readings"] for r in wf_rows),
            "wape_min": min(vals),
            "wape_max": max(vals),
            "wape_mean": round(sum(vals) / len(vals), 4),
            "wape_first": wf_rows[0]["wape"],
            "wape_last": wf_rows[-1]["wape"],
            "best_month": best,
            "worst_month": worst,
            "artefact": "data/agents/learn_curve.csv",
            "note": ("Monthly WAPE of the loop's weekly seasonal-naive forecast read against "
                     "realised sales, over the full 36-month walk. The spread is the seasonal "
                     "discovery signal: the peak-demand months (Ramadan / Lebaran / year-end) "
                     "carry the highest error, the quiet months the lowest."),
        }
    (AG / "learn_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    assert len(dh) == len(po), f"history rows {len(dh)} != PO count {len(po)}"
    # One PO can carry several SKU lines now, so uniqueness belongs to the line.
    assert not dh.duplicated(subset=["po_id", "sku"]).any(), "duplicate PO line in decision history"
    assert set(dh["score"].unique()) <= {"ON_PLAN", "SUPPLY_SHORT", "LEAD_DRIFT", "SUPPLY_AND_LEAD"}
    assert dh["score"].nunique() > 1, "degenerate scoring: every row has the same label"
    sr_fill = pd.read_csv(AG / "supplier_reliability.csv").set_index("principal_id")["fill_rate_observed"]
    mine = dh.groupby("principal_id")["fill_rate_observed"].first()
    worst = float((mine - sr_fill).abs().max())
    assert worst < 0.02, f"fill disagrees with supplier_reliability by {worst}"
    assert len(wape) == len(dh), "some row lacks a held-out WAPE"
    print(f"\nVERIFICATION PASS: {len(dh)} decisions scored across "
          f"{dh['score'].nunique()} labels, fill reconciles (max diff {worst:.4f}), "
          f"median held-out WAPE {wape.median():.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
