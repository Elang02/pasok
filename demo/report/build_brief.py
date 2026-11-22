"""Build the one-read brief that sits beside the proposal and the deck."""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT = Path(__file__).resolve().parent
DARK = RGBColor(0x1D, 0x1D, 0x1F)
GREY = RGBColor(0x5F, 0x5F, 0x5F)
TINT = "F1EEE8"


def setup():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
    sec.top_margin = Inches(0.55)
    sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)
    st = doc.styles["Normal"]
    st.font.name = "Helvetica"
    st.font.size = Pt(9.5)
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.line_spacing = 1.15
    return doc


def title(doc, text, sub):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(22)
    r.font.bold = True
    r.font.color.rgb = DARK
    p.paragraph_format.space_after = Pt(2)
    q = doc.add_paragraph()
    r2 = q.add_run(sub)
    r2.font.size = Pt(10.5)
    r2.font.color.rgb = GREY
    q.paragraph_format.space_after = Pt(10)


def h(doc, text, before=12, size=13):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = True
    r.font.color.rgb = DARK
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True


def lead(doc, text, size=9.5, italic=False, colour=DARK, after=6):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.italic = italic
    r.font.color.rgb = colour
    p.paragraph_format.space_after = Pt(after)
    return p


def numbered(doc, items):
    for text in items:
        p = doc.add_paragraph(style="List Number")
        r = p.add_run(text)
        r.font.size = Pt(9.5)
        p.paragraph_format.space_after = Pt(3)


def table(doc, headers, rows, widths, size=8.2, header_bg="E9E5DC"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    tblPr = t._tbl.tblPr
    tblPr.append(tblPr.makeelement(qn("w:tblW"), {qn("w:type"): "dxa",
                                                  qn("w:w"): str(int(sum(widths) * 1440))}))
    tblPr.append(tblPr.makeelement(qn("w:tblLayout"), {qn("w:type"): "fixed"}))
    for i, w in enumerate(widths):
        t.columns[i].width = Inches(w)
    for cell, text in zip(t.rows[0].cells, headers):
        cell.width = Inches(widths[headers.index(text)])
        p = cell.paragraphs[0]
        r = p.add_run(text)
        r.font.bold = True
        r.font.size = Pt(size)
        p.paragraph_format.space_after = Pt(1)
        shd = cell._tc.get_or_add_tcPr().makeelement(qn("w:shd"), {qn("w:val"): "clear",
                                                                 qn("w:fill"): header_bg})
        cell._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, text in enumerate(row):
            cells[i].width = Inches(widths[i])
            p = cells[i].paragraphs[0]
            r = p.add_run(text)
            r.font.size = Pt(size)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.line_spacing = 1.05
    return t


def main():
    doc = setup()
    title(doc, "Pasok, in one read",
          "A brief for the presenter: how it works, where the cloud sits, and what each part is for. "
          "Aligned with the proposal (Agentic AI Hackathon 2026) and the submitted deck, checked against the repository.")

    lead(doc, "The whole thing in one sentence: one pass at six on 31 October placed 323 orders worth "
              "IDR 17.41 billion across 600 SKUs in 57 seconds, every one of them inside policy, and none "
              "of them waited for a person.")

    h(doc, "1.  How it works: five steps, ten programs")
    lead(doc, "The proposal names a closed loop with five steps. On the machine each step is a program that "
              "writes a file the next step reads.", after=6)
    table(doc,
          ["Step (proposal)", "Program", "What it leaves behind"],
          [["Perceive", "stock_position.py, supplier_reliability.py",
            "sellable position per SKU; lead time and fill per principal from 1,975 receipts"],
           ["Forecast", "decision.py (forecast block)", "baseline per SKU, plus the event multiplier learned from 33 past events"],
           ["Decide", "decision.py, consolidation.py",
            "size per SKU: cover target = lead p90 + 7-day review + buffer, then three guardrails, then gates"],
           ["Issue", "order_executor.py, order_intake.py, notification.py",
            "order in the ordering system, a note to the principal, or an escalation"],
           ["Learn", "learn.py, one_pass.py", "accuracy week by week, and one paragraph of reason per order"]],
          widths=[1.15, 2.6, 2.92])
    lead(doc, "run_chain.sh runs them in that order and pasok-loop.timer starts it at 06:00 WIB. A failing step "
              "stops the chain, and record_run.py still writes the row that says so.", size=9.2, italic=True,
         colour=GREY)

    h(doc, "2.  Four agents, one at a time")

    def agent(doc, name, question, rows):
        p = doc.add_paragraph()
        r = p.add_run(name)
        r.font.size = Pt(11)
        r.font.bold = True
        r.font.color.rgb = DARK
        r2 = p.add_run("   " + question)
        r2.font.size = Pt(9)
        r2.font.color.rgb = GREY
        p.paragraph_format.space_before = Pt(7)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        for label, text in rows:
            q = doc.add_paragraph()
            b = q.add_run(label + "  ")
            b.font.size = Pt(9.2)
            b.font.bold = True
            t = q.add_run(text)
            t.font.size = Pt(9.2)
            q.paragraph_format.space_after = Pt(1.5)
            q.paragraph_format.left_indent = Inches(0.0)
            q.paragraph_format.line_spacing = 1.1

    agent(doc, "Demand Agent", "when demand rises, and by how much", [
        ("Reads", "the sales ledger (10.01 million rows over 1,396 days), the event registry, and the "
                  "per-SKU ramp table. It also splits the catalogue twice, by volume (260 A, 188 B, 152 C) "
                  "and by volatility, from each SKU's coefficient of variation."),
        ("Decides", "one shape per SKU and event, learned from 33 past occurrences: the peak multiplier, how "
                    "many days before the peak it starts building, the build slope, and the decay after. "
                    "4,208 SKU-event pairs have no shape, 425 step, and 167 are genuinely ramped. A flat bump "
                    "is what a SKU gets when it has no history, and that is the 11.6% error against 7.8%."),
        ("Writes", "forecast_daily, event, event_mult and forecast_daily_eff in decisions.csv, one row per SKU."),
        ("On screen", "deck page 5 (13 of 600 SKUs move, the rest stay within ten percent of a normal day) and "
                      "page 8 (7.8% against 11.6%, 120 of 120 unregistered spikes caught)."),
        ("Without it", "every SKU is planned against the same flat week, so a pre-Lebaran order arrives after "
                       "the wave has already passed."),
    ])

    agent(doc, "Stock Position Agent", "how much can actually be sold, today", [
        ("Reads", "purchase orders, receipts and sales, on every run."),
        ("Computes", "one sellable number per SKU: on hand plus in transit plus open purchase orders. Days of "
                     "cover is that number over velocity, and a SKU is below reorder when cover falls under "
                     "its lead time plus seven days of safety (src/agents/stock_position.py:46 and :221)."),
        ("Writes", "position_snapshot.csv and the stock summary the console reads."),
        ("On screen", "deck page 6, where days of cover is 44.8 and the order is justified by an arrival gap; "
                      "page 11, where the position becomes IDR 17.41 bn of orders."),
        ("Without it", "an order is sized against the stock on the shelf alone, which ignores everything already "
                       "on a truck, and the buyer double-orders the same week."),
    ])

    agent(doc, "Supplier Reliability Agent", "how long that principal really takes", [
        ("Reads", "1,975 receipts, not the supplier master record."),
        ("Computes", "lead time p50 and p90 per principal, the observed fill rate (received over ordered), "
                     "on-time-in-full as on-time multiplied by fill, a drift flag when the recent mean sits "
                     "20% above the historical p90, and buffer days as the p90 to p50 spread, never below two."),
        ("Writes", "supplier_reliability.csv, plus the summary the /suppliers page shows."),
        ("On screen", "deck page 8, where the strip names P06 at 82.9% fill and 14.3 days lead."),
        ("Without it", "the plan uses the lead time printed in the master record, which is the one number in a "
                       "distributor nobody updates."),
    ])

    agent(doc, "Decision Agent", "what to send, hold, or redirect, and why", [
        ("Reads", "everything the first three agents wrote, plus the catalogue and each principal's fill."),
        ("Sizes", "cover target is lead p90 plus the seven-day review plus the buffer. Demand while the truck "
                  "runs comes off the forecast, and the position at arrival is sellable minus that demand. The "
                  "gap is demand until the next arrival minus the position at arrival; 407 units for SKU0436. "
                  "The order is the gap divided by the principal's fill, so 407 / 0.976 = 417."),
        ("Guards", "three rules run before any gate: the forecast is smoothed, a jump is damped against the "
                   "previous order (1.25 down to 0.32 times in the replay), and one delivery is capped at what "
                   "the shelf can still sell, which bound seven SKUs this morning and trimmed 10,028 units."),
        ("Gates", "MOQ with a deferral option, an expiry ceiling at the larger of four fifths of shelf life and "
                  "shelf life minus thirty days, and a peak envelope at the item's own peak times 1.05, which "
                  "is 10,763 units for SKU0436. The order is not gated on rupiah value; that was a deliberate "
                  "change, and the rationale says so."),
        ("Writes", "decisions.csv (323 orders on the snapshot), decision_summary.json, and one plain sentence "
                   "per order."),
        ("On screen", "pages 6, 7, 9 and 11: the same number from four angles, which is what makes the deck "
                      "survive a question about any one of them."),
        ("Without it", "the buyer gets a number with no explanation, and the first question in the room cannot "
                       "be answered from the screen."),
    ])

    h(doc, "3.  The cloud: who does what")
    table(doc,
          ["Part", "Its job in the demo", "Evidence"],
          [["SAP AI Core, RPT-1.6",
            "scores 600 SKUs at once: stockout in 14 days, expiry, ABC class, cover left. It flags 577 SKUs at "
            "expiry risk and 0 stockouts", "data/sap/rpt_summary.json, 10.73 s"],
           ["SAP orchestration, gpt-5.4",
            "writes the reason for each order: 40 of 40 parse as JSON, none templated",
            "data/sap/rationale_summary.json, 166 s"],
           ["AWS Lambda", "the same chain packaged as a function, plus the endpoint the console calls",
            "aws/, endpoint returns 403 today"],
           ["Amazon Bedrock", "fallback writer through Mantle; native Bedrock is closed to 86 of 86 models",
            "aws/README.md"],
           ["AgentCore Runtime", "agent runtime: written and healthy on /ping, deploy stopped by a quota of 0",
            "\u201cwritten, quota 0\u201d on deck page 10; see section 4"],
           ["This laptop", "the morning chain that actually runs, the console on 8090, the ordering system on 8099",
            "data/orders/last_run.json"]],
          widths=[1.45, 3.35, 1.87])
    lead(doc, "The safe sentence for the stage: \u201cSAP scores and writes the reason; AWS runs it; and for this "
              "demo the chain runs on one machine on a six o'clock timer.\u201d", after=4)

    h(doc, "4.  Why AgentCore is not running, in its own words")
    lead(doc, "The proposal puts the four agents on Amazon Bedrock AgentCore. The runtime is written and it "
              "answers /ping locally, but it was never deployed, and the reason is an account quota rather "
              "than the code.", after=6)
    table(doc,
          ["What we tried", "What came back", "What it means"],
          [["deploy the AgentCore runtime",
            "quota for runtime creation is 0 on account 321043733040",
            "the service refuses before a container is ever started; nothing in our code is reached"],
           ["run the runtime locally and call /ping",
            "Healthy",
            "the image, the handler and the agent loop are sound; only the hosted service is closed"],
           ["republish the Lambda with the current chain",
            "SCP denies lambda:* on that account, and the function belongs to account 865152853021",
            "the packaged lane cannot be updated from this machine, so it still holds an 11 October snapshot"],
           ["call the Lambda function URL",
            "403 with x-amzn-ErrorType AccessDeniedException on all three actions",
            "the URL is no longer public, so this is a policy answer, not a handler crash"],
           ["call Bedrock Converse on every model",
            "NOT_AUTHORIZED on 86 of 86 models",
            "native Bedrock is closed; the route that answers is Mantle with short-lived SigV4 keys"],
           ["create a Bedrock Knowledge Base for the event registry",
            "not attempted after the two blocks above",
            "the registry ships as a versioned CSV instead, which is what the agents actually read"]],
          widths=[1.9, 2.35, 2.42], size=8.0)
    lead(doc, "The sentence for a judge: \u201cAgentCore is where this is designed to run, and that deploy is "
              "blocked on a quota we do not control. What we could prove locally, we proved; what needs the "
              "account, we report with the exact error rather than claiming a deploy.\u201d",
         size=9.2, italic=True, colour=GREY)

    doc.add_page_break()
    h(doc, "5.  Three gaps between the proposal and the demo", before=0)
    lead(doc, "Say these before a judge finds them. Each one is a boundary, not a failure.", after=6)
    table(doc,
          ["The proposal says", "The demo runs", "The sentence that is true"],
          [["agents coordinate through AgentCore collaboration, Memory, and Gateway",
            "agents share files; decision history is decision_history.csv; there is no gateway",
            "\u201cAgents share files, not messages, so a decision can be audited a month later.\u201d"],
           ["orders flow into the distributor's SAP business system",
            "SAP is read for scoring and reasons; orders go to a separate ordering system",
            "\u201cSAP is the scorer and the writer; the order goes to the ordering system, and that is the seam "
            "we have not closed.\u201d"],
           ["a Bedrock Knowledge Base holds the event registry",
            "the registry is a versioned CSV in the repository",
            "\u201cThe event registry is a versioned file; Knowledge Base is the next step, not something we "
            "claim runs today.\u201d"]],
          widths=[2.1, 2.35, 2.22])

    h(doc, "6.  The deck, page by page: the number to defend")
    table(doc,
          ["Page", "What it claims", "The number"],
          [["2", "the calendar moves, a fixed reorder point does not",
            "Lebaran drifts 33 days in four years; Imlek 26; Nyepi 17"],
           ["3", "guardrails cut the bullwhip",
            "2.68 to 0.24 times; fill 98.93% against 98.68%; stock 2,187 to 274 units"],
           ["4", "four agents, one loop", "each agent hands over one number the next can check"],
           ["5", "the nearest event and what it moves",
            "13 of 600 SKUs move; Kakao Sari Cokelat Batang 58 to 79 a day (1.35 times)"],
           ["6", "one SKU, one order",
            "417 units = a 407 gap at a 97.6% fill; lead 18, review 7, buffer 6, target 31 days"],
           ["7", "the same decision on screen", "inside policy limits; SO-2026-000284"],
           ["8", "a learned shape against a flat bump",
            "error 7.8% against 11.6%; 120 of 120 unregistered spikes caught; network fill 90.60%"],
           ["9", "three rules keep one order honest",
            "1.25 to 0.32 times; 7 of 600 trimmed by the shelf-life cap"],
           ["10", "SAP and AWS", "600 SKUs in 10.73 s; 89.5% agreement; 40 of 40 rationales; AgentCore quota 0"],
           ["11", "one snapshot in money",
            "323 orders, IDR 17.41 bn, 0 escalated, 502 SKUs redirected worth IDR 12.68 bn"],
           ["12", "where the numbers come from",
            "600 SKUs, 120 outlets and 1,396 days are generated; PIHPS, the calendar and GAPMMI are not"],
           ["13", "five results beside published figures", "99.89%; 0.54%; 22 days; 0.21%; 1.3%"]],
          widths=[0.5, 2.5, 3.67], size=8.0)
    lead(doc, "One correction for page 11: the submitted PDF reads \u201cthe last planning pass, 28 October\u201d. "
              "The pass ran at six on 31 October, on the 28 October snapshot. Say: \u201cthe pass at six this "
              "morning, on the 28 October snapshot\u201d.", size=9.2, italic=True, colour=GREY)

    h(doc, "7.  Four sentences that are most likely to be asked")
    numbered(doc, [
        "Is the data real? Sales, stock, lead times and fill are generated; the calendar, PIHPS prices and the "
        "published comparisons are not. Page 12 says so itself.",
        "Is 89.5% accuracy? No. It is two scorers agreeing on one snapshot, and all of the agreement comes from "
        "537 SKUs both of them considered safe.",
        "If SAP already exists, why this? SAP scores a 14-day stockout risk from tabular features; it does not read "
        "the event calendar and does not cap an order by shelf life. What it adds is 577 SKUs at expiry risk.",
        "What does it cost to run? One pass takes 57 seconds on one machine; the metered parts are the SAP calls "
        "and the model calls, and both ran here on limited quota.",
    ])

    h(doc, "Sources")
    lead(doc, "Proposal: Pasok, Agentic AI for FMCG Distributors (Agentic AI Hackathon 2026, Track: Intelligence "
              "Supply Chain). Deck: the submitted PDF, 13 pages, Team AIGO. Repository: data/orders/last_run.json, "
              "data/agents/decision_summary.json, data/sap/rpt_summary.json, data/sap/rationale_summary.json, "
              "src/agents/*.py, run_chain.sh, aws/README.md and aws/GATES.md.", size=8.6, colour=GREY)

    path = OUT / "Pasok_brief.docx"
    doc.save(str(path))
    print("wrote", path)


if __name__ == "__main__":
    main()
