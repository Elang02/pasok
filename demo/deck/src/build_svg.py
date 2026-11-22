"""Regenerate the Pasok demo deck in the ppt-master project.

Design: a ledger sheet, not a slide deck. One warm paper, one ink, a single
rust accent that appears at most twice a page, hairlines instead of cards,
numbers set in the serif and right-aligned like a book of accounts.
"""
from pathlib import Path

OUT = Path("/home/ubuntu/work/ppt-master/projects/pasok_demo_ppt169_20261027/svg_output")
OQ = "\u201c"
CQ = "\u201d"

BG = "#F7F3EA"
INK = "#1F1B16"
BODY = "#2A2622"
MUTED = "#6B6257"
RULE = "#D8CDBB"
ACCENT = "#B4551F"
DEEP = "#2F4858"

SANS = "'Segoe UI', Calibri, Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', serif"

W, H = 1280, 720
L, R = 96, 1184          # text column
TOP = 64                 # running rule
FOOT = 636               # footer rule


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attrs(size=24, fill=BODY, family=SANS, anchor=None, ls=None, style=None, weight=None):
    a = f' text-anchor="{anchor}"' if anchor else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    st = f' font-style="{style}"' if style else ""
    w = f' font-weight="{weight}"' if weight else ""
    return f'font-family="{family}" font-size="{size}"{w}{st}{a}{l} fill="{fill}"'


def text(x, y, s, size=24, fill=BODY, family=SANS, anchor=None, ls=None, style=None, weight=None):
    return f'    <text x="{x}" y="{y}" {_attrs(size, fill, family, anchor, ls, style, weight)}>{esc(s)}</text>'


def para(x, y, lines, size=24, lh=34, **kw):
    """One paragraph in one <text>: later lines are tspans, not sibling nodes."""
    attrs = _attrs(size=size, **kw)
    if len(lines) == 1:
        return f'    <text x="{x}" y="{y}" {attrs}>{esc(lines[0])}</text>'
    body = esc(lines[0]) + "".join(
        f'<tspan x="{x}" dy="{lh}">{esc(l)}</tspan>' for l in lines[1:])
    return f'    <text x="{x}" y="{y}" {attrs}>{body}</text>'


def rule(x1, y, x2, color=RULE, h=1):
    return f'    <rect x="{x1}" y="{y}" width="{x2 - x1}" height="{h}" fill="{color}"/>'


def tick(x, y, h=14, color=ACCENT, w=2):
    return f'    <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}"/>'


def ledger_rows(x_label, x_value, y0, rows, gap=44, label_size=24, value_size=28, value_family=SERIF):
    """Rows of label left, value right, hairline between (a ledger, not cards)."""
    out = []
    for i, (label, value) in enumerate(rows):
        y = y0 + i * gap
        out.append(text(x_label, y, label, size=label_size, fill=BODY))
        if value:
            out.append(text(x_value, y, value, size=value_size, fill=INK,
                            family=value_family, anchor="end"))
        if i < len(rows) - 1:
            out.append(rule(x_label, y + 16, x_value, color=RULE))
    return "\n".join(out)


def page(num, role, inner, bg_extra=""):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" data-pptx-page-role="{role}">
{bg_extra}  <rect id="page-bg" data-pptx-role="background" x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>
{inner}
</svg>
'''


def head(page_no, headline, foot_left, accent_rule=True):
    """Running head + headline + hairline. No eyebrow, no kicker."""
    parts = []
    parts.append(text(R, TOP, str(page_no), size=16, fill=MUTED, anchor="end"))
    parts.append(rule(L, TOP + 12, R, color=INK, h=2))
    y = 168
    for i, line in enumerate(headline):
        parts.append(text(L, y + i * 54, line, size=44, fill=INK, family=SERIF, ls="-0.5"))
    yr = y + (len(headline) - 1) * 54 + 40
    parts.append(rule(L, yr, R, color=RULE))
    if accent_rule:
        parts.append(rule(L, yr, L + 96, color=ACCENT, h=3))
    return "\n".join(parts), yr


def foot(pageno, footnote):
    return (f'  <g id="page-footnote" data-pptx-bounds="{L} 644 {R - L} 36">\n'
            f'{rule(L, 644, R)}\n'
            f'{text(L, 672, footnote, size=16, fill=MUTED)}\n'
            f'{text(R, 672, str(pageno), size=16, fill=MUTED, anchor="end")}\n'
            f'  </g>')


PAGES = {}

# ---------------------------------------------------------------- P01 cover
PAGES["P01_cover.svg"] = page(1, "cover", f'''  <g id="masthead" data-pptx-bounds="{L} 108 {R - L} 140">
{text(L, 196, "Pasok", size=96, fill=INK, family=SERIF, ls="-2")}
{rule(L, 224, R, color=INK, h=2)}
{text(R, 196, "DEMO DAY · TRACK A", size=16, fill=MUTED, anchor="end", ls="2.4")}
  </g>
  <g id="claim" data-pptx-bounds="{L} 300 680 200">
{para(L, 348, ["A reorder agent for FMCG distributors.",
              "It sizes the order, writes the reason,",
              "and holds the order when the numbers",
              "look wrong."], size=28, lh=40, fill=BODY)}
  </g>
  <g id="facts" data-pptx-bounds="860 300 324 240">
{text(860, 316, "SKUs on one desk", size=16, fill=MUTED)}
{text(860, 352, "600", size=32, fill=INK, family=SERIF)}
{text(860, 400, "principals, lead times measured", size=16, fill=MUTED)}
{text(860, 436, "12", size=32, fill=INK, family=SERIF)}
{text(860, 484, "orders in one pass", size=16, fill=MUTED)}
{text(860, 520, "480", size=32, fill=INK, family=SERIF)}
  </g>
  <g id="byline" data-pptx-bounds="{L} 548 {R - L} 92">
{rule(L, 552, R)}
{text(L, 592, "Vicentius Elang Krisnanto · Joshua Sahusilawane · Bintang Neera", size=24, fill=BODY)}
{text(L, 622, "Sistem Informasi, Unika Atma Jaya · 31 October 2026 · BINUS Alam Sutera", size=16, fill=MUTED)}
  </g>''')

# ---------------------------------------------------------------- P02 problem
inner, yr = head(2, ["One buyer reorders 600 SKUs", "against a calendar that moves"], "")
PAGES["P02_problem.svg"] = page(2, "content", inner + "\n" + f'''  <g id="claim-body" data-pptx-bounds="{L} 276 660 160">
{para(L, 318, ["69% of FMCG volume moves through general trade.",
              "Most stores reorder at a fixed point, set once.",
              "Every event drifts, so last year's plan lands in",
              "the wrong week."], size=24, lh=36)}
  </g>
  <g id="drift" data-pptx-bounds="792 276 392 160">
{text(792, 318, "9 of 12 suppliers", size=28, fill=INK, family=SERIF)}
{text(792, 344, "deliver below 95% fill, so the", size=16, fill=MUTED)}
{text(792, 364, "calendar slips as well as moves.", size=16, fill=MUTED)}
{text(792, 404, "480 orders", size=28, fill=ACCENT, family=SERIF)}
{text(792, 428, "is what one pass of this desk sends.", size=16, fill=MUTED)}
  </g>
  <g id="timeline" data-pptx-bounds="{L} 444 {R - L} 186">
{rule(L, 470, R)}
''' + "".join(
    (text(L + i * 136, 500, d, size=16, fill=BODY) + "\n" + tick(L + i * 136, 508, h=14) + "\n" +
     text(L + i * 136, 540, y, size=16, fill=MUTED))
    for i, (d, y) in enumerate([("5 Jun", "2019"), ("24 May", "2020"), ("13 May", "2021"), ("2 May", "2022"),
                                ("22 Apr", "2023"), ("10 Apr", "2024"), ("31 Mar", "2025"), ("20 Mar", "2026")])) + f'''
{para(L, 578, ["Eight years, eight dates, each one earlier.",
              "A reorder point set last year buys for the wrong week."], size=24, lh=34)}
  </g>''' + "\n" + foot(2, "Sources: general-trade share from the proposal; event dates from data/demand/event_calendar.csv."))

# ---------------------------------------------------------------- P03 variance
inner, yr = head(3, ["An unguarded agent over-orders,", "and the index shows it"], "")
PAGES["P03_variance.svg"] = page(3, "content", inner + "\n" + f'''  <g id="variance" data-pptx-bounds="{L} {yr + 40} 700 210">
{text(L, yr + 84, "no rules", size=24, fill=BODY)}
{rule(L + 200, yr + 68, L + 200 + 300, color=ACCENT, h=28)}
{text(L + 520, yr + 84, "2.68x", size=32, fill=INK, family=SERIF)}
{text(L, yr + 148, "three rules", size=24, fill=BODY)}
{rule(L + 200, yr + 132, L + 200 + 36, color=DEEP, h=28)}
{text(L + 520, yr + 148, "0.24x", size=32, fill=INK, family=SERIF)}
{rule(L, yr + 176, L + 620, color=RULE)}
{text(L, yr + 204, "order variance, 250 trading days", size=16, fill=MUTED)}
  </g>
  <g id="side" data-pptx-bounds="812 {yr + 40} 372 210">
{ledger_rows(812, R, yr + 84, [("fill", "98.93%"), ("stockout days", "5"), ("average stock", "2,187")], gap=44, label_size=16, value_size=24)}
{text(812, yr + 204, "units held, same 250 days", size=16, fill=MUTED)}
  </g>
  <g id="method" data-pptx-bounds="{L} 520 {R - L} 110">
{rule(L, 528, R)}
{para(L, 566, ["Same forecaster, same 250 days of the Bank Indonesia retail index.", "The only difference is the three rules on page 9."], size=24, lh=34)}
  </g>''' + "\n" + foot(3, "Artefact: simulation/results.json, 250 days, 30-day warmup. Guarded fill 98.68%, stockout days 6, average stock 274."))

# ---------------------------------------------------------------- P04 agents
inner, yr = head(4, ["Four agents run one pass,", "and the model never picks a quantity"], "")
PAGES["P04_agents.svg"] = page(4, "content", inner + "\n" + f'''  <g id="flow" data-pptx-bounds="{L} {yr + 40} {R - L} 200">
{rule(L, yr + 120, R, color=RULE, h=2)}
''' + "".join(
    (text(L + i * 272, yr + 78, n, size=16, fill=ACCENT) + "\n" +
     tick(L + i * 272, yr + 96, h=8, color=INK) + "\n" +
     text(L + i * 272, yr + 150, name, size=24, fill=INK) + "\n" +
     para(L + i * 272, yr + 182, desc, size=16, lh=22, fill=MUTED))
    for i, (n, name, desc) in enumerate([
        ("01", "Demand Agent", ["forecast, event ramp,", "anomaly flag"]),
        ("02", "Stock Position Agent", ["sellable units, days", "of cover, two flags"]),
        ("03", "Supplier Reliability", ["lead p50 and p90,", "fill rate, drift"]),
        ("04", "Decision Agent", ["action, quantity, reason,", "then send or hold"])])) + f'''
  </g>
  <g id="quote" data-pptx-bounds="{L} 516 {R - L} 84">
{rule(L, 520, R)}
{text(L, 568, "The model writes the reason, never the quantity.", size=32, fill=INK, family=SERIF)}
  </g>''' + "\n" + foot(4, "Quantity comes from arithmetic over measured inputs; the sentence a buyer reads comes from the model."))

# ---------------------------------------------------------------- P05 console
inner, yr = head(5, ["The console names the next event", "and the goods that spike"], "")
PAGES["P05_console.svg"] = page(5, "content", inner + "\n" + f'''  <g id="question" data-pptx-bounds="{L} {yr + 40} 700 120">
{text(L, yr + 86, OQ + "What needs more stock for a spike next month?" + CQ, size=28, fill=INK, family=SERIF, style="italic")}
{rule(L, yr + 104, L + 700, color=RULE)}
{text(L, yr + 132, "asked in the console, 26 October 2026", size=16, fill=MUTED)}
  </g>
  <g id="answer" data-pptx-bounds="812 {yr + 40} 372 160">
{text(812, yr + 84, "79", size=44, fill=ACCENT, family=SERIF)}
{text(812, yr + 118, "days to Christmas,", size=16, fill=MUTED)}
{text(812, yr + 138, "the next registered event", size=16, fill=MUTED)}
  </g>
  <g id="numbers" data-pptx-bounds="{L} 508 {R - L} 120">
{rule(L, 516, R)}
{para(L, 556, ["median SKU 1.60 times normal · one SKU passes 2.5, the strongest 2.63", "nothing inside one month, and the console says so"], size=24, lh=34)}
  </g>''' + "\n" + foot(5, "Four steps, 6.1 seconds, and every number in the answer checked against the records before it was printed."))

# ---------------------------------------------------------------- P06 one sku
inner, yr = head(6, ["One SKU, from eight days of cover", "to a scored order"], "")
PAGES["P06_one_sku.svg"] = page(6, "content", inner + "\n" + f'''  <g id="cover-line" data-pptx-bounds="{L} {yr + 40} {R - L} 120">
{text(L, yr + 78, "8.2 days of cover", size=28, fill=INK, family=SERIF)}
{text(L + 320, yr + 78, "14-day trigger", size=28, fill=INK, family=SERIF)}
{text(L + 640, yr + 78, "17-day target", size=28, fill=ACCENT, family=SERIF)}
{rule(L, yr + 96, R, color=INK, h=2)}
{text(L, yr + 124, "where it stood", size=16, fill=MUTED)}
{text(L + 320, yr + 124, "lead 7 + review 7", size=16, fill=MUTED)}
{text(L + 640, yr + 124, "lead 7 + review 7 + buffer 3", size=16, fill=MUTED)}
  </g>
  <g id="order" data-pptx-bounds="{L} 452 700 140">
{rule(L, 464, R, color=RULE)}
{text(L, 508, "2,092 units, IDR 15.9M", size=32, fill=INK, family=SERIF)}
{text(L, 536, "inside an IDR 95.1M credit line · delivery at p90 of 7 days, learned", size=16, fill=MUTED)}
{text(L, 556, "PO-0314, issued without a person", size=16, fill=MUTED)}
  </g>
  <g id="grade" data-pptx-bounds="880 452 304 140">
{text(880, 508, "97.70%", size=44, fill=INK, family=SERIF)}
{text(880, 542, "fill, 48 units short", size=16, fill=MUTED)}
{text(880, 562, "fed back into the next forecast", size=16, fill=MUTED)}
  </g>''' + "\n" + foot(6, "SKU0286, biscuits, principal P03. Trace: demo/one_pass.md."))

# ---------------------------------------------------------------- P07 forecast
inner, yr = head(7, ["The forecast learns what each SKU", "does around an event"], "")
PAGES["P07_forecast.svg"] = page(7, "content", inner + "\n" + f'''  <g id="wape" data-pptx-bounds="{L} {yr + 40} 620 210">
{text(L, yr + 84, "learned ramp", size=24, fill=BODY)}
{rule(L + 220, yr + 68, L + 220 + 260, color=ACCENT, h=28)}
{text(L + 500, yr + 84, "0.0775", size=32, fill=INK, family=SERIF)}
{text(L, yr + 148, "flat bump", size=24, fill=BODY)}
{rule(L + 220, yr + 132, L + 220 + 390, color=DEEP, h=28)}
{text(L + 500, yr + 148, "0.1161", size=32, fill=INK, family=SERIF)}
{rule(L, yr + 176, L + 500, color=RULE)}
{text(L, yr + 204, "WAPE, lower is better", size=16, fill=MUTED)}
  </g>
  <g id="novelty" data-pptx-bounds="812 {yr + 40} 372 210">
{ledger_rows(812, R, yr + 84, [("novel spikes caught", "120 of 120"), ("false alarms", "0.65 per 100 days")], gap=52, label_size=16, value_size=24)}
  </g>
  <g id="method" data-pptx-bounds="{L} 512 {R - L} 110">
{rule(L, 520, R)}
{para(L, 558, ["30,490 M5 series, 154 event windows, scored leave-one-occurrence-out.", "A spike with no registered event still gets flagged for a human to name."], size=24, lh=34)}
  </g>''' + "\n" + foot(7, "Artefacts: experiments/e2_results.json, data/demand/sku_ramps.csv."))

# ---------------------------------------------------------------- P08 lead
inner, yr = head(8, ["Lead time comes from goods receipts,", "not from a promise"], "")
PAGES["P08_lead.svg"] = page(8, "content", inner + "\n" + f'''  <g id="fill" data-pptx-bounds="{L} {yr + 40} 560 200">
{ledger_rows(L, L + 460, yr + 84, [("network fill", "90.32%"), ("P02, the slowest principal", "81.1%")], gap=56, label_size=24, value_size=28)}
  </g>
  <g id="evidence" data-pptx-bounds="700 {yr + 40} 484 200">
{ledger_rows(700, R, yr + 84, [("goods receipts behind the p90s", "1,956"), ("principals below 95% fill", "9 of 12")], gap=56, label_size=16, value_size=24)}
  </g>
  <g id="why" data-pptx-bounds="{L} 520 {R - L} 110">
{rule(L, 508, R)}
{para(L, 546, ["The Decision Agent plans against p90, so a slow supplier earns a longer cover target", "instead of a complaint, and the shelf waits for the truck."], size=24, lh=34)}
  </g>''' + "\n" + foot(8, "P02 is the slowest principal in this catalogue, and the one whose bread perished first. Artefact: data/agents/supplier_reliability.csv."))

# ---------------------------------------------------------------- P09 rules
inner, yr = head(9, ["Three rules guard the order stream"], "")
PAGES["P09_rules.svg"] = page(9, "content", inner + "\n" + f'''  <g id="rules" data-pptx-bounds="{L} {yr + 44} 720 240">
''' + "".join(
    (text(L, yr + 92 + i * 72, n, size=16, fill=ACCENT) + "\n" +
     text(L + 48, yr + 96 + i * 72, name, size=28, fill=INK, family=SERIF) + "\n" +
     text(L + 240, yr + 96 + i * 72, desc, size=24, fill=BODY) + "\n" +
     rule(L, yr + 116 + i * 72, L + 700, color=RULE))
    for i, (n, name, desc) in enumerate([
        ("1", "Smooth", "the forecast before it drives sizing"),
        ("2", "Damp", "against the last order, week to week"),
        ("3", "Cap", "so variance out stays near variance in")])) + f'''
  </g>
  <g id="formula" data-pptx-bounds="860 {yr + 44} 324 240">
{text(860, yr + 92, "cover = lead p90 + review + buffer", size=16, fill=MUTED)}
{text(860, yr + 118, "buffer = z · √(lead variance² + forecast error²)", size=16, fill=MUTED)}
{text(860, yr + 176, "1.33x → 0.36x", size=32, fill=INK, family=SERIF)}
{text(860, yr + 204, "replay, 104 days", size=16, fill=MUTED)}
  </g>
  <g id="honest" data-pptx-bounds="{L} 520 {R - L} 110">
{rule(L, 528, R)}
{para(L, 566, ["Replay: 1.33x to 0.36x. Cap touched 0 of 600 orders.", "All three are coded. On this snapshot none cut a unit, so the replay is the evidence."], size=24, lh=34)}
  </g>''' + "\n" + foot(9, "Source: src/agents/decision.py, blocks 433-464 and 516."))

# ---------------------------------------------------------------- P10 sap
inner, yr = head(10, ["SAP scores the catalogue", "and writes the reason"], "")
PAGES["P10_sap.svg"] = page(10, "content", inner + "\n" + f'''  <g id="sap" data-pptx-bounds="{L} 302 {R - L} 238">
''' + "".join(
    (text(L, 332 + i * 72, label, size=16, fill=MUTED, ls="1.6") + "\n" +
     text(L, 368 + i * 72, big, size=32, fill=INK, family=SERIF) + "\n" +
     text(L + 300, 368 + i * 72, note, size=24, fill=BODY) + "\n" +
     rule(L, 386 + i * 72, R, color=RULE))
    for i, (label, big, note) in enumerate([
        ("SAP-RPT-1.6", "600 SKUs", "scored in 10.73 seconds"),
        ("GPT-5.4", "40 of 40", "rationales, none from a template"),
        ("JOULE", "0.895", "agreement with the agent, queue inside the tool")])) + f'''
  </g>
  <g id="caveat" data-pptx-bounds="{L} 548 {R - L} 88">
{rule(L, 552, R)}
{para(L, 590, ["RPT flags 577 SKUs as expiry risk where we flag none.", "The definitions differ, and we say so rather than average them."], size=24, lh=34)}
  </g>''' + "\n" + foot(10, "Buyer approves inside Joule; artefacts: data/sap/rpt_summary.json, data/sap/rationale_summary.json."))

# ---------------------------------------------------------------- P11 lane
inner, yr = head(11, ["The AWS lane answers live"], "")
PAGES["P11_lane.svg"] = page(11, "content", inner + "\n" + f'''  <g id="lane" data-pptx-bounds="{L} {yr + 60} {R - L} 200">
{rule(L, yr + 120, L + 760, color=INK, h=2)}
''' + "".join(
    (tick(L + i * 380, yr + 112, h=16) + "\n" +
     text(L + i * 380, yr + 90, name, size=28, fill=INK, family=SERIF) + "\n" +
     text(L + i * 380, yr + 158, note, size=16, fill=MUTED))
    for i, (name, note) in enumerate([
        ("Lambda function URL", "four agents, one bundle"),
        ("Bedrock, Mantle endpoint", "the answering model"),
        ("SAP AI Core", "fallback and scoring")])) + f'''
  </g>
  <g id="blocker" data-pptx-bounds="{L} 500 {R - L} 130">
{rule(L, 508, R)}
{para(L, 546, ["AgentCore is written and blocked by a quota on this account.", "The application deploys and waits for the quota; until then Lambda hosts the lane."], size=24, lh=34)}
  </g>''' + "\n" + foot(11, "Evidence: aws/GATES.md Gate 2, agentcore/app/pasok_agent/main.py."))

# ---------------------------------------------------------------- P12 ledger
inner, yr = head(12, ["What one snapshot moved"], "")
PAGES["P12_ledger.svg"] = page(12, "content", inner + "\n" + f'''  <g id="split" data-pptx-bounds="{L} {yr + 40} {R - L} 190">
{text(L, yr + 76, "IDR 40.66 bn of orders, split by who sent them", size=24, fill=BODY)}
{rule(L, yr + 96, L + 740, color=ACCENT, h=28)}
{rule(L + 740, yr + 96, R, color=DEEP, h=28)}
{text(L, yr + 168, "auto-issued · IDR 30.27 bn", size=24, fill=INK, family=SERIF)}
{text(L + 520, yr + 168, "held · IDR 10.40 bn", size=24, fill=INK, family=SERIF)}
{text(L, yr + 196, "445 of 480 went out without a person", size=16, fill=MUTED)}
{text(L + 520, yr + 196, "35 waited: 15 over a credit line, 15 near expiry, 6 mid switch", size=16, fill=MUTED)}
  </g>
  <g id="redirect" data-pptx-bounds="{L} 470 700 110">
{rule(L, 478, R)}
{text(L, 520, "IDR 7.78 bn", size=32, fill=ACCENT, family=SERIF)}
{text(L, 548, "redirected instead of bought: 414 surplus SKUs moved to a depot that could sell them", size=16, fill=MUTED)}
  </g>
  <g id="queue" data-pptx-bounds="880 470 304 110">
{text(880, 498, "0 of 18,824", size=28, fill=INK, family=SERIF)}
{text(880, 524, "replay orders that hit the money gate", size=16, fill=MUTED)}
{text(880, 556, "fifteen did, this pass", size=16, fill=ACCENT)}
  </g>''' + "\n" + foot(12, "Run log, evening of 26 October; artefacts in data/orders/. The queue is real even when it is empty."))

# ---------------------------------------------------------------- P13 close
PAGES["P13_close.svg"] = page(13, "ending", f'''  <g id="masthead" data-pptx-bounds="{L} 110 {R - L} 120">
{rule(L, 116, R, color=INK, h=2)}
{text(L, 182, "A pilot on one distributor, for one month", size=44, fill=INK, family=SERIF, ls="-0.5")}
{rule(L, 212, R, color=RULE)}
  </g>
  <g id="commitments" data-pptx-bounds="{L} 260 780 280">
''' + "".join(
    (text(L, 306 + i * 66, n, size=16, fill=ACCENT) + "\n" +
     text(L + 44, 312 + i * 66, line, size=24, fill=BODY) + "\n" +
     rule(L, 330 + i * 66, L + 760, color=RULE))
    for i, (n, line) in enumerate([
        ("1", "Run it on their receipts, not our synthetic file."),
        ("2", "Connect their ERP in place of our order desk."),
        ("3", "Measure fill rate and stock value at month end."),
        ("4", "Ask us about any SKU and we will show the trace.")])) + f'''
  </g>
  <g id="sign" data-pptx-bounds="900 260 284 280">
{text(900, 306, "Pasok", size=44, fill=INK, family=SERIF)}
{text(900, 340, "Team Pasok", size=16, fill=MUTED)}
{text(900, 372, "github.com/Elangk1", size=24, fill=BODY)}
{text(900, 398, "(private; access on request)", size=16, fill=MUTED)}
{text(900, 444, "Sistem Informasi", size=16, fill=MUTED)}
{text(900, 466, "Unika Atma Jaya", size=16, fill=MUTED)}
{text(900, 500, "31 October 2026", size=16, fill=MUTED)}
  </g>''')

for name, svg in PAGES.items():
    (OUT / name).write_text(svg, encoding="utf-8")
print("wrote", len(PAGES), "pages to", OUT)
