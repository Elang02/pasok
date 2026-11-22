"""
Pasok — stand-in for a distributor's ordering API (demo only)
=============================================================

This is NOT part of the agent. It is a fake ERP/OMS endpoint used to prove the swap in
`src/agents/order_intake.py`: the intake posts the same orders to this service over
HTTP exactly as it would to a real distributor's ordering system.

Run it and point the intake at it:

    .venv/bin/python tools/fake_distributor_api.py --port 8099 &
    PASOK_ORDER_ENDPOINT=http://127.0.0.1:8099 .venv/bin/python src/agents/order_intake.py --reset

Endpoints
---------
    GET  /health                  -> {"status": "ok", "system": "..."}
    POST /orders                  -> acknowledge an order (its own reference + terms)
    POST /receipts                -> post a goods receipt against a reference

The rules here are deliberately NOT the ones in LocalOrderDesk, so the demo shows the
agent adapting to a system it does not control: this desk rounds to a different pack
size (48), rejects orders below its own minimum value, and can promise a longer lead
than the agent asked for.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot_date() -> date:
    """The last day of the generated sales window, read from the data.

    This desk promises delivery from the day the order was actually placed,
    so a literal here promises against a day the loop never saw.
    """
    with (ROOT / "data" / "stock" / "position_snapshot.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    if rows and rows[0].get("snapshot"):
        return date.fromisoformat(rows[0]["snapshot"])
    raise SystemExit("position_snapshot.csv carries no snapshot date; "
                     "run run_chain.sh step 1 first")


SNAPSHOT = snapshot_date()
PACK = 48                     # this desk's pack size, different from the agent's assumption
MIN_VALUE_IDR = 5_000_000     # it refuses small orders outright (median order ~15M)
EXTRA_LEAD_DAYS = 2           # it adds a day or two on top of the requested lead
STATE = {"seq": 0, "orders": {}, "receipts": []}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    def log_message(self, format, *args):        # keep the demo output clean
        pass

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok", "system": "FAKE-DISTRIBUTOR-ERP",
                                    "pack_size": PACK, "min_value_idr": MIN_VALUE_IDR})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        body = self._read()

        if self.path == "/orders":
            po = body.get("po_id")
            if po in STATE["orders"]:
                return self._send(200, {**STATE["orders"][po], "duplicate": True})

            value = float(body["qty"]) * float(body["unit_cost_idr"])
            if value < MIN_VALUE_IDR:
                return self._send(422, {
                    "po_id": po, "reference": "", "rejected": True,
                    "reason": f"order value {value:,.0f} below system minimum {MIN_VALUE_IDR:,}",
                    "system": "FAKE-DISTRIBUTOR-ERP",
                })

            STATE["seq"] += 1
            ref = f"ERP{STATE['seq']:05d}"
            accepted = max(PACK, int(float(body["qty"]) // PACK) * PACK)
            promised = (SNAPSHOT + timedelta(
                days=int(body.get("lead_p90_days", 6)) + EXTRA_LEAD_DAYS)).isoformat()
            ack = {
                "po_id": po, "reference": ref, "sku": body["sku"],
                "principal_id": body["principal_id"],
                "units_ordered": float(body["qty"]), "units_accepted": float(accepted),
                "shortfall_units": round(float(body["qty"]) - accepted, 1),
                "acceptance": "FULL" if float(body["qty"]) == accepted else "PARTIAL",
                "reason": f"ERP pack size {PACK}",
                "unit_cost_idr": int(body["unit_cost_idr"]),
                "value_idr": round(accepted * float(body["unit_cost_idr"]), 0),
                "promised_delivery": promised,
                "submitted_at": body.get("submitted_at", ""),
                "system": "FAKE-DISTRIBUTOR-ERP",
                "duplicate": False,
            }
            STATE["orders"][po] = ack
            return self._send(201, ack)

        if self.path == "/receipts":
            ref = body.get("reference")
            for ack in STATE["orders"].values():
                if ack["reference"] == ref:
                    row = {"reference": ref, "po_id": ack["po_id"],
                           "units_accepted": ack["units_accepted"],
                           "units_received": float(body["units_received"]),
                           "received_at": (SNAPSHOT + timedelta(days=8)).isoformat(),
                           "status": "RECEIVED", "system": "FAKE-DISTRIBUTOR-ERP"}
                    STATE["receipts"].append(row)
                    return self._send(201, row)
            return self._send(404, {"error": f"unknown reference {ref}"})

        self._send(404, {"error": "not found"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    args = ap.parse_args()
    srv = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"fake distributor ERP listening on http://127.0.0.1:{args.port} "
          f"(pack {PACK}, min value {MIN_VALUE_IDR:,})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
