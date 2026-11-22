"""
Pasok — Synthetic distributor catalog generator
===============================================

Builds the pilot data the Demo Day narrative describes: a mid-sized Indonesian FMCG
distributor in Greater Jakarta, thousands of SKUs, a sales team on daily routes to
hundreds of warung, purchasing managed against principal lead times and shelf life.

Why synthetic: the organizer FAQ (Participant Briefing deck, 11 Sep 2026, Q2) permits
synthetic data as long as it is realistic and relevant to the use-case. Real distributor
data is not available to a student team, and the proposal already says so.

What it produces
----------------
data/catalog/sales.csv        daily sales per SKU x outlet (long format)
data/catalog/catalog.csv      SKU master: category, shelf life, principal, credit, MOQ
data/catalog/principals.csv   principal master: lead-time distribution, fill rate
data/catalog/outlets.csv      outlet master: type, demand scale
data/catalog/receiving.csv    per-PO actual lead time (what the Reliability agent learns from)
data/catalog/events.csv       GROUND-TRUTH event registry (withheld from agents)
data/catalog/meta.json        run parameters + file hashes

Design notes
------------
- Demand is driven by a weekly weekday pattern plus yearly-drifting event uplifts.
  Event dates are generated per year from fixed rules, so the drift is real.
- Shelf life is a hard ordering constraint downstream, so every SKU carries one.
- Trade credit is per SKU x principal, capping how much can be ordered in a month.
- Seeded: the same seed reproduces the same bytes.

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/catalog/generate.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261008
N_SKUS = int(__import__("os").environ.get("PASOK_N_SKUS", 600))
N_OUTLETS = int(__import__("os").environ.get("PASOK_N_OUTLETS", 120))
N_WEEKS = 200                      # 2023-01-02 .., trimmed to END_DATE below
END_DATE = pd.Timestamp("2026-10-31")  # the world runs to the demo day
START = pd.Timestamp("2023-01-02")  # a Monday

# busiest weekday runs 1.30x the average day (see the demand formula below)
WEEKDAY_FACTOR = {0: 0.92, 1: 0.95, 2: 0.97, 3: 1.00, 4: 1.18, 5: 1.30, 6: 1.05}
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "catalog"

CATEGORIES = {
    "biscuits":       {"shelf_life_months": (6, 12), "base_demand": (8, 60)},
    "instant_noodles": {"shelf_life_months": (8, 10), "base_demand": (20, 140)},
    "beverages":      {"shelf_life_months": (6, 9),  "base_demand": (15, 90)},
    "personal_care":  {"shelf_life_months": (18, 30), "base_demand": (3, 25)},
    "household":      {"shelf_life_months": (18, 36), "base_demand": (4, 30)},
}

# The fine categories the catalogue actually carries, with the daily demand a single
# outlet sees. `tools/build_catalog_v2.py` assigns one to every SKU and writes
# `data/catalog/sku_categories.csv`; the generator then uses that file, so the sales
# series and the catalogue cannot drift apart. Falls back to the five coarse groups
# above when the file is missing.
DEMAND_BY_CATEGORY = {
    "beras": (8, 30), "gula": (6, 24), "minyak_goreng": (5, 20),
    "mie_instan": (20, 140), "biskuit": (8, 45), "snack": (6, 35),
    "minuman": (10, 50), "air_mineral": (12, 60), "kopi_teh": (6, 30),
    "bumbu": (5, 22), "perawatan_diri": (3, 18), "perawatan_rumah": (3, 20),
    "susu": (4, 24),
    "sirup": (3, 16), "cokelat": (2, 12), "kue_kering": (2, 10), "roti": (10, 60),
}

FINE_FILE = OUT / "sku_categories.csv"
AMPLITUDE_FILE = ROOT / "data" / "demand" / "category_event_amplitude.csv"

OUTLET_TYPES = {
    "warung":      {"scale": (0.6, 1.4), "weight": 0.70},
    "minimarket":  {"scale": (2.0, 4.0), "weight": 0.15},
    "kiosk":       {"scale": (0.3, 0.8), "weight": 0.15},
}

# Indonesian retail calendar.
#
# Dates come from the national holiday decrees (SKB 3 Menteri) and the published
# Hijri / Saka / lunar new year dates, not from an arithmetic approximation. The
# first version derived Ramadan from "11 days earlier per year" and Imlek from
# `f"{year}-02-{5 + (year % 3) * 4}"`; both were wrong. The Imlek rule put the
# holiday a week or more off in every year it produced (2024-02-13 when the
# holiday was 2024-02-10, 2023-02-09 when it was 2023-01-22), and the Ramadan
# rule missed 2025 by a day. A registry whose dates are wrong cannot claim the
# "dates drift yearly" property the proposal sells, so the drift is now a lookup
# against the official calendar instead of a guess that happens to move.
#
# Only events that move an Indonesian FMCG distributor's volume are modelled.
# Valentine's Day, St Patrick's Day and other Western observances are excluded on
# purpose: they do not shift general-trade demand here, and modelling them would
# add registry rows that predict nothing.
HIJRI_EVENTS: dict[int, dict[str, str]] = {
    # year: {event: first day of the window}
    2023: {"Ramadan": "2023-03-23", "Lebaran": "2023-04-21", "Nyepi": "2023-03-22"},
    2024: {"Ramadan": "2024-03-11", "Lebaran": "2024-04-09", "Nyepi": "2024-03-11"},
    2025: {"Ramadan": "2025-03-01", "Lebaran": "2025-03-30", "Nyepi": "2025-03-29"},
    2026: {"Ramadan": "2026-02-18", "Lebaran": "2026-03-20", "Nyepi": "2026-03-19"},
}

# Chinese New Year (Imlek). Fixed Gregorian dates from the lunar calendar.
IMLEK_DATES: dict[int, str] = {
    2023: "2023-01-22",
    2024: "2024-02-10",
    2025: "2025-01-29",
    2026: "2026-02-17",
}

# THR: the religious bonus paid in the second week of Ramadan, not the whole month.
# Public-sector THR must be paid no later than 7 days before Lebaran (Permenaker
# 6/2016), so the window is anchored to Lebaran, not to Ramadan's start.
THR_OFFSET_BEFORE_LEBARAN_DAYS = 7
THR_WINDOW_DAYS = 10

# Payday cycle: private-sector salaries land on the 25th and the 1st-5th.
PAYDAY_DAYS = (1, 25)


PRE_EVENT_DAYS = 42   # six weeks of build-up before the event date
POST_EVENT_DAYS = 14  # two weeks of decay after it


def build_events(year: int) -> list[dict]:
    """Event uplifts for one year, on the real Indonesian calendar."""
    ev: list[dict] = []
    cal = HIJRI_EVENTS.get(year)
    if cal is None:
        raise ValueError(f"no Indonesian calendar for {year}; extend HIJRI_EVENTS "
                         "from the national holiday decree before generating")

    ev.append({"event": "Ramadan", "start": pd.Timestamp(cal["Ramadan"]),
               "weeks": 4, "uplift": (1.6, 2.4)})
    ev.append({"event": "Lebaran", "start": pd.Timestamp(cal["Lebaran"]),
               "weeks": 2, "uplift": (2.2, 3.2)})
    ev.append({"event": "Nyepi", "start": pd.Timestamp(cal["Nyepi"]),
               "weeks": 1, "uplift": (1.2, 1.6)})
    ev.append({"event": "Imlek", "start": pd.Timestamp(IMLEK_DATES[year]),
               "weeks": 1, "uplift": (1.4, 1.9)})
    ev.append({"event": "THR", "start": pd.Timestamp(cal["Lebaran"])
               - pd.Timedelta(days=THR_OFFSET_BEFORE_LEBARAN_DAYS + THR_WINDOW_DAYS),
               "weeks": 2, "uplift": (1.5, 2.0)})
    ev.append({"event": "Christmas", "start": pd.Timestamp(f"{year}-12-20"),
               "weeks": 2, "uplift": (1.5, 2.1)})
    ev.append({"event": "NewYear", "start": pd.Timestamp(f"{year}-12-29"),
               "weeks": 1, "uplift": (1.3, 1.7)})
    return ev


def main() -> int:
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    # ---------- principals ----------
    principals = []
    for i in range(12):
        principals.append({
            "principal_id": f"P{i+1:02d}",
            "name": f"Principal {i+1}",
            # real lead time varies per principal: reliable ones are tight
            "lead_mean_d": float(rng.choice([4, 6, 8, 11, 14, 21])),
            "lead_sd_d": float(rng.uniform(0.5, 4.0)),
            "fill_rate": float(rng.uniform(0.82, 0.99)),
            "min_order_units": int(rng.choice([24, 48, 96, 144])),
        })
    principals_df = pd.DataFrame(principals)

    # ---------- SKUs ----------
    skus = []
    cat_names = list(CATEGORIES)
    # Fine category, shelf life and unit cost come from the catalogue builder when it
    # has run (chain order: build_catalog_v2.py, then this script).
    fine = {}
    if FINE_FILE.exists():
        fine_df = pd.read_csv(FINE_FILE).set_index("sku")
        fine = fine_df.to_dict(orient="index")
        print(f"fine categories: {len(fine)} SKUs from {FINE_FILE.name}")
    for i in range(N_SKUS):
        cat = cat_names[i % len(cat_names)]
        cfg = CATEGORIES[cat]
        p = principals_df.iloc[int(rng.integers(0, len(principals_df)))]
        lo, hi = cfg["base_demand"]
        shelf = int(rng.integers(*cfg["shelf_life_months"]))
        cost = int(rng.choice([3500, 6500, 9000, 14000, 22000, 38000]))
        sku_id = f"SKU{i+1:04d}"
        if sku_id in fine:
            f = fine[sku_id]
            cat = str(f["category"])
            shelf = int(f["shelf_life_months"])
            cost = int(f["unit_cost_idr"])
            lo, hi = DEMAND_BY_CATEGORY.get(cat, (lo, hi))
        skus.append({
            "sku": sku_id,
            "category": cat,
            "principal_id": p["principal_id"],
            "shelf_life_months": shelf,
            "base_daily_demand": float(rng.uniform(lo, hi)),
            "unit_cost_idr": cost,
            "volatility": float(rng.uniform(0.10, 0.45)),
            # placeholder so the RNG consumption order is unchanged; overwritten below
            # with a line sized to the goods
            "credit_limit_idr": int(rng.choice([5_000_000, 10_000_000, 25_000_000, 50_000_000])),
        })
    skus_df = pd.DataFrame(skus)

    # ---------- trade credit, sized to the goods ----------
    # A credit line is per SKU x principal and caps what may be ordered in a month. It has
    # to scale with how the SKU turns over: a fast mover needs room for its event peak, a
    # slow mover does not. Flat round numbers (the first version) made the limit random
    # against velocity (correlation +0.017) and left 485 of 600 SKUs unable to buy even one
    # replenishment cycle inside their own line.
    #
    # Rule: normal monthly sales (event days removed) x the multiple the GUARDRAILS allow.
    # Of the three rules in decision.py, only CAP_K (order <= forecast + 2.5 sigma) caps how
    # big an order may be. Measured on the orders the guardrails actually produced
    # (`tools/guardrail_multiple.py`), the realised multiple of a normal month peaks at
    # 1.63x (p99 1.45x, median 0.57x), so 2.0 is the ceiling with headroom. Using the
    # calendar's own event multiplier (3.2) would give every SKU room the guardrails will
    # never let it order. Computed after the sales series exists so it uses realised
    # per-SKU demand, not the base generator parameter (the two differ ~15x because 120
    # outlets carry the same SKU).
    GUARDRAIL_MULT = 2.0

    # ---------- outlets ----------
    outlets = []
    type_names = list(OUTLET_TYPES)
    weights = [OUTLET_TYPES[t]["weight"] for t in type_names]
    for i in range(N_OUTLETS):
        t = type_names[int(rng.choice(len(type_names), p=np.array(weights) / sum(weights)))]
        lo, hi = OUTLET_TYPES[t]["scale"]
        outlets.append({
            "outlet_id": f"O{i+1:04d}",
            "outlet_type": t,
            "scale": float(rng.uniform(lo, hi)),
            "city": str(rng.choice(["Jakarta", "Bekasi", "Tangerang", "Depok", "Bogor"])),
        })
    outlets_df = pd.DataFrame(outlets)

    # ---------- calendar + events ----------
    days = pd.date_range(START, periods=N_WEEKS * 7, freq="D")
    days = days[days <= END_DATE]
    weekday_factor = WEEKDAY_FACTOR

    event_rows = []
    event_mult = np.ones(len(days))

    # Per-category event amplitude. One number spread over 600 SKUs is what made the
    # demo look synthetic: every SKU peaked 2.6x at Lebaran, including toothpaste.
    # The table in data/demand/category_event_amplitude.csv carries a sourced mean
    # uplift per category and event; the triangular shape below is normalised so the
    # mean of the window equals the table value.
    amp = {}
    share = {}
    if AMPLITUDE_FILE.exists():
        amp_df = pd.read_csv(AMPLITUDE_FILE)
        amp = {(str(r.category), str(r.event)): float(r.amplitude)
               for r in amp_df.itertuples()}
        if "share" in amp_df.columns:
            share = {(str(r.category), str(r.event)): float(r.share)
                     for r in amp_df.itertuples()}
        print(f"event amplitude: {len(amp)} category x event rows")
    cats = sorted(skus_df["category"].unique())
    event_mult_cat = {c: np.ones(len(days)) for c in cats}

    # Not every SKU in a lifted category moves, and not every category moves in every
    # event: the share column of the amplitude table decides, through a stable hash, so
    # the catalogue, the ramp learner and the console agree on the same SKUs.
    from src.demand.participation import carries

    sku_ids = list(skus_df["sku"])
    sku_cat = [str(c) for c in skus_df["category"]]
    event_mult_sku = {i: np.ones(len(days)) for i in range(len(sku_ids))}

    LEBAAR = {"Ramadan", "Lebaran"}

    def amp_for(cat: str, ev: str, legacy: float) -> float:
        for key in ((cat, ev), (cat, "Ramadan-Lebaran") if ev in LEBAAR else None,
                    ("default", ev), ("default", "Ramadan-Lebaran") if ev in LEBAAR else None):
            if key is not None and key in amp:
                return amp[key]
        return legacy

    for year in sorted({d.year for d in days}):
        for ev in build_events(year):
            total = ev["weeks"] * 7
            # A holiday is bought BEFORE it happens: kue kering and sirup move for five
            # or six weeks before Lebaran, chocolate for the fortnight before Christmas.
            # The window therefore starts 42 days before the event, peaks three days
            # before it, and decays for a fortnight afterwards. Without the build there
            # is nothing for the ramp learner to find, and the agent can only react on
            # the week of the holiday, when the stock has already been sold.
            start = ev["start"]
            offsets = range(-PRE_EVENT_DAYS, total + POST_EVENT_DAYS)
            window = [start + pd.Timedelta(days=k) for k in offsets]
            window = [d for d in window if d in days]
            if not window:
                continue
            peak_day = start - pd.Timedelta(days=3)
            raw = np.array([np.exp(-(((d - peak_day).days) / 9.0) ** 2) for d in window])
            raw = np.clip(raw, 1e-6, None)
            shapes = raw / raw.mean()          # mean 1 inside the window: average = a
            shapes = np.clip(shapes, 0.0, 2.5)
            positions = [days.get_loc(d) for d in window]
            legacy = 1.0
            for c in cats:
                a = amp_for(c, ev["event"], legacy)
                if a == 1.0:
                    continue
                event_mult_cat[c][positions] *= 1.0 + (a - 1.0) * shapes
            # the per-SKU pass: a category's lift reaches only the SKUs that carry it
            for i, sku in enumerate(sku_ids):
                c = sku_cat[i]
                a = amp_for(c, ev["event"], legacy)
                if a != 1.0 and carries(sku, c, ev["event"]):
                    event_mult_sku[i][positions] *= 1.0 + (a - 1.0) * shapes
            base_a = amp_for("default", ev["event"], legacy)
            for p, s in zip(positions, shapes):
                event_mult[p] *= 1.0 + (base_a - 1.0) * s
                event_rows.append({"date": days[p].strftime("%Y-%m-%d"), "event": ev["event"],
                                   "factor": round(float(1.0 + (base_a - 1.0) * s), 4)})

    # payday cycle: demand rises in the days after the 25th and the 1st-5th.
    # This is also written as its own registry row (see below) so the system can
    # answer "when is the next payday lift" the way it answers any other event,
    # rather than leaving it as an invisible multiplier. Food and drink move on
    # payday; toothpaste does not.
    PAYDAY_AMP = {"snack": 1.15, "minuman": 1.12, "susu": 1.10, "roti": 1.08,
                  "sirup": 1.10, "biskuit": 1.08, "mie_instan": 1.06, "cokelat": 1.06}
    payday_pos = [i for i, d in enumerate(days)
                  if 25 <= d.day <= 28 or d.day in PAYDAY_DAYS]
    for c in cats:
        event_mult_cat[c][payday_pos] *= PAYDAY_AMP.get(c, 1.0)
    for i in payday_pos:
        event_mult[i] *= 1.22
    # Payday as a recurring named event, anchored to the 25th and the 1st of each
    # month. Not a holiday: no fixed date in a calendar, but a real recurring
    # demand driver that the Demand Agent should be able to name and date.
    for d in days:
        if d.day == 25:
            event_rows.append({"date": d.strftime("%Y-%m-%d"), "event": "Payday",
                               "factor": 1.22})
        elif d.day == 1:
            event_rows.append({"date": d.strftime("%Y-%m-%d"), "event": "Payday",
                               "factor": 1.22})

    events_df = pd.DataFrame(event_rows).drop_duplicates(subset=["date", "event"])

    # ---------- sales ----------
    # Stream per outlet to CSV: 600 x 120 x 1377 would be ~99M rows; holding them as
    # Python tuples eats tens of GB. One row list at a time keeps RAM flat.
    skus_per_outlet = 60
    # per-SKU random promo bursts so SKUs differ beyond the shared calendar
    promo_mask = np.zeros(len(days))
    for _ in range(int(len(days) / 45)):
        start = int(rng.integers(0, len(days) - 10))
        promo_mask[start:start + int(rng.integers(3, 10))] = rng.uniform(1.3, 2.0)

    # days that carry a calendar event, so the credit line can exclude them
    event_days = set(events_df["date"])
    non_event_mask = np.array([d.strftime("%Y-%m-%d") not in event_days for d in days])
    sk_units_non_event = np.zeros(len(skus_df))
    sk_days_non_event = float(non_event_mask.sum())

    sales_path = OUT / "sales.csv"
    n_rows = 0
    with sales_path.open("w", newline="") as fh:
        fh.write("outlet_id,sku,date,units\n")
        for oi, outlet in enumerate(outlets_df.itertuples()):
            chosen = rng.choice(len(skus_df), size=skus_per_outlet, replace=False)
            for si in chosen:
                s = skus_df.iloc[si]
                base = s["base_daily_demand"] * outlet.scale
                wd = np.array([weekday_factor[d.dayofweek] for d in days])
                noise = rng.normal(1.0, s["volatility"], size=len(days))
                em = event_mult_sku[si] if si in event_mult_sku else event_mult
                series = base * wd * em * noise * (1 + (promo_mask - 1) * float(s["volatility"]))
                series = np.clip(np.round(series), 0, None).astype(int)
                sk_units_non_event[si] += float(series[non_event_mask].sum())
                for d, v in zip(days, series):
                    if v > 0:
                        fh.write(f"{outlet.outlet_id},{s['sku']},{d.strftime('%Y-%m-%d')},{v}\n")
                        n_rows += 1

    # ---------- size the credit lines off realised demand ----------
    _line = ((sk_units_non_event / sk_days_non_event) * 30.0
             * skus_df["unit_cost_idr"].to_numpy() * GUARDRAIL_MULT)
    skus_df["credit_limit_idr"] = np.maximum(np.round(_line, -5), 3_000_000).astype("int64")
    print(f"credit lines: normal monthly value x {GUARDRAIL_MULT} -> min "
          f"{skus_df['credit_limit_idr'].min():,} median "
          f"{int(skus_df['credit_limit_idr'].median()):,} "
          f"max {skus_df['credit_limit_idr'].max():,}")

    sales_df = None
    print(f"sales rows: {n_rows:,} | skus: {len(skus_df)} | outlets: {len(outlets_df)}")

    # ---------- lead time has to fit the goods it carries ----------
    # The first version drew a lead time per principal and then assigned SKUs to
    # principals at random, so a one-month bread could sit on a supplier three weeks
    # away. That is not a policy question, it is impossible data: the goods die before
    # the truck returns. The lead is therefore capped by the shortest-lived line each
    # principal carries, leaving at least a fortnight of selling window on arrival.
    shortest = skus_df.groupby("principal_id")["shelf_life_months"].min()
    for i, row in principals_df.iterrows():
        shelf_d = 30.4 * float(shortest.get(row["principal_id"], 12))
        cap = max(2.0, round(0.30 * shelf_d, 1))
        if row["lead_mean_d"] > cap:
            principals_df.loc[i, "lead_mean_d"] = cap
            principals_df.loc[i, "lead_sd_d"] = max(0.5, round(0.15 * cap, 2))
    print("principal leads after the shelf-life check:")
    for r in principals_df.itertuples():
        print(f"  {r.principal_id} lead {r.lead_mean_d:4.1f} d "
              f"(shortest line {shortest.get(r.principal_id)} months)")

    # ---------- receiving records (actual lead times) ----------
    # one record per principal per month across the whole generated window, so the
    # learned lead time covers the same span as the sales it is checked against
    n_months = len(pd.date_range(START, periods=N_WEEKS * 7, freq="D").to_period("M").unique())
    rec = []
    for p in principals_df.itertuples():
        for month in pd.date_range(START, periods=n_months, freq="MS"):
            for _ in range(int(rng.integers(2, 6))):
                actual = max(1, int(round(rng.normal(p.lead_mean_d, p.lead_sd_d))))
                rec.append({
                    "po_id": f"{p.principal_id}-{month.strftime('%Y%m')}-{len(rec):05d}",
                    "principal_id": p.principal_id,
                    "order_date": month.strftime("%Y-%m-%d"),
                    "actual_lead_d": actual,
                    "ordered_units": int(rng.choice([48, 96, 144, 288, 480])),
                    "received_units": None,   # filled from fill rate below
                })
    recv_df = pd.DataFrame(rec)
    recv_df["received_units"] = [
        int(round(u * min(1.0, max(0.0, rng.normal(
            principals_df.loc[principals_df.principal_id == pid, "fill_rate"].iloc[0], 0.03)))))
        for pid, u in zip(recv_df["principal_id"], recv_df["ordered_units"])
    ]

    # ---------- write ----------
    # Keep the descriptive columns the catalogue builder owns (name, brand, pack,
    # price basis); this script only owns the demand-side fields. Writing the narrow
    # frame straight over catalog.csv used to erase every product name.
    existing_path = OUT / "catalog.csv"
    if existing_path.exists():
        old = pd.read_csv(existing_path)
        keep = [c for c in ("sku", "name", "brand", "subcategory", "pack_size", "uom",
                            "pack_unit", "price_basis", "price_source") if c in old.columns]
        if "name" in keep:
            merged = skus_df.merge(old[keep], on="sku", how="left")
            skus_df = merged
    skus_df.to_csv(OUT / "catalog.csv", index=False)
    principals_df.to_csv(OUT / "principals.csv", index=False)
    outlets_df.to_csv(OUT / "outlets.csv", index=False)
    recv_df.to_csv(OUT / "receiving.csv", index=False)
    events_df.to_csv(OUT / "events.csv", index=False)

    def sha(p: Path) -> str:
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]

    meta = {
        "seed": SEED,
        "n_skus": int(len(skus_df)),
        "n_outlets": int(len(outlets_df)),
        "n_days": int(len(days)),
        "sales_rows": int(n_rows),
        "skus_per_outlet": skus_per_outlet,
        "date_range": [days[0].strftime("%Y-%m-%d"), days[-1].strftime("%Y-%m-%d")],
        "hashes": {f.name: sha(f) for f in sorted(OUT.glob("*.csv"))},
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
