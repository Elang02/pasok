"""Refresh the data snapshot inside the Lambda bundle from the repo artefacts.

The Lambda answers `/action=sku|network|exceptions` straight out of the CSV snapshot shipped
inside its zip, so a fix that changes an artefact is not in the deployed system until the
snapshot is refreshed and the function is redeployed. This copies by basename, reports any
bundle file with no source, and never touches handler.py.

    .venv/bin/python tools/refresh_lambda_bundle.py            # copy
    .venv/bin/python tools/refresh_lambda_bundle.py --check    # compare only, exit 1 on drift
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "aws" / "lambda" / "pasok_agent" / "data"

# where each bundled basename lives in the repo
SOURCES = {
    "decisions.csv": "data/agents",
    "decision_summary.json": "data/agents",
    "decision_history.csv": "data/agents",
    "rationales.csv": "data/agents",
    "position_snapshot.csv": "data/stock",
    "position_summary.json": "data/stock",
    "catalog.csv": "data/catalog",
    "principals.csv": "data/catalog",
    "purchase_orders.csv": "data/orders",
    "order_acks.csv": "data/orders",
    "order_submissions.csv": "data/orders",
    "order_summary.json": "data/orders",
    "approval_queue.csv": "data/orders",
    "redirect_decisions.csv": "data/orders",
    "notification_ledger.csv": "data/orders",
    "notification_summary.json": "data/orders",
    "intake_summary.json": "data/orders",
    "learn_summary.json": "data/agents",
    "one_pass.json": "data/agents",
    "branch_depot_ledger.csv": "data/orders",
    "rationales.csv": "data/sap",
    "redirect_summary.json": "data/orders",
    "sku_city_demand.csv": "data/catalog",
    "supplier_reliability.csv": "data/agents",
    "supplier_switch_proposals.csv": "data/orders",
    "supplier_switch_summary.json": "data/orders",
}


def digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report drift, change nothing")
    a = ap.parse_args()
    if not BUNDLE.is_dir():
        print(f"no bundle at {BUNDLE}")
        return 1
    stale, missing, fresh, unknown = [], [], 0, []
    for name in sorted(p.name for p in BUNDLE.iterdir() if p.is_file()):
        if name.endswith(".bak"):
            continue
        src_dir = SOURCES.get(name)
        if not src_dir:
            unknown.append(name)
            continue
        src = ROOT / src_dir / name
        dst = BUNDLE / name
        if not src.exists():
            missing.append(f"{name} (no {src_dir})")
            continue
        if digest(src) == digest(dst):
            fresh += 1
            continue
        stale.append(name)
        if not a.check:
            shutil.copy2(src, dst)
    print(f"fresh {fresh} | stale {len(stale)} | missing {len(missing)} | unknown {len(unknown)}")
    for label, items in (("stale", stale), ("missing", missing), ("unknown", unknown)):
        for i in items:
            print(f"  {label}: {i}")
    if a.check and (stale or missing):
        print("the deployed snapshot is behind the repo: redeploy before claiming the fix is live")
        return 1
    if not a.check and stale:
        print(f"refreshed {len(stale)} file(s); the bundle still needs deploying to AWS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
