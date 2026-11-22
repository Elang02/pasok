"""Tambahkan empat event baru ke kalender permintaan.

Tanggal diverifikasi dari sumber resmi (Kemenag dan SKB 3 Menteri): Valentine tetap 14
Februari, Kemerdekaan 17 Agustus, Idul Adha 27 Mei 2026, Maulid Nabi 25 Agustus 2026.

Tiga hal yang sengaja dibedakan dari lima event lama:
1. Pengalinya kecil, 1,00 sampai 1,22. Lima event besar (Lebaran 2,5x, Ramadan 1,9x, Natal
   1,7x) pengalinya diukur dari catatan penjualan; empat ini tidak ada di catatan, jadi
   pengalinya ASUMSI dari musiman FMCG Indonesia, dan registry menandainya sebagai assumed.
2. Kepekaan per SKU tidak dikarang: diambil dari pola event yang sudah ada di SKU itu, jadi
   SKU yang biasanya naik lebih tinggi saat Lebaran juga naik lebih tinggi saat Valentine,
   dan sebaliknya.
3. Hari puncaknya diberi jarak bangun dan surut sendiri: Idul Adha naik dua minggu sebelum,
   Valentine naik empat hari sebelum.

Jalan: .venv/bin/python tools/add_secondary_events.py
"""
from __future__ import annotations

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMAND = ROOT / "data" / "demand"

NEW = {
    "Valentine": {"first": "2023-02-14", "last": "2026-02-14", "occ": 4,
                  "base": {"biscuits": 1.22, "beverages": 1.06, "personal_care": 1.05,
                           "instant_noodles": 1.00, "household": 1.00},
                  "peak_days": 0, "build": 5, "decay": 4},
    "IdulAdha": {"first": "2023-06-29", "last": "2026-05-27", "occ": 4,
                 "base": {"beverages": 1.15, "household": 1.12, "biscuits": 1.10,
                          "instant_noodles": 1.06, "personal_care": 1.03},
                 "peak_days": 0, "build": 14, "decay": 7},
    "Independence": {"first": "2023-08-17", "last": "2026-08-17", "occ": 4,
                     "base": {"beverages": 1.20, "biscuits": 1.12, "instant_noodles": 1.05,
                              "household": 1.04, "personal_care": 1.02},
                     "peak_days": 0, "build": 7, "decay": 7},
    "Maulid": {"first": "2023-09-28", "last": "2026-08-25", "occ": 4,
               "base": {"beverages": 1.08, "biscuits": 1.06, "instant_noodles": 1.03,
                        "personal_care": 1.02, "household": 1.00},
               "peak_days": 0, "build": 5, "decay": 5},
}
NOTE = "assumed from Indonesian seasonality, not measured"


def main() -> int:
    cat = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")[["sku", "category"]]
    ramps = pd.read_csv(DEMAND / "sku_ramps.csv")
    reg = pd.read_csv(DEMAND / "event_registry.csv")
    if "Valentine" in set(ramps.event):
        print("event tambahan sudah ada; tidak dijalankan dua kali")
        return 0
    reg["source"] = reg.get("source", "learned from the record")
    reg["source"] = reg["source"].fillna("learned from the record")

    sens = ramps.groupby("sku")["peak_mult"].mean()
    sens = (sens / sens.mean()).clip(0.85, 1.15).to_dict()

    rows = []
    for ev, cfg in NEW.items():
        for r in cat.itertuples(index=False):
            mult = cfg["base"].get(r.category, 1.0) * sens.get(r.sku, 1.0)
            rows.append({"sku": r.sku, "event": ev,
                         "peak_mult": 1.0 if abs(mult - 1.0) < 0.03 else round(mult, 2),
                         "days_to_peak": cfg["peak_days"], "build_slope": cfg["build"],
                         "decay_slope": cfg["decay"]})
    newr = pd.DataFrame(rows)
    pd.concat([ramps, newr], ignore_index=True).to_csv(DEMAND / "sku_ramps.csv", index=False)

    add = pd.DataFrame([{"event": e, "first_seen": c["first"], "last_seen": c["last"],
                         "occurrences": c["occ"],
                         "mean_factor": round(float(newr[newr.event == e].peak_mult.mean()), 4),
                         "median_factor": round(float(newr[newr.event == e].peak_mult.median()), 4),
                         "source": NOTE} for e, c in NEW.items()])
    out = pd.concat([reg, add], ignore_index=True)
    out.to_csv(DEMAND / "event_registry.csv", index=False)

    print(f"registry: {len(out)} event | ramps: {len(ramps) + len(newr)} baris")
    print(add[["event", "last_seen", "mean_factor"]].to_string(index=False))
    print("yang diukur dari catatan:", int((out.source != NOTE).sum()),
          "| yang diasumsikan:", int((out.source == NOTE).sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
