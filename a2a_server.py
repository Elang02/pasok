"""
Pasok — A2A server
==================

Exposes the four-agent replenishment loop over the Agent2Agent protocol, exactly the way
the organiser's tutorial does (`joule_a2a/project/Python-LangGraph/solution/server.py`):

    GET  /.well-known/agent-card.json   -> the Agent Card (discovery)
    POST /                              -> A2A message/send (task lifecycle)
    GET  /health

SAP Joule reaches this over a BTP Destination and reads the result from
`artifacts[0].parts[0].text`. The artifact our executor emits is named
`replenishment_result`.

Run locally:  .venv/bin/python a2a_server.py        (PORT env, default 8080)
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps.jsonrpc import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)
from fastapi.middleware.cors import CORSMiddleware

import pasok_answers as pasok_agents

# the tool surface, shared by the A2A skills above and the /mcp endpoint below.
# One source of truth: SAP Joule over A2A and the AWS lane over MCP call the
# same functions, so they can never disagree about what Pasok knows.
mcp_tool_registry = {
    "network_summary": pasok_agents.summary,
    "stock_running_out": pasok_agents.stockout_within_a_week,
    "spike_within_a_month": pasok_agents.spike_within_a_month,
    "exceptions": pasok_agents.exceptions,
    "sku_decision": lambda sku: pasok_agents.sku_decision(sku),
    "order_status": lambda po: pasok_agents.order_status(po),
    "answer": pasok_agents.answer,
}

ARTIFACT_NAME = "replenishment_result"


class PasokExecutor(AgentExecutor):
    """Bridges the A2A task lifecycle to the Pasok multi-agent loop."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.working),
                final=False,
            )
        )

        user_input = context.get_user_input()
        # The caller may send a plain question or a JSON object with a named intent.
        intent = "summary"
        target = ""
        try:
            parsed = json.loads(user_input)
            intent = str(parsed.get("intent", intent))
            target = str(parsed.get("sku") or parsed.get("po_id") or "")
        except (json.JSONDecodeError, TypeError):
            low = user_input.lower()
            po = _extract_po(user_input)
            sku = _extract_sku(user_input)
            if po:
                intent, target = "order", po
            elif sku:
                intent, target = "sku", sku
            elif "run out" in low or "runs out" in low or "stockout" in low \
                    or "stock out" in low or "habis" in low:
                intent = "stockout"
            elif "spike" in low or "ramp" in low or "lonjak" in low \
                    or ("more stock" in low) or ("within a month" in low):
                intent = "spike"
            elif "exception" in low or "queue" in low or "attention" in low:
                intent = "exceptions"

        loop = asyncio.get_event_loop()
        report = await loop.run_in_executor(
            None, lambda: pasok_agents.answer(intent=intent, target=target)
        )

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                artifact=Artifact(
                    artifactId=ARTIFACT_NAME,
                    name=ARTIFACT_NAME,
                    parts=[TextPart(text=report)],
                ),
            )
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            )
        )


def _extract_sku(text: str) -> str:
    import re
    m = re.search(r"SKU\d+", text, re.IGNORECASE)
    return m.group(0).upper() if m else ""


def _extract_po(text: str) -> str:
    import re
    m = re.search(r"PO-?\d+", text, re.IGNORECASE)
    if not m:
        return ""
    digits = re.search(r"\d+", m.group(0))
    return f"PO-{digits.group(0)}" if digits else ""


# --------------------------------------------------------------- app wiring
_vcap = json.loads(os.environ.get("VCAP_APPLICATION", "{}"))
_uris = _vcap.get("application_uris", [])
APP_URL = f"https://{_uris[0]}" if _uris else f"http://localhost:{os.environ.get('PORT', '8080')}"

agent_card = AgentCard(
    name="Pasok Replenishment Agent",
    description=(
        "Autonomous replenishment for FMCG distributors: forecast, stock position, supplier "
        "reliability and the decision that issues or escalates the purchase order."
    ),
    url=APP_URL,
    version="1.0.0",
    capabilities=AgentCapabilities(streaming=False),
    skills=[
        AgentSkill(
            id="network_summary",
            name="Replenishment summary",
            description=(
                "How the network performed: orders placed, auto-issued versus escalated, the "
                "bullwhip amplification ratio, and the SAP RPT stockout score."
            ),
            tags=["supply-chain", "replenishment", "forecast", "bullwhip"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
        AgentSkill(
            id="sku_decision",
            name="SKU decision",
            description=(
                "Why one SKU was reordered, held, redirected or escalated: days of cover, the "
                "learned event ramp, the supplier's lead time and the credit limit behind it."
            ),
            tags=["sku", "decision", "rationale"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
        AgentSkill(
            id="exception_queue",
            name="Exception queue",
            description=(
                "The SKUs slipping under their coverage floor or at stockout risk, with the "
                "action proposed for each."
            ),
            tags=["exceptions", "stockout", "expiry"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
        AgentSkill(
            id="stockout_within_a_week",
            name="Stock that runs out within a week",
            description=(
                "SKUs whose stock runs dry within seven days, and which of them run out "
                "before the next delivery can arrive, with the value at risk and the order "
                "the loop already placed."
            ),
            tags=["stockout", "cover", "urgency"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
        AgentSkill(
            id="spike_within_a_month",
            name="Stock to build up for a coming spike",
            description=(
                "SKUs carrying a learned demand ramp inside the next month, with how much "
                "extra stock the ramp implies: the event, the peak day, the multiplicative "
                "uplift per SKU and the extra units."
            ),
            tags=["ramp", "event", "replenishment", "uplift"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
        AgentSkill(
            id="order_status",
            name="Order status",
            description=(
                "Where a purchase order ended up in the distributor's ordering system: its "
                "reference, accepted versus ordered units and the promised delivery."
            ),
            tags=["order", "status", "delivery"],
            inputModes=["text/plain"],
            outputModes=["text/markdown"],
        ),
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/markdown"],
)

handler = DefaultRequestHandler(
    agent_executor=PasokExecutor(),
    task_store=InMemoryTaskStore(),
)
app = A2AFastAPIApplication(agent_card=agent_card, http_handler=handler).build()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "agent": "pasok", "skills": [s.id for s in agent_card.skills]}


# --------------------------------------------------------------- MCP endpoint
# The same tools the A2A skills wrap, over MCP, on the same process. SAP Joule
# and the AWS Lambda lane both reach Pasok here instead of each carrying a copy
# of the artefacts.
#
#   GET  /mcp/            -> tool discovery
#   POST /mcp/            -> call a tool
@app.get("/mcp/")
def mcp_tools():
    return {"name": "Pasok", "tools": sorted(mcp_tool_registry)}


@app.post("/mcp/")
async def mcp_call(payload: dict):
    """MCP-style tool call: {"name": "...", "arguments": {...}}."""
    name = (payload or {}).get("name") or ""
    args = (payload or {}).get("arguments") or {}
    fn = mcp_tool_registry.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}", "available": sorted(mcp_tool_registry)}
    try:
        return {"name": name, "content": [{"type": "text", "text": fn(**args)}]}
    except TypeError as e:
        return {"name": name, "error": f"bad arguments for {name}: {e}"}
    except Exception as e:  # noqa: BLE001
        return {"name": name, "error": f"{type(e).__name__}: {e}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
