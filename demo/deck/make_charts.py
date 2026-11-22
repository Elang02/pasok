"""Draw the three charts the deck needs, straight from the artefacts.

  fig_calendar.png  event dates per year, showing the drift
  fig_bullwhip.png  demand vs orders, unguarded vs guarded (same seed as results.json)
  fig_lead.png      measured lead time per principal, P02 highlighted

Run: .venv/bin/python demo/deck/make_charts.py
"""
import csv
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from datetime import date, timedelta

ROOT = Path("/home/ubuntu/pasok")
ASSETS = ROOT / "demo/deck/assets"
INK = "#141A46"
VIOLET = "#6C4BE0"
AMBER = "#F2A33C"
GREY = "#8A8FA3"
LIGHT = "#D9D5EE"

plt.rcParams.update({
    "font.family": "Liberation Sans",
    "font.size": 9,
    "axes.edgecolor": LIGHT,
    "axes.labelcolor": INK,
    "xtick.color": "#5B6178",
    "ytick.color": "#5B6178",
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# ------------------------------------------------------------------ calendar
dates = list(csv.DictReader((ROOT / "data/demand/event_dates.csv").open()))
order = ["Christmas", "NewYear", "Imlek", "Nyepi", "THR", "Ramadan", "Lebaran"]
series: dict[str, list[date]] = {k: [] for k in order}
for r in dates:
    if r["event"] in series and date.fromisoformat(r["date"]).year <= 2026:
        series[r["event"]].append(date.fromisoformat(r["date"]))
for k in series:
    series[k].sort()

fig, ax = plt.subplots(figsize=(6.3, 2.75), dpi=200)
for i, name in enumerate(order):
    ds = series[name]
    if not ds:
        continue
    fixed = name in ("Christmas", "NewYear")
    colour = VIOLET if fixed else AMBER
    xs = [d.timetuple().tm_yday for d in ds]
    if len(xs) > 1:
        ax.plot(xs, [i] * len(xs), color=colour, lw=1.1, alpha=0.55, zorder=2)
    ax.scatter(xs, [i] * len(xs), s=42, color=colour, zorder=3, edgecolor="white", linewidth=0.6)
    drift = max(xs) - min(xs) if len(xs) > 1 else 0
    label = "fixed" if fixed else f"{drift} days"
    ax.annotate(label, xy=(372, i), va="center", ha="left", fontsize=9.5,
                color=VIOLET if fixed else AMBER)

ax.set_yticks(range(len(order)))
ax.set_yticklabels(order, fontsize=10.5, color=INK)
ax.set_ylim(-0.6, len(order) - 0.4)
ax.set_xlim(0, 430)
ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 3, 5, 7, 9, 11)))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
ax.tick_params(axis="x", labelsize=10)
ax.grid(axis="x", color="#EFEDF8", lw=0.7)
ax.set_axisbelow(True)
for side in ("left", "right", "top"):
    ax.spines[side].set_visible(False)
ax.set_xlabel("date within the year, one dot per year 2023 to 2026",
              fontsize=9.4, color="#5B6178", labelpad=6)
fig.tight_layout(pad=0.3)
fig.savefig(ASSETS / "fig_calendar.png", facecolor="white")
plt.close(fig)
print("calendar: seven events, drift annotated")

# ------------------------------------------------------------------ bullwhip
sys.path.insert(0, str(ROOT / "simulation"))
import replenish_sim as sim

rng = np.random.default_rng(sim.SEED)
demand = sim.make_demand(rng)
orders_a = sim.policy_unguarded(demand, rng)
orders_b = sim.policy_guarded(demand, rng)
d = demand[sim.WARMUP:]
oa = orders_a[sim.WARMUP:]
ob = orders_b[sim.WARMUP:]
amp_a = oa.var() / d.var()
amp_b = ob.var() / d.var()


def roll(x, w=7):
    return np.convolve(x, np.ones(w) / w, mode="valid")


fig, ax = plt.subplots(figsize=(6.6, 2.6), dpi=220)
x = np.arange(len(d))
ax.fill_between(x, 0, d, color="#EFEDF8", linewidth=0)
ax.plot(x, d, color=GREY, lw=0.8, label="demand")
ax.plot(roll(x), roll(oa), color=AMBER, lw=1.4, label=f"orders, unguarded ({amp_a:.2f}x)")
ax.plot(roll(x), roll(ob), color=VIOLET, lw=1.6, label=f"orders, guarded ({amp_b:.2f}x)")
ax.set_xlim(0, len(d))
ax.set_xlabel("trading days in the simulation")
ax.set_ylabel("units per day")
ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=3)
ax.grid(axis="y", color="#EFEDF8", lw=0.8)
ax.set_axisbelow(True)
fig.tight_layout(pad=0.3)
fig.savefig(ASSETS / "fig_bullwhip.png", facecolor="white")
plt.close(fig)
print(f"bullwhip: {amp_a:.2f}x vs {amp_b:.2f}x, days {len(d)}")

# --------------------------------------------------------------------- lead
sup = list(csv.DictReader((ROOT / "data/agents/supplier_reliability.csv").open()))
sup.sort(key=lambda r: float(r["lead_mean_d"]), reverse=True)
shown = sup[:3] + sup[-3:]
names = [r["principal_id"] for r in shown]
means = [float(r["lead_mean_d"]) for r in shown]
p90 = [float(r["lead_p90_d"]) for r in shown]
colors = [AMBER if n == "P02" else VIOLET for n in names]

fig, ax = plt.subplots(figsize=(6.3, 1.95), dpi=220)
y = np.arange(len(names))
ax.barh(y, means, color=colors, height=0.60)
for i, (m, p) in enumerate(zip(means, p90)):
    ax.text(m + 0.25, i, f"{m:.1f}d (p90 {p:.0f})", va="center", fontsize=9.5, color="#5B6178")
ax.set_yticks(y)
ax.set_yticklabels(names, fontsize=11, color=INK)
ax.invert_yaxis()
ax.set_xlabel("measured lead time, days", fontsize=9.5)
ax.set_xlim(0, max(means) * 1.42)
ax.tick_params(axis="x", labelsize=9)
ax.grid(axis="x", color="#EFEDF8", lw=0.8)
ax.set_axisbelow(True)
ax.spines["left"].set_visible(False)
fig.tight_layout(pad=0.3)
fig.savefig(ASSETS / "fig_lead.png", facecolor="white")
plt.close(fig)
print("lead: six shown, worst", names[0], means[0], "days; best", names[-1], means[-1], "days")
