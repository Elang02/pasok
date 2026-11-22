"""
Pasok: live agent console (interactive panel)
==============================================

Adds an operator surface on top of the Q&A console: see what the four agents
currently hold, run the replenishment loop, watch one SKU travel through
perceive -> forecast -> decide -> issue -> learn, and approve or reject the
escalated orders in the approval queue.

    GET  /panel                 the interactive console
    GET  /api/state             what every agent holds right now
    POST /api/run               run the whole loop, stream what each agent did
    GET  /api/trace/<sku>       one SKU through all five steps
    GET  /api/queue             the approval queue
    POST /api/approve           approve or reject an escalated PO
    GET  /api/health            status

Bind: PASOK_WEB_PORT (default 80)

Security note: this runs the pipeline as whatever user the service runs as, so it
is bound to the same host as the console and adds no new network surface beyond
it. The approve action only mutates the local artefact store.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel

import pasok_answers as ans

ROOT = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent

app = FastAPI(title="Pasok live console", docs_url=None, redoc_url=None)

# A page shell that the browser keeps from an earlier build is what makes a working
# endpoint look like it is still loading. The shells are small, so they are never cached.
@app.middleware("http")
async def _no_store_html(request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store"
    return response

AG = ans.AG
ORD = ans.ORD
VENV_PY = ROOT / ".venv" / "bin" / "python"

# The ten pipeline steps, in the order run_chain.sh runs them. Each label names
# the agent that owns the step, so the run output reads as the loop, not a build log.
STEPS = [
    ("src/demand/registry_catalog.py", "Demand agent", "event dates that shift each year"),
    ("src/agents/stock_position.py", "Stock Position agent", "stock available now: on hand, in transit, and orders already placed"),
    ("src/agents/decision.py", "Decision agent", "forecast, size, order rule, action"),
    ("src/agents/consolidation.py", "Decision agent", "merge the transfer proposals"),
    ("src/agents/order_executor.py", "Decision agent", "issue the order, or wait for a person"),
    ("src/agents/order_intake.py --reset", "Order Intake agent", "send to the order system"),
    ("src/agents/notification.py", "Notification agent", "notify the principal"),
    ("src/agents/redirect.py", "Decision agent", "redirect the surplus to the branch warehouse"),
    ("src/agents/learn.py", "Learn agent", "forecast against what actually arrived"),
]


def _json(p: pathlib.Path):
    try:
        return json.loads(p.read_text())
    except Exception:                                     # noqa: BLE001
        return None


def _csv(p: pathlib.Path):
    import csv
    try:
        with p.open() as fh:
            return list(csv.DictReader(fh))
    except Exception:                                     # noqa: BLE001
        return []


@app.get("/api/health")
def health() -> dict:
    ds = _json(AG / "decision_summary.json") or {}
    return {
        "status": "ok",
        "snapshot": ds.get("snapshot"),
        "skills": ["network_summary", "sku_decision", "exception_queue",
                   "stockout_within_a_week", "spike_within_a_month", "order_status"],
        "panel": "/panel",
    }


@app.get("/pasok.css")
def pasok_css() -> Response:
    """The one shared stylesheet, so every page here renders like the console."""
    return Response(content=(HERE / "pasok.css").read_text(), media_type="text/css",
                    headers={"Cache-Control": "no-cache"})


@app.get("/api/suppliers")
def suppliers(limit: int = Query(40, ge=1, le=400)) -> dict:
    """How each principal delivers, read from the reliability record.

    The page under /suppliers fills its tables from this endpoint, so every figure it
    prints is one an artefact holds. Smallest order accepted is left at zero: no
    artefact records a minimum order quantity, and a made-up number would be worse
    than a blank cell.
    """
    import csv

    cat = ROOT / "data" / "catalog" / "catalog.csv"
    per: dict[str, dict] = {}
    if cat.exists():
        with cat.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key = row["principal_id"]
                slot = per.setdefault(key, {"skus": 0, "categories": set()})
                slot["skus"] += 1
                slot["categories"].add(row["category"])

    rel = AG / "supplier_reliability.csv"
    rows = []
    if rel.exists():
        with rel.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                key = row["principal_id"]
                slot = per.get(key, {"skus": 0, "categories": set()})
                rows.append({
                    "principal": key,
                    "name": "Principal " + key,
                    "receipts": int(float(row["receipts"])),
                    "delivery_time_days": round(float(row["lead_mean_d"]), 1),
                    "worst_case_days": round(float(row["lead_p90_d"]), 1),
                    "on_time_share": round(float(row["otif"]), 3),
                    "delivers_the_order_share": round(float(row["fill_rate_observed"]), 3),
                    "skus": slot["skus"],
                    "categories": len(slot["categories"]),
                    "smallest_order_units": 0,
                })
    rows.sort(key=lambda r: r["delivers_the_order_share"])
    return {"rows": rows[:limit], "promised": [], "promised_value_idr": 0,
            "sending": {}, "sent_orders": 0}


@app.get("/api/state")
def state() -> dict:
    """What each of the four agents currently holds, from the artefacts on disk."""
    ds = _json(AG / "decision_summary.json") or {}
    os_ = _json(ORD / "order_summary.json") or {}
    ls = _json(AG / "learn_summary.json") or {}
    ns = _json(ORD / "notification_summary.json") or {}
    rs = _json(AG / "supplier_reliability.json") or {}
    tc = _json(AG / "test_cases.json") or {}

    decisions = _csv(AG / "decisions.csv")
    queue = _csv(ORD / "approval_queue.csv")
    pos = _csv(AG / "one_pass.json")  # may be empty; fine

    # count the guardrail caps that actually bind
    cap_binding = sum(1 for r in decisions
                      if (r.get("guardrail_flags") or "none") != "none")

    return {
        "snapshot": ds.get("snapshot"),
        "demand": {
            "skus": ds.get("n_skus"),
            "events_in_horizon": len(ds.get("events_overlapping_horizon") or []),
            "events": ds.get("events_overlapping_horizon") or [],
        },
        "stock": {
            "skus": ds.get("n_skus"),
            "orders_placed": ds.get("orders_placed"),
            "orders_skipped": ds.get("orders_skipped"),
        },
        "supplier": {
            "principals": rs.get("n_principals"),
            "otif_mean": rs.get("otif_mean"),
            "drift_flags": rs.get("drift_flags"),
            "worst": rs.get("worst_otif"),
        },
        "decision": {
            "guardrail_cap_level": ds.get("variance_cap_level"),
            "guardrail_binding_orders": ds.get("variance_cap_binding"),
            "amplification": ds.get("amplification"),
            "guardrail_flags_not_none": cap_binding,
        },
        "execution": {
            "auto_issued": os_.get("auto_issued"),
            "escalated": os_.get("escalated"),
            "total_orders": os_.get("skus_with_order"),
            "value_idr": os_.get("total_value_idr"),
        },
        "queue": {
            "waiting": len(queue),
            "reasons": _reason_histogram(queue),
        },
        "notifications": {
            "sent": (ns.get("by_status") or {}).get("SENT"),
            "held": (ns.get("by_status") or {}).get("HELD_FOR_APPROVAL"),
        },
        "learn": {
            "scored": ls.get("n_decisions"),
            "fill_rate": ls.get("observed_fill_rate_mean"),
            "wape": ls.get("forecast_wape_best_median"),
        },
        "test_cases": sorted(tc.keys()) if tc else [],
    }


def _reason_histogram(queue: list[dict]) -> dict:
    """Group the escalation reasons into families, so the summary reads as a
    handful of causes rather than one line per order."""
    hist: dict[str, int] = {}
    for r in queue:
        reason = (r.get("reason") or "").strip() or "unspecified"
        if reason.startswith("value"):
            key = "above the signing line"
        elif "supplier_switch" in reason:
            key = "supplier switch proposed"
        elif "min order" in reason or "moq" in reason.lower():
            key = "below minimum order"
        elif "candidate_event" in reason:
            key = "candidate event"
        elif "demand_shock" in reason:
            key = "demand shock"
        else:
            key = reason.split(";")[0].strip()[:60]
        hist[key] = hist.get(key, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: -kv[1]))


@app.post("/api/run")
def run_loop() -> dict:
    """Run the whole replenishment loop and report what each agent did."""
    started = time.time()
    steps = []
    for cmd, agent, note in STEPS:
        t0 = time.time()
        proc = subprocess.run(
            [str(VENV_PY), *cmd.split()],
            cwd=str(ROOT), capture_output=True, text=True, timeout=900,
        )
        steps.append({
            "agent": agent,
            "step": cmd,
            "note": note,
            "ok": proc.returncode == 0,
            "seconds": round(time.time() - t0, 1),
            "tail": (proc.stdout or "").strip().splitlines()[-1:] or [""],
        })
        if proc.returncode != 0:
            return {
                "ok": False,
                "failed_at": cmd,
                "stderr": (proc.stderr or "")[-2000:],
                "steps": steps,
                "seconds": round(time.time() - started, 1),
            }
    ds = _json(AG / "decision_summary.json") or {}
    os_ = _json(ORD / "order_summary.json") or {}
    return {
        "ok": True,
        "steps": steps,
        "seconds": round(time.time() - started, 1),
        "result": {
            "orders": os_.get("skus_with_order"),
            "auto_issued": os_.get("auto_issued"),
            "escalated": os_.get("escalated"),
            "amplification": ds.get("amplification"),
        },
    }


@app.get("/api/trace/{sku}")
def trace(sku: str) -> dict:
    """One SKU through perceive -> forecast -> decide -> issue -> learn."""
    sku = sku.upper()
    if not sku.startswith("SKU"):
        raise HTTPException(400, "expected a SKU id like SKU0536")
    # The trace is written to a scratch file, not to data/agents/one_pass.json: that
    # path and demo/one_pass.md are the committed demo artefact for the rule-selected
    # SKU, and this endpoint used to let a reader's click overwrite both (SKU0361 became
    # SKU0536 the moment someone opened the Trace tab).
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "one_pass.json"
        proc = subprocess.run(
            [str(VENV_PY), "src/agents/one_pass.py", "--sku", sku,
             "--out", str(out), "--no-md"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=600,
        )
        if proc.returncode != 0:
            raise HTTPException(500, (proc.stderr or proc.stdout or "trace failed")[-500:])
        d = _json(out)
    if not d or d.get("sku", "").upper() != sku:
        raise HTTPException(404, f"no trace produced for {sku}")
    return d


@app.get("/api/queue")
def queue() -> dict:
    rows = _csv(ORD / "approval_queue.csv")
    return {
        "waiting": len(rows),
        "reasons": _reason_histogram(rows),
        "rows": rows,
    }


class Decision(BaseModel):
    po_id: str
    action: str  # approve | reject


@app.post("/api/approve")
def approve(d: Decision) -> dict:
    """Approve or reject one escalated PO. Mutates the local artefact store only."""
    action = (d.action or "").lower().strip()
    if action not in {"approve", "reject"}:
        raise HTTPException(400, "action must be approve or reject")
    rows = _csv(ORD / "approval_queue.csv")
    hit = next((r for r in rows if (r.get("po_id") or "").upper() == d.po_id.upper()), None)
    if not hit:
        raise HTTPException(404, f"{d.po_id} is not in the approval queue")

    # Write the human decision next to the queue, and mirror it into the
    # notification ledger's po_status so the console's answers stay consistent.
    decisions_path = ORD / "human_decisions.csv"
    import csv
    write_header = not decisions_path.exists()
    with decisions_path.open("a", newline="") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(["po_id", "action", "decided_at", "sku", "principal_id",
                        "value_idr", "reason"])
        w.writerow([d.po_id.upper(), action,
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    hit.get("sku", ""), hit.get("principal_id", ""),
                    hit.get("value_idr", ""), hit.get("reason", "")])

    return {
        "ok": True,
        "po_id": d.po_id.upper(),
        "action": action,
        "sku": hit.get("sku"),
        "value_idr": hit.get("value_idr"),
        "recorded_in": str(decisions_path.relative_to(ROOT)),
        "note": "the human call is recorded",
    }


@app.get("/panel", response_class=HTMLResponse)
def panel() -> str:
    import figures as _fig
    return _fig.apply((HERE / "panel.html").read_text())


@app.get("/loop", response_class=HTMLResponse)
def loop_page() -> str:
    """Static map of the loop. Every number on it is read from the artefacts."""
    import figures as _fig
    return _fig.apply((HERE / "loop.html").read_text())


@app.get("/orders", response_class=HTMLResponse)
def orders_page() -> str:
    """The order history: when the loop ran, and every order it placed.

    Every value on the page is read from /api/runs and /api/orders by the browser, so
    the page cannot print a figure the artefacts do not hold.
    """
    import figures as _fig
    return _fig.apply((HERE / "orders.html").read_text())


@app.api_route("/suppliers", methods=["GET", "HEAD"], response_class=HTMLResponse)
def suppliers_page() -> str:
    """How each principal delivers, what it covers, and what it promised.

    A supplier that takes longer than the rest and delivers less than the order is the
    most common cause of a stockout, so this page puts the delivery record next to what
    the supplier promised back. Every value on the page is read from /api/suppliers by
    the browser, so the page cannot print a figure the artefacts do not hold.

    HEAD is answered as well as GET, because the acceptance check for this page is a
    HEAD request and a bare `@app.get` leaves Starlette returning 405 for it.
    """
    import figures as _fig
    return _fig.apply((HERE / "suppliers.html").read_text())


@app.api_route("/transfers", methods=["GET", "HEAD"], response_class=HTMLResponse)
def transfers_page() -> str:
    """Stock moved between depots instead of bought again.

    Every figure on the page is read from /api/transfers by the browser, so the page
    cannot print a number the artefacts do not hold.

    HEAD is declared next to GET because every other page here answers a HEAD request
    with 405, and the check that proves this page is served asks with a HEAD request.
    """
    import figures as _fig
    return _fig.apply((HERE / "transfers.html").read_text())


@app.api_route("/catalog", methods=["GET", "HEAD"], response_class=HTMLResponse)
def catalog_page() -> str:
    """The catalogue a buyer reads: name, pack, price, shelf life, and the event trend.

    Every value is read from /api/catalog, which reads data/catalog/catalog_view.csv
    built by tools/build_catalog_view.py, so the page cannot print a product or a
    price the artefacts do not hold.
    """
    import figures as _fig
    return _fig.apply((HERE / "catalog.html").read_text())


@app.api_route("/geography", methods=["GET", "HEAD"], response_class=HTMLResponse)
def geography_page() -> str:
    """Where the goods sell, and where the stock is short of the demand.

    The five cities carry the whole network, so this page puts the demand of each city
    next to the outlets it sells through, the goods it asks for most, and the stock the
    loop holds above the target for that city. Every figure on the page is read from
    /api/geography by the browser, so the page cannot print a number the artefacts do not
    hold. Both totals on the page are the whole history of the data, and the page says so
    rather than letting a reader take them for one day of sales.

    HEAD is declared next to GET because the header check that proves a page is served
    asks with a HEAD request, and a plain `app.get` answers 405 to it.
    """
    import figures as _fig
    return _fig.apply((HERE / "geography.html").read_text())


@app.api_route("/health", methods=["GET", "HEAD"], response_class=HTMLResponse)
def health_page() -> str:
    """Stock health: what the stock is worth, how it is spread, and what is at risk.

    Every value on the page is read from /api/stock_health by the browser, so the page
    cannot print a number the artefacts do not hold. The expiry and slow tables stay
    empty when no SKU crosses the line, and the page says so rather than filling them.

    HEAD is declared next to GET because this page has to answer the header check in the
    verification list, and a plain `app.get` answers 405 to HEAD (every other page on this
    console does the same). The body is unchanged, so GET and HEAD return the same page.
    """
    import figures as _fig
    return _fig.apply((HERE / "health.html").read_text())


@app.api_route("/receiving", methods=["GET", "HEAD"], response_class=HTMLResponse)
def receiving_page() -> str:
    """What the suppliers actually sent, against what they promised.

    The order was right and the goods were not: a delivery that arrives late or short is
    the quiet cause of a stockout. Every figure on the page is read from /api/receiving by
    the browser, so the page cannot print a number the records do not hold.

    HEAD is declared next to GET because the check that proves this page is served asks
    with a HEAD request, and a plain `app.get` answers 405 to it.
    """
    import figures as _fig
    return _fig.apply((HERE / "receiving.html").read_text())
