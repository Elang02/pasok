"""
Pasok: web console
===================

A small web UI over the four-agent loop, so the two test questions (and the rest) can be
asked from a browser instead of a terminal.

    GET /                 the console
    GET /api/ask?q=...    routes the question to an intent and returns the answer
    GET /api/health       status + available skills
    GET /api/data         the raw artefacts behind the answers

Bind:  PASOK_WEB_PORT (default 80)
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response

import pandas as pd

import pasok_answers as ans

# The answer lane lives in src/sap/ask.py: gpt-5.4 through the SAP AI Core orchestration
# deployment writes the prose, and pasok_answers supplies the numbers. Imported by path
# because src/ is not a package. Aliased, because this module has a route called `ask`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src" / "sap"))
import ask as _model                                              # noqa: E402
import figures as _fig

ROOT = pathlib.Path(__file__).resolve().parents[1]
HERE = pathlib.Path(__file__).resolve().parent

app = FastAPI(title="Pasok", docs_url=None, redoc_url=None)

# A page shell the browser keeps from an earlier build is what makes a working endpoint
# look like it is still loading. The shells are small, so they are never cached.
@app.middleware("http")
async def _no_store_html(request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store"
    return response

# The six questions the demo asks, kept as the catalogue the console's starter links
# mirror. They used to be injected as buttons into the overview and the panel as well,
# which is what made the same question look like three different features.
ROUTES = [
    ("stockout", "Running out soon",
     "What is going to run out of stock in the next seven days?"),
    ("spike", "Spike next month",
     "What goods need more stock because a spike is coming within a month?"),
    ("exceptions", "Waiting for a person",
     "Which SKUs are waiting in the queue?"),
    ("summary", "Network performance",
     "How did the network perform overall?"),
    ("sku", "Why SKU0041",
     "Why was SKU0041 reordered?"),
    ("order", "Where PO-0155",
     "Where did PO-0155 end up?"),
]


@app.get("/api/health")
def health() -> dict:
    tc = ans._json(ans.AG / "test_cases.json")
    return {
        "status": "ok",
        "skills": [s["id"] for s in ans.__dict__.get("_skills", [])]
                  or ["network_summary", "sku_decision", "exception_queue",
                      "stockout_within_a_week", "spike_within_a_month", "order_status"],
        "snapshot": json.loads((ans.AG / "decision_summary.json").read_text()).get("snapshot"),
        "orders": json.loads((ans.ORD / "order_summary.json").read_text()).get("skus_with_order"),
        "test_cases": sorted(tc.keys()) if tc else [],
    }


def route_question(text: str) -> tuple[str, str]:
    """Kept as the name this module already uses.

    The word list itself lives in pasok_answers, next to the facts it selects, so the chat
    lane and the answer lane cannot drift apart again. Lingering Indonesian phrases are
    kept on purpose: they are how the operator types.
    """
    return ans.route_question(text)


def _answer_with_model(text: str) -> dict:
    """The facts from the committed files, then the model's prose. Nothing is cached.

    Elang, 18 Okt 2026: "gausah ada template jawaban, saya mau AI nya yang ngerespon,
    gausah save jawaban dulu, kecuali approval itu boleh disave, saya mau biar statusnya
    terupdate terus". So every call re-reads the artefacts and re-asks the model, and the
    deterministic text travels with the answer as `facts` rather than being presented as
    the answer. When the model is unreachable the answer is None with a reason, and the
    console shows the facts. A template passed off as the model's answer would be a lie.
    """
    intent, target = route_question(text)
    try:
        facts = ans.answer(intent, target)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"the files behind the answer are unreadable: {type(exc).__name__}",
        )
    out = _model.answer(text, facts)
    return {
        "intent": intent,
        "target": target,
        "question": text,
        "answer": out["answer"],
        "facts": facts,
        "source": "model" if out["answer"] else "model unreachable",
        "model": out["model"],
        "ms": out["ms"],
        "attempts": out["attempts"],
        "error": out["error"],
    }


@app.get("/api/ask")
def ask(q: str = Query("", min_length=0)) -> dict:
    """The one place a question is answered. The model writes it, the files ground it."""
    text = (q or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty question")
    return _answer_with_model(text)


def _scrub(obj):
    """Replace NaN/Infinity floats with None so the payload is valid JSON."""
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v) for v in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float("inf"), float("-inf"))):
        return None
    return obj


def _json_safe(obj) -> bool:
    try:
        json.dumps(obj, allow_nan=False)
        return True
    except (ValueError, TypeError):
        return False


@app.get("/api/data")
def data() -> JSONResponse:
    def load(p: pathlib.Path):
        try:
            return json.loads(p.read_text())
        except Exception:                                    # noqa: BLE001
            return None
    payload = {
        "decision_summary": load(ans.AG / "decision_summary.json"),
        "order_summary": load(ans.ORD / "order_summary.json"),
        "test_cases": load(ans.AG / "test_cases.json"),
        "learn_summary": load(ans.AG / "learn_summary.json"),
    }
    # pandas writes NaN/Infinity into these artefacts; both are invalid JSON
    # for a strict parser, so scrub them before the response is serialised.
    scrubbed = json.loads(json.dumps(payload, allow_nan=False, default=str)
                          if _json_safe(payload) else
                          json.dumps(_scrub(payload), allow_nan=False, default=str))
    return JSONResponse(scrubbed)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """The console, at the front door.

    It used to be an overview page whose only content was a pointer to /chat, and that
    page is what made the same question look like three different features. The console
    page now IS the front door.
    """
    return _fig.apply((HERE / "chat.html").read_text())


@app.get("/demo", response_class=HTMLResponse)
def demo() -> str:
    """The demo-day page: the product performing, built to the taste-skill sheet."""
    return _fig.apply((HERE / "demo.html").read_text())


@app.get("/pasok.css")
def pasok_css() -> Response:
    """The one shared stylesheet for every Pasok page."""
    return Response(
        content=(HERE / "pasok.css").read_text(),
        media_type="text/css",
        headers={"Cache-Control": "no-cache"},
    )


# --------------------------------------------------------------------------
# The interactive surfaces: /chat (talk to the agents and watch the loop run)
# and /panel (agent state, queue, one-SKU trace). They are merged into THIS app
# rather than mounted, so no redirect_slashes round-trip is introduced.
# --------------------------------------------------------------------------
import chat as _chat                                            # noqa: E402
import live as _live                                            # noqa: E402

for _r in _chat.app.routes:
    if _r.path not in {x.path for x in app.routes}:
        app.routes.append(_r)
for _r in _live.app.routes:
    if _r.path not in {x.path for x in app.routes}:
        app.routes.append(_r)


@app.get("/api/reason")
def reason(q: str = Query("", min_length=0)) -> dict:
    """A second name for the same answer lane as /api/ask.

    There used to be two: a template on /api/ask and the model on /api/reason, so the
    same question had two different answers depending on which button a page called, and
    the model's lane was the only one that could say it had nothing. Now there is one
    lane, and this name survives only so the demo page's live-model sample keeps working.
    """
    text = (q or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="empty question")
    out = _answer_with_model(text)
    return {
        "question": text,
        "intent": out["intent"],
        "provider": out["model"],
        "answer": out["answer"],
        "error": out["error"],
        "grounded": out["facts"],
        "ms": out["ms"],
    }


@app.get("/order", response_class=HTMLResponse)
def one_order() -> HTMLResponse:
    """One order, and the arithmetic that produced it.

    The deck needs a picture of a single order with its reason, not a chat answer. Every
    number below is read from data/agents/one_pass.json, the trace the chain wrote for the
    worked example, so the page cannot drift from the order it describes.
    """
    op = json.loads((ROOT / "data" / "agents" / "one_pass.json").read_text())
    per, iss, dec = op["perceive"], op["issue"], op.get("decide", {})
    sku = op.get("sku", "")
    cat = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")
    hit = cat.loc[cat["sku"] == sku]
    name = str(hit.iloc[0]["name"]) if len(hit) else ""
    rows = [
        ("Stock on hand", f"{per['on_hand_units']:,.0f} units"),
        ("Days of cover", f"{per['days_of_cover']:.1f} days, trigger at {per['lead_trigger_days']:.1f}"),
        ("Sells while the truck runs", f"{dec.get('demand_lead_units', 0):,.0f} units"),
        ("On hand when the lot lands", f"{dec.get('pos_at_arrival_units', 0):,.0f} units"),
        ("Demand until the next arrival", f"{dec.get('demand_window_units', 0):,.0f} units"),
        ("The gap", f"{dec.get('need_units', 0):,.0f} units"),
        ("Principal ships", f"{dec.get('supplier_fill_rate', 0) * 100:.0f}% of what it is asked"),
        ("Order placed", f"{iss['qty']:,.0f} units, IDR {iss['value_idr']:,.0f}"),
        ("Rule that could have escalated it",
         str(iss.get("escalation_reason", "inside policy limits"))
         .replace("within policy limits", "inside policy limits")),
        ("Notification", f"{iss.get('notification_status', '')} to {op.get('principal_id', '')}"),
        ("Ordering system reference", iss.get("intake", {}).get("system_reference", "")),
    ]
    body = "".join(
        f'<tr><th scope="row">{k}</th><td>{v}</td></tr>' for k, v in rows)
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Pasok: {iss['po_id']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/pasok.css"></head><body>
<main class="sheet">
<p class="kicker">One order</p>
<h1>{iss['po_id']} · {sku}</h1>
<p class="lede">{name}. Why the ordering system placed it, in the order it decided.</p>
<table class="rec">{body}</table>
<p class="lede">{dec.get('rationale', '')}</p>
</main></body></html>"""
    return HTMLResponse(html)


if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PASOK_WEB_PORT", "80")))
