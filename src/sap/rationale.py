"""
Pasok — Decision rationale via SAP Orchestration (gpt-5.4)
==========================================================

Turns the Decision Agent's exception queue into buyer-facing recommendations, written
by gpt-5.4 through the SAP orchestration deployment (real SAP Generative AI Hub
pipeline: templating module -> LLM module).

Contract with the model: return ONE JSON object per call with a `recommendation` and a
`why` field. The prompt carries only real numbers from our own artefacts.

If the orchestration call fails for a row we keep the deterministic template rationale
and tag `source=template` — we never fabricate a model answer.

Run
---
    cd <repo root>
    .venv/bin/python src/sap/rationale.py
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "data" / "agents"
SAP = ROOT / "data" / "sap"
OUT = SAP

ORCH_DEPLOYMENT = os.environ.get("ORCH_DEPLOYMENT", "d8c092efb8980093")
TOKEN_FILE = Path(os.environ.get("AIGO_TOKEN_FILE", "/tmp/aigo_token.txt"))
API_FILE = Path(os.environ.get("AIGO_API_FILE", "/tmp/aigo_apiurl.txt"))

MAX_QUEUE = 40          # demo-sized batch; the queue can be larger
SLEEP_BETWEEN = 0.4     # be polite to the shared hackathon tenant

SYSTEM = (
    # The buyer reads sixty of these in a row. Every word has to earn its place, and no
    # word may be one they have to translate. A model echoes the labels in its prompt,
    # so the prompt below this one is written in plain words too.
    "You write one short answer for the person who buys stock for an Indonesian FMCG "
    "distributor. They know the trade, they do not read code, and they have sixty other "
    "rows waiting.\n"
    "1. The decision comes first, then the numbers behind it. Nothing else.\n"
    "2. Say 'stock left', 'delivery time', 'sells per day', 'order rule'. Never a field "
    "name, a code, an underscore in capitals, an arrow, or a value such as nan. If "
    "something is missing, write 'none'.\n"
    "3. No preamble, no restating the question, no 'so' or 'thus' or 'overall', no "
    "closing summary, no advice the numbers do not carry.\n"
    "4. Round the way a person reads: whole units, full rupiah, shares as percentages.\n"
    "Answer with ONE JSON object and nothing outside it, keys exactly "
    "\"recommendation\" (one sentence the buyer can act on) and \"why\" (one sentence "
    "carrying the specific numbers you were given)."
)


def get_token() -> tuple[str, str]:
    tok = TOKEN_FILE.read_text().strip()
    api = API_FILE.read_text().strip().replace("https://", "").rstrip("/")
    return tok, api


def build_prompt(row: pd.Series) -> str:
    return (
        # Plain labels on purpose: the model reuses the words it is given, so jargon in
        # this prompt comes back out of the model's mouth.
        f"SKU {row['sku']} from supplier {row['principal_id']}\n"
        f"- Available to sell now: {row['sellable_units']:,.0f} units "
        f"(on hand {row['on_hand_units']:,.0f}, on the way {row['in_transit_units']:,.0f})\n"
        f"- Sells per day: {row['velocity_units_day']:,.0f} units\n"
        f"- Days of stock left: {row['days_of_cover']:.1f}\n"
        f"- Worst-case delivery time from this supplier: {row['lead_time_days']} days\n"
        f"- Our order rule says an order is needed now: {'yes' if row['below_reorder'] else 'no'}\n"
    )


def call_orchestration(token: str, api: str, prompt: str) -> tuple[dict | None, dict]:
    body = {
        "config": {
            "modules": {
                "prompt_templating": {
                    "prompt": {
                        "template": [
                            {"role": "system", "content": SYSTEM},
                            {"role": "user", "content": prompt},
                        ]
                    },
                    "model": {"name": "gpt-5.4", "params": {"max_completion_tokens": 220}},
                }
            }
        },
        "placeholder_values": {},
    }
    req = urllib.request.Request(
        f"https://{api}/v2/inference/deployments/{ORCH_DEPLOYMENT}/v2/completion",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "AI-Resource-Group": "default",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return None, {"error": f"HTTP {e.code}", "body": e.read().decode()[:300]}
    except Exception as e:  # network/timeout
        return None, {"error": str(e)[:200]}

    text = ""
    try:
        text = resp["final_result"]["choices"][0]["message"]["content"]
    except Exception:
        try:
            text = resp["intermediate_results"]["llm"]["choices"][0]["message"]["content"]
        except Exception:
            text = ""
    meta = {
        "request_id": resp.get("request_id"),
        "model": resp.get("intermediate_results", {}).get("llm", {}).get("model"),
        "usage": resp.get("intermediate_results", {}).get("llm", {}).get("usage"),
    }
    return {"text": text, "raw": resp}, meta


def parse_json_reply(text: str) -> dict | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
        if "recommendation" in d and "why" in d:
            return d
    except Exception:
        return None
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    dec = pd.read_csv(AG / "decisions.csv")
    snap = pd.read_csv(ROOT / "data" / "stock" / "position_snapshot.csv")
    rpt = pd.read_csv(SAP / "rpt_scores.csv")

    df = snap.merge(
        rpt[["sku", "STOCKOUT_NEXT14", "STOCKOUT_NEXT14_conf", "DAYS_COVER_LEFT"]],
        on="sku", how="left",
    )
    # exception queue: agent says reorder, or the SAP model flags stockout risk
    q = df[(df["below_reorder"]) | (df["STOCKOUT_NEXT14"].astype(str).str.lower() == "yes")].copy()
    q = q.sort_values("sellable_units").head(MAX_QUEUE)
    print(f"exception queue: {len(q)} SKUs (of {len(df)})")

    token, api = get_token()
    rows = []
    t0 = time.time()
    ok = 0
    for _, r in q.iterrows():
        prompt = build_prompt(r)
        resp, meta = call_orchestration(token, api, prompt)
        if resp is None:
            rows.append({
                "sku": r["sku"], "source": "template", "recommendation": "Buyer review",
                "why": r["rationale"], "model": None, "request_id": None, "error": meta.get("error"),
            })
            continue
        parsed = parse_json_reply(resp["text"])
        if parsed:
            ok += 1
            rows.append({
                "sku": r["sku"], "source": "orchestration",
                "recommendation": parsed["recommendation"], "why": parsed["why"],
                "model": meta.get("model"), "request_id": meta.get("request_id"), "error": None,
            })
        else:
            rows.append({
                "sku": r["sku"], "source": "orchestration_unparsed",
                "recommendation": resp["text"][:200], "why": r["rationale"],
                "model": meta.get("model"), "request_id": meta.get("request_id"), "error": "json_parse",
            })
        time.sleep(SLEEP_BETWEEN)

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "rationales.csv", index=False)
    (OUT / "rationale_raw_sample.json").write_text(json.dumps(
        [{"sku": r["sku"], "source": r["source"], "text": r["recommendation"]} for _, r in out.head(3).iterrows()],
        indent=2))

    summary = {
        "queue_size": int(len(q)),
        "orchestration_ok": int(ok),
        "json_parse_rate": round(ok / max(1, len(q)), 3),
        "fallback_template": int((out["source"] == "template").sum()),
        "elapsed_s": round(time.time() - t0, 1),
        "deployment": ORCH_DEPLOYMENT,
        "model_seen": out["model"].dropna().unique().tolist(),
    }
    (OUT / "rationale_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print()
    for _, r in out.head(3).iterrows():
        print(f"[{r['source']}] {r['sku']}: {r['recommendation'][:110]}")
        print(f"      why: {str(r['why'])[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
