"""
Pasok — AWS Lambda runtime for the four-agent replenishment loop
================================================================

This is the AWS lane of Pasok. It runs the four-agent reasoning layer on AWS Lambda,
with the LLM brain served by SAP AI Core (gpt-5.4) — the composition the proposal
describes: AWS hosts the agent, SAP is the business system.

It answers the demo questions from the bundled artefacts (no invented numbers) and can
call SAP AI Core for a live rationale when credentials are present.

Invocation payload:
    {"action": "exceptions", "limit": 5}
    {"action": "sku", "sku": "SKU0536"}
    {"action": "network"}
    {"action": "ask", "prompt": "Why was the top escalation held?"}
"""
from __future__ import annotations

import csv
import json
import os
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).parent / "data"
_SAP_TOKEN_CACHE = None
_BR_CACHE = None
_BR_EXP = 0.0


def _rows(name):
    p = DATA / name
    if not p.exists():
        return []
    with p.open(newline="") as f:
        return list(csv.DictReader(f))


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def exceptions(limit=5):
    pos = _rows("position_snapshot.csv")
    out = []
    for r in pos:
        if r.get("below_reorder") == "True" or r.get("expiry_risk") == "True":
            out.append({
                "sku": r["sku"],
                "principal_id": r["principal_id"],
                "days_of_cover": _num(r.get("days_of_cover")),
                "sellable_units": _num(r.get("sellable_units")),
                "below_reorder": r.get("below_reorder") == "True",
            })
    out.sort(key=lambda x: x["days_of_cover"])
    return {"exceptions": out[: max(1, min(int(limit), 50))], "total": len(out)}


def sku_detail(sku):
    sku = sku.strip().upper()
    dec = next((r for r in _rows("decisions.csv") if r["sku"].upper() == sku), None)
    po = next((r for r in _rows("purchase_orders.csv") if r["sku"].upper() == sku), None)
    pos = next((r for r in _rows("position_snapshot.csv") if r["sku"].upper() == sku), None)
    hist = next((r for r in _rows("decision_history.csv") if r["sku"].upper() == sku), None)
    if not dec:
        return {"error": f"{sku} not found"}
    return {
        "sku": sku,
        "position": pos,
        "decision": dec,
        "order": po,
        "learn": hist,
    }


def network():
    sc = DATA / "decision_summary.json"
    oc = DATA / "order_summary.json"
    lc = DATA / "learn_summary.json"
    return {
        "decision_summary": json.loads(sc.read_text()) if sc.exists() else {},
        "order_summary": json.loads(oc.read_text()) if oc.exists() else {},
        "learn_summary": json.loads(lc.read_text()) if lc.exists() else {},
    }


def pasok_mcp(name: str, arguments: dict | None = None) -> dict:
    """Call a tool on the Pasok MCP endpoint.

    The four-agent loop runs locally in the Pasok console and publishes its
    tools over MCP at PASOK_MCP_URL. The AWS lane is a client of that endpoint
    rather than a second copy of the artefacts, so there is exactly one brain.

    Returns {} when the endpoint is not configured or not reachable, and every
    caller falls back to the bundled artefacts. That keeps the Lambda working
    when the local console is down, which is the failure mode that matters
    during a live demo.
    """
    url = os.environ.get("PASOK_MCP_URL")
    if not url:
        return {}
    body = {"name": name, "arguments": arguments or {}}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=int(os.environ.get("PASOK_MCP_TIMEOUT", "30"))) as r:
            payload = json.loads(r.read().decode())
        if "error" in payload:
            return {"mcp_error": payload["error"]}
        parts = payload.get("content") or []
        text = parts[0].get("text", "") if parts else ""
        return {"tool": name, "text": text}
    except Exception as e:  # noqa: BLE001
        return {"mcp_error": f"{type(e).__name__}: {str(e)[:160]}"}


def _sap_token():
    """Fetch (and cache) a SAP AI Core OAuth token from client credentials."""
    global _SAP_TOKEN_CACHE
    if _SAP_TOKEN_CACHE:
        return _SAP_TOKEN_CACHE
    explicit = os.environ.get("SAP_TOKEN")
    if explicit:
        _SAP_TOKEN_CACHE = explicit
        return explicit
    cid = os.environ.get("SAP_CLIENTID")
    csec = os.environ.get("SAP_CLIENTSECRET")
    url = os.environ.get("SAP_TOKEN_URL")
    if not (cid and csec and url):
        return None
    import base64
    import urllib.parse
    import urllib.request
    basic = base64.b64encode(f"{cid}:{csec}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            _SAP_TOKEN_CACHE = json.loads(r.read())["access_token"]
            return _SAP_TOKEN_CACHE
    except Exception:
        return None


def ask_sap(prompt):
    """Live rationale from SAP AI Core (gpt-5.4) via the OpenAI-style chat endpoint.

    Primary reasoning path for the demo: AWS Bedrock is gated on the team account
    (native converse returns "Operation not allowed" on 86/86 models on the
    original account, and the replacement account has exhausted its daily token
    quota), so SAP AI Core carries the live reasoning.
    """
    tok = _sap_token()
    if not tok:
        return None
    import urllib.request
    api = os.environ.get("SAP_API", "api.ai.prod.ap-southeast-2.aws.ml.hana.ondemand.com")
    dep = os.environ.get("SAP_CHAT_DEPLOYMENT", "")  # isi lewat env var
    if not dep:
        return None
    body = {"messages": [
        {"role": "system", "content": "You are Pasok, an autonomous supply-chain "
                                      "replenishment agent. Answer in one short paragraph, "
                                      "grounded in the numbers given. Never invent figures."},
        {"role": "user", "content": prompt}],
        "max_completion_tokens": int(os.environ.get("SAP_MAX_TOKENS", "220"))}
    req = urllib.request.Request(
        f"https://{api}/v2/inference/deployments/{dep}/chat/completions"
        "?api-version=2024-12-01-preview",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "AI-Resource-Group": "default",
                 "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=100) as r:
            resp = json.loads(r.read().decode())
        return {"provider": f"sap-ai-core/{dep}",
                "text": resp["choices"][0]["message"]["content"].strip()}
    except Exception as e:
        return {"sap_error": str(e)[:160]}


def _bedrock_token():
    """Short-term Bedrock bearer token minted from the function role (cached ~11h)."""
    global _BR_CACHE, _BR_EXP
    now = time.time()
    if _BR_CACHE and now < _BR_EXP:
        return _BR_CACHE
    try:
        from bedrock_token import token_from_env
        tok = token_from_env(os.environ.get("BEDROCK_REGION", "us-west-2"))
    except Exception:
        tok = None
    if tok:
        _BR_CACHE, _BR_EXP = tok, now + 11 * 3600
    return tok


def ask_bedrock(prompt):
    """Live rationale from Amazon Bedrock via the Mantle compatible endpoint.
    Returns None if unavailable, so the caller can fall back."""
    tok = _bedrock_token()
    if not tok:
        return None
    import urllib.request
    region = os.environ.get("BEDROCK_REGION", "us-west-2")
    model = os.environ.get("BEDROCK_MODEL", "moonshotai.kimi-k2.5")
    body = {"model": model, "max_tokens": 220, "messages": [
        {"role": "system", "content": "You are Pasok, an autonomous supply-chain "
                                      "replenishment agent. Answer in one short paragraph, grounded "
                                      "in the numbers given. Never invent figures."},
        {"role": "user", "content": prompt}]}
    req = urllib.request.Request(
        f"https://bedrock-mantle.{region}.api.aws/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read().decode())
        return {"provider": f"bedrock-mantle/{model}",
                "text": resp["choices"][0]["message"]["content"].strip()}
    except Exception as e:
        return {"bedrock_error": str(e)[:160]}



def handler(event, context):
    """Entrypoint for both direct invoke and a Lambda Function URL (HTTP)."""
    http = isinstance(event, dict) and "requestContext" in event
    # Function URL / API Gateway shape: payload arrives as a JSON string in `body`
    if http:
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64
            raw = base64.b64decode(raw).decode()
        try:
            event = json.loads(raw)
        except Exception:
            event = {"action": "ask", "prompt": raw}

    if isinstance(event, str):
        try:
            event = json.loads(event)
        except Exception:
            event = {"action": "ask", "prompt": event}

    action = (event or {}).get("action", "network")
    if action == "exceptions":
        result = exceptions(int((event or {}).get("limit", 5)))
        # the live loop knows more than the bundle: prefer the MCP endpoint
        live = pasok_mcp("exceptions")
        if live.get("text"):
            result = {"source": "pasok-mcp", "exceptions_text": live["text"],
                      "bundled": result}
    elif action == "sku":
        result = sku_detail(str((event or {}).get("sku", "")))
    elif action == "ask":
        prompt = str((event or {}).get("prompt", ""))
        ctx = network()
        # ground the answer in the live loop when it is reachable
        live_ctx = pasok_mcp("network_summary")
        if live_ctx.get("text"):
            ctx = {"live_summary": live_ctx["text"], "bundled": ctx}
        grounded = (
            f"Network: {ctx['decision_summary'].get('n_skus')} SKUs, "
            f"{ctx['order_summary'].get('auto_issued')} auto-issued, "
            f"{ctx['order_summary'].get('escalated')} escalated, "
            f"amplification raw {ctx['decision_summary'].get('amplification', {}).get('raw')} -> "
            f"guarded {ctx['decision_summary'].get('amplification', {}).get('guarded')}. "
            f"Question: {prompt}"
        )
        # SAP AI Core is the primary reasoning path: Bedrock is gated on the
        # team account and the replacement account has exhausted its daily quota.
        sap = ask_sap(grounded)
        if sap and sap.get("text"):
            result = {"grounded_context": ctx, "prompt": prompt,
                      "provider": sap["provider"], "answer": sap["text"]}
        else:
            bedrock = ask_bedrock(grounded)
            result = {"grounded_context": ctx, "prompt": prompt,
                      "provider": (bedrock or {}).get("provider",
                                                      "bedrock-mantle (sap fallback)"),
                      "answer": (bedrock or {}).get("text"),
                      "sap_error": (sap or {}).get("sap_error")}
    else:
        result = network()

    return {"statusCode": 200,
            "headers": {"content-type": "application/json", "access-control-allow-origin": "*"},
            "body": result}
