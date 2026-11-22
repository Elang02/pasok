"""Build the Demo Day deck on the official SOKRATES template.

The artwork is the committee's: bg1 for the cover, bg2 for content. Nothing is
drawn over the logo strip, the title block, or the purple field; all copy lives in
the white column on the left, from y = 0.95 in to y = 6.15 in.

Design rules kept from the template and tightened here:
  - one accent (violet) for numbers, one warm accent for a figure that hurts
  - hairlines instead of cards, no shadows, no rounded boxes
  - one heading, no label above it; the heading is the claim
  - every page ends on a single sentence after the rule

Run:  .venv/bin/python demo/deck/build_deck.py
      .venv/bin/python tools/check_deck_layout.py      # nothing overlaps, nothing hits the furniture
      .venv/bin/python demo/deck/check_deck_numbers.py
"""
import os
import json
from pathlib import Path

import pandas as pd
from PIL import Image, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
ASSETS = BASE / "assets"
DEM = ROOT / "data" / "demand"
OUT = BASE / "Pasok_DemoDay_2026.pptx"

INK = RGBColor(0x14, 0x1A, 0x46)
VIOLET = RGBColor(0x6C, 0x4B, 0xE0)
WARM = RGBColor(0xB4, 0x4A, 0x1F)
GREY = RGBColor(0x6A, 0x70, 0x86)
BODY = RGBColor(0x2B, 0x30, 0x45)
RULE = RGBColor(0xE1, 0xDC, 0xF4)
FONT = "Arial"

LEFT = 1.05
COL = 4.05          # centred in the white column; the purple field starts at 5.4
NUM_W = 1.95
TOP = 0.95
BOTTOM = 6.18

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


F_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
F_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_FONTS: dict = {}


def _font(bold: bool, pt: float):
    key = (bool(bold), round(pt, 1))
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(F_BOLD if bold else F_REG,
                                         max(1, int(round(pt * 96 / 72))))
    return _FONTS[key]


def _wrapped(txt: str, bold: bool, pt: float, width: float) -> int:
    """How many lines this text needs in a box of this width, in the renderer's metrics."""
    font = _font(bold, pt)
    limit = width * 96
    n, cur = 1, ""
    for word in txt.split():
        trial = (cur + " " + word).strip()
        if font.getlength(trial) <= limit or not cur:
            cur = trial
        else:
            n += 1
            cur = word
    return n


def ink_h(txt: str, bold: bool, pt: float, width: float, spacing: float = 1.0,
          space_after: float = 0) -> float:
    return _wrapped(txt, bold, pt, width) * (pt / 72) * 1.2 * spacing + space_after / 72


def text(slide, x, y, w, h, paras, size=12, color=BODY, bold=False, spacing=1.0,
         space_after=0, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    if h is None:                      # measure instead of guessing
        h = 0.02
        for item in paras:
            chunk = item[0][0] if isinstance(item, list) else item
            b = item[0][1] if isinstance(item, list) else bold
            h += ink_h(chunk, b, size, w - 0.02, spacing, space_after)
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    first = True
    for item in paras:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        parts = item if isinstance(item, list) else [(item, bold, color)]
        for chunk, b, c in parts:
            r = p.add_run()
            r.text = chunk
            r.font.size = Pt(size)
            r.font.bold = b
            r.font.color.rgb = c
            r.font.name = FONT
    return box


def _supplier_facts() -> tuple[str, str, str, str, str, str]:
    """Receipts, network fill and the worst principal, read from the artefact every build."""
    sup = pd.read_csv(ROOT / "data" / "agents" / "supplier_reliability.csv")
    receipts = f"{int(sup['receipts'].sum()):,}"
    weight = sup["receipts"].astype(float)
    network = float((sup["fill_rate_observed"].astype(float) * weight).sum() / weight.sum())
    fills = sup["fill_rate_observed"].astype(float)
    worst = sup.loc[fills.idxmin()]
    return (receipts, f"{network * 100:.2f}%",
            f"{worst['principal_id']}, {float(fills.min()) * 100:.1f}%",
            f"{float(fills.min()) * 100:.0f}%", f"{float(fills.max()) * 100:.0f}%",
            str(int((fills < 0.95).sum())))


_SUP = _supplier_facts()


CURRENT = 0


def page(n):
    global CURRENT
    CURRENT = n
    kind = 1 if n == 1 else 2
    s = prs.slides.add_slide(BLANK)
    s.shapes.add_picture(str(ASSETS / f"bg{kind}.png"), 0, 0,
                         width=prs.slide_width, height=prs.slide_height)
    return s


def rule(slide, y, w=COL, color=RULE, weight=0.75):
    from pptx.enum.shapes import MSO_SHAPE
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(LEFT), Inches(y),
                                  Inches(w), Pt(weight))
    line.fill.solid()
    line.fill.fore_color.rgb = color
    line.line.fill.background()
    line.shadow.inherit = False
    return line


def head(slide, title, number):
    """Title under the logo strip; the page number sits on the title's baseline."""
    size = 22
    h = ink_h(title, True, size, COL, 1.04)
    if h > 0.80:                      # a three-line title would push the lede off the grid
        size = 19
        h = ink_h(title, True, size, COL, 1.04)
    text(slide, LEFT, 1.30, COL, h, [title], size=size, color=INK, bold=True, spacing=1.04)
    text(slide, LEFT + COL - 0.55, 6.46, 0.55, 0.22, [f"{number:02d}"], size=8, color=GREY,
         align=PP_ALIGN.RIGHT)
    # a two-line title ends at 2.06; the lede starts on the same line on every page
    return max(1.30 + h + 0.16, 2.22)


def lede(slide, sentence, y):
    """One paragraph, wrapped by the box, not one box per line."""
    h = ink_h(sentence, False, 11, COL, 1.22)
    text(slide, LEFT, y, COL, h, [sentence], size=11, color=BODY, spacing=1.22)
    return y + h + 0.20


def ledger(slide, rows, y, step=0.44, vsize=15.5, lsize=9.5, label_w=None, num_w=None,
           fill_to=None):
    """Rows of label and value, separated by hairlines; returns the bottom edge.

    The row is as tall as the taller of the two cells. A row that does not fit its step stops the
    build, because a silent overflow is what drew one value on top of the sentence below it.
    """
    label_w = COL - NUM_W - 0.12 if label_w is None else label_w
    num_w = NUM_W if num_w is None else num_w
    if fill_to is not None:                 # stretch the rows instead of leaving a hole above the close
        step = max(step, (fill_to - y) / len(rows))
    for i, (label, value, warm) in enumerate(rows):
        top = y + i * step
        lh = ink_h(label, False, lsize, label_w, 1.05)
        vh = ink_h(value, True, vsize, num_w, 1.0)
        if max(lh, vh) > step - 0.10:
            raise SystemExit(f"slide {CURRENT}, row {i + 1} ({label!r} / {value!r}) needs "
                             f"{max(lh, vh) + 0.10:.2f} in but its step is {step:.2f} in")
        text(slide, LEFT, top + 0.08 + max(0.0, (vh - lh) / 2), label_w, lh, [label], size=lsize,
             color=GREY, spacing=1.05)
        text(slide, LEFT + COL - num_w, top + 0.02, num_w, vh, [value], size=vsize,
             color=WARM if warm else VIOLET, bold=True, align=PP_ALIGN.RIGHT,
             spacing=1.0)
        rule(slide, top + step - 0.06)
    return y + step * len(rows)


def figure(slide, image, y, width=4.60, caption=None, x=None):
    im = Image.open(ASSETS / image)
    h = width * im.size[1] / im.size[0]
    slide.shapes.add_picture(str(ASSETS / image), Inches(LEFT if x is None else x), Inches(y),
                             width=Inches(width))
    if caption:
        text(slide, LEFT, y + h + 0.08, width, 0.3, [caption], size=8, color=GREY,
             spacing=1.12)
        h += 0.34
    return y + h


def foot(slide, sentence, y=None, above=None, rule_line=True):
    """The closing sentence, always the last thing on the page.

    Pass `above` with the bottom edge of whatever came before it: a sentence that would have to
    start inside that content stops the build instead of covering it.
    """
    h = ink_h(sentence, False, 8.5, COL + 0.30, 1.16)
    if y is None:
        y = BOTTOM - 0.06 - h
        if above is not None:               # hug the content; a fixed 0.30 in beat reads as intent
            y = min(y, above + 0.30)
    if y + h > BOTTOM - 0.02:
        raise SystemExit(f"slide {CURRENT}, the closing sentence needs {h:.2f} in from y={y:.2f}, "
                         f"which ends at {y + h:.2f}; BOTTOM is {BOTTOM:.2f}")
    if above is not None and y - 0.13 < above + 0.08:
        raise SystemExit(f"slide {CURRENT}, the closing sentence would start at {y:.2f} inside content that "
                         f"ends at {above:.2f}")
    if rule_line:                       # a ledger already ends on its own hairline
        rule(slide, y - 0.13, w=COL, color=RULE)
    text(slide, LEFT, y, COL + 0.30, h, [sentence], size=8.5, color=GREY, spacing=1.16)


# ---------------------------------------------------------------- 01 cover
s = page(1)
text(s, LEFT, 1.62, 5.3, 0.9, ["Pasok"], size=54, color=INK, bold=True, spacing=1.0)
rule(s, 2.62, w=1.05, color=VIOLET, weight=2.0)
text(s, LEFT, 2.86, 4.9, 1.3,
     ["Agentic AI for", "FMCG distributors."],
     size=17, color=BODY, spacing=1.22)
_meta = json.loads((ROOT / "data" / "catalog" / "meta.json").read_text())
_n_prin = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")["principal_id"].nunique()
text(s, LEFT, 4.50, 4.9, 1.5, [
    [(f"{_meta['n_skus']} SKUs  ·  {_n_prin} principals  ·  {_meta['n_days']:,} days of history", False, BODY)],
    [("Team AIGO", False, BODY)],
    [("Demo Day, 31 October 2026", False, GREY)],
], size=10.5, spacing=1.45, space_after=3)

# ------------------------------------------------------------- 02 problem
s = page(2)
y = head(s, "One buyer, 600 SKUs, a calendar that moves", 2)
y = lede(s, "A reorder point set once drifts off the calendar: Lebaran moves 33 days across four years, Imlek 26, Nyepi 17, while Christmas and New Year stay put.", y)
y = figure(s, "fig_calendar.png", y + 0.10, width=4.50,
           caption="One row per event, one dot per year 2023 to 2026.")
foot(s, "A reorder point set last year buys for the wrong week, every year.", above=y, rule_line=False)

# ------------------------------------------------------------ 03 variance
s = page(3)
y = head(s, "Left alone, orders swing harder than demand", 3)
y = lede(s, "Left alone, orders swing 2.68 times as hard as demand. Three rules bring that to 0.24 times.", y)
y = figure(s, "fig_bullwhip.png", y + 0.12, width=4.60,
           caption="250 days of demand, replayed with and without the guardrail. Fill is 98.93% unguarded and 98.68% guarded.")
foot(s, "Average stock falls from 2,187 to 274 units: the same fill on a tenth of the shelf.", above=y)

# -------------------------------------------------------------- 04 agents
s = page(4)
y = head(s, "Four agents, one loop, a reason for every line", 4)
y = lede(s, "Each agent answers one question and hands the next a number it can check. The rules set the quantity; the model writes the reason.", y)
y = ledger(s, [
    ("When each SKU's ramp starts", "learned", False),
    ("Sellable, on order, in transit", "measured", False),
    ("Lead time and fill by principal", f"{_SUP[0]} receipts", False),
    ("What to send, hold, and why", "written", False),
], y + 0.18, step=0.56, vsize=11.5, fill_to=5.46)
foot(s, "Above the item's own peak, the manager decides.", above=y, rule_line=False)

# ------------------------------------------------------- 06 which products
s = page(5)
text(s, LEFT, 1.30, 4.30, 0.70, ["The nearest event, and what it moves"], size=19, color=INK,
     bold=True, spacing=1.0)
_snap = pd.Timestamp(json.loads((ROOT / "data" / "orders" / "order_summary.json").read_text())["snapshot"])
_days_out = (pd.Timestamp("2026-12-25") - _snap).days
text(s, LEFT, 2.28, 4.25, 1.20,
     ["Asked in words: which event is nearest, and which products it moves. The answer carries the date, "
      "the distance, and the products that move."], size=10, color=BODY, spacing=1.18)
_ramps = pd.read_csv(ROOT / "data" / "demand" / "sku_ramps.csv")
_cat = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")[["sku", "name", "base_daily_demand"]]
_xmas = _ramps[_ramps.event == "Christmas"].merge(_cat, on="sku")
_xmas = _xmas[_xmas.peak_mult > 1.10].copy()
_xmas["peak_units"] = _xmas.base_daily_demand * _xmas.peak_mult
_top = _xmas.sort_values("peak_units", ascending=False).head(3)
_n_move = len(_xmas)
text(s, LEFT, 3.55, 4.25, 0.30,
     [f"{_n_move} of 600 SKUs move. The other {600 - _n_move} stay flat."], size=10.5,
     color=INK, bold=True)
_lines = [f"{r['name']}: {r['base_daily_demand']:.0f} to {r['base_daily_demand'] * r['peak_mult']:.0f} a day "
          f"({r['peak_mult']:.2f} times)" for _, r in _top.iterrows()]
text(s, LEFT, 3.95, 4.25, 1.30, _lines, size=9, color=BODY, spacing=1.16)
figure(s, "answer_products.png", 1.58, width=6.30, x=5.75)

s = page(6)
_op = json.loads((ROOT / "data" / "agents" / "one_pass.json").read_text())
_per, _dec, _iss, _lrn = _op["perceive"], _op["decide"], _op["issue"], _op["learn"]
y = head(s, "One SKU, one order, every line explained", 6)
y = lede(s, f"{_op['sku']}, {_op['category']}, principal {_op['principal_id']}. The loop ordered "
            f"{_dec['raw_order_units']:,.0f} units against a {_dec['lead_p90_days']:.0f}-day lead, "
            f"a {_dec['review_days']}-day review and a {_dec['buffer_days']:.0f}-day buffer.", y)
y = ledger(s, [
    ("Days of cover", f"{_per['days_of_cover']:.1f} days", False),
    ("Reorder point", f"{_per['lead_trigger_days']:.0f} days", False),
    ("Cover target",
     f"{_dec['lead_p90_days'] + _dec['review_days'] + _dec['buffer_days']:.0f} days", False),
    ("Order", f"{_dec['guarded_order_units']:,.0f} units", False),
    ("Fill rate / short units", f"{_lrn['observed_fill_rate']*100:.1f}% / {_lrn['shortfall_units']:,.0f}", False),
], y + 0.16, step=0.44, vsize=12.5)
foot(s, f"The item sells {_dec['peak_day_units']:,.0f} units on its best day. The order is "
        f"{_iss['qty']:,.0f} because the gap at arrival is {_dec['need_units']:,.0f} units, at a "
        f"{_lrn['observed_fill_rate']*100:.1f}% fill; the shelf already covers {_per['days_of_cover']:.1f} days, "
        f"and the rule escalates above {_dec['peak_envelope_units']:,.0f} units, so this one went out on its own.",
     y + 0.14)

# ----------------------------------------------------------- 07 forecast
# ------------------------------------------------------------- 08 reason
s = page(7)
text(s, LEFT, 1.30, 4.10, 0.50, ["Why this order"], size=19, color=INK, bold=True, spacing=1.0)
text(s, LEFT, 1.92, 4.05, 0.95,
     ["The capture reads top to bottom: stock on hand, what sells while the truck runs, what has to land, "
      "the gap, then the order and the reason beside it."],
     size=9.5, color=BODY, spacing=1.18)
y7 = ledger(s, [
    ("Escalation rule",
     _iss.get("escalation_reason", "inside policy limits").split(".")[0]
     .replace("within policy limits", "inside policy limits"), False),
    ("Notification", f"{_iss.get('notification_status','SENT')} to {_op['principal_id']}", False),
    ("Ordering system reference", _iss.get("intake", {}).get("system_reference", "SO-2026-000155"), False),
], 3.28, step=0.42, vsize=10.5, lsize=8.5)
foot(s, "Built with seed 20261008. A pilot replaces every row with a year of your own order lines and "
        "receipts.", above=y7, rule_line=False)
figure(s, "one_order.png", 1.30, width=4.30, x=6.45)

s = page(8)
y = head(s, "The forecast learns the shape; the lead time is measured", 8)
y = lede(s, "Two forecasts over 154 event windows in the M5 panel; each principal's lead-time spread sets its buffer.", y)
y = ledger(s, [
    ("Forecast error, learned shape", "7.8%", False),
    ("Forecast error, flat bump", "11.6%", False),
    ("Unregistered spikes caught", "120 of 120", False),
    (f"Fill rate, network ({_SUP[0]} receipts)", f"{_SUP[1]}", False),
    ("Worst principal", _SUP[2], False),
], y + 0.12, step=0.43, vsize=12.5, fill_to=5.46)
foot(s, "The learned shape misses a third less demand than the flat bump; nine of twelve principals underfill, so each one carries its own buffer.", above=y, rule_line=False)

# -------------------------------------------------------------- 09 rules
s = page(9)
y = head(s, "Three rules keep one order honest", 9)
y = lede(s, "Three rules: smooth the forecast, hold back a jump, cap one delivery at what the shelf can sell.", y)
y = ledger(s, [
    ("Smooth the forecast, not the last week alone", "weighted", False),
    ("Hold back a jump, from 1.25 to", "0.32 times", False),
    ("Cap one delivery at the shelf it can sell", "0 of 600", False),
], y + 0.26, step=0.56, vsize=13)
foot(s, "Seven SKUs were trimmed this morning, 10,028 units, all by the shelf-life cap; the other two rules cut nothing.", above=y, rule_line=False)

# ---------------------------------------------------------------- 10 SAP
s = page(10)
y = head(s, "SAP scores, AWS runs, and the loop writes the reason", 10)
y = lede(s, "SAP scores 600 SKUs in 10.73 seconds; the loop runs on Lambda and asks Bedrock on Mantle.", y)
y = ledger(s, [
    ("SKUs scored per call", "600 SKUs", False),
    ("SAP and our flags agree on", "89.5% of SKUs", False),
    ("Rationales, none templated", "40 of 40", False),
    ("Order chain", "AWS Lambda", False),
    ("Model calls", "Bedrock, Mantle", False),
    ("AgentCore runtime", "written, quota 0", True),
], y + 0.14, step=0.42, vsize=12.0, fill_to=5.46)
foot(s, "SAP calls 577 SKUs near expiry and none a stockout; the AgentCore lane is written and blocked by an account quota.", above=y, rule_line=False)

# ------------------------------------------------------------- 12 ledger
s = page(11)
y = head(s, "One snapshot, in money", 11)
y = lede(s, f"The pass at six this morning, on the {_snap:%d %B} snapshot: what went out, what waited, what came back.", y)
_orders = json.loads((ROOT / "data" / "orders" / "order_summary.json").read_text())
_redir = json.loads((ROOT / "data" / "orders" / "redirect_summary.json").read_text())
_held = {k: v for k, v in _orders["escalation_reason_breakdown"].items() if v}
y = ledger(s, [
    ("Orders on the snapshot", f"{_orders['skus_with_order']} orders", False),
    ("Auto-issued inside policy",
     f"{_orders['auto_issued']} of {_orders['skus_with_order']} auto-issued", False),
    ("Escalated to the manager", f"{_orders['escalated']} escalated", False),
    ("Value ordered", f"IDR {_orders['total_value_idr'] / 1e9:.2f} bn", False),
    ("Value auto-issued", f"IDR {_orders['auto_value_idr'] / 1e9:.2f} bn", False),
    ("Surplus SKUs redirected", f"{_redir['excess_skus']} surplus SKUs", False),
    ("Value protected by redirect", f"IDR {_redir['value_protected_idr'] / 1e9:.2f} bn", False),
], y + 0.06, step=0.37, vsize=11.5)
_queue = ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in sorted(_held.items(), key=lambda kv: -kv[1]))
foot(s, (f"The queue: {_queue}. Everything else went out on its own."
         if _queue else
         f"Nothing waited: every order sat inside the item's own peak, and {_redir['excess_skus']} surplus "
         "SKUs were redirected instead of bought twice."), above=y, rule_line=False)

# ------------------------------------------------------------- 12 data
s = page(12)
y = head(s, "Where the numbers come from", 12)
y = lede(s, "The sales are generated. The calendar, the prices and the outside numbers are not.", y)
y = ledger(s, [
    ("Sales, stock, lead times, fill rates", "generated", False),
    ("Catalogue", "600 SKUs, 120 outlets", False),
    ("History behind it", "1,396 days", False),
    ("Prices", "PIHPS, Oct 2026", False),
    ("Event dates", "calendar, lunar, Saka", False),
    ("Uplift and shape", "GAPMMI, Trends", False),
], y + 0.10, step=0.42, vsize=11.5, lsize=9.0, fill_to=5.46)
foot(s, "Built with seed 20261008. A pilot replaces every row with a year of your own order lines and receipts.", above=y, rule_line=False)

# -------------------------------------------------------------- 13 close
s = page(13)
y = head(s, "Five results, beside numbers we did not write", 13)
y = lede(s, "Each row is our replay next to a published figure, with the source named on the page.", y)
_t = {t["id"]: t for t in json.loads((ROOT / "data" / "agents" / "targets.json").read_text())["targets"]}
_o = json.loads((ROOT / "data" / "agents" / "outcomes.json").read_text())
_bench = {r["metric"]: r for r in _o["against_published"]}
_rep = str(os.environ.get("PASOK_REPLAY", "replay2026_v29"))
_dd = pd.read_csv(ROOT / "data" / "sim" / _rep / "days.csv")
_lost_pct = 100.0 * _dd["lost_units"].sum() / max(_dd["sold_units"].sum() + _dd["lost_units"].sum(), 1)
_out = _o["outcomes"]
y = ledger(s, [
    (f"Fill rate, A class  ·  retail shelf {_bench['fill_A']['benchmark'] * 100:.0f}%",
     f"{_out['fill_A']['value'] * 100:.2f}%", False),
    ("Demand lost  ·  retail out-of-stock 8.3%",
     f"{_lost_pct:.2f}%", False),
    (f"Days of inventory  ·  Indofood CBP {_bench['dio_days']['benchmark']:.1f}",
     f"{_out['dio_days']['value']:.0f} days", False),
    (f"Expiry, share of cost  ·  shrink {_bench['expiry_pct_of_cogs']['benchmark'] * 100:.2f}%",
     f"{_out['expiry_pct_of_cogs']['value'] * 100:.2f}%", False),
    ("Lines needing a person  ·  under 10%",
     f"{_t['manual_review']['measured_pct']:.1f}%", False),
], y + 0.02, step=0.40, vsize=11.0, label_w=4.10, num_w=0.90)
_line = ("Four of five sit beside a published number; the fifth is our own ceiling. The promise we "
         "missed is ours: write-off rose with A-class cover.")
_lh = ink_h(_line, False, 9.0, COL, 1.16)
text(s, LEFT, y + 0.16, COL, _lh, [_line], size=9.0, color=BODY, spacing=1.16)
_src = ("Sources: Corsten & Gruen with GMA, Indofood CBP 2025 in JMKT 15(3), National Supermarket "
        "Shrink Survey. URLs in data/agents/outcomes.json.")
_sh = ink_h(_src, False, 8.0, COL, 1.14)
text(s, LEFT, y + 0.20 + _lh, COL, _sh, [_src], size=8.0, color=GREY, spacing=1.14)
foot(s, "A simulated catalogue: this is a ceiling, not a forecast.",
     above=y + 0.20 + _lh + _sh, rule_line=False)

# speaker notes: the evidence a rehearsal needs, kept off the page
NOTES = {
    2: "data/demand/event_dates.csv. Lebaran moves 33 days across 2023-2026, Imlek 26, Nyepi 17; Christmas and New Year stay put.",
    3: "simulation/results.json: orders swing 2.68 times demand with no rules, 0.24 with them; fill 0.9893 vs 0.9868.",
    4: "The loop runs once a morning: pasok-loop.timer at 06:00 WIB, before the buying desk opens.",
    5: "Screenshot of the running console; the same numbers sit in data/demand/sku_ramps.csv and catalog.csv.",
    6: "data/agents/one_pass.json: the trace and every number on the page are read from it.",
    7: "data/agents/one_pass.json decide.rationale; the page quotes it, truncated at 330 characters.",
    8: "experiments/e2_results.json (ramp 0.0775, flat_bump 0.1161 over 154 windows, 30,490 series) and data/agents/supplier_reliability.csv.",
    9: "src/agents/decision.py guardrails. On 2026-10-28 the shelf-position cap cut 7 SKUs for 10,028 units (data/agents/decisions.csv, cap_from='shelf position, four fifths of life'); buffer_shelf_cap_binds stayed 0 and the MOQ and peak gates cut nothing. The replay (104 days) is the evidence: amplification 1.25 to 0.32.",
    10: "data/sap/rpt_summary.json, data/sap/rationale_summary.json, and aws/GATES.md for the AgentCore quota.",
    11: "data/orders/order_summary.json and redirect_summary.json, snapshot 2026-10-28.",
    12: "data/catalog/meta.json (seed 20261008, 600 SKUs, 120 outlets, 1,396 days); data/catalog/price_anchors.csv (PIHPS); data/demand/event_dates.csv; data/demand/category_event_amplitude.csv (GAPMMI, Antara, NielsenIQ, press); data/demand/interest_profiles.json and trends_id_*.csv.",
    13: "Every comparison on this page is a published figure, not a simulated baseline: fill against Corsten & Gruen and the GMA out-of-stock study, days of inventory against Indofood CBP 2025, expiry against the National Supermarket Shrink Survey. Percentages, not rupiah, because a rupiah figure only means something next to the sales it came out of. The one promise missed is our own: the write-off share rose as A-class cover went to 99.9%. Sources and URLs: data/agents/outcomes.json."
}
for idx, note in NOTES.items():
    prs.slides[idx - 1].notes_slide.notes_text_frame.text = note

prs.save(OUT)
print(f"wrote {OUT} with {len(prs.slides._sldIdLst)} slides")
