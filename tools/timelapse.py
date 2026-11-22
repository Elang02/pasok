#!/usr/bin/env python
"""Timelapse of the October record: one frame per operating day.

Setiap frame dibangun dari berkas dunia (data/sim/live), bukan dari angka yang ditulis
tangan. Warna, huruf, dan susunannya mengikuti palet konsol di web/pasok.css supaya tidak
ada sistem desain kedua.

Jalan: .venv/bin/python tools/timelapse.py [--name live] [--out demo/timelapse_october.mp4]
"""
from __future__ import annotations

import argparse
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.animation import FFMpegWriter
from matplotlib.patches import FancyBboxPatch, Rectangle

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Palet konsol (web/pasok.css), disalin apa adanya. Tidak ada warna baru.
PAPER, PAPER2, RULE = "#1c1c1c", "#262626", "#33332f"
INK, NEUTRAL, MUTED = "#f1f1ef", "#9a9b96", "#b5b6b0"
ACCENT, OK, WARN, BAD = "#8fa68e", "#9fb894", "#d3ae7a", "#d98a7f"

BAND_BAD, BAND_WARN = 5.0, 10.0          # hari cover: di bawah 5 tipis, di atas 10 tenang
FPS = 24
FRAME_DAYS = 1.3                          # detik per hari
HOLD_LAST = 3.0                           # tahan di frame terakhir


def daily_frames(sim: pathlib.Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Kembalikan (log harian, cover per SKU per hari)."""
    log = pd.read_csv(sim / "days.csv")
    d = pd.read_csv(sim / "world" / "stock_daily.csv", parse_dates=["date"])
    d["sku"] = d["sku"].astype(str)

    def piv(col: str) -> pd.DataFrame:
        return d.pivot(index="date", columns="sku", values=col).sort_index()

    sales = piv("sales")
    vel = sales.rolling(28, min_periods=7).mean()
    sellable = (piv("on_hand").fillna(0) + piv("in_transit").fillna(0)
                + piv("open_po").fillna(0))
    cover = (sellable / vel.replace(0, np.nan)).clip(upper=60)
    return log, cover


def panel(ax, x, y, w, h, colour=PAPER2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.012",
                                linewidth=0, facecolor=colour, transform=ax.transAxes,
                                zorder=0))


def draw(ax, log: pd.DataFrame, cover: pd.DataFrame, i: int) -> None:
    row = log.iloc[i]
    day = pd.Timestamp(row["day"])
    ax.set_facecolor(PAPER)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    ax.text(0.045, 0.945, "Pasok · the replenishment loop, day by day", color=NEUTRAL,
            fontsize=13, family="monospace", va="center")
    ax.text(0.045, 0.878, day.strftime("%d %B %Y"), color=INK, fontsize=40,
            family="monospace", va="center")
    badge = "demand: recorded" if row["demand_source"] != "modelled" else "demand: modelled"
    badge_c = ACCENT if row["demand_source"] != "modelled" else WARN
    ax.text(0.955, 0.898, badge, color=badge_c, fontsize=14, family="monospace",
            ha="right", va="center")
    ax.text(0.955, 0.858, f"review day: {'yes' if row['review'] else 'no'}", color=NEUTRAL,
            fontsize=12, family="monospace", ha="right", va="center")

    # hari ini, di sebelah kiri
    panel(ax, 0.045, 0.30, 0.30, 0.50)
    # The daily row writes the day's DEMAND into sold_units on the days the agent is not
    # called, and the unmet part into lost_units, so the honest label for that column is the
    # demand, and the second line is what the world could not serve.
    facts = [("units demanded", f"{row['sold_units']:,}"),
             ("units not served", f"{row['lost_units']:,}"),
             ("units arrived", f"{row['arrived_units']:,}"),
             ("units on hand", f"{row['on_hand_units']:,}"),
             ("days of cover, median", f"{row['cover_median']:.1f}"),
             ("SKUs out of stock", f"{row['out_of_stock']:,}")]
    if row["review"]:
        facts.append(("orders placed", f"Rp {row['decided_value_idr']:,}"))
    for k, (label, value) in enumerate(facts):
        yy = 0.745 - k * 0.072
        ax.text(0.075, yy, label, color=NEUTRAL, fontsize=12, family="monospace", va="center")
        col = BAD if (label == "units not served" and row["lost_units"] > 0) else INK
        ax.text(0.325, yy, value, color=col, fontsize=15, family="monospace",
                ha="right", va="center")

    # sebaran cover 600 SKU hari ini
    vals = cover.loc[day].dropna().sort_values().to_numpy()
    if len(vals):
        panel(ax, 0.375, 0.30, 0.58, 0.50)
        ax.text(0.395, 0.775, "days of cover, one dot per SKU, thinnest on the left",
                color=NEUTRAL, fontsize=12, family="monospace", va="center")
        xs = np.linspace(0.40, 0.935, len(vals))
        cols = np.where(vals < BAND_BAD, BAD, np.where(vals < BAND_WARN, WARN, OK))
        ys = 0.34 + (np.clip(vals, 0, 45) / 45.0) * 0.40
        ax.scatter(xs, ys, s=7, c=cols, alpha=0.9, zorder=3, linewidths=0)
        ax.plot([0.40, 0.935], [0.34 + 10 / 45 * 0.40] * 2, color=RULE, lw=1, ls="--", zorder=2)
        thin = int((vals < BAND_BAD).sum())
        ax.text(0.395, 0.325, f"{thin} SKU under {BAND_BAD:.0f} days of cover", color=BAD,
                fontsize=12, family="monospace", va="center")

    # jejak sampai hari ini
    panel(ax, 0.045, 0.075, 0.91, 0.19, PAPER2)
    days = pd.to_datetime(log["day"]).to_numpy()
    on_hand = log["on_hand_units"].to_numpy(dtype=float)
    xs = 0.075 + (np.arange(len(log)) / max(len(log) - 1, 1)) * 0.85
    ys = 0.11 + (on_hand - on_hand.min()) / max(on_hand.max() - on_hand.min(), 1) * 0.11
    ax.plot(xs, ys, color=RULE, lw=1.5, zorder=2)
    ax.plot(xs[:i + 1], ys[:i + 1], color=ACCENT, lw=2.5, zorder=3)
    ax.scatter([xs[i]], [ys[i]], color=ACCENT, s=45, zorder=4)
    for j, r in log.iterrows():
        if r["review"]:
            ax.scatter([xs[j]], [0.095], color=OK, s=16, zorder=4, marker="^")
    ax.text(0.075, 0.245, "units on hand", color=NEUTRAL, fontsize=11, family="monospace",
            va="center")
    ax.text(0.955, 0.245, "triangles: a day the agent reviewed and could order",
            color=NEUTRAL, fontsize=11, family="monospace", ha="right", va="center")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="live")
    ap.add_argument("--out", default="demo/timelapse_october.mp4")
    ap.add_argument("--frames-dir", default="demo/timelapse_frames")
    a = ap.parse_args()
    sim = ROOT / "data" / "sim" / a.name
    log, cover = daily_frames(sim)
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = ROOT / a.frames_dir
    frames.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 9), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    writer = FFMpegWriter(fps=FPS, bitrate=4000,
                          metadata={"title": f"Pasok {a.name} day by day"})
    with writer.saving(fig, str(out), dpi=120):
        for i in range(len(log)):
            ax.clear()
            draw(ax, log, cover, i)
            for _ in range(int(FRAME_DAYS * FPS)):
                writer.grab_frame(facecolor=PAPER)
            if i == len(log) - 1:
                for _ in range(int(HOLD_LAST * FPS)):
                    writer.grab_frame(facecolor=PAPER)
    plt.close(fig)

    # papan cerita: enam hari penting, satu gambar
    picks = [0, 1, 6, 7, 10, len(log) - 1]
    fig2, axes = plt.subplots(2, 3, figsize=(18, 9.5), dpi=110)
    fig2.patch.set_facecolor(PAPER)
    for ax2, i in zip(axes.ravel(), picks):
        draw(ax2, log, cover, min(i, len(log) - 1))
    fig2.tight_layout(pad=1.1)
    board = ROOT / "demo" / "timelapse_storyboard.png"
    fig2.savefig(board, facecolor=PAPER)
    plt.close(fig2)

    print(f"video   : {out} ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"papan   : {board}")
    print(f"hari    : {len(log)} frame, {len(log) * FRAME_DAYS + HOLD_LAST:.1f} detik")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
