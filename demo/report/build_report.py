"""Build the study report for Demo Day: DOCX, then PDF through LibreOffice.

Every number here is printed in the deck, in the talk script, or in the JSON under data/agents.
The appendix maps each one to its file so a reader can check a figure instead of trusting it.
"""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[2]
SHOTS = Path("/tmp/rep")
OUT = ROOT / "demo" / "report"
INK = RGBColor(0x1a, 0x1a, 0x1a)
GREY = RGBColor(0x55, 0x55, 0x55)


def body(doc, text, size=10.5, space_after=6, first_indent=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.28
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if first_indent:
        p.paragraph_format.first_line_indent = Inches(0.22)
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
    h.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    h.paragraph_format.space_after = Pt(6)
    return h


def lead(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.line_spacing = 1.2
    r = p.add_run(text)
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = GREY
    return p


def numbered(doc, items, size=10.5):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.24
        r = p.add_run(f"{i}.  ")
        r.font.size = Pt(size)
        r.bold = True
        r2 = p.add_run(item)
        r2.font.size = Pt(size)


def table(doc, rows, widths, header=True, size=9):
    width_pt = sum(widths)
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for ci, value in enumerate(row):
            cells[ci].width = Inches(widths[ci])
            para = cells[ci].paragraphs[0]
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.space_before = Pt(2)
            run = para.add_run(str(value))
            run.font.size = Pt(size)
            run.bold = header and ri == 0
    for ci, w in enumerate(widths):
        t.columns[ci].width = Inches(w)
        for cell in t.columns[ci].cells:
            cell.width = Inches(w)
    for row in t.rows:
        tr = row._tr
        trPr = tr.get_or_add_trPr()
        cant = trPr.makeelement(qn("w:cantSplit"), {})
        trPr.append(cant)
    if header:
        hdr = t.rows[0]._tr
        hp = hdr.get_or_add_trPr()
        hp.append(hp.makeelement(qn("w:tblHeader"), {}))
    return t


def figure(doc, name, caption, width=6.35):
    path = SHOTS / name
    doc.add_picture(str(path), width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(12)
    r = cap.add_run(caption)
    r.italic = True
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY


doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Inches(11.69), Inches(8.27)
for side in ("left_margin", "right_margin"):
    setattr(sec, side, Inches(1.0))
sec.top_margin, sec.bottom_margin = Inches(0.95), Inches(0.95)
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(10.5)

# ---------------------------------------------------------------- title page
t = doc.add_paragraph()
t.paragraph_format.space_before = Pt(90)
r = t.add_run("Pasok")
r.font.size = Pt(34)
r.bold = True
r.font.color.rgb = INK

sub = doc.add_paragraph()
r = sub.add_run("An agentic ordering loop for FMCG distributors")
r.font.size = Pt(15)
r.font.color.rgb = GREY

doc.add_paragraph()
prov = doc.add_paragraph()
r = prov.add_run(
    "Study report for Demo Day, 31 October 2026\n"
    "Team AIGO, BINUS Alam Sutera\n"
    "Code, data, and every number in this report: github.com/Elangk1/pasok"
)
r.font.size = Pt(10.5)
r.font.color.rgb = INK

doc.add_paragraph()
box = doc.add_paragraph()
box.paragraph_format.space_before = Pt(40)
r = box.add_run(
    "This report is what we read before practising. It explains what the loop does, why each "
    "number on screen is the number it is, and where a reader can check it. The last two sections "
    "are the run sheet for fifteen minutes and the answers to the questions we expect."
)
r.font.size = Pt(10.5)
r.italic = True
r.font.color.rgb = GREY

doc.add_page_break()

# ---------------------------------------------------------------- 1 summary
heading(doc, "1.  The short version")
lead(doc, "One paragraph, then the four numbers that carry the pitch.")

body(doc, "Pasok is an ordering loop for a distributor that sells six hundred products through one "
          "hundred and twenty outlets. Every morning at six it reads stock, open purchase orders and "
          "the event calendar, forecasts demand for each product, and places the orders a buyer would "
          "have placed, except it writes down its reason for every line. This morning it placed 323 "
          "orders worth IDR 17.41 bn and stopped to ask a person about none of them; inside the policy "
          "envelope it does not wait, outside it does.")
body(doc, "The four numbers we lead with are the four a jury can check in the repository: fill rate "
          "for the top class of products at 99.89 percent against a published retail figure of 92 "
          "percent, demand lost at 0.54 percent against 8.3 percent, days of inventory at 22 against "
          "56.7 at Indofood CBP, and expiry at 0.21 percent of cost against a published shrink figure "
          "of 2.70 percent. The fifth comparison is our own target and we missed it, which the last "
          "slide says out loud.")

table(doc, [
    ["Quantity", "Value", "Where it comes from"],
    ["Products, outlets, days of history", "600, 120, 1,396", "data/catalog/catalog.csv, data/demand/daily_sales.csv"],
    ["Rows of daily sales", "10,012,803", "data/demand/daily_sales.csv"],
    ["Orders this morning, value", "323, IDR 17.41 bn", "data/orders/last_run.json"],
    ["Orders a person had to decide", "0", "data/orders/last_run.json"],
    ["Lines that would need a person on a normal day", "1.3 percent", "data/sim/replay2026_v29/"],
    ["Round trip of the loop", "56.7 seconds", "data/orders/last_run.json"],
], widths=[2.75, 1.55, 2.6])

# ---------------------------------------------------------------- 2 problem
heading(doc, "2.  The problem we chose")
lead(doc, "A distributor in this size is not short of data. It is short of a decision that can be "
          "explained six weeks later.")

body(doc, "Six hundred products, twelve principals, one hundred and twenty outlets, and four rules "
          "that interact: a minimum order quantity per principal, a shelf life that must not exceed a "
          "share of the remaining life, a peak envelope that keeps a single order from swallowing the "
          "month, and a review cycle that decides how far ahead a decision is meant to hold. A "
          "spreadsheet handles each rule alone. It cannot show which rule bound a line, and that is "
          "the sentence a manager needs when a write-off lands or a shelf runs dry.")
body(doc, "The data we work with is a generated catalogue with a fixed seed, because no distributor "
          "will hand over three years of sales for a student competition. Prices, event dates, demand "
          "shapes, and the published comparisons are real and cited; the product-level history is "
          "simulated. Section 9 separates the two without hedging, and slide 12 of the deck does the "
          "same on one page.")

# ---------------------------------------------------------------- 3 loop
heading(doc, "3.  What runs every morning at six")
figure(doc, "n_orders_crop.png", "Figure 1. The console after the morning run: 323 orders, 323 placed without a "
                          "person, 0 waiting, IDR 17.41 bn of value placed, and the next run at six the "
                          "following morning.")

body(doc, "The loop is one process with four roles. A demand agent forecasts each product for the "
          "horizon the review cycle asks for. A policy agent turns the forecast into a quantity, then "
          "applies the four rules. An execution agent writes the order into SAP and reads the purchase "
          "order back. A reasoning agent writes one paragraph per order and one paragraph for the day, "
          "which is the text the console shows and the deck quotes.")
body(doc, "Two rules about the loop matter for the demo. First, it runs inside a policy envelope: "
          "minimum quantity, shelf-life cap, and peak envelope are gates; anything inside them is "
          "placed and explained, anything outside is escalated. Second, the loop is supervised, not "
          "autonomous. The pilot runs in draft mode, so orders are written and not sent, and a person "
          "signs the first working day. We say this on stage because a jury that hears only "
          "\"autonomous\" will spend the rest of the hour looking for the human.")
body(doc, "The mechanism behind \"placed without a person\" is worth stating plainly. The envelope is "
          "computed per product, from its own peak, its own cover days, and a tolerance of five "
          "percent. For the order in section 4 that ceiling is 10,763 units. The order is 417. Nothing "
          "in the loop had a reason to ask.")

# ---------------------------------------------------------------- 4 one order
heading(doc, "4.  One order, line by line")
lead(doc, "This is the page a technical jury will read first, so we rehearsed it until each clause "
          "matches a field in the file.")

figure(doc, "n_order_crop.png", "Figure 2. The page the loop writes for one order: what the product sells, what "
                          "the order covers, and the three quantities a reader can check.", width=6.35)

body(doc, "The order is 417 units. The gap is 407: demand over the coverage window minus the stock "
          "that will already be there when the truck arrives. The order exceeds the gap by 2.4 percent "
          "because the supplier fills 97.6 percent of what it is asked for, and asking for exactly the "
          "gap would leave a shortfall. That is the whole arithmetic, and it is written on the page.")
body(doc, "The number that confuses people is 44.8 days. It is not the stock in the warehouse. It is "
          "everything the distributor can already count on at the moment of decision: 1,743 units on "
          "hand, 5,762 in transit, and 6,667 already on a purchase order, which together cover 44.8 "
          "days at the rate the policy uses for cover. On-hand alone is 5.5 days, and that is the "
          "number to say if someone asks how tight the shelf is. Both are printed on the page, in that "
          "order, which is why the section reads as a reconciliation and not as a boast.")
body(doc, "The other three quantities on the page are the gates. The minimum order quantity is 120 "
          "units and the order clears it. The shelf-life cap allows 0.8 of the remaining life, and this "
          "product is inside it. The peak envelope is 10,763 units for the window, and 417 is far "
          "below it. None of the three bound this line, and the page says so by printing the ceiling "
          "next to the order.")

# ---------------------------------------------------------------- 5 demand
heading(doc, "5.  Where the demand number comes from")
lead(doc, "The forecast is the part a jury can break in one question, so we keep two answers ready: "
          "what it is, and what it cannot do.")

body(doc, "The model is a gradient-boosted regressor over the product's own history plus calendar "
          "features: day of week, month, the Indonesian event calendar with its moving dates, and the "
          "days around each event. Events are not a flat multiplier. Each event has a shape, taken from "
          "observed behaviour in the days before and after, and each product has a measured response.")
body(doc, "Two honest details. The event shapes were tested on 154 event windows from the M5 panel, "
          "the Walmart competition dataset, because it is the only public source with daily store-level "
          "sales around calendar events; those 154 windows are not Indonesian holidays. And the "
          "response is not uniform: 13 of 600 products move, 500 stay within ten percent of a normal "
          "day, and 87 rise about six percent. A jury that hears \"Christmas moves demand\" and then "
          "sees thirteen products will trust the rest of the page more, not less.")
body(doc, "The aggregate result we quote is that orders swing 1.25 times as hard as demand under the "
          "old routine and 0.32 times after the four rules, measured on a 104-day replay. That is the "
          "number on slide 3, and it comes from data/agents/decision_summary.json, not from a slide "
          "that was drawn by hand.")

# ---------------------------------------------------------------- 6 results
heading(doc, "6.  What the results say")
lead(doc, "Four of the five rows sit beside a published figure. The fifth is our own target and it "
          "did not hold.")

table(doc, [
    ["What we measure", "Ours", "Published", "Source"],
    ["Fill rate, A class", "99.89 percent", "92 percent retail shelf", "Corsten and Gruen with GMA"],
    ["Demand lost to stockouts", "0.54 percent", "8.3 percent out of stock at retail", "Corsten and Gruen with GMA"],
    ["Days of inventory", "22 days", "56.7 days", "Indofood CBP, JMKT 15(3), 2025"],
    ["Expiry, share of cost", "0.21 percent", "2.70 percent shrink", "National Supermarket Shrink Survey"],
    ["Lines needing a person", "1.3 percent", "under 10 percent, our target", "data/agents/targets.json"],
], widths=[1.9, 1.0, 1.55, 1.82])

body(doc, "The fifth row is the one we name on stage. Pushing cover for the top class of products to "
          "99.9 percent raised write-off from 0.19 to 0.21 percent of cost. Both numbers are small; the "
          "direction is the point, and a pilot would fix it by shortening the review horizon for the "
          "products that expire fastest rather than by loosening the fill target.")

figure(doc, "n_console_crop.png", "Figure 3. The console the jury will see: the run's facts on one line, then "
                                 "the products with the least cover, ranked, each row openable.", width=6.35)

body(doc, "The screen above is the one we open when a jury asks a hard question, because it carries "
          "its own evidence. The tightest product has 11.9 days of cover and the slowest supplier "
          "delivers in six, so nothing runs out before the next truck; the same line of facts reports "
          "323 orders, 100 percent placed without a person, and zero waiting. If someone doubts a "
          "number, we press the row and the console answers for that product alone.")

# ---------------------------------------------------------------- 7 suppliers
heading(doc, "7.  The supplier record underneath the forecast")
lead(doc, "The forecast decides how much to ask for. The supplier decides how much actually arrives, "
          "and the two are kept apart on purpose.")

figure(doc, "n_suppliers_crop.png", "Figure 4. Supplier reliability from the console: lead time, the ninetieth "
                             "percentile the policy uses, and the share of orders delivered.", width=6.35)

body(doc, "Twelve principals, an average lead time of 8.4 days, and a worst case of 14.3 days at P06, "
          "whose ninetieth percentile is 11. The policy uses the tail, not the average, because a "
          "shortfall at the tail is what empties a shelf. Fill rates across principals run from 82.9 "
          "percent at P06 to 98 at P01, and the order in section 4 carries the 97.6 percent of its own "
          "principal rather than a network average. That is a small design decision with a visible "
          "consequence: nine of twelve principals sit below a 95 percent fill rate, which the deck says "
          "in one line instead of hiding behind the network number.")

# ---------------------------------------------------------------- 8 transfers
heading(doc, "8.  Moving stock instead of buying it")
figure(doc, "n_transfers_crop.png", "Figure 5. Where the moved value lands: five city depots, largest first. "
                             "Every move leaves the central depot as a proposal, not a purchase.", width=6.35)

body(doc, "Before an order goes out, the loop checks whether another outlet is holding what this one "
          "is short of. This morning that produced 489 moves worth IDR 12.68 bn across five city "
          "depots, which is the cheapest stock in the system because it is already paid for. The "
          "transfer is a proposal, not an action: the receiving order is written for a person to "
          "approve, and the deck shows one so the jury can see the difference between a suggestion and "
          "a purchase.")

# ---------------------------------------------------------------- 9 limits
heading(doc, "9.  What this is not")
lead(doc, "Five sentences we say before a jury finds them, in this order.")

numbered(doc, [
    "The catalogue is generated with a fixed seed. Prices, event dates, demand shapes, and the "
    "published comparisons are real; the product-level sales history is simulated.",
    "The figures are a ceiling, not a forecast. A replay on generated data shows what the rules do "
    "when the world behaves as modelled; it does not promise a distributor the same four points.",
    "The event shapes come from a public panel of 154 windows, not from Indonesian holidays. The "
    "calendar dates are Indonesian, the shapes are borrowed, and the page says so.",
    "The loop is supervised. Orders are written in draft mode and a person signs the first working "
    "day; the pilot is how that person's judgement gets into the policy, line by line.",
    "One promise we set for ourselves did not hold: write-off rose as we pushed cover for the top "
    "class to 99.9 percent. We name it on the last slide rather than after the questions.",
])

# ---------------------------------------------------------------- 10 run sheet
heading(doc, "10.  The fifteen minutes")
lead(doc, "Thirteen sections, one per slide, timed from the script at 133 words a minute. The full "
          "text is demo/TALK_SCRIPT.md; this is the shape.")

table(doc, [
    ["Time", "Slide", "What happens", "Seconds"],
    ["0:00", "1", "Who we are, what the loop did this morning, the promise of one explained order", "55"],
    ["0:55", "2", "The calendar year, and why a flat multiplier cannot survive it", "70"],
    ["2:05", "3", "Swings: 1.25 before the rules, 0.32 after, on a 104-day replay", "70"],
    ["3:15", "4", "Four agents, one loop, and the three gates that decide what it may place", "70"],
    ["4:25", "5", "600 products, 13 move, 500 stay flat, measured on 154 event windows", "65"],
    ["5:30", "6", "One order: 407 gap, 97.6 percent fill, 417 units, caps printed", "75"],
    ["6:45", "7", "The page the loop writes for that order, reason included", "80"],
    ["8:05", "8", "Forecast quality and the supplier record: 82.9 percent at the worst principal", "65"],
    ["9:10", "9", "Where the numbers come from: generated, real, assumed, on one page", "55"],
    ["10:05", "10", "The SAP and AWS path that wrote this morning's orders", "65"],
    ["11:10", "11", "The pass at six, on the snapshot from the day before", "60"],
    ["12:10", "12", "Five results beside published figures", "65"],
    ["13:15", "13", "What we would do first in a pilot, and what we already know is weak", "35"],
], widths=[0.55, 0.5, 4.47, 0.75])

body(doc, "Three habits that keep the fifteen minutes from slipping. Say the number before the "
          "mechanism, because the mechanism is what eats a minute. When a slide is a screenshot, point "
          "at one field and read it, then stop; nothing is worse than narrating a screen nobody can "
          "read at the back of the room. And leave the last section short on purpose: if the clock is "
          "long, drop slide 10 then slide 3, which the script marks as its own escape route.")

# ---------------------------------------------------------------- 11 questions
heading(doc, "11.  Ten questions, and the short answer")
lead(doc, "Each answer is one breath. The evidence line points at the file if the jury wants proof.")

table(doc, [
    ["Question", "Answer", "Evidence"],
    ["Is the data real?", "Prices, event dates, demand shapes and comparisons are real and cited; the "
                          "product-level history is generated with a fixed seed.", "data/catalog, data/demand"],
    ["Why is fill only 90.6 percent?", "90.6 is the network figure across all classes; the top class, "
                                       "the one we quote, is 99.89 percent.", "data/agents/outcomes.json"],
    ["If it is autonomous, who is responsible?", "The person who signs the pilot day, and the file that "
                                                 "says which rule bound which line. Draft mode until then.",
     "web/orders.html, decisions.csv"],
    ["What breaks first?", "The shelf-life cap, because it is the rule that trades fill for write-off; "
                           "the last slide names it.", "data/agents/decisions.csv"],
    ["How do you know the forecast is better?", "Two forecasts, one flat bump and one learned shape, "
                                                "scored on the same replay: a third less lost demand.",
     "experiments/"],
    ["Why 417 and not 407?", "The supplier fills 97.6 percent of what it is asked for, so the order "
                             "carries the shortfall.", "one_pass.json"],
    ["What is 44.8 days?", "Shelf, truck, and open purchase orders at the current velocity. On-hand "
                           "alone is 5.5 days.", "one_pass.json"],
    ["Does it need SAP?", "It writes to SAP today and reads the purchase order back; the loop is the "
                          "same if the ERP changes.", "src/agents/order_executor.py"],
    ["What would you do with a real distributor?", "Run four weeks in draft, compare the buyer's orders "
                                                   "with ours, and let the differences become the policy.",
     ".planning/"],
    ["What is the cost of a false alarm?", "0.65 extra orders per hundred days in the replay, which is "
                                           "what the peak envelope is for.", "experiments/e2_results.json"],
], widths=[1.72, 2.9, 1.65], size=8.5)

# ---------------------------------------------------------------- appendix
heading(doc, "Appendix A.  Every number, and the file behind it")
lead(doc, "This is the table we keep open during practice. If a number is not here, it is not said on "
          "stage.")

table(doc, [
    ["Number", "What it means", "File"],
    ["323 orders, IDR 17.41 bn", "The run of 30 October", "data/orders/last_run.json"],
    ["56.7 seconds", "Runtime of the loop", "data/orders/last_run.json"],
    ["99.89 / 0.54 / 22 / 0.21", "Fill, lost demand, cover, expiry", "data/agents/outcomes.json"],
    ["1.3 percent", "Lines needing a person", "data/sim/replay2026_v29/"],
    ["1.25 to 0.32", "Order swing before and after the rules", "data/agents/decision_summary.json"],
    ["44.8 days, 5.5 days", "Cover incl. transit and PO, on-hand only", "data/agents/one_pass.json"],
    ["407, 417, 97.6 percent", "Gap, order, supplier fill", "data/agents/one_pass.json"],
    ["10,763 units", "Peak envelope for this order", "data/agents/one_pass.json"],
    ["154 windows", "Event shapes tested on the M5 panel", "experiments/"],
    ["0.65 per 100 days", "False alarms in the replay", "experiments/e2_results.json"],
    ["82.9 percent, 14.3 days", "Worst principal: fill, lead time", "data/agents/supplier_reliability.csv"],
    ["489 moves, IDR 12.68 bn", "Transfers instead of buying", "data/agents/transfers.json"],
    ["10,028 units", "Trimmed by the shelf-life cap", "data/agents/decisions.csv"],
], widths=[1.75, 2.2, 2.32], size=8)

heading(doc, "Appendix B.  Reproducing one morning")
lead(doc, "Six commands in the order the loop runs them; the README carries the same list.")

for line in """python src/agents/loop.py --snapshot 2026-10-28   reads stock, open orders, and the calendar.
python src/agents/decision.py --write-orders   forecasts, sizes, applies the three gates.
python src/agents/order_executor.py --sap --dry-run   writes to SAP and reads the order back.
python src/agents/reasoning.py --per-order   writes one paragraph per order and for the day.
python web/app.py --port 8090   serves the console the demo uses.
python tools/figures_gate.py   42 figures, then the deck and script gates.""".splitlines():
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(0.06)
    para.paragraph_format.space_after = Pt(1)
    para.paragraph_format.line_spacing = 1.0
    run = para.add_run(line)
    run.font.name = "Consolas"
    run.font.size = Pt(7.5)

doc.save(str(OUT / "Pasok_study_report.docx"))
print("wrote", OUT / "Pasok_study_report.docx")
