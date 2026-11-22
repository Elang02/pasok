from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

INK, GREY, RULE = RGBColor(0x1a,0x1a,0x1a), RGBColor(0x66,0x66,0x66), "D8D8D8"
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
sec.top_margin = Inches(0.6); sec.bottom_margin = Inches(0.6)
sec.left_margin = Inches(0.65); sec.right_margin = Inches(0.65)
st = doc.styles["Normal"]; st.font.name = "Helvetica"; st.font.size = Pt(9.4)
st.paragraph_format.space_after = Pt(3); st.paragraph_format.line_spacing = 1.1

def para(text, size=9.4, bold=False, italic=False, colour=INK, after=3, before=0):
    p = doc.add_paragraph(); r = p.add_run(text)
    r.font.size = Pt(size); r.bold = bold; r.italic = italic; r.font.color.rgb = colour
    p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(before)
    return p

def h(text, size=15, before=0, after=4):
    p = doc.add_paragraph(); r = p.add_run(text)
    r.font.size = Pt(size); r.bold = True; r.font.color.rgb = INK
    p.paragraph_format.space_before = Pt(before); p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.keep_with_next = True
    return p

def shade(cell, hexfill):
    tcPr = cell._tc.get_or_add_tcPr()
    el = OxmlElement("w:shd"); el.set(qn("w:val"), "clear"); el.set(qn("w:fill"), hexfill)
    tcPr.append(el)

def table(headers, rows, widths, size=8.8, head_fill="F2EFE9"):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout"); layout.set(qn("w:type"), "fixed"); tblPr.append(layout)
    for i, w in enumerate(widths):
        for cell in t.columns[i].cells: cell.width = Inches(w)
    for i, htext in enumerate(headers):
        c = t.rows[0].cells[i]; c.text = ""
        r = c.paragraphs[0].add_run(htext); r.bold = True; r.font.size = Pt(size)
        c.paragraphs[0].paragraph_format.space_after = Pt(1)
        shade(c, head_fill)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); trPr.append(th)
    for row in rows:
        tr = t.add_row()
        trPr = tr._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit"); trPr.append(cs)
        cells = tr.cells
        for i, val in enumerate(row):
            cells[i].text = ""
            p = cells[i].paragraphs[0]; r = p.add_run(str(val)); r.font.size = Pt(size)
            p.paragraph_format.space_after = Pt(1); p.paragraph_format.line_spacing = 1.0
    for i, w in enumerate(widths):
        for cell in t.columns[i].cells: cell.width = Inches(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

h("The talk, page by page", 20, after=2)
para("A jury can follow a talk only when each page answers the question the page before it left open. For every "
     "page this sheet gives what it has to settle, the sentence that settles it, and the question it hands on. "
     "Say the sentence, then the question, and the thirteen pages become one argument.", colour=GREY, after=8)

para("The order holds. It starts with the calendar that moves, goes through the rule that amplifies a wrong "
     "point, and arrives at a loop that re-derives the date every morning. From there it is one decision (6), "
     "the same decision as a record (7), the two inputs that can be wrong (8), the gates that keep it honest "
     "(9), the systems it touches (10), the money one morning moves (11), how much of it is real (12), and what "
     "it produces beside published figures (13). Reordering it now would break the only thing that already "
     "holds.", size=9.2, after=10)

rows = [
 ("1", "Cover: Pasok, Team AIGO",
  "A running system on a real catalogue, not a chatbot.",
  "\u201cEvery morning at six, Pasok answers one question: what do we reorder today, and why.\u201d",
  "\u201cIt starts with a date that nobody owns.\u201d"),
 ("2", "The calendar is the plan",
  "The input everyone pins down is the one that moves.",
  "\u201cA reorder point set once a year buys for the wrong week, every year.\u201d",
  "\u201cA fixed point is one way to be wrong. The deeper problem is what the rule does to orders.\u201d"),
 ("3", "Guardrails, sized on a public index",
  "An untouched rule magnifies what it is fed, and a guardrail cuts that without buying service with stock.",
  "\u201cLeft alone, orders swing 2.68 times as hard as demand. Three rules bring that to 0.24.\u201d",
  "\u201cSo what replaces the fixed point? A loop that re-derives the date every morning.\u201d"),
 ("4", "Four agents, one loop",
  "Four questions that can be answered apart, and a model that writes only prose.",
  "\u201cThe rules set the quantity. The model writes the reason, and only the reason.\u201d",
  "\u201cWe meet it the way the buyer does, with a question in words.\u201d"),
 ("5", "The nearest event, and what it moves",
  "The interface is the buyer's question, and every answer can be checked.",
  "\u201cThirteen of six hundred SKUs move. The rest stay within ten percent of a normal day, and every sentence carries a number you can open and check.\u201d",
  "\u201cThe event is one input. Here is one order, end to end.\u201d"),
 ("6", "One SKU, one order",
  "One order is arithmetic that can be redone by hand.",
  "\u201c417 units, because the gap at arrival is 407 at a 97.6 percent fill, and the rule escalates above 10,763.\u201d",
  "\u201cThe arithmetic is one thing. The record is another.\u201d"),
 ("7", "The same decision on screen",
  "A decision leaves a record: rule, recipient, reference.",
  "\u201cThe rule, the recipient and the order reference are on the record. Nothing is reconstructed afterwards.\u201d",
  "\u201cTwo of those inputs could be wrong: the forecast and the lead time.\u201d"),
 ("8", "A learned shape against a flat bump",
  "The two inputs are measured, including the bad one.",
  "\u201cThe learned shape misses a third less than a flat bump, and fill on arrival is 90.6 percent. That is not good. It is what the receipts say.\u201d",
  "\u201cGiven inputs like that, what keeps one order honest?\u201d"),
 ("9", "Three rules keep one order honest",
  "The gates are specific, they bind, and they cost a quarter point of fill.",
  "\u201cSeven SKUs were trimmed this morning, 10,028 units, and in all seven the binding limit was the shelf.\u201d",
  "\u201cThe rules are ours. The systems they talk to are not.\u201d"),
 ("10", "SAP scores, AWS runs",
  "It touches systems a distributor already runs, and the parts that are not live are named.",
  "\u201cSAP scores all six hundred in 10.7 seconds and flags 577 near expiry. The AgentCore lane is written and blocked on a quota, and we say so.\u201d",
  "\u201cThat chain ran this morning. Here is what it produced.\u201d"),
 ("11", "One snapshot in money",
  "One morning moves real money with no queue.",
  "\u201c323 orders, 17.41 billion rupiah, zero escalated, and one reason on every line.\u201d",
  "\u201cIf a judge asks how much of this is real, the next page answers that.\u201d"),
 ("12", "Where the numbers come from",
  "Simulated rows are named as simulated, and the results are a ceiling.",
  "\u201cThe sales are generated. The calendar, the prices and the outside numbers are not.\u201d",
  "\u201cAnd here is what that produces against numbers we did not write.\u201d"),
 ("13", "Five results, beside published figures",
  "Five operating metrics sit at or beyond published figures, the miss is named, and the ask is a pilot.",
  "\u201cFour of these five sit beside a published number. The fifth is our own ceiling, and the pilot is how we tune it.\u201d",
  "(Close: stop talking, invite the first question.)"),
]
table(["#", "Page", "What it settles", "Say this", "The question it leaves open"],
      rows, [0.28, 1.32, 1.85, 2.12, 1.4], size=8.2)

h("Four lines where the slide and your voice disagree", 13, before=6)
para("Four statements in the deck you submitted are contradicted by the data behind them. Editing the file "
     "tonight is riskier than saying the right number out loud. If a juror points at the screen, say the slide "
     "is one revision behind and give the corrected line.", colour=GREY, after=4)
table(["Page", "On the slide", "What the data says", "Say instead"],
      [["5", "\u201cThe other 587 stay flat\u201d", "they stay within ten percent of a normal day (filter is peak above 1.10)",
        "\u201cThe other 587 stay within ten percent.\u201d"],
       ["6", "\u201cthe shelf already covers 44.8 days\u201d", "44.8 is shelf plus in transit plus open orders; on the shelf alone it is 5.5 days",
        "\u201cWith stock on the road and on order, 44.8 days; on the shelf tonight, five and a half.\u201d"],
       ["9", "\u201c0 of 600\u201d and \u201c1.33 to 0.36\u201d", "7 of 600 trimmed, 10,028 units, all bound by the shelf cap; the replay is 1.25 to 0.32",
        "\u201cSeven of six hundred, bound by the shelf, and the replay goes 1.25 to 0.32.\u201d"],
       ["13", "\u201cDemand lost \u00b7 retail 92.0% out\u201d", "retail out-of-stock is 8.3 percent; 92.0 is the fill rate on the other side of the same coin",
        "\u201cRetail is out of stock 8.3 percent of the time.\u201d"]],
      [0.35, 1.85, 2.55, 2.2], size=8.2)

h("If the clock runs long", 13, before=6)
para("Drop page 12 first, because the sources line on page 13 still names where the numbers come from. Then "
     "drop page 4, because the four agents appear again on pages 6 to 9. Pages 3 and 13 stay: page 3 is the "
     "only page that puts a number on the problem, and page 13 is the only close.", size=9.2, after=4)
para("At 133 words a minute the script runs 13 minutes 50 seconds, leaving 70 seconds. If you lose more than "
     "that, cut page 12 (50 s) and page 4 (55 s) and you are back inside the slot.", size=9.2, colour=GREY)

doc.save("demo/report/Pasok_talk_flow.docx")
print("wrote demo/report/Pasok_talk_flow.docx")
