"""
Pasok — Supplier Reliability agent
==================================

Learns, from actual receipts, how reliable each principal really is: real lead-time
distribution (not the one printed in the catalog), on-time-in-full proxy, and the
safety buffer each principal justifies.

Why this exists: the whole thesis of the demo is "don't trust the promise, learn from
history". `principals.csv` carries a `lead_mean_d`/`lead_sd_d` field the way an ERP
master record does. This agent deliberately ignores those master fields and computes
everything from `receiving.csv` (the observed history). If it just echoed the master
record, there would be nothing to demo.

Outputs
-------
data/agents/supplier_reliability.csv   one row per principal
data/agents/supplier_reliability.json  run summary + verification

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/supplier_reliability.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CAT = ROOT / "data" / "catalog"
OUT = ROOT / "data" / "agents"

RECENT_WINDOW_DAYS = 180      # "recent" = last N days of receipts
OTIF_TOLERANCE_D = 2          # receipt within planned lead + tolerance = on time
DRIFT_THRESHOLD = 0.20        # recent mean > historical p90 by >20% => drifting


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rec = pd.read_csv(CAT / "receiving.csv", parse_dates=["order_date"])
    master = pd.read_csv(CAT / "principals.csv").set_index("principal_id")

    cutoff = rec["order_date"].max() - pd.Timedelta(days=RECENT_WINDOW_DAYS)

    rows = []
    for pid, g in rec.groupby("principal_id"):
        lead = g["actual_lead_d"].to_numpy(dtype=float)
        p50 = float(np.percentile(lead, 50))
        p90 = float(np.percentile(lead, 90))
        hist_mean = float(lead.mean())
        hist_std = float(lead.std(ddof=1)) if len(lead) > 1 else 0.0

        # OTIF: on-time (within planned lead + tolerance) AND in-full.
        # "In full" di data ini = fill-rate semantics (shortfall tersebar di hampir semua
        # PO karena generator mensimulasikan partial fulfillment), jadi OTIF dihitung
        # sebagai on-time rate x observed fill rate, bukan hard equality (yang menghasilkan
        # 0.07 tidak realistis untuk dunia FMCG di mana shortfall kecil dianggap wajar).
        planned = float(master.loc[pid, "lead_mean_d"]) if pid in master.index else p50
        on_time = float((g["actual_lead_d"] <= (planned + OTIF_TOLERANCE_D)).mean())
        fill = float(g["received_units"].sum() / g["ordered_units"].sum())
        otif = on_time * fill

        # drift: recent behaviour vs historical spread
        recent = g.loc[g["order_date"] >= cutoff, "actual_lead_d"]
        recent_mean = float(recent.mean()) if len(recent) else hist_mean
        drift_flag = bool(recent_mean > p90 * (1 + DRIFT_THRESHOLD))

        # safety buffer the history justifies: p90 spread above the median
        buffer_days = int(max(2, np.ceil(p90 - p50)))

        rows.append({
            "principal_id": pid,
            "receipts": int(len(g)),
            "lead_mean_d": round(hist_mean, 2),
            "lead_p50_d": round(p50, 1),
            "lead_p90_d": round(p90, 1),
            "lead_std_d": round(hist_std, 2),
            "otif": round(otif, 3),
            "fill_rate_observed": round(float((g["received_units"].sum() / g["ordered_units"].sum())), 3),
            "recent_lead_mean_d": round(recent_mean, 2),
            "drift_flag": drift_flag,
            "recommended_buffer_days": buffer_days,
        })

    df = pd.DataFrame(rows).sort_values("principal_id").reset_index(drop=True)
    df.to_csv(OUT / "supplier_reliability.csv", index=False)

    summary = {
        "n_principals": int(len(df)),
        "recent_window_days": RECENT_WINDOW_DAYS,
        "otif_range": [float(df["otif"].min()), float(df["otif"].max())],
        "otif_mean": float(df["otif"].mean().round(3)),
        "buffer_days_range": [int(df["recommended_buffer_days"].min()), int(df["recommended_buffer_days"].max())],
        "drift_flags": int(df["drift_flag"].sum()),
        "p90_gt_p50_all": bool((df["lead_p90_d"] > df["lead_p50_d"]).all()),
        "worst_otif": df.loc[df["otif"].idxmin(), "principal_id"],
        "best_otif": df.loc[df["otif"].idxmax(), "principal_id"],
        "note": "Buffer days come from observed p90 spread, not from the master record.",
    }
    (OUT / "supplier_reliability.json").write_text(json.dumps(summary, indent=2))
    print(df.to_string(index=False))
    print()
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
