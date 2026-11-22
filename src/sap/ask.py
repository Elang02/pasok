"""
Pasok — the answer lane: the model writes the answer, the artefacts supply the numbers.
=======================================================================================

Elang, 18 Okt 2026: "gausah ada template jawaban, saya mau AI nya yang ngerespon, gausah
save jawaban dulu, kecuali approval itu boleh disave, saya mau biar statusnya terupdate
terus".

So there are two lanes and they do different jobs:

    facts   the deterministic readers over the committed artefacts (pasok_answers.py).
            They are the only source of numbers, and they are cheap and offline.
    answer  gpt-5.4 through the SAP AI Core orchestration deployment, given the facts.
            It writes the prose a buyer reads.

Nothing here is cached. Every call re-reads the artefacts and re-asks the model, because a
saved answer is a stale answer. The only state this module keeps is the OAuth token, and
only because the keybroker rate-limits.

If the model is unreachable the caller gets `answer=None` and the reason, and the console
shows the facts with that reason. It never invents an answer and never silently falls back
to a template: the operator asked for the model's answer, so a template presented as one
would be a lie.

Wording rule: no jargon in anything a buyer reads.

Run
---
    cd <repo root>
    .venv/bin/python src/sap/ask.py "What is going to run out of stock within a week?"
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ORCH_DEPLOYMENT = os.environ.get("ORCH_DEPLOYMENT", "d8c092efb8980093")
KEYBROKER = os.environ.get(
    "AIGO_KEYBROKER",
    "https://hackathon-keybroker.cfapps.ap10.hana.ondemand.com/ai-core/aigo-key",
)
TOKEN_FILE = Path(os.environ.get("AIGO_TOKEN_FILE", "/tmp/aigo_token.txt"))
API_FILE = Path(os.environ.get("AIGO_API_FILE", "/tmp/aigo_apiurl.txt"))

TIMEOUT = int(os.environ.get("PASOK_MODEL_TIMEOUT", "150"))

SYSTEM = (
    # Ashraf, 18 Okt 2026: "sangat tidak menjawab untuk user awam kalo gini, gaada tanggal,
    # gaada apa apa, cuman tiba tiba data yang ga jelas alasannya... namanya agentic ya
    # bener bener kayak ngobrol sama orang gak sih harusnya, dan infonya lengkap yang
    # dibutuhkan". The old prompt asked for "one short answer" and told the model to stop
    # when the numbers ran out, and it did exactly that: "Lebaran" with no date, then a
    # heap of figures with no reason to care about them.
    "You are the assistant inside Pasok, the console an Indonesian FMCG distributor uses to "
    "keep stock. You are talking to the person who buys that stock. They know the trade, "
    "they do not read code, and they asked you because they want a straight answer.\n"
    "Write the way a good colleague writes when they know the answer: one sentence that "
    "answers the question, with the date or the number in it, then the few things the "
    "reader needs in order to act, in your own words. It has to read as a reply to them, "
    "not as a table with the labels removed.\n"
    "1. The first sentence answers the question. If they asked when, it carries the date "
    "and how far away that is. If they asked which or how many, it carries that. Never "
    "open by describing what you are about to say.\n"
    "2. Then give what they need: what it means for them, what it is worth, what the system "
    "is already doing about it, and what it needs from them. Say plainly when nothing is "
    "needed. Skip anything the facts do not carry. Three or four sentences is usually "
    "enough, and a short list is fine when the answer really is a list of items.\n"
    "3. Use only the numbers in FACTS. Never calculate, never round differently, never "
    "invent a SKU, and never drop a number the question asked for. Percentages as "
    "percentages, rupiah as rupiah with thousands separated, units as whole units.\n"
    "4. Plain words a buyer uses: stock left, delivery time, sells per day, order rule, "
    "waiting for a person. Never a field name, a stored code such as HOLD_ONE_CYCLE, an "
    "underscore in capitals, an arrow, or a value such as nan. If something is missing, "
    "write none.\n"
    "5. No preamble, no restating the question, no 'overall', no closing pleasantry, no "
    "offer to help further. No semicolons and no em dashes. One idea per sentence.\n"
    "6. Write the whole answer in the language the question was asked in. An English "
    "question gets English only: no Indonesian words anywhere, not even inside a mixed "
    "phrase, and the same rule holds the other way round. Keep SKU codes, supplier codes "
    "such as P08 and order numbers such as PO-0001 exactly as they are."
)


def _read_cached() -> tuple[str, str] | None:
    if TOKEN_FILE.exists() and API_FILE.exists():
        tok = TOKEN_FILE.read_text().strip()
        api = API_FILE.read_text().strip().replace("https://", "").rstrip("/")
        if tok and api:
            return tok, api
    return None


def _fetch_token() -> tuple[str, str]:
    """Ask the hackathon keybroker for a fresh key, then OAuth it."""
    req = urllib.request.Request(KEYBROKER, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        key = json.loads(r.read().decode())
    uaa = key.get("uaa", key)
    token_url = uaa["url"].rstrip("/") + "/oauth/token"
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": uaa["clientid"],
        "client_secret": uaa["clientsecret"],
    }).encode()
    treq = urllib.request.Request(
        token_url, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(treq, timeout=40) as r:
        tok = json.loads(r.read().decode())["access_token"]
    api = (key.get("serviceurls", {}).get("AI_API_URL", "")
           .replace("https://", "").rstrip("/"))
    TOKEN_FILE.write_text(tok)
    API_FILE.write_text(api)
    return tok, api


def token(force: bool = False) -> tuple[str, str]:
    """A token and the API host.

    A cached token is reused, which is why an EXPIRED one has to be handled: the caller
    retries once through `force`, because during a demo a 401 that never refreshes looks
    exactly like a dead service.
    """
    if not force:
        cached = _read_cached()
        if cached:
            return cached
    return _fetch_token()


ID_WORDS = {"apa", "yang", "berapa", "kapan", "stok", "barang", "habis", "paling",
            "dan", "untuk", "naik", "bulan", "depan", "mana", "gimana", "kok", "ini",
            "itu", "siapa", "supplier", "telat", "terlambat"}


def _language(question: str) -> str:
    """Which language to answer in. The model drifts between the two on this box, so the
    prompt carries an explicit directive instead of relying on rule 6 alone."""
    words = {w.strip("?.,!").lower() for w in (question or "").split()}
    if words & ID_WORDS:
        return "LANGUAGE: write the whole answer in Indonesian."
    return "LANGUAGE: write the whole answer in English, with no Indonesian words in it."


def _orchestrate(tok: str, api: str, question: str, facts: str) -> dict:
    prompt = (f"Question: {question}\n\n"
              f"FACTS (the only numbers you may use):\n{facts}\n\n"
              f"{_language(question)}")
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
                    "model": {"name": "gpt-5.4",
                              "params": {"max_completion_tokens": 900}},
                }
            }
        },
        "placeholder_values": {},
    }
    req = urllib.request.Request(
        f"https://{api}/v2/inference/deployments/{ORCH_DEPLOYMENT}/v2/completion",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {tok}",
            "AI-Resource-Group": "default",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def _text_of(payload: dict) -> str:
    final = payload.get("final_result") or {}
    choices = final.get("choices") or []
    if not choices:
        raise RuntimeError("the model returned no choices")
    return ((choices[0].get("message") or {}).get("content") or "").strip()


def answer(question: str, facts: str) -> dict:
    """The model's answer to `question`, grounded on `facts`.

    Returns {answer, error, ms, model, attempts}. `answer` is None when the model could
    not be reached, and `error` says why, so the console can show real facts instead of
    a plausible sentence nothing verified.
    """
    t0 = time.time()
    tok, api = token()
    attempts = 1
    try:
        payload = _orchestrate(tok, api, question, facts)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            # The cached token expired. Refresh once, then try again, once.
            attempts = 2
            tok, api = token(force=True)
            try:
                payload = _orchestrate(tok, api, question, facts)
            except Exception as e2:                               # noqa: BLE001
                return {"answer": None, "error": _why(e2), "ms": _ms(t0),
                        "model": None, "attempts": attempts}
        else:
            return {"answer": None, "error": _why(e), "ms": _ms(t0),
                    "model": None, "attempts": attempts}
    except Exception as e:                                        # noqa: BLE001
        return {"answer": None, "error": _why(e), "ms": _ms(t0),
                "model": None, "attempts": attempts}

    try:
        text = _text_of(payload)
    except Exception as e:                                        # noqa: BLE001
        return {"answer": None, "error": _why(e), "ms": _ms(t0),
                "model": None, "attempts": attempts}
    model = ((payload.get("final_result") or {}).get("model")
             or (payload.get("intermediate_results") or {}).get("model"))
    return {"answer": text, "error": None, "ms": _ms(t0),
            "model": model or "gpt-5.4", "attempts": attempts}


def _ms(t0: float) -> int:
    return int((time.time() - t0) * 1000)


def _why(e: BaseException) -> str:
    if isinstance(e, urllib.error.HTTPError):
        try:
            detail = e.read().decode()[:200]
        except Exception:                                         # noqa: BLE001
            detail = ""
        return f"HTTP {e.code} from SAP AI Core. {detail}".strip()
    if isinstance(e, urllib.error.URLError):
        return f"SAP AI Core unreachable: {e.reason}"
    return f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    import pasok_answers as ans

    q = " ".join(sys.argv[1:]) or "What is going to run out of stock within a week?"
    f = ans.stockout_within_a_week()
    print(f"Q: {q}\n")
    out = answer(q, f)
    if out["answer"]:
        print(out["answer"])
        print(f"\n[{out['model']} in {out['ms']} ms, {out['attempts']} attempt(s)]")
    else:
        print(f"no answer: {out['error']}")
        raise SystemExit(1)
