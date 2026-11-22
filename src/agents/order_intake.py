"""
Pasok — Order Intake (the distributor's ordering system, pluggable)
===================================================================

Proposal line 11: the loop's purchase orders flow *into the distributor's ordering
system*; line 22: the Decision Agent "drafts the purchase order in the distributor's
ordering system, and notifies the principal".

This module is the seam where that happens, and the reason it is a seam and not a
hard-coded SAP call: a real distributor's ordering system is SAP (OData / S/4), an ERP,
an OMS, or a Google Sheet. Nobody can point this build at a production endpoint that
does not exist yet. So the intake ships with two interchangeable adapters behind one
interface:

  local  -> a file-backed store that emulates an order desk (default; deterministic,
            works with no accounts, which is what the demo runs on)
  http   -> POSTs to a real endpoint given by PASOK_ORDER_ENDPOINT, so a distributor
            with an ordering API plugs in by setting one environment variable

Behaviour is the part that matters and it is identical across adapters:

  * only AUTO_ISSUED orders are submitted; ESCALATED ones stay in the human queue
    (proposal line 31: "supervision, not approval gating")
  * idempotency: a po_id already submitted is never submitted twice
  * the ordering system has its own reference format (`SO-<yyyy>-<seq>`), not ours
  * it may accept fewer units than ordered, rounded to the principal's order multiple,
    and it says why
  * it returns a promised delivery date built from the SKU's learned p90 lead time
  * a goods receipt can be posted back, which is what the learn step reconciles

Outputs
-------
data/orders/order_submissions.csv   one row per submitted order (our id -> their id)
data/orders/order_acks.csv          one row per acknowledgement with the system's terms
data/orders/intake_store.json       the local order desk's own store (local adapter)
data/orders/intake_summary.json     roll-up + reconciliation against purchase_orders

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/order_intake.py                    # file-backed desk
    .venv/bin/python src/agents/order_intake.py --reset            # clear the desk first

    # against a live ordering API (the demo proof; see tools/fake_distributor_api.py)
    PASOK_ORDER_ENDPOINT=http://127.0.0.1:8099 .venv/bin/python src/agents/order_intake.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORD = ROOT / "data" / "orders"
STORE = ORD / "intake_store.json"
STOCK = ROOT / "data" / "stock"


def snapshot_date() -> date:
    """The last day of the generated sales window, read from the data.

    Stock Position writes this value into `position_snapshot.csv`; the order
    desk promises delivery against the same date the decision was made on.
    A literal here drifts the moment the window moves, and the promise then
    points at a day the loop never saw.
    """
    with (STOCK / "position_snapshot.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    if rows and rows[0].get("snapshot"):
        return date.fromisoformat(rows[0]["snapshot"])
    raise SystemExit("position_snapshot.csv carries no snapshot date; "
                     "run run_chain.sh step 1 first")


SNAPSHOT = snapshot_date()
PROMISE_LEAD_DAYS = 6          # fallback when the SKU's p90 lead time is unknown
ORDER_MULTIPLE = 24            # the order desk's own pack size (cases of 24)


# ----------------------------------------------------------------------------
# the interface every adapter implements
# ----------------------------------------------------------------------------

class OrderDesk:
    """The distributor's ordering system, as this build needs it."""

    def submit(self, order: dict) -> dict:
        raise NotImplementedError

    def post_receipt(self, reference: str, received_units: float) -> dict:
        raise NotImplementedError


class LocalOrderDesk(OrderDesk):
    """File-backed order desk: the demo's stand-in for a real ERP.

    Deterministic. It applies the same rules a real system would apply without being
    told to: sequence-numbered references, pack multiples, and it rejects an order
    twice.
    """

    def __init__(self, store_path: Path = STORE, order_multiple: int = ORDER_MULTIPLE):
        self.path = store_path
        self.order_multiple = order_multiple
        self.state = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        return {"seq": 0, "orders": {}, "receipts": []}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.state, indent=2))

    def submit(self, order: dict) -> dict:
        po = order["po_id"]
        # One purchase order can carry several SKU lines now that MOQ is judged on the
        # principal's basket, so the idempotency key must be the line, not the PO header.
        key = f"{po}:{order['sku']}"
        if key in self.state["orders"]:
            return {**self.state["orders"][key]["ack"], "duplicate": True}

        self.state["seq"] += 1
        ref = f"SO-{SNAPSHOT.year}-{self.state['seq']:06d}"

        # the desk rounds to its own pack size and never accepts less than a pack
        qty = float(order["qty"])
        accepted = max(self.order_multiple, int(qty // self.order_multiple) * self.order_multiple)
        shortfall = round(qty - accepted, 1)
        acceptance = "FULL" if shortfall == 0 else "PARTIAL"

        promised = (SNAPSHOT + timedelta(days=int(order["lead_p90_days"]))).isoformat()
        ack = {
            "po_id": po,
            "reference": ref,
            "sku": order["sku"],
            "principal_id": order["principal_id"],
            "units_ordered": qty,
            "units_accepted": float(accepted),
            "shortfall_units": shortfall,
            "acceptance": acceptance,
            "reason": ("" if acceptance == "FULL" else
                       f"rounded to pack multiple {self.order_multiple}"),
            "unit_cost_idr": int(order["unit_cost_idr"]),
            "value_idr": round(accepted * float(order["unit_cost_idr"]), 0),
            "promised_delivery": promised,
            "submitted_at": order["submitted_at"],
            "system": "local-order-desk",
            "duplicate": False,
        }
        self.state["orders"][key] = {"ack": ack}
        self._save()
        return ack

    def post_receipt(self, reference: str, received_units: float) -> dict:
        for rec in self.state["orders"].values():
            ack = rec["ack"]
            if ack["reference"] == reference:
                row = {"reference": reference, "po_id": ack["po_id"],
                       "units_accepted": ack["units_accepted"],
                       "units_received": float(received_units),
                       "received_at": (SNAPSHOT + timedelta(days=PROMISE_LEAD_DAYS)).isoformat(),
                       "status": "RECEIVED"}
                self.state["receipts"].append(row)
                self._save()
                return row
        raise KeyError(f"no order with reference {reference}")


class HttpOrderDesk(OrderDesk):
    """POSTs to a real ordering system. Set PASOK_ORDER_ENDPOINT to switch.

    This is the adapter that proves the swap: the endpoint can be the distributor's
    SAP OData service, an ERP middleware, or (as in the demo) the stand-in desk in
    `tools/fake_distributor_api.py`. The request/response shape is the contract.
    """

    def __init__(self, base_url: str, timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())

    def submit(self, order: dict) -> dict:
        return self._post("/orders", order)

    def post_receipt(self, reference: str, received_units: float) -> dict:
        return self._post("/receipts", {"reference": reference,
                                        "units_received": received_units})


class OrderRefused(Exception):
    """The ordering system refused the order, with its own reason."""

    def __init__(self, code: int, payload: dict):
        self.code = code
        self.payload = payload
        super().__init__(f"HTTP {code}: {payload.get('reason', 'refused')}")


class RecordingHttpOrderDesk(HttpOrderDesk):
    """HttpOrderDesk that keeps the raw request/response pair for the demo evidence."""

    def __init__(self, base_url: str, timeout: int = 20):
        super().__init__(base_url, timeout)
        self.trace: list[dict] = []

    def _post(self, path: str, payload: dict) -> dict:
        try:
            out = super()._post(path, payload)
            self.trace.append({"path": path, "request": payload, "response": out, "http": 200})
            return out
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"reason": body[:200], "system": "external"}
            self.trace.append({"path": path, "request": payload,
                               "response": parsed, "http": e.code})
            # the body is consumed here, so carry the reason on a fresh error
            raise OrderRefused(e.code, parsed) from None


# ----------------------------------------------------------------------------
# the intake itself
# ----------------------------------------------------------------------------

def make_desk(reset: bool) -> tuple[OrderDesk, str]:
    if reset and STORE.exists():
        STORE.unlink()
    endpoint = os.environ.get("PASOK_ORDER_ENDPOINT", "").strip()
    if endpoint:
        return RecordingHttpOrderDesk(endpoint), f"http:{endpoint}"
    return LocalOrderDesk(), "local:data/orders/intake_store.json"


def submit_safe(desk: OrderDesk, order: dict) -> tuple[dict, bool]:
    """Submit one order; a refusal from the ordering system is a normal outcome.

    A real ERP can reject an order (below its minimum value, no credit line, blocked
    SKU). The loop must not crash on that: the order goes back to the human queue with
    the system's reason, exactly like an escalation.
    """
    try:
        ack = desk.submit(order)
        if ack.get("rejected"):
            return ack, False
        return ack, True
    except (urllib.error.HTTPError, OrderRefused) as e:
        if isinstance(e, OrderRefused):
            code, parsed = e.code, e.payload
        else:
            body = e.read().decode()
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"reason": body[:200]}
            code = e.code
        return {"po_id": order["po_id"], "reference": "",
                "sku": order["sku"], "principal_id": order["principal_id"],
                "units_ordered": order["qty"], "units_accepted": 0.0,
                "shortfall_units": order["qty"], "acceptance": "REJECTED",
                "reason": f"HTTP {code}: {parsed.get('reason', 'refused')}",
                "unit_cost_idr": order["unit_cost_idr"], "value_idr": 0.0,
                "promised_delivery": "", "submitted_at": order["submitted_at"],
                "system": parsed.get("system", "external"), "duplicate": False}, False


def load_orders() -> list[dict]:
    """Submitted orders = AUTO_ISSUED only. Escalated ones are the human queue."""
    po = list(csv.DictReader((ORD / "purchase_orders.csv").open()))
    dec = {d["sku"]: d for d in csv.DictReader((ROOT / "data" / "agents" / "decisions.csv").open())}
    out = []
    for r in po:
        if r["status"] != "AUTO_ISSUED":
            continue
        out.append({
            "po_id": r["po_id"],
            "sku": r["sku"],
            "principal_id": r["principal_id"],
            "qty": float(r["qty"]),
            "unit_cost_idr": int(float(r["unit_cost_idr"])),
            "value_idr": float(r["value_idr"]),
            "lead_p90_days": float(dec.get(r["sku"], {}).get("lead_p90_days", PROMISE_LEAD_DAYS)),
            "submitted_at": datetime.combine(
                SNAPSHOT, time(9, 0)
            ).isoformat(timespec="seconds"),
        })
    out.sort(key=lambda r: r["po_id"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="clear the local desk first")
    ap.add_argument("--receipts", action="store_true", help="also post goods receipts for every ack")
    args = ap.parse_args()

    ORD.mkdir(parents=True, exist_ok=True)
    desk, desk_label = make_desk(args.reset)

    orders = load_orders()
    subs, acks, rejected = [], [], []
    for o in orders:
        ack, ok = submit_safe(desk, o)
        if ok:
            subs.append({
                "po_id": o["po_id"], "reference": ack["reference"], "sku": o["sku"],
                "principal_id": o["principal_id"], "units_ordered": o["qty"],
                "submitted_at": o["submitted_at"], "system": ack["system"],
                "resubmitted": bool(ack.get("duplicate")),
            })
        else:
            rejected.append(ack)
        acks.append(ack)

    # idempotency check: submit the same orders again, nothing new may be created
    dup_accepted = 0
    for o in orders:
        _, ok = submit_safe(desk, o)
        if ok and desk.submit(o).get("duplicate"):
            dup_accepted += 1

    receipts = []
    if args.receipts:
        for a in acks:
            if a["reference"]:
                receipts.append(desk.post_receipt(a["reference"], a["units_accepted"]))

    def w(path: Path, rows: list[dict], fields: list[str]) -> None:
        with path.open("w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(rows)

    if subs:
        w(ORD / "order_submissions.csv", subs,
          ["po_id", "reference", "sku", "principal_id", "units_ordered",
           "submitted_at", "system", "resubmitted"])
    if acks:
        w(ORD / "order_acks.csv", acks,
          ["po_id", "reference", "sku", "principal_id", "units_ordered", "units_accepted",
           "shortfall_units", "acceptance", "reason", "unit_cost_idr", "value_idr",
           "promised_delivery", "submitted_at", "system", "duplicate"])

    escalated = sum(1 for r in csv.DictReader((ORD / "purchase_orders.csv").open())
                    if r["status"] == "ESCALATED")
    full = sum(1 for a in acks if a["acceptance"] == "FULL")
    partial = sum(1 for a in acks if a["acceptance"] == "PARTIAL")

    summary = {
        "snapshot": SNAPSHOT.isoformat(),
        "desk": desk_label,
        "orders_in_ledger": len(orders) + escalated,
        "submitted": len(subs),
        "escalated_not_submitted": escalated,
        "rejected_by_system": len(rejected),
        "accepted_full": full,
        "accepted_partial": partial,
        "units_ordered": round(sum(a["units_ordered"] for a in acks), 1),
        "units_accepted": round(sum(a["units_accepted"] for a in acks), 1),
        "units_shortfall": round(sum(a["shortfall_units"] for a in acks), 1),
        "value_accepted_idr": round(sum(a["value_idr"] for a in acks), 0),
        "idempotent_resubmits": dup_accepted,
        "receipts_posted": len(receipts),
        "reference_format": "issued by the ordering system, not by us",
        "swap_point": ("set PASOK_ORDER_ENDPOINT to point the same intake at a real "
                       "distributor ordering API; adapters differ only in transport"),
        "rejections_sample": rejected[:2],
        "sample_ack": acks[0] if acks else None,
    }
    (ORD / "intake_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    assert len(acks) == len(orders), f"acked {len(acks)} != auto-issued {len(orders)}"
    assert len(subs) + len(rejected) == len(orders), "submitted + rejected != orders"
    if subs:
        assert all(s["reference"] for s in subs), "a submitted order has no system reference"
    assert dup_accepted == len(subs), (
        f"idempotency broken: resubmitted {dup_accepted} of {len(subs)} accepted orders")
    assert len({a["reference"] for a in acks if a["reference"]}) == len(subs), \
        "duplicate references issued"
    print(f"\nVERIFICATION PASS: {len(subs)} submitted / {len(rejected)} refused by "
          f"{desk_label}, {full} full + {partial} partial, {dup_accepted} resubmits deduped, "
          f"{escalated} escalated held back")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
