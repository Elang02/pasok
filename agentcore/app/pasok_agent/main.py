#!/usr/bin/env python3
"""
Pasok — AgentCore Runtime agent (four-agent replenishment system)
=================================================================
Entrypoint for Amazon Bedrock AgentCore Runtime. Exposes the Pasok agent over the
AgentCore HTTP protocol (@app.entrypoint). The agent answers the demo questions by
querying the four agents' artifacts (decisions, stock position, supplier reliability,
purchase orders) — all bundled in ./data/.

Design note: the number crunching (forecast, guardrails, RPT scoring) runs in the
offline pipeline (src/); this runtime exposes the *reasoning* layer: it looks up the
per-SKU evidence each agent produced and answers in plain language, exactly what the
demo shows. The Bedrock model owns the orchestration and the rationale.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
log = app.logger

DATA = Path(__file__).parent / "data"

# ---------------------------------------------------------------- data loaders
_DECISIONS: list[dict] | None = None
_POSITION: dict[str, dict] = {}
_ORDERS: list[dict] | None = None
_CATALOG: dict[str, dict] = {}
_PRINCIPALS: dict[str, dict] = {}
_SUMMARY: dict = {}


def _rows(name: str) -> list[dict]:
    p = DATA / name
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def _load() -> None:
    global _DECISIONS, _ORDERS, _SUMMARY
    if _DECISIONS is not None:
        return
    _DECISIONS = _rows("decisions.csv")
    _ORDERS = _rows("purchase_orders.csv")
    for r in _rows("position_snapshot.csv"):
        _POSITION[r["sku"]] = r
    for r in _rows("catalog.csv"):
        _CATALOG[r["sku"]] = r
    for r in _rows("principals.csv"):
        _PRINCIPALS[r["principal_id"]] = r
    sp = DATA / "decision_summary.json"
    _SUMMARY = json.loads(sp.read_text()) if sp.exists() else {}


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- tools
@tool
def get_sku_decision(sku: str) -> str:
    """Return the Decision Agent's full recommendation for one SKU: forecast, event
    multiplier, lead time, buffer, guardrail flags, raw vs guarded order, and the
    plain-language rationale string."""
    _load()
    sku = sku.strip().upper()
    for d in _DECISIONS or []:
        if d["sku"].upper() == sku:
            return json.dumps(d, indent=2)
    return f"SKU {sku} not found in the decision snapshot."


@tool
def get_stock_position(sku: str) -> str:
    """Return the Stock Position Agent's live view for one SKU: sellable units,
    days of cover, lead time, shelf life, and the two risk flags (below_reorder,
    expiry_risk)."""
    _load()
    sku = sku.strip().upper()
    row = _POSITION.get(sku)
    if not row:
        return f"SKU {sku} not found in the stock position snapshot."
    return json.dumps(row, indent=2)


@tool
def list_exception_skus(limit: int = 10) -> str:
    """List SKUs that need attention: below reorder point, expiry risk, or an
    escalated purchase order. Returns the top N by severity."""
    _load()
    out = []
    for sku, row in _POSITION.items():
        if row.get("below_reorder") == "True" or row.get("expiry_risk") == "True":
            out.append({
                "sku": sku,
                "days_of_cover": _num(row.get("days_of_cover")),
                "below_reorder": row.get("below_reorder") == "True",
                "expiry_risk": row.get("expiry_risk") == "True",
                "lost_sales_total": _num(row.get("lost_sales_total")),
            })
    out.sort(key=lambda x: (x["days_of_cover"], -x["lost_sales_total"]))
    return json.dumps(out[:max(1, min(limit, 50))], indent=2)


@tool
def get_supplier_reliability(principal_id: str) -> str:
    """Return the Supplier Reliability Agent's learned reality for one principal:
    observed lead-time p50/p90 (NOT the catalog promise), fill rate, and the safety
    buffer that principal justifies."""
    _load()
    pid = principal_id.strip().upper()
    rows = _rows("supplier_reliability.csv")
    for r in rows:
        if r.get("principal_id", "").upper() == pid:
            return json.dumps(r, indent=2)
    return f"Principal {pid} not found. Known principals: {sorted(_PRINCIPALS)[:12]}"


@tool
def get_order(sku: str) -> str:
    """Return the purchase order the Decision Agent issued for one SKU: quantity,
    value, status (AUTO / QUEUED / ESCALATED), and the reason it got that status."""
    _load()
    sku = sku.strip().upper()
    hits = [o for o in (_ORDERS or []) if o.get("sku", "").upper() == sku]
    if not hits:
        return f"No purchase order for {sku}."
    return json.dumps(hits[:3], indent=2)


@tool
def get_network_summary() -> str:
    """Return the network-level summary: how many orders auto-issued vs escalated, the
    bullwhip amplification ratio (raw vs guarded), and the aggregate RPT score.
    Use this when asked how the system performed overall."""
    _load()
    sp = DATA / "order_summary.json"
    orders = json.loads(sp.read_text()) if sp.exists() else {}

    # Headline numbers, unambiguous. The escalation reason breakdown is NOT exclusive:
    # one order can carry several reasons, so those counts must never be summed.
    dec = _SUMMARY or {}
    headline = {
        "skus": dec.get("n_skus"),
        "orders_placed": dec.get("orders_placed"),
        "auto_issued": orders.get("auto_issued"),
        "escalated": orders.get("escalated"),
        "auto_rate": orders.get("auto_rate"),
        "total_value_idr": orders.get("total_value_idr"),
        "amplification_raw": (dec.get("amplification") or {}).get("raw"),
        "amplification_guarded": (dec.get("amplification") or {}).get("guarded"),
        "amplification_reduction_pct": (dec.get("amplification") or {}).get("reduction_pct"),
    }
    breakdown = orders.get("escalation_reason_breakdown") or {}
    return json.dumps({
        "headline": headline,
        "escalation_reason_breakdown": breakdown,
        "escalation_reason_breakdown_note": (
            "Reasons are NOT exclusive: a single order can carry several. Do not sum "
            "these counts and do not treat their total as the number of escalated "
            "orders. The escalated count is headline.escalated."),
        "raw": {"decision_summary": dec, "order_summary": orders},
    }, indent=2)


@tool
def get_order_status(po_id: str) -> str:
    """Return where a purchase order ended up in the distributor's ordering system:
    the system's own reference, accepted vs ordered units, the promised delivery date,
    and the current status (CONFIRMED / RECEIVED / REJECTED / CANCELLED). Use this when
    asked whether an order was actually placed or received."""
    _load()
    po = po_id.strip().upper()
    p = DATA / "order_acks.csv"
    if not p.exists():
        return "Order intake has not run: no order_acks.csv artefact."
    rows = _rows("order_acks.csv")
    hits = [r for r in rows if r.get("po_id", "").upper() == po]
    if not hits:
        return (f"{po} is not in the intake log: either no order was issued for it, or it "
                f"was escalated and stayed in the human queue instead of being submitted.")
    return json.dumps(hits[:3], indent=2)


TOOLS = [
    get_sku_decision,
    get_stock_position,
    list_exception_skus,
    get_supplier_reliability,
    get_order,
    get_order_status,
    get_network_summary,
]

SYSTEM_PROMPT = """You are Pasok, an autonomous replenishment agent for an Indonesian
consumer-goods distributor. You run a four-agent loop: Demand (forecast + event ramp),
Stock Position (live sellable stock and risk flags), Supplier Reliability (learned lead
times, not the promised ones), and Decision (the orchestrator that issues, holds,
redirects, or escalates orders).

You always ground your answer in the tools. Never invent numbers: every figure you
quote must come from a tool result. When you recommend an action, name the real drivers
(cover days, learned lead time, event multiplier, shelf life, credit headroom) the way
the Decision Agent's rationale does. Answer in the user's language; be concise and
concrete. If asked about a SKU you cannot find, say so plainly and offer the exception
list instead."""


def _build_agent() -> Agent:
    try:
        from model_provider import build_model, describe
        model = build_model()
        log.info("Pasok runtime model: %s", describe())
    except Exception as exc:            # noqa: BLE001 - never fail to start on this
        log.warning("model provider fallback to Bedrock default: %s", exc)
        model = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
    )


_agent: Agent | None = None


@app.entrypoint
async def invoke(payload, context):
    global _agent
    if _agent is None:
        _agent = _build_agent()
    prompt = payload.get("prompt") if isinstance(payload, dict) else str(payload)
    result = _agent(prompt)
    yield {"result": str(result)}


if __name__ == "__main__":
    app.run()
