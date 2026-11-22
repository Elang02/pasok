"""Build the Pasok Demo Day deck on the official SOKRATES template.

Design rules, measured from the template (see 11-CONTEXT.md):
  - the artwork is furniture: no text over the logo strip and none below y = 6.2 in
  - the body column ends at x = 5.15 in below the title band
  - every claim gets a picture: a chart drawn from the artefacts, a live screenshot, or a diagram
  - no citations, file paths or build notes on a slide; those live in the speaker notes

Run:  .venv/bin/python demo/deck/make_charts.py && .venv/bin/python demo/deck/build_deck.py
      .venv/bin/python demo/deck/check_layout.py && .venv/bin/python demo/deck/check_numbers.py
"""
from pathlib import Path
import shutil

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BASE = Path("/home/ubuntu/pasok/demo/deck")
ASSETS = BASE / "assets"
TPL = Path("/tmp/tpl/ppt/media")
OUT = BASE / "Pasok_DemoDay_2026.pptx"

INK = RGBColor(0x14, 0x1A, 0x46)
VIOLET = RGBColor(0x6C, 0x4B, 0xE0)
ACCENT = RGBColor(0xF2, 0xA3, 0x3C)
GREY = RGBColor(0x5B, 0x61, 0x78)
BODY = RGBColor(0x2B, 0x30, 0x45)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = RGBColor(0xF4, 0xF2, 0xFB)
FONT = "Arial"

LEFT = 0.78
COL = 4.35
HEAD_W = 6.25
BODY_Y = 2.62
RIGHT_X = 5.5

ASSETS.mkdir(parents=True, exist_ok=True)
for n in (1, 2):
    src = TPL / f"image{n}.png"
    if src.exists():
        shutil.copy(src, ASSETS / f"bg{n}.png")

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def text(slide, x, y, w, h, runs, size=12, color=BODY, bold=False, spacing=1.0,
         space_after=0, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    first = True
    for item in runs:
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


def background(slide, kind):
    slide.shapes.add_picture(str(ASSETS / f"bg{kind}.png"), 0, 0,
                             width=prs.slide_width, height=prs.slide_height)


def head(slide, title, number, size=25):
    text(slide, LEFT, 0.95, HEAD_W, 1.4, [title], size=size, color=INK, bold=True, spacing=0.96)
    text(slide, 4.95, 0.58, 0.6, 0.28, [f"{number:02d}"], size=9.5, color=VIOLET,
         bold=True, align=PP_ALIGN.RIGHT)


def body(slide, paras, y=BODY_Y, size=11.5, gap=9, w=COL):
    text(slide, LEFT, y, w, 3.4, paras, size=size, color=BODY, spacing=1.38, space_after=gap)


def ledger(slide, rows, y=4.6, step=0.52, vsize=17, lsize=9, w=COL):
    """A quiet table: label left in grey, value right in violet. No rules, no boxes."""
    for i, (label, value) in enumerate(rows):
        top = y + i * step
        text(slide, LEFT, top + 0.07, w - 1.62, 0.26, [label], size=lsize, color=GREY)
        text(slide, LEFT + w - 1.55, top, 1.55, 0.34, [value], size=vsize, color=VIOLET,
             bold=True, align=PP_ALIGN.RIGHT)


def shot(slide, image, x, y, w, caption, pad=0.14):
    """A chart or screenshot in a white card, with one line saying what to look at."""
    from PIL import Image

    im = Image.open(ASSETS / image)
    h = w * im.size[1] / im.size[0]
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x - pad), Inches(y - pad),
                                  Inches(w + 2 * pad), Inches(h + 0.52 + pad))
    card.adjustments[0] = 0.03
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = RGBColor(0xE2, 0xDF, 0xF2)
    card.line.width = Pt(0.75)
    card.shadow.inherit = False
    slide.shapes.add_picture(str(ASSETS / image), Inches(x), Inches(y), width=Inches(w))
    text(slide, x, y + h + 0.12, w, 0.34, [caption], size=8, color=GREY, spacing=1.15)
    return y + h + 0.46


def step_map(slide, steps, x, y, w, step=0.62):
    """A vertical map: numbered stops, each with a fact and the detail under it."""
    for i, (title, sub) in enumerate(steps):
        top = y + i * step
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(top + 0.03),
                                     Inches(0.2), Inches(0.2))
        dot.fill.solid()
        dot.fill.fore_color.rgb = ACCENT if i == len(steps) - 1 else VIOLET
        dot.line.fill.background()
        if i < len(steps) - 1:
            line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + 0.09), Inches(top + 0.2),
                                          Inches(0.02), Inches(step - 0.18))
            line.fill.solid()
            line.fill.fore_color.rgb = RGBColor(0xE2, 0xDF, 0xF2)
            line.line.fill.background()
        text(slide, x + 0.34, top, w - 0.34, 0.3, [title], size=10.5, color=INK, bold=True)
        text(slide, x + 0.34, top + 0.25, w - 0.34, 0.3, [sub], size=8.5, color=GREY)


def lane(slide, boxes, x, y, w, step=0.86, height=0.56):
    """A vertical pipeline of systems, with arrows between them."""
    for i, (name, sub) in enumerate(boxes):
        top = y + i * step
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(top),
                                     Inches(w), Inches(height))
        box.adjustments[0] = 0.14
        box.fill.solid()
        box.fill.fore_color.rgb = INK if i == 0 else PALE
        box.line.color.rgb = RGBColor(0xE2, 0xDF, 0xF2)
        box.line.width = Pt(0.75)
        box.shadow.inherit = False
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.14)
        tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        r1 = p.add_run(); r1.text = name
        r1.font.size = Pt(10.5); r1.font.bold = True; r1.font.name = FONT
        r1.font.color.rgb = WHITE if i == 0 else INK
        r2 = p.add_run(); r2.text = "   " + sub
        r2.font.size = Pt(8); r2.font.name = FONT
        r2.font.color.rgb = RGBColor(0xC9, 0xC3, 0xEC) if i == 0 else GREY
        if i < len(boxes) - 1:
            arrow = slide.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(x + w / 2 - 0.07),
                                           Inches(top + height + 0.03), Inches(0.14), Inches(0.16))
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = ACCENT
            arrow.line.fill.background()


def notes(slide, body_text):
    slide.notes_slide.notes_text_frame.text = body_text


# ---------------------------------------------------------------- 1 title
s = prs.slides.add_slide(BLANK)
background(s, 1)
text(s, LEFT, 0.9, 5.4, 0.3, ["DEMO DAY  ·  TRACK A  ·  INTELLIGENCE SUPPLY CHAIN"],
     size=9, color=VIOLET, bold=True)
text(s, LEFT, 1.62, 6.2, 1.0, ["Pasok"], size=50, color=INK, bold=True)
text(s, LEFT, 2.8, 5.2, 1.4,
     ["A reorder agent for FMCG distributors. It sizes the order and writes the reason. When the "
      "numbers look wrong, it holds the order instead of sending it."],
     size=15.5, color=BODY, spacing=1.3)
text(s, LEFT, 5.2, 4.2, 0.8, [
    [("Vicentius Elang Krisnanto · Joshua Sahusilawane · Bintang Neera", True, INK)],
    [("Sistem Informasi, Unika Atma Jaya", False, GREY)],
], size=9.5, spacing=1.25, space_after=2)
text(s, LEFT, 6.02, 4.2, 0.3, ["31 October 2026  ·  BINUS Alam Sutera"], size=9, color=GREY)
notes(s, "Open with the sentence on screen and pause. We built a reorder agent a distributor can sign "
         "off, because the braking rules came before the model.\nTime: 40 s.")

# ---------------------------------------------------------------- 2 problem
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "One buyer reorders 600 SKUs against a calendar that moves", 2)
body(s, [
    "General trade is 69% of FMCG volume in Indonesia. Most stores still run a fixed reorder point.",
    "Every event that lifts demand drifts across the year, so last year's plan lands in the wrong week.",
], gap=8)
ledger(s, [("SKUs on one desk", "600"), ("Suppliers below 95% fill", "9 of 12")], y=4.75)
shot(s, "fig_calendar.png", RIGHT_X, 2.45, 6.85,
     "Each dot is a real event date from the registry. Lebaran keeps arriving earlier.")
notes(s, "Point at Lebaran: 21 April 2023, 20 March 2026, 32 days earlier. A number set once cannot "
         "follow that line, and the buyer only reviews weekly.\nTime: 75 s.")

# ---------------------------------------------------------------- 3 why autonomy is risky
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "An unguarded agent over-orders, and the chart shows it", 3)
body(s, [
    "Same forecaster, 250 trading days, Bank Indonesia retail index. One run without rules, one with them.",
    "The model is identical. Only the three rules differ.",
], gap=8)
ledger(s, [("Order variance, no rules", "2.68x"), ("Order variance, with rules", "0.24x")],
       y=4.6, step=0.55, vsize=16)
shot(s, "fig_bullwhip.png", RIGHT_X, 2.45, 6.85,
     "Seven-day averages. Amber is the agent without guardrails, violet with them; grey is demand.")
notes(s, "The amber line swings far above and below demand. The violet one tracks it. This is the "
         "reason the guardrails exist, and it is why we lead with them.\nTime: 70 s.")

# ---------------------------------------------------------------- 4 build
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "Four agents run one pass, and the model never picks the quantity", 4)
steps = [("Demand Agent", "forecast, event ramp, anomaly flag", INK),
         ("Stock Position Agent", "sellable, days of cover, two flags", INK),
         ("Supplier Reliability Agent", "lead p50/p90, fill rate, drift", INK),
         ("Decision Agent", "action, quantity, reason", VIOLET),
         ("Order system", "auto-issue or human queue", None)]
top = 2.55
for i, (name, sub, fill) in enumerate(steps):
    y = top + i * 0.64
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(LEFT), Inches(y),
                             Inches(4.35), Inches(0.48))
    box.adjustments[0] = 0.16
    if fill is None:
        box.fill.solid(); box.fill.fore_color.rgb = WHITE
        box.line.color.rgb = VIOLET; box.line.width = Pt(1.1)
    else:
        box.fill.solid(); box.fill.fore_color.rgb = fill; box.line.fill.background()
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = Inches(0.13); tf.margin_right = Inches(0.08)
    tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    r1 = p.add_run(); r1.text = name
    r1.font.size = Pt(10.5); r1.font.bold = True; r1.font.name = FONT
    r1.font.color.rgb = WHITE if fill else INK
    r2 = p.add_run(); r2.text = "   " + sub
    r2.font.size = Pt(7.5); r2.font.name = FONT
    r2.font.color.rgb = RGBColor(0xD8, 0xD3, 0xF5) if fill else GREY
    if i < len(steps) - 1:
        arrow = s.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(2.76), Inches(y + 0.49),
                                   Inches(0.15), Inches(0.12))
        arrow.fill.solid(); arrow.fill.fore_color.rgb = ACCENT
        arrow.line.fill.background()
text(s, LEFT, 6.0, COL, 0.28, ["The model writes the reason, never the quantity."],
     size=9.5, color=VIOLET, bold=True)
notes(s, "Four agents, one pass, no human in the middle unless an order breaks a rule. Say out loud "
         "that the model is not in the arithmetic.\nTime: 70 s.")

# ---------------------------------------------------------------- 5 demo console
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "The console names the next event and the goods that spike", 5)
body(s, [
    "Ask which event is next and it gives the date, the goods and how far demand moves. "
    "Ask for a spike inside a month and it answers none: Christmas sits outside that window.",
    "Christmas, 22 December 2026: 79 days out from the snapshot. The median SKU runs 1.60 times normal, one passes "
    "2.5, and the strongest SKU reaches 2.63.",
    "A spike counts from 1.25 times normal. Here the holiday factor lifts the whole catalogue, so the "
    "ranking matters more than the count.",
], y=2.62, gap=8)
shot(s, "shot_console.jpg", 5.55, 2.5, 6.95,
     "The console answering live on 26 October: no event inside a month, so no uplift, and\n"
     "every number in the answer checked against the records. 6.1 seconds, four steps.")
notes(s, "Live console output, 26 October, 6.1 s. If the network holds, run this question live and "
         "then ask the room to name a SKU. The screenshot is the fallback.\nTime: 85 s.")

# ---------------------------------------------------------------- 6 one pass
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "One SKU, from eight days of cover to a scored order", 6)
body(s, [
    "SKU0286, biscuits, principal P03. The loop found it below its trigger and sized the order itself.",
    "Nobody approved it. After the goods arrived the loop graded its own decision.",
], gap=8, w=4.3)
step_map(s, [
    ("8.2 days of cover", "under the 14-day trigger: lead 7 + review 7"),
    ("17-day cover target", "lead 7 + review 7 + buffer 3"),
    ("2,092 units", "IDR 15.9M, inside an IDR 95.1M credit line"),
    ("Delivery at p90", "7 days, learned from receipts"),
    ("Scored 97.70% fill", "48 units short, fed back in"),
], RIGHT_X + 0.1, 2.45, 6.7, step=0.66)
notes(s, "Walk the map top to bottom. The last stop is the one judges remember: the system graded its "
         "own order after delivery, and that score feeds the next forecast.\nTime: 70 s.")

# ---------------------------------------------------------------- 7 demand
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "The forecast learns what each SKU does around an event", 7)
body(s, [
    "30,490 M5 series, 154 event windows, scored leave-one-occurrence-out.",
    "A ramp per SKU beats a flat bump on the same windows.",
    "A spike with no registered event still gets flagged for a human to name.",
], gap=8)
ledger(s, [("Ramp WAPE", "0.0775"), ("Flat bump WAPE", "0.1161"),
           ("Novel spikes caught", "120 of 120"),
           ("False alarms per 100 days", "0.65")], y=4.3, step=0.45, vsize=15)
notes(s, "The calendar is not enough because the dates move. The ramp is per SKU and per event, "
         "re-estimated from the last occurrences.\nTime: 65 s.")

# ---------------------------------------------------------------- 8 supplier
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "Lead time comes from goods receipts, not from a promise", 8)
body(s, [
    "Every receipt updates p50 and p90 per principal.",
    "The Decision Agent plans against p90, so a slow supplier earns a longer cover target.",
], gap=8)
ledger(s, [("Network fill", "90.32%"), ("P02 on time", "81.1%")], y=4.75, step=0.55, vsize=16)
shot(s, "fig_lead.png", RIGHT_X, 2.45, 6.85,
     "Measured from 1,956 goods receipts. Amber is P02, the slowest principal in the catalogue.")
notes(s, "P02 takes 9 days on average and 11 at p90. The buffer is not a policy number, it is read "
         "from those receipts.\nTime: 65 s.")

# ---------------------------------------------------------------- 9 guardrails
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "Three rules guard the order stream", 9)
text(s, LEFT, 2.62, COL, 0.7, [
    [("cover = lead p90 + review + buffer", True, INK)],
    [("buffer = z · √(lead variance² + forecast error²)", False, BODY)],
], size=10, spacing=1.3, space_after=2)
ledger(s, [("Order variance on replay", "1.33x → 0.36x"), ("Orders the cap touched", "0 of 600")],
       y=3.95, step=0.55, vsize=15)
text(s, LEFT, 5.25, COL, 0.55, ["All three are coded. On this snapshot none cut a unit, so the replay is the evidence."],
     size=9.5, color=GREY, spacing=1.25)
lane(s, [("1  Smooth the forecast", "before it drives sizing"),
         ("2  Damp against the last order", "no oscillation week to week"),
         ("3  Cap the order", "variance out stays near variance in")],
     RIGHT_X, 2.5, 6.6, step=0.92, height=0.62)
notes(s, "These three rules are the contribution, not the model. The replay shows 1.33x down to 0.36x "
         "with the rules on.\nTime: 80 s.")

# ---------------------------------------------------------------- 10 sap
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "SAP scores the catalogue and writes the reason", 10)
body(s, [
    "sap-rpt-1.6 scores 600 SKUs in 10.73 seconds.",
    "gpt-5.4 wrote all 40 exception rationales, none from a template.",
    "Joule shows the queue, so the buyer approves inside the tool they already use.",
], gap=7)
ledger(s, [("Agreement with the agent", "0.895"), ("Rationales written", "40/40")],
       y=4.6, step=0.52, vsize=16)
text(s, LEFT, 5.8, COL, 0.55,
     ["RPT flags 577 SKUs as expiry risk where we flag none. The definitions differ."],
     size=9, color=GREY, spacing=1.25)
notes(s, "SAP is the scoring and reasoning service here, not the system of record. The proposal says "
         "otherwise, and we correct it on stage.\nTime: 75 s.")

# ---------------------------------------------------------------- 11 aws
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "The AWS lane answers live", 11)
body(s, [
    "Four agents in one Lambda behind a public Function URL.",
    "Bedrock through the Mantle endpoint, with SAP AI Core as the fallback brain.",
], gap=8, w=4.3)
lane(s, [("Lambda function URL", "four agents, one bundle"),
         ("Bedrock, Mantle endpoint", "the answering model"),
         ("SAP AI Core", "fallback and scoring")],
     RIGHT_X, 2.45, 6.4, step=0.95, height=0.66)
text(s, RIGHT_X, 5.35, 6.4, 0.5,
     ["AgentCore is written and blocked by a quota on this account, so Lambda hosts the lane today."],
     size=9, color=GREY, spacing=1.25)
notes(s, "State the limitation before a judge finds it. The architecture targets AgentCore, the "
         "account cannot run it, so Lambda hosts the lane.\nTime: 65 s.")

# ---------------------------------------------------------------- 12 impact
s = prs.slides.add_slide(BLANK)
background(s, 2)
head(s, "What one snapshot moved", 12)
body(s, [
    "480 orders. 445 went out without a person; 35 waited: 15 over a credit line, 15 near expiry, 6 mid switch.",
    "414 surplus SKUs moved to another depot, IDR 7.78 bn protected.",
    "In the year-long replay the money gate never fired: 0 of 18,824 orders. This pass, rebuilding a thin shelf, 15 did.",
], gap=8, w=4.2)
ledger(s, [("Ordered automatically", "IDR 30.27 bn"), ("Redirected, not bought", "IDR 7.78 bn")],
       y=4.95, step=0.5, vsize=14, w=4.2)
shot(s, "shot_orders_crop.jpg", 5.55, 2.5, 6.95,
     "The run log as it stood on the evening of 26 October, when this shot was taken.\n"
     "One row per run, newest first. The run that stopped is logged rather than hidden.")
notes(s, "For a distributor the number that matters is how much money moves without a person, and how "
         "much is deliberately held. Both are here.\nTime: 70 s.")

# ---------------------------------------------------------------- 13 close
s = prs.slides.add_slide(BLANK)
background(s, 1)
head(s, "A pilot on one distributor, for one month", 13, size=28)
body(s, [
    "Run it on their receipts, not our synthetic file.",
    "Connect their ERP in place of our order desk.",
    "Measure fill rate and stock value at the end of the month.",
], y=2.75, gap=10)
text(s, LEFT, 5.65, 4.4, 0.4, ["Ask us about any SKU and we will show the trace."],
     size=11.5, color=VIOLET, bold=True)
text(s, LEFT, 6.1, 4.4, 0.28, ["Team Pasok  ·  github.com/Elangk1 (private; access on request)"], size=8.5, color=GREY)
notes(s, "End on the pilot, not on a summary. If there is time, ask which SKU they want to see.\n"
         "Time: 45 s.")

prs.save(OUT)
print("slides:", len(prs.slides), "->", OUT, OUT.stat().st_size, "bytes")
