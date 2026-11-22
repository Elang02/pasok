"""Build the mechanism report: how the agents work and how the loop runs.

Same house style as the study report, one size smaller, with four diagrams drawn by
diagrams.py. Every claim about behaviour is taken from the module it names.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
FIG = Path(__file__).resolve().parent / "figures"
OUT = Path(__file__).resolve().parent
INK = RGBColor(0x1a, 0x1a, 0x1a)
GREY = RGBColor(0x55, 0x55, 0x55)


def body(doc, text, size=10.3, space_after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.28
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.color.rgb = INK
    return p


def heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for r in h.runs:
        r.font.color.rgb = INK
        r.font.name = "Calibri"
        r.font.size = Pt(15 if level == 1 else 11.5)
        r.bold = True
    h.paragraph_format.space_before = Pt(15 if level == 1 else 9)
    h.paragraph_format.space_after = Pt(5)
    return h


def lead(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(9)
    p.paragraph_format.line_spacing = 1.18
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(9.8)
    r.font.color.rgb = GREY
    return p


def numbered(doc, items, size=10.3):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.24
        r = p.add_run(f"{i}.  ")
        r.font.size = Pt(size)
        r.bold = True
        r2 = p.add_run(item)
        r2.font.size = Pt(size)


def table(doc, rows, widths, size=8.6):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, value in enumerate(row):
            cells[ci].width = Inches(widths[ci])
            para = cells[ci].paragraphs[0]
            para.paragraph_format.space_after = Pt(1.5)
            para.paragraph_format.space_before = Pt(1.5)
            para.paragraph_format.line_spacing = 1.0
            run = para.add_run(str(value))
            run.font.size = Pt(size)
            run.bold = ri == 0
    tblPr = t._tbl.tblPr
    tblW = tblPr.makeelement(qn("w:tblW"), {qn("w:type"): "dxa", qn("w:w"): str(int(sum(widths) * 1440))})
    tblPr.append(tblW)
    tblPr.append(tblPr.makeelement(qn("w:tblLayout"), {qn("w:type"): "fixed"}))
    for ci, w in enumerate(widths):
        t.columns[ci].width = Inches(w)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        trPr.append(trPr.makeelement(qn("w:cantSplit"), {}))
    hdr = t.rows[0]._tr.get_or_add_trPr()
    hdr.append(hdr.makeelement(qn("w:tblHeader"), {}))
    return t


def figure(doc, name, caption, width=6.27):
    doc.add_picture(str(FIG / name), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(11)
    r = cap.add_run(caption)
    r.italic = True
    r.font.size = Pt(8.4)
    r.font.color.rgb = GREY



doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Inches(11.69), Inches(8.27)
sec.left_margin = sec.right_margin = Inches(1.0)
sec.top_margin = sec.bottom_margin = Inches(0.9)
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(10.3)

# ------------------------------------------------------------------ cover
t = doc.add_paragraph()
t.paragraph_format.space_before = Pt(80)
r = t.add_run("How Pasok works")
r.font.size = Pt(32)
r.bold = True
r.font.color.rgb = INK
s = doc.add_paragraph()
r = s.add_run("Four agents, one loop, and the path of a single decision")
r.font.size = Pt(14)
r.font.color.rgb = GREY
doc.add_paragraph()
prov = doc.add_paragraph()
r = prov.add_run("Mechanism report for Demo Day, 31 October 2026\nTeam AIGO, BINUS Alam Sutera\n"
                 "Every behaviour described here is one function in the repository.")
r.font.size = Pt(10.3)
r.font.color.rgb = INK
doc.add_paragraph()
note = doc.add_paragraph()
note.paragraph_format.space_before = Pt(30)
r = note.add_run(
    "The study report explains what the system decided and how the numbers compare. This one "
    "explains the machinery: which program runs when, what each agent is allowed to write, how a "
    "forecast becomes a purchase order, and where the loop can be wrong.")
r.font.size = Pt(10.3)
r.italic = True
r.font.color.rgb = GREY
doc.add_page_break()

# ------------------------------------------------------------------ 1
heading(doc, "1.  The shape of the thing")
body(doc, "Pasok is one program chain that runs once a morning, plus a console that answers questions "
          "about what it did. There is no long-running agent deciding things in a loop all day. The "
          "chain starts at six, reads the files left by the day before, writes new files, and exits. "
          "The console reads the same files. That is the whole architecture, and most of the design "
          "choices below follow from it.")
body(doc, "Two consequences matter for anyone reading the code. First, a run is reproducible: the same "
          "snapshot in gives the same orders out, which is why a number on a slide can be checked by "
          "running one command. Second, nothing is held in memory between runs. If a step needs to know "
          "something, it reads a file; if it wants to say something, it writes one. The next agent "
          "cannot receive a message that later disappears.")
body(doc, "The chain is orchestrated by run_chain.sh, which stops on the first failure, and recorded by "
          "tools/record_run.py, which appends one row to data/orders/run_log.csv whether the chain "
          "succeeded or not. A failed morning is visible in the log instead of being absent from it.")

# ------------------------------------------------------------------ 2
heading(doc, "2.  The morning, step by step")
lead(doc, "Ten steps, in the order the shell script runs them. The table is the same list a reader can "
          "check against run_chain.sh.")



table(doc, [
    ["#", "Program", "What it does", "Writes"],
    ["1", "stock_position.py", "rebuilds on hand, in transit, and open purchase orders per SKU per day",
     "stock_daily.csv"],
    ["2", "supplier_reliability.py", "learns each principal's lead time, its ninetieth percentile, and the share it delivers",
     "supplier_reliability.csv"],
    ["3", "decision.py", "forecasts demand, sizes the order, applies the three guardrails",
     "decisions.csv"],
    ["4", "consolidation.py", "merges small orders for the same principal into one delivery week",
     "consolidation_summary.json"],
    ["5", "order_executor.py", "runs the gates and writes to SAP, or queues the line with a reason",
     "purchase_orders.csv"],
    ["6", "order_intake.py", "records what the supplier confirms, including partial deliveries",
     "intake_summary.json"],
    ["7", "notification.py", "writes the buyer note that goes with each exception", "notification_log.csv"],
    ["8", "redirect.py", "looks for stock in another outlet before buying more", "transfers.json"],
    ["9", "learn.py", "scores past forecasts week by week against what actually sold", "learn_summary.json"],
    ["10", "one_pass.py", "re-reads the whole run and writes the trace of one order", "one_pass.json"],
], widths=[0.32, 1.45, 2.35, 1.85])

body(doc, "The order is not arbitrary. Position has to exist before a decision can subtract it, the "
          "decision has to exist before consolidation can merge it, and the executor reads the "
          "consolidated file rather than the raw decisions. one_pass runs last because it documents "
          "the freshest artefacts, not the ones from a previous morning.")

# ------------------------------------------------------------------ 3
figure(doc, "d1_chain.png",
                  "Figure 1. The chain. Each box is one program; the file under a box is what that step writes and the next step reads.")

heading(doc, "3.  The four agents")
lead(doc, "The word agent is used loosely in the pitch, so it is worth being precise: each one is a "
          "program with a narrow permission, and the permission is a file.")



heading(doc, "The demand agent", 2)
body(doc, "It answers one question per product per day: how much will sell tomorrow, and over the window "
          "the policy asks about. The model is a gradient-boosted regressor over the product's own "
          "history plus calendar features. Events are not a multiplier on the whole catalogue. Each "
          "product carries a measured response and a shape, both stored in data/demand/sku_ramps.csv, "
          "and the forecast adds that shape only where the response is above 1.10.")
body(doc, "Its output is not a file other agents read directly; it is a column inside decisions.csv. "
          "That is deliberate. A forecast that no decision used is a number nobody can be held to.")

heading(doc, "The policy agent", 2)
body(doc, "This is decision.py, and it is the part worth reading line by line. It turns the forecast into "
          "a quantity in four moves, then guards it. The timing is time-phased rather than a fixed "
          "reorder point: demand_lead is what sells between now and the truck arriving, pos_at_arrival is "
          "what is left on the shelf then, and need_units is the gap between that and the demand over the "
          "coverage window. Coverage is lead p90 plus the review period plus a buffer, and class A adds a "
          "lead time on top because a missed sale there is expensive.")
body(doc, "Then three guardrails from the earlier experiment: forecast smoothing, order damping, and a "
          "variance cap. On a single snapshot they barely move, which is why decision_summary.json also "
          "replays the network order stream for 104 days and reports the swing before and after. The "
          "number on slide 3, 1.25 down to 0.32, comes from that replay, not from the snapshot.")

heading(doc, "The execution agent", 2)
body(doc, "order_executor.py is where a recommendation becomes an action. It walks every line, runs "
          "gate_reasons(), and splits the day into orders it issues itself and lines it hands to a "
          "person. The gate function is pure: it takes a row and returns reasons, so a synthetic row in a "
          "test can force each gate without the whole chain running.")

heading(doc, "The reasoning agent", 2)
body(doc, "For each order it writes a paragraph that names the drivers: what the product sells, what the "
          "order covers, which rule bound it. The sentences are generated from the fields of the row, not "
          "from a free model, so the paragraph cannot claim a cause the file does not contain. The same "
          "discipline applies to the console: the model writes the sentence, the numbers in it are checked "
          "against the table.")

# ------------------------------------------------------------------ 4
figure(doc, "d2_agents.png",
                  "Figure 2. The four roles, what each reads, and the one artefact each owns.")

heading(doc, "4.  Inside one line")
lead(doc, "This is the arithmetic a jury will ask about, on the product the deck shows: SKU0436, 333 units "
          "on its best day, 256 a day in this window, forty-two days of shelf life.")



body(doc, "The four quantities on the left are the whole sizing rule. Coverage is the lead time at its "
          "ninetieth percentile plus the review period plus a buffer: for this product, eight plus seven "
          "plus some days, which is why the window is thirty-one days. The gap is what remains after the "
          "stock that will already be there is subtracted, and the order divides that gap by the share "
          "the supplier actually delivers, 0.976. The result is 417 units, and the page prints the "
          "intermediate numbers so a reader can redo the subtraction rather than trust it.")
body(doc, "The gates are five, and each one writes a sentence rather than a flag:")
numbered(doc, [
    "Warehouse headroom. Space is the one resource every product shares, so an order that does not fit "
    "the remaining volume waits, whatever its value.",
    "The item's own peak envelope. This is the gate that replaces a rupiah ceiling. The envelope is the "
    "rate the item sells at its peak times the days it has to cover, with a five percent tolerance. "
    "A fast mover may legitimately order six hundred million rupiah on its own; a slow mover ordering "
    "forty million can still be beyond what it can sell, and that line waits for a person.",
    "The principal's minimum order. If the order is below the minimum and the shelf can wait, the line "
    "is deferred one cycle instead of being forced up to the minimum.",
    "A supplier switch. If another principal already supplies this category and delivers more of what "
    "is asked, the line is flagged for re-sourcing rather than silently reordered.",
    "An unexplained uplift. A jump with no registered event behind it is a demand shock until a person "
    "says otherwise.",
])
body(doc, "The rupiah value is printed on the page and deliberately is not a gate. The same money limit "
          "for every SKU says nothing about whether a particular item can sell what is being ordered, and "
          "the old rule escalated large but routine orders while letting small absurd ones through.")

# ------------------------------------------------------------------ 5
figure(doc, "d3_decision.png",
                  "Figure 3. From forecast to a decision. The left column is decision.py; the gates on the right are order_executor.py.")

heading(doc, "5.  When someone asks the console a question")
lead(doc, "The console is not a chatbot over a database. It is a lookup with a language model at one end "
          "and a checker at the other.")



body(doc, "The question is classified into one of a fixed set of shapes, because a fixed set can be "
          "tested. The rows for that shape are computed from the same artefacts the deck uses. Only then "
          "does a model see anything, and what it sees is the rows, not the database. After it writes, "
          "every number in the sentence is matched against the rows; a sentence with a number that is not "
          "there is rejected, and the console says it could not answer rather than printing a plausible "
          "figure. The trace under each answer names the model and the milliseconds, which is how a juror "
          "can tell a written answer from a computed one.")

# ------------------------------------------------------------------ 6
figure(doc, "d4_answer.png",
                  "Figure 4. The answer path. The model writes the sentence; the numbers in it come from rows the loop already computed.")

heading(doc, "6.  Where the loop can be wrong")
lead(doc, "Six failure modes we know about, in the order they are likely to bite.")

numbered(doc, [
    "The catalogue is generated. The rules behave as modelled on simulated demand; a real distributor's "
    "demand has shocks the generator does not produce.",
    "The lead time is learned from a short history. The ninetieth percentile of twelve deliveries is a "
    "noisy estimate, and the policy leans on it for every coverage window.",
    "The event shapes come from a public panel, not from Indonesian holidays. The dates are local, the "
    "shape is borrowed, and a real calendar would change the peak by an amount we cannot measure here.",
    "The shelf-life cap trades fill for write-off. Pushing cover for the top class to 99.9 percent "
    "raised write-off from 0.19 to 0.21 percent of cost; a pilot would tune that per category.",
    "Suppliers are assumed independent. If two principals share a factory, a single disruption removes "
    "two lead times at once and the buffer is too thin.",
    "The loop has no memory of a person's decision. When a buyer overrides a line, the override lives in "
    "the approval queue and not in the policy; learning from it is the next phase, not this one.",
])

# ------------------------------------------------------------------ 7
heading(doc, "7.  The record")
body(doc, "If a reader remembers one thing, it should be this table. Each artefact has one writer, and "
          "anything that quotes a number is reading one of them.")

table(doc, [
    ["Artefact", "Written by", "Read by", "What it holds"],
    ["stock_daily.csv", "stock_position.py", "decision.py, console", "on hand, in transit, open orders, per SKU per day"],
    ["supplier_reliability.csv", "supplier_reliability.py", "decision.py", "lead mean, p90, share delivered, per principal"],
    ["decisions.csv", "decision.py", "executor, console, deck", "forecast, position, gap, guarded order, rationale"],
    ["decision_summary.json", "decision.py", "deck slide 3", "swing before and after the guardrails, 104-day replay"],
    ["purchase_orders.csv", "order_executor.py", "intake, console", "every order with status and reason"],
    ["approval_queue.csv", "order_executor.py", "the buyer", "only the lines that stopped, one reason each"],
    ["transfers.json", "redirect.py", "console, deck", "stock moved between outlets instead of bought"],
    ["one_pass.json", "one_pass.py", "deck slide 7, console", "the trace of one order, field by field"],
    ["run_log.csv", "record_run.py", "console, log page", "one row per morning, success or failure"],
], widths=[1.6, 1.45, 1.5, 1.7])

body(doc, "Two smaller habits keep the record honest. Every JSON carries the snapshot date it was computed "
          "from, so a file from yesterday cannot be mistaken for this morning. And the gates that check "
          "the deck, the script, and the console read these files rather than a copy of the numbers, which "
          "is why a slide and the console cannot disagree in public.")

# ------------------------------------------------------------------ 8
heading(doc, "8.  Running it")
body(doc, "Six commands, in the order the chain runs them. The console is the last one because it only "
          "reads.")
for line in [
    "bash run_chain.sh",
    ".venv/bin/python tools/record_run.py --no-chain",
    ".venv/bin/python -m uvicorn app:app --port 8090",
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(line)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
body(doc, "The chain takes under a minute on the catalogue: 323 orders, 57.1 seconds on the morning of "
          "31 October. A run that fails leaves the previous files in place, which is why record_run.py "
          "reads the artefacts rather than assuming the chain succeeded.")

doc.save(str(OUT / "Pasok_mechanism_report.docx"))
print("wrote", OUT / "Pasok_mechanism_report.docx")
