"""Build the PIHPS price panel and the Eid al-Fitr event study.

Input : data/external/raw/com_*_YYYY.json (fetched by tools/pihps_fetch.py)
Output: data/external/pihps_harga.csv
        data/external/pihps_event_summary.json
"""
import csv
import glob
import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta

BASE_DIR = "/home/ubuntu/pasok/data/external"
RAW = os.path.join(BASE_DIR, "raw")
CSV_PATH = os.path.join(BASE_DIR, "pihps_harga.csv")
SUMMARY_PATH = os.path.join(BASE_DIR, "pihps_event_summary.json")

COMMODITIES = {
    "com_3": "Beras Medium",
    "com_10": "Telur Ayam",
    "com_17": "Minyak Goreng Curah",
    "com_18": "Minyak Goreng Kemasan",
    "com_20": "Gula Pasir",
}

LEBARAN = {
    2022: date(2022, 5, 2),
    2023: date(2023, 4, 22),
    2024: date(2024, 4, 10),
    2025: date(2025, 3, 31),
    2026: date(2026, 3, 20),
}

BASELINE_DAYS = 60      # median window: H-120 .. H-61
WINDOW_PRE = 60         # event window: H-60 .. H+30
WINDOW_POST = 30
THRESHOLD = 0.02        # rise = 2 percent above baseline median
MIN_RUN = 2             # consecutive days above threshold to count as onset


def parse_date(s):
    return datetime.strptime(s, "%d %b %y").date()


def load_panel():
    """province -> commodity -> date -> price (daily, weekends forward filled)."""
    panel = defaultdict(lambda: defaultdict(dict))
    for comcat, label in COMMODITIES.items():
        for path in sorted(glob.glob(os.path.join(RAW, f"{comcat}_*.json"))):
            with open(path, encoding="utf-8") as fh:
                rows = json.load(fh)
            for r in rows:
                price = r.get("price")
                if not price:
                    continue
                panel[r["name"]][label][parse_date(r["date"])] = float(price)
    return panel


def fill_days(series):
    """Reindex onto every calendar day, carrying the last quote up to 5 days."""
    if not series:
        return {}
    start, end = min(series), max(series)
    out = {}
    last = None
    gap = 0
    d = start
    while d <= end:
        if d in series:
            last = series[d]
            gap = 0
        else:
            gap += 1
        if last is not None and gap <= 5:
            out[d] = last
        d += timedelta(days=1)
    return out


def national_series(panel, label, min_coverage=10):
    """Median across provinces per calendar day (robust national level).

    Days where fewer than min_coverage provinces report are dropped: on
    national holidays only one or two provinces file, and the median of that
    sample is noise (2022-05-05 Telur Ayam would read 54,000 from Papua alone).
    """
    by_day = defaultdict(list)
    for prov, comms in panel.items():
        if label not in comms:
            continue
        for d, p in fill_days(comms[label]).items():
            by_day[d].append(p)
    out = {}
    for d, vals in by_day.items():
        if len(vals) < min_coverage:
            continue
        vals.sort()
        n = len(vals)
        out[d] = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return out


def despike(series, factor=1.25, side=5):
    """Drop one-day spikes that revert on both sides, then refill by carry."""
    keys = sorted(series)
    clean = dict(series)
    for i, d in enumerate(keys):
        before = [series[k] for k in keys[max(0, i - side):i]]
        after = [series[k] for k in keys[i + 1:i + 1 + side]]
        if len(before) < 3 or len(after) < 3:
            continue
        ref_before, ref_after = median(before), median(after)
        if series[d] > factor * ref_before and series[d] > factor * ref_after:
            del clean[d]
    return fill_days(clean)


def median(vals):
    v = sorted(vals)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def event_study(series, lebaran):
    """Return onset (days before Eid), peak offset, peak pct for one year."""
    base_vals = [series[lebaran + timedelta(days=-k)] for k in range(61, 121)
                 if lebaran + timedelta(days=-k) in series]
    if len(base_vals) < 30:
        return None
    baseline = median(base_vals)

    idx = {}
    for off in range(-WINDOW_PRE, WINDOW_POST + 1):
        d = lebaran + timedelta(days=off)
        if d in series:
            idx[off] = series[d] / baseline * 100.0

    # onset: first offset whose value and the next one both clear the threshold
    onset = None
    for off in range(-WINDOW_PRE, 1):
        if off in idx and off + 1 in idx and idx[off] >= 102 and idx[off + 1] >= 102:
            onset = -off
            break

    peak_off = max(idx, key=lambda k: (idx[k], -abs(k)))
    peak_pct = idx[peak_off] - 100.0
    pre_off = max((k for k in idx if k <= 0), key=lambda k: idx[k])

    return {
        "baseline_price": round(baseline, 2),
        "onset_days_before": onset,
        "peak_offset_days": peak_off,
        "peak_price": round(series[lebaran + timedelta(days=peak_off)], 2),
        "peak_pct": round(peak_pct, 2),
        "pre_peak_offset_days": pre_off,
        "pre_peak_pct": round(idx[pre_off] - 100.0, 2),
        "index": {str(k): round(v, 3) for k, v in idx.items()},
    }


def main():
    panel = load_panel()

    # ---------- CSV ----------
    rows = []
    for prov in sorted(panel):
        for label in COMMODITIES.values():
            for d, p in sorted(panel[prov].get(label, {}).items()):
                rows.append((d.isoformat(), prov, label, p))

    nat = {label: despike(national_series(panel, label)) for label in COMMODITIES.values()}
    for label, s in nat.items():
        for d, p in sorted(s.items()):
            rows.append((d.isoformat(), "Nasional (median provinsi)", label, round(p, 2)))

    rows.sort(key=lambda r: (r[0], r[2], r[1]))
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["tanggal", "provinsi", "komoditas", "harga"])
        w.writerows(rows)
    print("csv rows", len(rows), "bytes", os.path.getsize(CSV_PATH))

    # ---------- event study ----------
    summary = {
        "source": {
            "name": "PIHPS Nasional (Bank Indonesia)",
            "endpoint": "https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetChartKomoditas",
            "price_type": "Pasar Tradisional",
            "level": "provinsi, dirata-ratakan ke nasional dengan median",
            "unit": "IDR",
        },
        "method": {
            "event_dates": {str(k): v.isoformat() for k, v in LEBARAN.items()},
            "baseline": f"median of H-{BASELINE_DAYS + 60} .. H-{BASELINE_DAYS + 1} calendar days",
            "rise_threshold_pct": THRESHOLD * 100,
            "onset_rule": f"first day in H-{WINDOW_PRE}..H0 where price and the following day are both >= {100 + THRESHOLD * 100:.0f} of baseline",
            "peak_rule": f"max index inside H-{WINDOW_PRE} .. H+{WINDOW_POST}",
            "cleaning": [
                "national value = median across reporting provinces",
                "days with fewer than 10 reporting provinces dropped (national holidays)",
                "one-day spikes above 1.25x the surrounding 5-day medians dropped and carried forward",
                "calendar days without a quote carried forward for up to 5 days",
            ],
            "years": sorted(LEBARAN),
        },
        "commodities": {},
    }

    for label in COMMODITIES.values():
        series = nat[label]
        per_year = []
        for year, lb in LEBARAN.items():
            res = event_study(series, lb)
            if res is None:
                continue
            per_year.append({"year": year, "lebaran": lb.isoformat(), **res})
        onsets = [r["onset_days_before"] for r in per_year if r["onset_days_before"] is not None]
        summary["commodities"][label] = {
            "per_year": [{k: v for k, v in r.items() if k != "index"} for r in per_year],
            "average": {
                "onset_days_before": round(sum(onsets) / len(onsets), 1) if onsets else None,
                "onset_censored": bool(onsets) and min(onsets) >= WINDOW_PRE,
                "peak_offset_days": round(sum(r["peak_offset_days"] for r in per_year) / len(per_year), 1),
                "peak_pct": round(sum(r["peak_pct"] for r in per_year) / len(per_year), 2),
                "years_used": len(per_year),
            },
            "index_curve_avg": {
                str(off): round(sum(r["index"].get(str(off), 100.0) for r in per_year) / len(per_year), 3)
                for off in range(-WINDOW_PRE, WINDOW_POST + 1)
            },
        }

    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    print("summary bytes", os.path.getsize(SUMMARY_PATH))

    for label, c in summary["commodities"].items():
        a = c["average"]
        print(f"{label:26s} onset H-{a['onset_days_before']}  peak H{a['peak_offset_days']:+}  +{a['peak_pct']}%")


if __name__ == "__main__":
    main()
