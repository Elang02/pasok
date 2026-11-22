#!/usr/bin/env python
"""Record one run of the replenishment loop.

The loop is meant to run once a day, before the buying desk opens. This script runs the
chain and then appends one honest row to `data/orders/run_log.csv`: when it ran, what it
decided, and what the suppliers promised back. Every field is read from an artefact the
chain just wrote. Nothing here invents a number, and a run that failed is recorded as a
failure rather than skipped, because a missing run is the thing a buyer needs to see.

Run
---
    .venv/bin/python tools/record_run.py              run the chain, then record
    .venv/bin/python tools/record_run.py --no-chain   record the artefacts as they are
"""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORD = ROOT / "data" / "orders"
LOG = ORD / "run_log.csv"
LAST = ORD / "last_run.json"
WIB = timezone(timedelta(hours=7))

FIELDS = [
    "run_id", "ran_at_wib", "snapshot", "seconds", "chain_exit",
    "orders_placed", "placed_without_a_person", "waiting_for_a_person",
    "value_placed_idr", "value_waiting_idr",
    "acknowledged", "value_accepted_idr", "units_shortfall", "receipts_posted",
]


def load(p: pathlib.Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:                                          # noqa: BLE001
        return {}


def build_row(run_id: str, seconds: float, chain_exit: int) -> dict:
    orders = load(ORD / "order_summary.json")
    intake = load(ORD / "intake_summary.json")
    dec = load(ROOT / "data" / "agents" / "decision_summary.json")
    acked = (intake.get("accepted_full") or 0) + (intake.get("accepted_partial") or 0)
    return {
        "run_id": run_id,
        "ran_at_wib": datetime.now(WIB).strftime("%Y-%m-%d %H:%M"),
        "snapshot": orders.get("snapshot") or dec.get("snapshot") or "",
        "seconds": round(seconds, 1),
        "chain_exit": chain_exit,
        "orders_placed": orders.get("skus_with_order", 0),
        "placed_without_a_person": orders.get("auto_issued", 0),
        "waiting_for_a_person": orders.get("escalated", 0),
        "value_placed_idr": orders.get("auto_value_idr", 0.0),
        "value_waiting_idr": orders.get("escalated_value_idr", 0.0),
        "acknowledged": acked,
        "value_accepted_idr": intake.get("value_accepted_idr", 0.0),
        "units_shortfall": intake.get("units_shortfall", 0.0),
        "receipts_posted": intake.get("receipts_posted", 0),
    }


def append(row: dict) -> None:
    """Append the run, replacing an earlier row for the same run_id.

    Re-running the recorder on the same day corrects that day instead of adding a second
    run: the log is an audit trail, and two rows for one run would misstate how often the
    loop actually ran.
    """
    rows = []
    if LOG.exists():
        with LOG.open() as fh:
            rows = [r for r in csv.DictReader(fh) if r.get("run_id") != row["run_id"]]
    rows.append(row)
    rows.sort(key=lambda r: r.get("run_id") or "")
    with LOG.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})
    LAST.write_text(json.dumps(row, indent=2))


def main() -> int:
    run_chain = "--no-chain" not in sys.argv
    t0 = time.time()
    code = 0
    if run_chain:
        p = subprocess.run(["bash", str(ROOT / "run_chain.sh")],
                           cwd=str(ROOT), capture_output=True, text=True)
        code = p.returncode
        tail = (p.stdout or "").strip().splitlines()[-1:] or [""]
        print(f"chain exit {code}: {tail[0]}")
    # the run is named by the clock, not by the data: two runs on one day are one run
    run_id = datetime.now(WIB).strftime("%Y-%m-%d")
    row = build_row(run_id, time.time() - t0, code)
    append(row)
    print("recorded:", ", ".join(f"{k}={row[k]}" for k in
          ("run_id", "orders_placed", "placed_without_a_person",
           "waiting_for_a_person", "seconds")))
    return 0 if code == 0 else code


if __name__ == "__main__":
    raise SystemExit(main())
