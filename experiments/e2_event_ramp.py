"""
E2 — Event-Ramp Learner + Novelty Isolation on M5 (v3)
======================================================

Claim under test (from the Pasok proposal): an agent that learns HOW demand
builds/peaks/decays around a calendar event beats the standard tool (a flat
baseline with one uplift dumped on the event day), and can flag demand
departures no registered event explains.

v3 design fixes over v2:
- Dense demand: aggregate sampled series into one department-level series
  (per-series intermittent noise swamps the event signal on daily data).
- Day-of-week adjusted: retail demand has strong weekday structure. Both the
  learned shape and every predictor normalise by the same-weekday trailing
  baseline, so the comparison isolates the EVENT effect, not weekends.
- Leave-one-occurrence-out: a shape learned from occurrences {1..k-1,k+1..n}
  predicts occurrence k. Every occurrence is a test window; no leakage.
- E2b zone: injection needs no event within +-10 days (M5 has events most
  weeks; +-20 days found no candidates).

Run:  cd /home/ubuntu/pasok && .venv/bin/python experiments/e2_event_ramp.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "m5"
OUT = ROOT / "experiments" / "e2_results.json"

SEED = 20261008
HALF = 7                      # +-7 days around the event
WIN = 2 * HALF + 1
N_SERIES = 30490              # all M5 series aggregated (proposal line 29)
MIN_OCC = 4                   # event types with fewer occurrences are skipped
SUSTAIN = 3
THRESH_Z = 3.5


# ---------- data ----------

def load_calendar() -> pd.DataFrame:
    cal = pd.read_csv(DATA / "calendar.csv")
    cal["event"] = cal["event_name_1"].fillna(cal["event_name_2"])
    return cal


def load_dept_series(rng: np.random.Generator) -> np.ndarray:
    """Sample N_SERIES series and aggregate -> one dense dept-level daily series."""
    full = np.load(DATA / "sales_all.npy")
    keep = full.sum(axis=1) > 200
    full = full[keep]
    idx = rng.choice(len(full), size=min(N_SERIES, len(full)), replace=False)
    dept = full[idx].sum(axis=0).astype(float)
    return dept


# ---------- baselines & shapes ----------

def weekday_baseline(s: np.ndarray) -> np.ndarray:
    """Same-weekday trailing mean for every day (uses the 8 same-weekday values
    ending 7 days before the day, i.e. no same-window information)."""
    n = len(s)
    base = np.zeros(n)
    for wd in range(7):
        idx = np.arange(wd, n, 7)
        vals = s[idx]
        for j, i in enumerate(idx):
            lo = max(0, j - 8)
            hist = vals[lo:j]          # up to 8 previous same-weekday values
            if hist.size < 4:
                hist = s[max(0, i - 56):max(4, i - 7):7]
            base[i] = hist.mean() if hist.size else 0.0
    return base


def shape_at(s: np.ndarray, base: np.ndarray, pos: int) -> np.ndarray | None:
    """Event-window shape relative to the weekday baseline."""
    lo, hi = pos - HALF, pos + HALF + 1
    if lo < 0 or hi > len(s):
        return None
    b = base[lo:hi]
    if (b <= 0).any():
        return None
    return s[lo:hi] / b


def agg_wape(err: np.ndarray, actual: np.ndarray) -> float:
    return float(err.sum() / actual.sum())


# ---------- E2a ----------

def run_e2a(dept: np.ndarray, cal: pd.DataFrame) -> dict:
    base = weekday_baseline(dept)
    ev_days = np.where(cal["event"].notna().to_numpy())[0]

    # group occurrences by event type, keep types with enough occurrences
    by_event: dict[str, list[int]] = {}
    for d in ev_days:
        name = cal["event"].iat[d]
        by_event.setdefault(name, []).append(int(d))
    by_event = {k: sorted(v) for k, v in by_event.items() if len(v) >= MIN_OCC}
    print(f"event types with >={MIN_OCC} occurrences: {len(by_event)}")

    predictors = ("flat", "flat_bump", "ramp")
    err_acc = {p: 0.0 for p in predictors}
    act_acc = {p: 0.0 for p in predictors}
    windows = 0
    per_event: dict[str, dict] = {}

    for name, days in by_event.items():
        ev_err = {p: [] for p in predictors}
        ev_act = []
        for k, d in enumerate(days):
            lo, hi = d - HALF, d + HALF + 1
            if lo < 0 or hi > len(dept):
                continue
            actual = dept[lo:hi]
            b = base[lo:hi]
            if (b <= 0).any():
                continue

            # leave-one-occurrence-out shape from the OTHER occurrences
            others = [shape_at(dept, base, d2) for j, d2 in enumerate(days) if j != k]
            others = [c for c in others if c is not None]
            shape = np.mean(others, axis=0) if others else np.ones(WIN)

            # P0 flat: baseline only (no event knowledge)
            p0 = b.copy()
            # P1 flat bump: total observed uplift dumped on the event day
            uplift = actual.sum() - b.sum()
            p1 = b.copy()
            p1[HALF] += max(0.0, uplift)
            # P2 learned ramp
            p2 = b * shape

            ev_err["flat"].append(np.abs(p0 - actual).sum())
            ev_err["flat_bump"].append(np.abs(p1 - actual).sum())
            ev_err["ramp"].append(np.abs(p2 - actual).sum())
            ev_act.append(actual.sum())

        if not ev_act:
            continue
        act = np.sum(ev_act)
        per_event[name] = {
            "occurrences_tested": len(ev_act),
            "wape": {p: round(agg_wape(np.array(ev_err[p]), act), 4) for p in predictors},
        }
        for p in predictors:
            err_acc[p] += np.sum(ev_err[p])
            act_acc[p] += act
        windows += len(ev_act)

    overall = {p: round(err_acc[p] / act_acc[p], 4) for p in predictors}
    improvement = {
        "ramp_vs_flat_pct": round(100 * (overall["flat"] - overall["ramp"]) / overall["flat"], 2),
        "ramp_vs_flat_bump_pct": round(
            100 * (overall["flat_bump"] - overall["ramp"]) / overall["flat_bump"], 2),
    }
    return {
        "method": "leave-one-occurrence-out, day-of-week adjusted, dept-level dense series",
        "n_series_aggregated": N_SERIES,
        "event_types": sorted(per_event),
        "windows_tested": windows,
        "overall_wape": overall,
        "improvement_pct": improvement,
        "per_event_wape": per_event,
    }


# ---------- E2b ----------

def episodes(x: np.ndarray) -> list[tuple[int, int]]:
    """Sustained day-of-week z-score episodes: [(start, end), ...] end-exclusive."""
    n = len(x)
    flags = np.zeros(n, dtype=bool)
    for wd in range(7):
        idx = np.arange(56 + wd, n, 7)
        vals = x[idx]
        for j, i in enumerate(idx):
            hist = vals[max(0, j - 8):j]
            if hist.size < 4:
                continue
            mu, sd = hist.mean(), hist.std()
            if sd <= 1e-6:
                continue
            if abs((x[i] - mu) / sd) >= THRESH_Z:
                flags[i] = True
    out = []
    i = 0
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            if j - i >= SUSTAIN:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def run_e2b(dept: np.ndarray, cal: pd.DataFrame, rng: np.random.Generator) -> dict:
    ev = cal["event"].notna().to_numpy()
    n = len(dept)
    ev_days = set(np.where(ev)[0])

    def free_points() -> list[int]:
        return [d for d in range(int(n * 0.6), n - 60)
                if not any((d + off) in ev_days for off in range(-10, 11))]

    zone = free_points()
    if len(zone) < 50:
        return {"error": "no usable injection zone"}

    detected = missed = 0
    fp_days = 0
    # false positives on the untouched trace (whole clean test region)
    clean_eps = episodes(dept)
    fp_days = sum(e - s for s, e in clean_eps if s >= int(n * 0.6))

    for _ in range(120):
        s = dept.copy()
        start = int(rng.choice(zone))
        slen = int(rng.integers(5, 10))
        shocked = s.copy()
        shocked[start:start + slen] *= float(rng.uniform(2.2, 3.5))
        eps = episodes(shocked)
        if any(s0 <= start < e0 or (s0 <= start + slen and e0 >= start) for s0, e0 in eps):
            detected += 1
        else:
            missed += 1

    return {
        "series": "dept-level dense aggregate",
        "zone_rule": "no registered event within +-10 days",
        "injections": detected + missed,
        "detected": detected,
        "detection_rate": round(detected / max(1, detected + missed), 4),
        "fp_days_clean_last40pct": int(fp_days),
        "clean_days_last40pct": int(n * 0.4),
        "fp_days_per_100": round(fp_days / (n * 0.4) * 100, 3),
    }


def main() -> int:
    rng = np.random.default_rng(SEED)
    cal = load_calendar()
    dept = load_dept_series(rng)
    print(f"dept series: {len(dept)} days, total demand {dept.sum():.0f}", flush=True)

    e2a = run_e2a(dept, cal)
    print("E2a done", flush=True)
    e2b = run_e2b(dept, cal, rng)
    print("E2b done", flush=True)

    results = {
        "seed": SEED,
        "E2a_event_ramp": e2a,
        "E2b_novelty": e2b,
    }
    OUT.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
