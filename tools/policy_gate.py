"""
Pasok — policy gate for phase 18
================================

The order policy changed shape: no money ceiling, class-aware service level, space as a
constraint, MOQ per purchase order, downside gates. A gate is the only thing that stops
the old shape from creeping back, so this script fails loudly if any of it returns.

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python tools/policy_gate.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))


# 1. The money ceiling is gone from the code that issues orders.
src = (ROOT / "src" / "agents" / "order_executor.py").read_text()
check("no AUTO_LIMIT constant", "AUTO_LIMIT" not in src)
check("no hardcoded 200 million gate", not re.search(r"200[_e]?0*000_?000|200e6", src))

# 2. Service level is class-aware and recorded per line.
dec = pd.read_csv(ROOT / "data" / "agents" / "decisions.csv")
check("decisions carry abc_class", "abc_class" in dec.columns)
check("decisions carry service_z", "service_z" in dec.columns)
if {"abc_class", "service_z"} <= set(dec.columns):
    # The policy is per run: read the service levels the run recorded rather than a literal.
    summary = json.loads((ROOT / "data/orders/order_summary.json").read_text())
    want = summary.get("policy", {}).get("class_z") or {"A": 1.28, "B": 1.04, "C": 0.84}
    caps = summary.get("policy", {}).get("cover_cap_days") or {}
    bad = [
        f"{r.sku}:{r.abc_class}:{r.service_z}"
        for r in dec[["sku", "abc_class", "service_z"]].drop_duplicates().itertuples()
        if abs(float(r.service_z) - want.get(str(r.abc_class), -1)) > 0.006
    ]
    check("z matches the class map", not bad, ", ".join(bad[:3]))

# 3. Warehouse master exists and capacity is derived, not typed into the executor.
cap_path = ROOT / "data" / "warehouse" / "capacity.json"
uv_path = ROOT / "data" / "warehouse" / "unit_volume.csv"
check("capacity.json exists", cap_path.exists())
check("unit_volume.csv exists", uv_path.exists())
if cap_path.exists() and uv_path.exists():
    cap = json.loads(cap_path.read_text())
    uv = pd.read_csv(uv_path)
    check("capacity has a derivation", bool(cap.get("derivation")))
    check("unit volume covers the catalogue", len(uv) == 600, f"{len(uv)} rows")
    check("unit volume has no zero", bool((uv["m3_per_unit"] > 0).all()))

# 4. The executor reports space and the downside gates.
summ_path = ROOT / "data" / "orders" / "order_summary.json"
if summ_path.exists():
    s = json.loads(summ_path.read_text())
    for key in ("warehouse_capacity_m3", "warehouse_occupancy_m3", "warehouse_headroom_m3"):
        check(f"summary reports {key}", key in s)
    for reason in ("overstock", "near_expiry", "event_overreach", "storage_headroom", "below_moq"):
        check(f"breakdown tracks {reason}", reason in s.get("escalation_reason_breakdown", {}))
    check("no order exceeds headroom", s.get("order_volume_m3", 0) <= s.get("warehouse_headroom_m3", 0) + 1e-6)

# 5. MOQ is judged per purchase order: one po_id per principal.
po_path = ROOT / "data" / "orders" / "purchase_orders.csv"
if po_path.exists():
    po = pd.read_csv(po_path)
    pairs = po[["po_id", "principal_id"]].drop_duplicates()
    check("one PO id per principal", pairs["po_id"].is_unique and pairs["principal_id"].is_unique,
          f"{len(pairs)} pairs")

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
sys.exit(1 if failed else 0)
