"""
Pasok — Principal Notification Ledger (GSD 06-01)
=================================================

Closes the proposal claim (line 22): "The Decision Agent ... drafts the purchase
order in the distributor's ordering system, and notifies the principal".

For every PO in data/orders/purchase_orders.csv this emits a dispatch record:

  AUTO_ISSUED  -> SENT               (dispatched the moment the order was issued)
  ESCALATED    -> HELD_FOR_APPROVAL  (not sent until a human approves)

Outputs
-------
data/orders/notification_ledger.csv     one row per PO
data/orders/notification_summary.json   counts by status / principal / channel

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/notification.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "orders"
CAT = ROOT / "data" / "catalog"
SR = ROOT / "data" / "agents"

CHANNEL = "email+portal"          # recorded channel, not a live send
RECIPIENTS = {                     # deterministic per-principal recipient (demo)
    pid: f"orders+{pid.lower()}@principal.example.id" for pid in
    [f"P{i:02d}" for i in range(1, 13)]
}


def _body(r: pd.Series, lead_p90: float) -> str:
    eta = ""
    if r["status"] == "AUTO_ISSUED":
        eta = f" Expected delivery within {lead_p90:.0f} days (learned p90 lead time)."
    return (
        f"Purchase order {r['po_id']} — {r['qty']:.0f} units of {r['sku']} "
        f"(value IDR {r['value_idr']:,.0f}).{eta} "
        f"Status: {r['status'].replace('_', ' ').lower()}. "
        f"Rationale: {r['rationale']}"
    )


def main() -> int:
    po = pd.read_csv(OUT / "purchase_orders.csv")
    sr = pd.read_csv(SR / "supplier_reliability.csv")[["principal_id", "lead_p90_d"]]
    po = po.merge(sr, on="principal_id", how="left")

    rows = []
    for _, r in po.iterrows():
        auto = r["status"] == "AUTO_ISSUED"
        rows.append({
            "po_id": r["po_id"],
            "sku": r["sku"],
            "principal_id": r["principal_id"],
            "channel": CHANNEL,
            "recipient": RECIPIENTS.get(r["principal_id"], "orders@principal.example.id"),
            "subject": f"PO {r['po_id']} — {r['sku']} ({r['qty']:.0f} units)",
            "body": _body(r, float(r["lead_p90_d"]) if pd.notna(r["lead_p90_d"]) else 0.0),
            "dispatch_status": "SENT" if auto else "HELD_FOR_APPROVAL",
            "dispatched_at": r["issued_at"] if auto else "",
            "po_status": r["status"],
        })

    led = pd.DataFrame(rows)
    led.to_csv(OUT / "notification_ledger.csv", index=False)

    summary = {
        "n_pos": int(len(led)),
        "by_status": led["dispatch_status"].value_counts().to_dict(),
        "by_channel": led["channel"].value_counts().to_dict(),
        "by_principal": led.groupby("principal_id").size().to_dict(),
        "value_notified_idr": float(po.loc[po["status"] == "AUTO_ISSUED", "value_idr"].sum()),
        "value_held_idr": float(po.loc[po["status"] == "ESCALATED", "value_idr"].sum()),
    }
    (OUT / "notification_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    assert len(led) == len(po), f"ledger rows {len(led)} != PO count {len(po)}"
    # A PO can carry several SKU lines (MOQ is judged on the principal's basket), so the
    # ledger is unique per line, not per PO header.
    assert not led.duplicated(subset=["po_id", "sku"]).any(), "duplicate PO line in ledger"
    sent = led[led["dispatch_status"] == "SENT"]
    held = led[led["dispatch_status"] == "HELD_FOR_APPROVAL"]
    assert (sent["dispatched_at"].astype(str).str.len() > 0).all(), "SENT row missing dispatched_at"
    assert (held["dispatched_at"].astype(str).str.len() == 0).all(), "HELD row has dispatched_at"
    assert len(sent) == int((po["status"] == "AUTO_ISSUED").sum())
    print(f"\nVERIFICATION PASS: {len(led)} POs, {len(sent)} SENT, {len(held)} HELD_FOR_APPROVAL")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
