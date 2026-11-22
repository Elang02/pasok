"""
Pasok — Supplier Ordering API (the stand-in FMCG distributor's own service)
===========================================================================

This is the distributor-side system the agent talks to when it places an order. It is
the concrete answer to "simulate ordering from a real supplier, and keep it in a
database": a self-contained HTTP service with its own SQLite database.

It is deliberately a *separate* service with its own rules, because that is what a real
distributor is. It is NOT the agent, it does not know the agent's totals, and it can
disagree with the agent (minimum order value, credit limit per principal, pack size).
The agent's intake must cope with all of that.

Run
---
    .venv/bin/python tools/distributor_api.py --port 8099
    curl -s http://127.0.0.1:8099/health
    curl -s http://127.0.0.1:8099/orders | python3 -m json.tool | head -40

Point the agent at it
---------------------
    PASOK_ORDER_ENDPOINT=http://127.0.0.1:8099 .venv/bin/python src/agents/order_intake.py --reset

Endpoints
---------
    GET  /health                 service + its rules
    GET  /principals             the supplier book (lead times, credit terms)
    GET  /orders                 every order this system holds, newest first
    GET  /orders/<reference>     one order with its lines and status history
    POST /orders                 place an order -> acknowledgement + system reference
    POST /orders/<ref>/receipt   post a goods receipt
    POST /orders/<ref>/cancel    cancel an order
    GET  /stats                  counts, values, and the DB path (proof of persistence)

Database
--------
SQLite at `data/distributor_api/pasok_distributor.db` (WAL). Tables:
`orders`, `order_lines`, `order_events`, `receipts`. Every state change writes an
`order_events` row, so the database is an auditable history, not just a latest-state
table.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "data" / "distributor_api"
DB_PATH = DB_DIR / "pasok_distributor.db"


def snapshot_date() -> date:
    """The last day of the generated sales window, read from the data.

    The desk promises delivery from the day the order was actually placed,
    so a literal here promises against a day the loop never saw.
    """
    with (ROOT / "data" / "stock" / "position_snapshot.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    if rows and rows[0].get("snapshot"):
        return date.fromisoformat(rows[0]["snapshot"])
    raise SystemExit("position_snapshot.csv carries no snapshot date; "
                     "run run_chain.sh step 1 first")


SNAPSHOT = snapshot_date()
REF_YEAR = SNAPSHOT.year

# ---- this distributor's own commercial rules (not the agent's assumptions) ----
PACK_UNITS = 48                 # it ships in cases of 48
MIN_ORDER_VALUE_IDR = 5_000_000
LEAD_EXTRA_DAYS = 2             # it promises the learned p90 plus its own handling


def load_principals() -> dict[str, dict]:
    """The supplier book, read from the distributor's own master data."""
    out = {}
    p = ROOT / "data" / "catalog" / "principals.csv"
    for r in csv.DictReader(p.open()):
        out[r["principal_id"]] = {
            "principal_id": r["principal_id"],
            "name": r["name"],
            # credit terms as a real distributor holds them
            "credit_limit_idr": {
                "P01": 900_000_000, "P02": 400_000_000, "P03": 850_000_000,
                "P04": 500_000_000, "P05": 600_000_000, "P06": 450_000_000,
                "P07": 550_000_000, "P08": 500_000_000, "P09": 480_000_000,
                "P10": 520_000_000, "P11": 700_000_000, "P12": 600_000_000,
            }.get(r["principal_id"], 500_000_000),
            "min_order_units": int(float(r["min_order_units"])),
        }
    return out


PRINCIPALS = load_principals()


# ------------------------------------------------------------------ database

def connect() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    reference        TEXT PRIMARY KEY,
    po_id            TEXT UNIQUE,           -- the caller's own id, for idempotency
    sku              TEXT NOT NULL,
    principal_id     TEXT NOT NULL,
    units_ordered    REAL NOT NULL,
    units_accepted   REAL NOT NULL,
    shortfall_units  REAL NOT NULL,
    unit_cost_idr    INTEGER NOT NULL,
    value_idr        REAL NOT NULL,
    acceptance       TEXT NOT NULL,         -- FULL | PARTIAL | REJECTED
    reason           TEXT,
    status           TEXT NOT NULL,         -- REJECTED | CONFIRMED | RECEIVED | CANCELLED
    promised_delivery TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_lines (
    reference   TEXT NOT NULL,
    sku         TEXT NOT NULL,
    units       REAL NOT NULL,
    unit_cost_idr INTEGER NOT NULL,
    PRIMARY KEY (reference, sku)
);
CREATE TABLE IF NOT EXISTS order_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reference   TEXT,
    po_id       TEXT,
    event       TEXT NOT NULL,             -- SUBMITTED | REJECTED | RECEIVED | CANCELLED
    detail      TEXT,
    at          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    reference   TEXT NOT NULL,
    units_received REAL NOT NULL,
    received_at TEXT NOT NULL
);
"""


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def event(con: sqlite3.Connection, reference: str | None, po_id: str | None,
          kind: str, detail: str) -> None:
    con.execute("INSERT INTO order_events (reference, po_id, event, detail, at) "
                "VALUES (?,?,?,?,?)",
                (reference, po_id, kind, detail, datetime.utcnow().isoformat(timespec="seconds")))


# ------------------------------------------------------------------ order logic

def place_order(con: sqlite3.Connection, body: dict) -> tuple[int, dict]:
    po = (body.get("po_id") or "").strip()
    if not po:
        return 400, {"error": "po_id is required"}
    sku = (body.get("sku") or "").strip().upper()
    if not sku:
        return 400, {"error": "sku is required"}

    # idempotency: the caller's own id is the key
    row = con.execute("SELECT * FROM orders WHERE po_id = ?", (po,)).fetchone()
    if row:
        return 200, {**dict(row), "duplicate": True}

    pid = (body.get("principal_id") or "").strip().upper()
    pinfo = PRINCIPALS.get(pid)
    if not pinfo:
        return 422, {"po_id": po, "rejected": True, "system": SYSTEM_NAME,
                     "reason": f"unknown principal {pid!r}"}

    try:
        qty = float(body["qty"])
        unit_cost = int(float(body["unit_cost_idr"]))
    except (KeyError, TypeError, ValueError):
        return 400, {"error": "qty and unit_cost_idr must be numeric"}

    value_ordered = qty * unit_cost
    if value_ordered < MIN_ORDER_VALUE_IDR:
        event(con, None, po, "REJECTED",
              f"value {value_ordered:,.0f} below minimum {MIN_ORDER_VALUE_IDR:,}")
        con.commit()
        return 422, {"po_id": po, "reference": "", "rejected": True,
                     "system": SYSTEM_NAME, "acceptance": "REJECTED",
                     "reason": f"order value {value_ordered:,.0f} below system minimum "
                               f"{MIN_ORDER_VALUE_IDR:,}"}

    # credit headroom with this principal, against everything already held
    held = con.execute(
        "SELECT COALESCE(SUM(value_idr),0) v FROM orders WHERE principal_id=? "
        "AND status IN ('CONFIRMED','RECEIVED')", (pid,)).fetchone()["v"]
    if held + value_ordered > pinfo["credit_limit_idr"]:
        event(con, None, po, "REJECTED",
              f"credit headroom {pinfo['credit_limit_idr'] - held:,.0f} < {value_ordered:,.0f}")
        con.commit()
        return 422, {"po_id": po, "reference": "", "rejected": True,
                     "system": SYSTEM_NAME, "acceptance": "REJECTED",
                     "reason": f"order value {value_ordered:,.0f} exceeds credit headroom "
                               f"{pinfo['credit_limit_idr'] - held:,.0f} for {pid}"}

    # accepted quantity: this system rounds to its own pack size
    accepted = max(PACK_UNITS, int(qty // PACK_UNITS) * PACK_UNITS)
    shortfall = round(qty - accepted, 1)
    if accepted < pinfo["min_order_units"]:
        accepted = pinfo["min_order_units"]
        shortfall = round(qty - accepted, 1)
    acceptance = "FULL" if shortfall == 0 else "PARTIAL"

    seq = con.execute("SELECT COALESCE(MAX(CAST(SUBSTR(reference, 9) AS INTEGER)),0)+1 n "
                      "FROM orders WHERE reference LIKE ?",
                      (f"SO-{REF_YEAR}-%",)).fetchone()["n"]
    ref = f"SO-{REF_YEAR}-{seq:06d}"

    now = datetime.utcnow().isoformat(timespec="seconds")
    promised = (SNAPSHOT + timedelta(days=int(float(body.get("lead_p90_days", 6)))
                                     + LEAD_EXTRA_DAYS)).isoformat()
    value = round(accepted * unit_cost, 0)
    reason = "" if acceptance == "FULL" else f"rounded to pack multiple {PACK_UNITS}"

    con.execute(
        "INSERT INTO orders (reference, po_id, sku, principal_id, units_ordered, "
        "units_accepted, shortfall_units, unit_cost_idr, value_idr, acceptance, reason, "
        "status, promised_delivery, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ref, po, sku, pid, qty, float(accepted), shortfall, unit_cost, value,
         acceptance, reason, "CONFIRMED", promised, now, now))
    con.execute("INSERT INTO order_lines (reference, sku, units, unit_cost_idr) VALUES (?,?,?,?)",
                (ref, sku, float(accepted), unit_cost))
    event(con, ref, po, "SUBMITTED", f"{accepted} of {qty} units accepted ({acceptance})")
    con.commit()

    return 201, {"po_id": po, "reference": ref, "sku": sku, "principal_id": pid,
                 "units_ordered": qty, "units_accepted": float(accepted),
                 "shortfall_units": shortfall, "acceptance": acceptance,
                 "reason": reason, "unit_cost_idr": unit_cost, "value_idr": value,
                 "promised_delivery": promised,
                 "submitted_at": body.get("submitted_at", ""),
                 "system": SYSTEM_NAME, "duplicate": False}


def post_receipt(con: sqlite3.Connection, ref: str, units: float) -> tuple[int, dict]:
    row = con.execute("SELECT * FROM orders WHERE reference = ?", (ref,)).fetchone()
    if not row:
        return 404, {"error": f"unknown reference {ref}"}
    if row["status"] in ("RECEIVED", "CANCELLED"):
        return 409, {"error": f"order {ref} is {row['status']}"}
    now = datetime.utcnow().isoformat(timespec="seconds")
    con.execute("INSERT INTO receipts (reference, units_received, received_at) VALUES (?,?,?)",
                (ref, float(units), now))
    con.execute("UPDATE orders SET status='RECEIVED', updated_at=? WHERE reference=?", (now, ref))
    event(con, ref, row["po_id"], "RECEIVED", f"{units} units")
    con.commit()
    return 201, {"reference": ref, "po_id": row["po_id"], "units_accepted": row["units_accepted"],
                 "units_received": float(units), "received_at": now, "status": "RECEIVED",
                 "system": SYSTEM_NAME}


def cancel_order(con: sqlite3.Connection, ref: str, reason: str) -> tuple[int, dict]:
    row = con.execute("SELECT * FROM orders WHERE reference = ?", (ref,)).fetchone()
    if not row:
        return 404, {"error": f"unknown reference {ref}"}
    now = datetime.utcnow().isoformat(timespec="seconds")
    con.execute("UPDATE orders SET status='CANCELLED', updated_at=? WHERE reference=?", (now, ref))
    event(con, ref, row["po_id"], "CANCELLED", reason or "cancelled by caller")
    con.commit()
    return 200, {"reference": ref, "status": "CANCELLED", "reason": reason, "system": SYSTEM_NAME}


SYSTEM_NAME = "PASOK-DISTRIBUTOR-ERP/1.0"


# ------------------------------------------------------------------ HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "PasokDistributorAPI/1.0"

    def _send(self, code: int, payload) -> None:
        body = json.dumps(payload, indent=1).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self) -> dict:
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def log_message(self, format, *args):
        print(f"{self.address_string()} {format % args}", flush=True)

    def do_GET(self):
        path = urlparse(self.path).path
        con = connect()
        try:
            if path == "/health":
                return self._send(200, {
                    "status": "ok", "system": SYSTEM_NAME, "database": str(DB_PATH),
                    "rules": {"pack_units": PACK_UNITS,
                              "min_order_value_idr": MIN_ORDER_VALUE_IDR,
                              "lead_extra_days": LEAD_EXTRA_DAYS,
                              "principals": len(PRINCIPALS)}})
            if path == "/principals":
                return self._send(200, list(PRINCIPALS.values()))
            if path == "/orders":
                rows = con.execute("SELECT * FROM orders ORDER BY created_at DESC, reference DESC "
                                   "LIMIT 200").fetchall()
                return self._send(200, [dict(r) for r in rows])
            if path.startswith("/orders/"):
                ref = path.split("/orders/", 1)[1].strip("/")
                row = con.execute("SELECT * FROM orders WHERE reference=?", (ref,)).fetchone()
                if not row:
                    return self._send(404, {"error": f"unknown reference {ref}"})
                lines = con.execute("SELECT * FROM order_lines WHERE reference=?", (ref,)).fetchall()
                evs = con.execute("SELECT * FROM order_events WHERE reference=? ORDER BY id",
                                  (ref,)).fetchall()
                rec = con.execute("SELECT * FROM receipts WHERE reference=? ORDER BY id",
                                  (ref,)).fetchall()
                return self._send(200, {"order": dict(row),
                                        "lines": [dict(x) for x in lines],
                                        "events": [dict(x) for x in evs],
                                        "receipts": [dict(x) for x in rec]})
            if path == "/stats":
                o = con.execute(
                    "SELECT COUNT(*) n, COALESCE(SUM(value_idr),0) v, "
                    "SUM(status='CONFIRMED') conf, SUM(status='RECEIVED') rec, "
                    "SUM(status='CANCELLED') canc FROM orders").fetchone()
                ev = con.execute("SELECT COUNT(*) n FROM order_events").fetchone()["n"]
                rej = con.execute("SELECT COUNT(*) n FROM order_events WHERE event='REJECTED'"
                                  ).fetchone()["n"]
                return self._send(200, {
                    "database": str(DB_PATH),
                    "orders": o["n"], "confirmed": o["conf"], "received": o["rec"],
                    "cancelled": o["canc"], "rejected": rej,
                    "value_idr": o["v"], "events": ev})
            return self._send(404, {"error": "not found"})
        finally:
            con.close()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read()
        con = connect()
        try:
            if path == "/orders":
                code, payload = place_order(con, body)
                return self._send(code, payload)
            if path == "/receipts":
                # alias: the intake posts {"reference": ..., "units_received": ...}
                code, payload = post_receipt(con, str(body.get("reference", "")),
                                             float(body.get("units_received", 0)))
                return self._send(code, payload)
            if path.startswith("/orders/") and path.endswith("/receipt"):
                ref = path.split("/orders/", 1)[1][:-len("/receipt")]
                code, payload = post_receipt(con, ref, float(body.get("units_received", 0)))
                return self._send(code, payload)
            if path.startswith("/orders/") and path.endswith("/cancel"):
                ref = path.split("/orders/", 1)[1][:-len("/cancel")]
                code, payload = cancel_order(con, ref, body.get("reason", ""))
                return self._send(code, payload)
            return self._send(404, {"error": "not found"})
        except ValueError as e:
            return self._send(400, {"error": str(e)})
        finally:
            con.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8099)
    ap.add_argument("--reset", action="store_true", help="drop and recreate the database")
    args = ap.parse_args()

    if args.reset and DB_PATH.exists():
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(DB_PATH) + suffix)
            if p.exists():
                p.unlink()

    con = connect()
    init_db(con)
    con.close()

    srv = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"{SYSTEM_NAME} on http://127.0.0.1:{args.port} | db {DB_PATH} | "
          f"pack {PACK_UNITS} | min value {MIN_ORDER_VALUE_IDR:,}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
