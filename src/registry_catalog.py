#!/usr/bin/env python3
"""
Pasok - event-driver catalogue (Phase 7, plan 07-01)
====================================================

Proposal line 13 names the registry's intended contents: Imlek, Lebaran, Nyepi,
Christmas, THR weeks, payday cycles, principal promos. This script writes a single
honest table that says, for each named driver, where it actually lives in the build.

It does NOT touch data/demand/event_registry.csv. The Decision Agent reads that file
to build event windows; adding rows there would change the forecast overlay and the
orders. This is documentation, not tuning.

Output: data/demand/registry_catalog.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "demand"

# driver, kind, in_generator, in_registry, note   (verified against src/catalog/generate.py)
CATALOG = [
    ("Imlek", "shared_calendar", "yes", "yes",
     "generate.py build_events(): late Jan / mid Feb, 1 week, uplift 1.4-1.9"),
    ("Lebaran", "shared_calendar", "yes", "yes",
     "generate.py build_events(): ramadan_start + 29 days, 2 weeks, uplift 2.2-3.2"),
    ("Nyepi", "shared_calendar", "no", "no",
     "not modelled: Balinese Hindu holiday, low general-trade weight in Greater Jakarta"),
    ("Christmas", "shared_calendar", "yes", "yes",
     "generate.py build_events(): Dec 20, 2 weeks, uplift 1.5-2.1"),
    ("THR weeks", "payday_cycle", "yes", "no",
     "modelled as a Ramadan payday multiplier (generate.py line 83); not a registry row"),
    ("payday cycles", "payday_cycle", "yes", "no",
     "explicit cycle, demand rises after the 25th and the 1st (generate.py line 170)"),
    ("principal promos", "per_sku_random", "yes", "no",
     "per-SKU random promo bursts, 3-9 days, boost 1.3-2.0 (generate.py lines 181-185)"),
    ("Ramadan", "shared_calendar", "yes", "yes",
     "generate.py build_events(): 4-week window, uplift 1.6-2.4 (also the event the ramp fit ranks highest)"),
    ("NewYear", "shared_calendar", "yes", "yes",
     "generate.py build_events(): Dec 29, 1 week, uplift 1.3-1.7"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    registry = {r["event"] for r in csv.DictReader((OUT / "event_registry.csv").open())}

    # ---- per-year occurrence calendar (proposal line 13: "dates drift yearly") ----
    # One row per occurrence, straight from the distributor's own observed event table.
    # Occurrences are detected as contiguous date runs (a gap over 30 days starts a new
    # one), so a window that crosses New Year is not split or merged.
    per_event_dates: dict[str, list[tuple[str, float]]] = {}
    with (ROOT / "data" / "catalog" / "events.csv").open() as f:
        for r in csv.DictReader(f):
            per_event_dates.setdefault(r["event"], []).append((r["date"], float(r["factor"])))

    cal = []
    for event, pairs in per_event_dates.items():
        pairs.sort()
        run = [pairs[0]]
        runs = []
        for prev, cur in zip(pairs, pairs[1:]):
            gap = (dt.date.fromisoformat(cur[0]) - dt.date.fromisoformat(prev[0])).days
            if gap > 30:
                runs.append(run)
                run = []
            run.append(cur)
        runs.append(run)
        for run in runs:
            facs = [p[1] for p in run]
            cal.append({
                "event": event,
                "year": int(run[0][0][:4]),
                "start_date": run[0][0],
                "end_date": run[-1][0],
                "days": len(run),
                "peak_factor": round(max(facs), 4),
                "mean_factor": round(sum(facs) / len(facs), 4),
            })
    cal.sort(key=lambda r: (r["event"], r["start_date"]))

    cal_path = OUT / "event_calendar.csv"
    with cal_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["event", "year", "start_date", "end_date",
                                          "days", "peak_factor", "mean_factor"])
        w.writeheader()
        w.writerows(cal)

    per_event_years = {}
    for r in cal:
        per_event_years.setdefault(r["event"], []).append(r["year"])

    years_by_event = {e: sorted(y) for e, y in per_event_years.items()}
    lunar = {"Ramadan", "Lebaran", "Imlek"}
    drift = {}
    for e, ys in years_by_event.items():
        first = next(r for r in cal if r["event"] == e and r["year"] == ys[0])
        last = next(r for r in cal if r["event"] == e and r["year"] == ys[-1])
        f_md, l_md = first["start_date"][5:], last["start_date"][5:]
        drift[e] = {"first_year": ys[0], "first_date": first["start_date"],
                    "last_year": ys[-1], "last_date": last["start_date"],
                    "shifts_in_calendar": f_md != l_md,
                    "cadence": "lunar ~354d" if e in lunar else "fixed 365d"}

    rows = []
    for driver, kind, in_gen, in_reg, note in CATALOG:
        # trust the registry file over the hard-coded claim
        actual_in_reg = "yes" if (driver in registry) else in_reg
        rows.append({
            "driver": driver, "kind": kind, "in_generator": in_gen,
            "in_registry": actual_in_reg, "note": note,
        })

    path = OUT / "registry_catalog.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["driver", "kind", "in_generator", "in_registry", "note"])
        w.writeheader()
        w.writerows(rows)

    named_in_proposal = ["Imlek", "Lebaran", "Nyepi", "Christmas", "THR weeks",
                         "payday cycles", "principal promos"]
    covered = [r for r in rows if r["driver"] in named_in_proposal]
    summary = {
        "drivers_total": len(rows),
        "named_in_proposal_line_13": named_in_proposal,
        "in_registry": sum(1 for r in covered if r["in_registry"] == "yes"),
        "modelled_but_not_a_registry_row": [r["driver"] for r in covered
                                            if r["in_generator"] == "yes" and r["in_registry"] == "no"],
        "not_modelled": [r["driver"] for r in covered if r["in_generator"] == "no"],
        "registry_rows_unchanged": len(registry),
        "calendar_artefact": "data/demand/event_calendar.csv",
        "calendar_occurrences": len(cal),
        "calendar_years_by_event": years_by_event,
        "drift": drift,
    }
    (OUT / "registry_catalog_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print(f"\nwritten: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
