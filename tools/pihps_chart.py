"""Render the Eid al-Fitr price-index chart from pihps_event_summary.json."""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

SUMMARY = "/home/ubuntu/pasok/data/external/pihps_event_summary.json"
OUT = "/home/ubuntu/pasok/demo/pihps_event_risers.png"

SERIES = [
    ("Telur Ayam", "Eggs", "#C07A33"),
    ("Minyak Goreng Kemasan", "Cooking oil, packaged", "#A6483F"),
    ("Minyak Goreng Curah", "Cooking oil, bulk", "#7C8A93"),
    ("Gula Pasir", "Sugar", "#6B5B8E"),
    ("Beras Medium", "Rice, medium", "#2F6B5F"),
]


def main():
    with open(SUMMARY, encoding="utf-8") as fh:
        summary = json.load(fh)

    fig, ax = plt.subplots(figsize=(9.2, 5.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ends = []
    for key, label, color in SERIES:
        curve = summary["commodities"][key]["index_curve_avg"]
        xs = sorted(int(k) for k in curve)
        ys = [curve[str(x)] for x in xs]
        ax.plot(xs, ys, color=color, linewidth=2.1, label=label,
                solid_capstyle="round", zorder=3)
        ends.append({"label": label, "color": color, "x": xs[-1],
                     "y": ys[-1], "line_y": ys[-1]})

    # spread the right-edge labels so equal end values do not collide
    ends.sort(key=lambda e: e["line_y"])
    min_gap = 0.62
    for i in range(1, len(ends)):
        if ends[i]["y"] - ends[i - 1]["y"] < min_gap:
            ends[i]["y"] = ends[i - 1]["y"] + min_gap
    for e in ends:
        if abs(e["y"] - e["line_y"]) > 0.12:
            ax.plot([e["x"] + 0.6, e["x"] + 2.6], [e["line_y"], e["y"]],
                    color=e["color"], linewidth=0.6, alpha=0.55,
                    solid_capstyle="round", zorder=2)
        ax.annotate(e["label"], xy=(e["x"] + 3.0, e["y"]), xytext=(2, 0),
                    textcoords="offset points", va="center", fontsize=8.8,
                    color=e["color"])

    ax.axvline(0, color="#9AA3A8", linewidth=1.0, linestyle=(0, (4, 3)), zorder=1)
    ax.text(1.4, 0.985, "Eid al-Fitr", transform=ax.get_xaxis_transform(),
            fontsize=8.6, color="#6E777C", va="top")

    ax.axhline(100, color="#D6DBDE", linewidth=0.9, zorder=1)

    ax.set_xlim(-60, 44)
    ax.set_ylim(93.5, 109.5)
    ax.yaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_major_locator(MultipleLocator(15))
    ax.set_xlabel("Days relative to Eid al-Fitr (H0)", fontsize=9.5, color="#3F484C")
    ax.set_ylabel("Price index (100 = pre-window median)", fontsize=9.5, color="#3F484C")

    ax.grid(axis="y", color="#EDF0F1", linewidth=0.8, zorder=0)
    ax.grid(axis="x", visible=False)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#C9D0D4")
    ax.tick_params(colors="#5A6368", labelsize=8.6, length=3)

    ax.set_title("Indonesian food prices climb around Eid al-Fitr",
                 fontsize=13.5, color="#1F2A2E", loc="left", pad=26,
                 fontweight="semibold")
    ax.text(0, 1.035,
            "Daily traditional-market prices, average of 2022 to 2026. Index 100 = median of the 60 days before each 60-day window.",
            transform=ax.transAxes, fontsize=8.8, color="#6E777C", va="bottom")

    fig.text(0.125, 0.015,
             "Source: PIHPS Nasional, Bank Indonesia. National median across 34 provinces.",
             fontsize=7.6, color="#8A9397")

    fig.subplots_adjust(left=0.085, right=0.845, top=0.845, bottom=0.135)
    fig.savefig(OUT, facecolor="white")
    print("saved", OUT)


if __name__ == "__main__":
    main()
