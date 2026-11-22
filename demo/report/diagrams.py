"""Draw the four diagrams for the mechanism report.

The canvas is 7 inches wide because the document prints them at 6.27 inches: at that
scale an 8.4 point label lands at 7.5 point on paper, which stays readable. Everything is
laid out in inches so a box can be moved without reflowing its neighbours.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

INK = "#1d1d1f"
GREY = "#5f5f5f"
LINE = "#3f3f3f"
FILL = "#f7f5f0"
ACCENT = "#edf2f5"
GO = "#edf3ea"
STOP = "#f8efeb"
W = 7.0


def canvas(h):
    fig = plt.figure(figsize=(W, h), dpi=260)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax, h


def box(ax, x, y, w, h, title, sub=None, fill=FILL, size=8.6, sub_size=None, left=None):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.015,rounding_size=0.05",
                                linewidth=0.8, edgecolor=LINE, facecolor=fill, zorder=2))
    if left:
        ax.text(x + 0.08, y + h / 2 + 0.09, title, ha="left", va="center", fontsize=size,
                color=INK, fontweight="bold", zorder=3)
        if sub:
            ax.text(x + 0.08, y + h / 2 - 0.13, sub, ha="left", va="center",
                    fontsize=sub_size or size - 1.4, color=GREY, zorder=3, linespacing=1.3)
    else:
        ax.text(x + w / 2, y + h / 2 + (0.09 if sub else 0), title, ha="center", va="center",
                fontsize=size, color=INK, fontweight="bold", zorder=3)
        if sub:
            ax.text(x + w / 2, y + h / 2 - 0.14, sub, ha="center", va="center",
                    fontsize=sub_size or size - 1.4, color=GREY, zorder=3, linespacing=1.3)


def arrow(ax, p, q, rad=0.0, size=7.4, label=None, lx=0.0, ly=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=8, linewidth=0.8,
                                 color=LINE, shrinkA=1.5, shrinkB=1.5, zorder=1,
                                 connectionstyle=f"arc3,rad={rad}"))
    if label:
        ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, ha="center", va="center",
                fontsize=size, color=GREY, zorder=3,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"))


def head(ax, h, text, sub=None):
    ax.text(0.02, h - 0.22, text, ha="left", va="center", fontsize=10.6, color=INK,
            fontweight="bold")
    if sub:
        ax.text(0.02, h - 0.46, sub, ha="left", va="center", fontsize=7.6, color=GREY)


def foot(ax, text, y):
    ax.text(0.02, y, text, ha="left", va="top", fontsize=7.4, color=GREY, linespacing=1.45)


# ------------------------------------------------------------------ 1 the chain
def chain():
    fig, ax, h = canvas(6.0)
    head(ax, h, "The morning chain, end to end",
         "run_chain.sh runs ten programs in this order; each writes the file the next one reads.")

    left = [("1  position", "stock_position.py · on hand, transit, open orders"),
            ("2  supplier", "supplier_reliability.py · lead mean, p90, fill"),
            ("3  decide", "decision.py · forecast, size, guard"),
            ("4  consolidate", "consolidation.py · merge small orders"),
            ("5  execute", "order_executor.py · SAP, or escalate")]
    right = [("6  intake", "order_intake.py · supplier confirms"),
             ("7  notify", "notification.py · one note per exception"),
             ("8  redirect", "redirect.py · move stock, no purchase"),
             ("9  learn", "learn.py · accuracy week by week"),
             ("10  explain", "one_pass.py · trace of one order"),
             ("record", "record_run.py · one row in the log")]

    bw, bh, gap = 2.55, 0.56, 0.20
    y0 = 4.70
    for i, (t, sub) in enumerate(left):
        y = y0 - i * (bh + gap)
        box(ax, 0.25, y, bw, bh, t, sub, left=True, size=8.2, sub_size=6.5)
        if i:
            arrow(ax, (0.25 + bw / 2, y + bh + gap), (0.25 + bw / 2, y + bh))
    for i, (t, sub) in enumerate(right):
        y = y0 - i * (bh + gap)
        box(ax, 4.20, y, bw, bh, t, sub, left=True, size=8.2, sub_size=6.5)
        if i:
            arrow(ax, (4.20 + bw / 2, y + bh + gap), (4.20 + bw / 2, y + bh))

    ybot = y0 - 4 * (bh + gap) + bh / 2
    ax.plot([0.25 + bw, 3.40, 3.40], [ybot, ybot, y0 + bh / 2], color=LINE, lw=0.8, zorder=1)
    arrow(ax, (3.40, y0 + bh / 2), (4.20, y0 + bh / 2))

    foot(ax, "A failing step stops the chain, and record_run.py still writes the row that says so. A failed morning is "
             "visible in the log\ninstead of missing from it.", 0.95)
    fig.savefig(OUT / "d1_chain.png", facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ 2 four agents
def agents():
    fig, ax, h = canvas(4.35)
    head(ax, h, "Four agents, one record",
         "Each agent reads files and writes the one artefact its role owns. No agent calls another.")

    cols = [("Demand", "daily sales, event dates,\nmeasured ramps", "forecast per SKU-day",
             "a model over history,\nplus the event shape"),
            ("Policy", "forecast, position,\nsupplier p90 and fill", "decisions.csv",
             "sizes the line,\nthen guards it"),
            ("Execution", "decisions, catalogue,\nsupplier master", "purchase_orders.csv",
             "runs the gates,\nwrites to SAP"),
            ("Reasoning", "every artefact\nabove", "one paragraph per order",
             "the sentence the\nconsole quotes")]
    bw, bh, gap = 1.56, 0.58, 0.16
    for i, (name, reads, writes, note) in enumerate(cols):
        x = 0.22 + i * (bw + gap)
        box(ax, x, 2.95, bw, bh, name, size=8.8)
        ax.text(x + 0.02, 2.80, "reads", fontsize=6.0, color="#8a6d3b", va="top")
        ax.text(x + 0.02, 2.64, reads, fontsize=6.3, color=GREY, va="top", linespacing=1.35)
        ax.text(x + 0.02, 2.05, "writes", fontsize=6.0, color="#8a6d3b", va="top")
        ax.text(x + 0.02, 1.89, writes, fontsize=6.6, color=INK, va="top", linespacing=1.3)
        ax.text(x + 0.02, 1.63, note, fontsize=6.2, color=GREY, va="top", linespacing=1.35)
        if i:
            arrow(ax, (x - gap, 3.24), (x, 3.24))

    box(ax, 0.22, 0.55, 6.56, 0.62,
        "data/agents and data/orders: the record all four share",
        "a message between agents cannot be re-read a month later; a file can",
        fill=ACCENT, size=8.6, sub_size=6.8)
    fig.savefig(OUT / "d2_agents.png", facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ 3 one line
def decision():
    fig, ax, h = canvas(5.2)
    head(ax, h, "One line, from forecast to a decision",
         "The arithmetic in decision.py on the left; the gates in order_executor.py on the right.")

    rows = [("Forecast", "units a day over the window, event ramp in"),
            ("Sells while the truck runs", "forecast x lead p90 = 4,572"),
            ("Position at arrival", "7,505 stock now - 4,572 = 2,932"),
            ("Demand until next arrival", "forecast x cover 31 d = 3,340"),
            ("Gap", "3,340 - 2,932 = 407")]
    bw, bh, gap = 2.55, 0.52, 0.15
    y0 = 4.00
    for i, (t, s) in enumerate(rows):
        y = y0 - i * (bh + gap)
        box(ax, 0.22, y, bw, bh, t, s, left=True, size=8.0, sub_size=6.5)
        if i:
            arrow(ax, (0.22 + bw / 2, y + bh + gap), (0.22 + bw / 2, y + bh))

    yb = y0 - 4 * (bh + gap)
    steps = [("Fill adjustment", "407 / 0.976 = 417", ACCENT),
             ("Guardrails", "smooth, damp, cap variance", ACCENT),
             ("Gates", "MOQ, shelf cap, peak envelope", ACCENT)]
    for i, (t, s, f) in enumerate(steps):
        y = yb + i * (bh + gap)
        box(ax, 3.15, y, 2.10, bh, t, s, fill=f, size=8.0, sub_size=6.5)
        if i == 0:
            arrow(ax, (0.22 + bw, y + bh / 2), (3.15, y + bh / 2))
        else:
            arrow(ax, (3.15 + 1.05, y - gap), (3.15 + 1.05, y))

    box(ax, 5.55, yb + 2 * (bh + gap), 1.23, bh, "Inside", "to SAP, explained", fill=GO, size=7.6,
        sub_size=6.2)
    box(ax, 5.55, yb + 1 * (bh + gap), 1.23, bh, "Outside", "queue, one reason", fill=STOP, size=7.6,
        sub_size=6.2)
    arrow(ax, (5.25, yb + 2 * (bh + gap) + bh / 2), (5.55, yb + 2 * (bh + gap) + bh / 2))
    arrow(ax, (5.25, yb + 2 * (bh + gap) + 0.06), (5.55, yb + (bh + gap) + bh / 2 + 0.06), rad=-0.22)

    foot(ax, "The rupiah value is printed, not gated: the envelope is the item's own peak, so a fast mover may order "
             "600M on its own\nwhile a slow mover at 40M still waits for a person. Warehouse headroom, a supplier switch, "
             "and an unexplained uplift are\nthe other three reasons a line stops, each with a sentence.", 0.62)
    fig.savefig(OUT / "d3_decision.png", facecolor="white")
    plt.close(fig)


# ------------------------------------------------------------------ 4 answer
def answer():
    fig, ax, h = canvas(4.5)
    head(ax, h, "When someone asks the console a question",
         "The console answers from files, and each number in the sentence is checked against the table.")

    steps = [("Question", "typed in the console, in English or Indonesian", FILL),
             ("Classify", "which question class, and therefore which table", FILL),
             ("Facts", "the rows, already computed by the morning loop", FILL),
             ("Sentence", "a model writes it; the trace names the model", ACCENT),
             ("Check", "each number in the sentence must be present in the rows", ACCENT),
             ("Answer", "the sentence, then the rows it came from", FILL)]
    x, bw, bh, gap = 0.95, 5.10, 0.44, 0.135
    ytop = 3.60
    for i, (t, sub, f) in enumerate(steps):
        y = ytop - i * (bh + gap)
        ax.add_patch(FancyBboxPatch((x, y), bw, bh, boxstyle="round,pad=0.012,rounding_size=0.04",
                                    linewidth=0.8, edgecolor=LINE, facecolor=f, zorder=2))
        ax.text(x + 0.14, y + bh / 2, t, ha="left", va="center", fontsize=8.4, color=INK,
                fontweight="bold", zorder=3)
        ax.text(x + 1.12, y + bh / 2, sub, ha="left", va="center", fontsize=7.0, color=GREY,
                zorder=3)
        if i:
            arrow(ax, (x + 0.55, y + bh + gap), (x + 0.55, y + bh))

    foot(ax, "The model never sees the database and never does arithmetic it could get wrong. If a number in the "
             "sentence is missing\nfrom the rows, the answer is rejected and the console says so rather than printing it.",
         0.52)
    fig.savefig(OUT / "d4_answer.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    chain()
    agents()
    decision()
    answer()
    print("wrote", *(p.name for p in sorted(OUT.glob("d*.png"))))
