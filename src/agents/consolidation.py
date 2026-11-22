"""
Pasok — Supplier Switch Proposals (GSD 06-06, part 1)
======================================================

Closes half of proposal line 31: the Decision Agent escalates when a *supplier switch*
is on the table.

For each principal whose learned fill rate sits below the network median, propose the
best alternative principal that carries the same category and offers better observed
lead time + fill. The proposal is an artefact for the human queue — nothing switches
automatically.

Output
------
data/orders/supplier_switch_proposals.csv

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/consolidation.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "data" / "agents"
CAT = ROOT / "data" / "catalog"
OUT = ROOT / "data" / "orders"


def main() -> int:
    sr = pd.read_csv(AG / "supplier_reliability.csv")
    cat = pd.read_csv(CAT / "catalog.csv")[["sku", "category", "principal_id"]]
    prin = pd.read_csv(CAT / "principals.csv")

    # category coverage per principal
    cov = cat.groupby("principal_id")["category"].apply(lambda s: set(s)).to_dict()
    median_fill = float(sr["fill_rate_observed"].median())

    weak = sr[sr["fill_rate_observed"] < median_fill].copy()
    rows = []
    for _, r in weak.iterrows():
        pid = r["principal_id"]
        cats = cov.get(pid, set())
        cands = []
        for _, o in sr.iterrows():
            if o["principal_id"] == pid:
                continue
            overlap = cats & cov.get(o["principal_id"], set())
            if not overlap:
                continue
            # better on both axes: lower p90 lead, higher fill
            if (o["lead_p90_d"] <= r["lead_p90_d"]) and (o["fill_rate_observed"] > r["fill_rate_observed"]):
                name = prin.loc[prin["principal_id"] == o["principal_id"], "name"]
                cands.append({
                    "principal_id": o["principal_id"],
                    "name": (name.iloc[0] if len(name) else o["principal_id"]),
                    "lead_p90_d": float(o["lead_p90_d"]),
                    "fill_rate_observed": float(o["fill_rate_observed"]),
                    "categories": ",".join(sorted(overlap)),
                    "lead_gain_d": round(float(r["lead_p90_d"]) - float(o["lead_p90_d"]), 1),
                    "fill_gain": round(float(o["fill_rate_observed"]) - float(r["fill_rate_observed"]), 4),
                })
        if not cands:
            continue
        best = sorted(cands, key=lambda c: (-c["fill_rate_observed"], c["lead_p90_d"]))[0]
        rows.append({
            "from_principal": pid,
            "from_fill_rate": float(r["fill_rate_observed"]),
            "from_lead_p90_d": float(r["lead_p90_d"]),
            "to_principal": best["principal_id"],
            "to_name": best["name"],
            "to_fill_rate": best["fill_rate_observed"],
            "to_lead_p90_d": best["lead_p90_d"],
            "shared_categories": best["categories"],
            "expected_fill_gain": best["fill_gain"],
            "expected_lead_gain_d": best["lead_gain_d"],
            "reason": (f"{pid} fill {r['fill_rate_observed']:.3f} below network median {median_fill:.3f}; "
                       f"{best['principal_id']} covers {best['categories']} at fill {best['fill_rate_observed']:.3f} "
                       f"(+{best['fill_gain']:.3f}) and lead p90 {best['lead_p90_d']:.0f}d"),
        })

    df = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "supplier_switch_proposals.csv", index=False)

    summary = {
        "network_median_fill": round(median_fill, 4),
        "weak_principals": sorted(weak["principal_id"].tolist()),
        "proposals": int(len(df)),
        "pairs": df[["from_principal", "to_principal"]].to_dict(orient="records") if len(df) else [],
    }
    (OUT / "supplier_switch_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    if len(df):
        assert df["from_principal"].is_unique, "duplicate source principal"
        for _, r in df.iterrows():
            assert r["to_fill_rate"] > r["from_fill_rate"], "candidate not better on fill"
            assert r["to_lead_p90_d"] <= r["from_lead_p90_d"], "candidate not better or equal on lead"
            assert r["shared_categories"], "no shared category"
    print(f"\nVERIFICATION PASS: {len(df)} switch proposals, all better-on-both-axes, category-overlapping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
