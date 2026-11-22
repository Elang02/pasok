"""One source of truth for the AWS/SAP story, per console screen.

The rubric's heaviest line (technical execution on AWS/SAP, 25 percent) is answered by
naming components, not adjectives. Three artefacts have to say the same thing and must
not drift apart:

    web/*.html                        one strip per screen, in the page itself
    demo/aws-sap-per-screen.md        the written map a judge can read afterwards
    demo/aws-sap-per-screen.pdf       one page a judge can photograph

All three are generated from MAP below by tools/aws_sap_card.py, and
tools/ui_component_gate.py fails if a screen's strip stops matching this file.

Honesty rule for every line: `aws` and `sap` may only name a component that is live and
demonstrable today, with the artefact that proves it. Anything designed but blocked by the
account gate goes in `gated`, in the same words the page would say out loud.
"""

from __future__ import annotations

LAMBDA_URL = "https://vyfesxclb5gwzqqkg5csbkgxeq0jdnpf.lambda-url.us-west-2.on.aws/"
ORCH_DEPLOYMENT = "d8c092efb8980093"
MODEL = "gpt-5.4-2026-03-05"

MAP = [
    {
        "file": "chat.html",
        "route": "/",
        "name": "Console",
        "claim": "A buyer asks in plain words and reads an answer whose numbers are checked "
                 "against the records before it is shown.",
        "aws": "AWS Lambda `pasok_agent` (us-west-2, public Function URL) answers the same "
               "question class through `{\"action\":\"ask\"}`",
        "sap": f"SAP AI Core orchestration `{ORCH_DEPLOYMENT}`, model `{MODEL}` writes the "
               "sentence; the trace under each answer names it and its milliseconds",
        "gated": "native Bedrock `Converse` and AgentCore Runtime are account-gated; the "
                 "Lambda lane is the substitute, with Bedrock reached through Mantle",
    },
    {
        "file": "orders.html",
        "route": "/orders",
        "name": "Order history",
        "claim": "Every purchase order the loop placed, with its status and the reason it "
                 "holds that status.",
        "aws": "Lambda `{\"action\":\"network\"}` returns the same order summary "
               "the page shows",
        "sap": "SAP AI Core wrote the plain-language rationale on every escalated order "
               "(`data/sap/rationales.csv`, 40 of 40, no template fallback)",
        "gated": "the SAP business system itself is reached through a pluggable intake, "
                 "proven against a stand-in ERP, not a live SAP write",
    },
    {
        "file": "receiving.html",
        "route": "/receiving",
        "name": "Receiving",
        "claim": "What actually arrived against what was ordered, and what that says about "
                 "each supplier.",
        "aws": "Lambda `{\"action\":\"sku\"}` returns the same delivery and fill figures "
               "from the bundled artefacts",
        "sap": "the order intake seam (file-backed default, HTTP adapter by "
               "`PASOK_ORDER_ENDPOINT`) is where a distributor's own system plugs in",
        "gated": "no SAP business-system write path is built; the seam is the honest "
                 "substitute and it is demonstrable",
    },
    {
        "file": "health.html",
        "route": "/health",
        "name": "Stock health",
        "claim": "Days of cover per SKU, the coverage floor, and which stock is at risk of "
                 "expiring.",
        "aws": "Lambda `{\"action\":\"exceptions\"}` returns the same flags, sorted by the "
               "same urgency rule",
        "sap": "SAP AI Core RPT-1.6 (`sap-rpt-1.6`) scored all 600 SKUs on three targets in "
               "one call: 293 stockout-Yes, 52 expiry-Yes (`data/sap/rpt_scores.csv`)",
        "gated": "the Bedrock Knowledge Base that the proposal names for the registry does "
                 "not exist; the registry is a file the Decision Agent reads",
    },
    {
        "file": "transfers.html",
        "route": "/transfers",
        "name": "Depot transfers",
        "claim": "Stock that would expire where it sits is moved to a depot where it will "
                 "sell.",
        "aws": "Lambda lane answers from the same redirect artefact",
        "sap": f"the redirect decision carries its `{MODEL}` rationale like every other "
               "high-stakes action",
        "gated": "nothing here is blocked; the transfer is planned and recorded, not "
                 "executed against a warehouse system",
    },
    {
        "file": "suppliers.html",
        "route": "/suppliers",
        "name": "Suppliers",
        "claim": "Each principal's real lead time (p50 and p90), its fill rate, and whether "
                 "either has drifted.",
        "aws": "Lambda `{\"action\":\"sku\"}` carries the same supplier reliability figures",
        "sap": "no SAP dependency on this screen: the numbers come from the receiving "
               "records, and it is worth saying so out loud",
        "gated": "lead-time drift detection reports over a one-day window on this snapshot; "
                 "the year of history is on `/loop`",
    },
    {
        "file": "geography.html",
        "route": "/geography",
        "name": "Cities",
        "claim": "Where the demand and the orders are, city by city.",
        "aws": "Lambda lane answers from the same order and stock artefacts",
        "sap": "no SAP dependency; this is a reading of the same records",
        "gated": "city granularity is the outlet file's own field, not a geocoded feed",
    },
    {
        "file": "loop.html",
        "route": "/loop",
        "name": "Loop map",
        "claim": "The nine stages the loop runs, in order, with what each one read and "
                 "wrote.",
        "aws": "the four-agent reasoning layer is the same code the Lambda lane runs; the "
               "runtime is the host, the artefacts are the evidence",
        "sap": f"SAP AI Core `{MODEL}` writes the run report at the end of a loop "
               "(`/api/chat` streams the stages, then the model's summary)",
        "gated": "multi-agent coordination is in-process on the Lambda; AgentCore Memory "
                 "and Gateway return empty lists on this account",
    },
    {
        "file": "panel.html",
        "route": "/panel",
        "name": "Agent panel",
        "claim": "Agent state, the exception queue, one SKU traced end to end, and the "
                 "approvals waiting for a person.",
        "aws": "Lambda `{\"action\":\"exceptions\"}` and `{\"action\":\"sku\"}` mirror the "
               "queue and the single-SKU trace",
        "sap": "RPT-1.6 scores the SKU and gpt-5.4 writes its rationale; the Joule "
               "capability that carries the approval is published to the tenant",
        "gated": "AgentCore Memory and Gateway are empty on this account; the decision "
                 "history is a durable file instead",
    },
    {
        "file": "demo.html",
        "route": "/demo",
        "name": "Demo page",
        "claim": "The product performing: the model answers live, in front of the room.",
        "aws": "the Mantle endpoint serves the answering models on this account "
               "(`moonshotai.kimi-k2.5`, `deepseek.v3.2`, `qwen3-235b`, `zai.glm-4.7`)",
        "sap": f"the same page's live sample runs through SAP AI Core `{MODEL}`",
        "gated": "Amazon Nova and Llama are not served by Mantle (404) and stay behind the "
                 "native Bedrock gate",
    },
]

# What runs today, what is blocked, and by whom it can be lifted. Printed on the card so a
# judge who asks "where is your gateway" hears the quota evidence before the substitute.
GATES = [
    ("Native Bedrock `Converse` / `InvokeModel`",
     "`Operation not allowed`, all 86 active text models",
     "BYPASSED: Mantle endpoint serves models today"),
    ("AgentCore Runtime",
     "`Total Agents per Account` quota = 0, increase refused",
     "BLOCKED: only AWS can lift it; the lane runs on Lambda"),
    ("Bedrock Knowledge Base",
     "none exist on the account",
     "NOT BUILT: registry is a file, swap documented"),
    ("AgentCore Memory / Gateway",
     "`list-memories` and `list-gateways` return empty",
     "SUBSTITUTED: durable files, in-process coordination"),
    ("SAP business-system write",
     "no live write path",
     "SEAM: file-backed intake, proven against a stand-in ERP"),
]

# Said in the same words on the card, the strip and the doc: what the demo claims and what
# it deliberately does not.
NOT_CLAIMED = (
    "The console is served over the committed artefacts; the AWS lane answers the same "
    "question classes on Lambda, it does not host these pages. No post-deployment result is "
    "claimed: the stockout and inventory targets are targets. SAP is the scoring and "
    "reasoning layer here, not the system of record."
)


def rich(text: str) -> str:
    """Backticks become <code>, because the console reads this as HTML, not as markdown."""
    import re as _re
    return _re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def strip(entry: dict) -> str:
    """The one line a screen carries: what makes this screen true, in components."""
    return (
        f'<footer class="prov">'
        f'<span class="prov-k">AWS</span> {rich(entry["aws"])}'
        f'<span class="prov-sep">·</span>'
        f'<span class="prov-k">SAP</span> {rich(entry["sap"])}'
        f'</footer>'
    )


def by_file(name: str) -> dict:
    return next(e for e in MAP if e["file"] == name)
