"""Gate: every console screen names the AWS and SAP parts that make it true.

Fails if the console's strips drift from tools/aws_sap_map.py, if the answer trace stops
naming the component that wrote the sentence, or if the judge-facing card and the written
map go missing. Run before any demo, next to the other ui_* gates.

Run
---
    .venv/bin/python tools/ui_component_gate.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import aws_sap_map as M                                              # noqa: E402

WEB = ROOT / "web"
DEMO = ROOT / "demo"
MARK_BEGIN = "<!-- PROV:BEGIN -->"
MARK_END = "<!-- PROV:END -->"

fails: list[str] = []
oks: list[str] = []


def check(cond: bool, ok: str, bad: str) -> None:
    (oks if cond else fails).append(ok if cond else bad)


def main() -> int:
    # 1. every screen carries its own strip, word for word
    for entry in M.MAP:
        page = WEB / entry["file"]
        html = page.read_text() if page.exists() else ""
        if not html:
            fails.append(f"{entry['file']}: missing")
            continue
        m = re.search(re.escape(MARK_BEGIN) + r"(.*?)" + re.escape(MARK_END), html, re.S)
        if not m:
            fails.append(f"{entry['file']}: no provenance strip between the markers")
            continue
        strip = " ".join(m.group(1).split())
        # an out-of-date strip is the exact failure this gate exists for
        check(strip == " ".join(M.strip(entry).split()),
              f"{entry['file']}: strip is current",
              f"{entry['file']}: strip is stale, regenerate with tools/aws_sap_card.py")
        # the strip must carry both labels and the page's own facts
        check("<span class=\"prov-k\">AWS</span>" in m.group(1)
              and "<span class=\"prov-k\">SAP</span>" in m.group(1),
              f"{entry['file']}: names both AWS and SAP",
              f"{entry['file']}: strip is missing the AWS or SAP label")

    # 2. the console's own stylesheet must know how to draw the strip
    css = (WEB / "pasok.css").read_text()
    check(".prov {" in css, "pasok.css: has the strip rule",
          "pasok.css: no .prov rule, the strip renders unstyled")

    # 3. the answer trace names the component, not just the agent
    chat = (WEB / "chat.py").read_text()
    check('"agent": "SAP AI Core"' in chat,
          "chat.py: the answer trace names SAP AI Core",
          "chat.py: the answer trace no longer names SAP AI Core")
    check('ORCH_DEPLOYMENT' in chat,
          "chat.py: the trace reads the deployment id from the answer module",
          "chat.py: the trace does not carry the deployment id")
    ask = (ROOT / "src" / "sap" / "ask.py").read_text()
    check("ORCH_DEPLOYMENT" in ask,
          "ask.py: the deployment id has one home",
          "ask.py: ORCH_DEPLOYMENT missing")

    # 4. the two judge-facing artefacts exist and agree with the map
    md = DEMO / "aws-sap-per-screen.md"
    pdf = DEMO / "aws-sap-per-screen.pdf"
    check(md.exists(), "demo/aws-sap-per-screen.md exists",
          "demo/aws-sap-per-screen.md missing")
    check(pdf.exists(), "demo/aws-sap-per-screen.pdf exists",
          "demo/aws-sap-per-screen.pdf missing")
    if md.exists():
        text = md.read_text()
        missing = [e["route"] for e in M.MAP if e["route"] not in text]
        check(not missing, "the map covers every screen",
              f"the map is missing screens: {', '.join(missing)}")
        check(M.LAMBDA_URL in text, "the map carries the live Lambda URL",
              "the map lost the Lambda URL")
        check(M.ORCH_DEPLOYMENT in text, "the map carries the orchestration id",
              "the map lost the orchestration id")
    if pdf.exists():
        info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
        pages = next((l.split()[-1] for l in info.splitlines() if l.startswith("Pages")), "?")
        check(pages == "1", "the card is exactly one page",
              f"the card is {pages} pages, a judge cannot photograph it in one shot")

    # 5. no screen may claim a component the account gate blocks, and every screen states
    #    its honest limit
    for entry in M.MAP:
        blob = (entry["aws"] + " " + entry["sap"]).lower()
        for banned, why in (("agentcore runtime runs", "AgentCore Runtime is quota-0"),
                            ("converse", "native Bedrock Converse is gated"),
                            ("knowledge base owns", "no Knowledge Base exists")):
            check(banned not in blob, "", f"{entry['route']}: claims {why}")
        check(bool(entry.get("gated")), f"{entry['route']}: states its honest limit",
              f"{entry['route']}: no honest limit stated")

    for line in oks:
        if line:
            print(f"  ok   {line}")
    for line in fails:
        print(f"  FAIL {line}")
    print(f"\nui_component_gate: {len(oks)} passed, {len(fails)} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
