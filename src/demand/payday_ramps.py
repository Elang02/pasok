"""Belajari faktor payday per SKU dari catatan penjualan dan tulis ke sku_ramps.csv.

Payday berulang tiap bulan (tanggal 25 sampai 28, serta 1 sampai 5), jadi ia tidak punya satu
tanggal puncak seperti kejadian kalender. Modelnya pun beda: faktor level hari, yaitu
(mean unit pada hari payday) / (mean unit pada hari bukan payday), satu angka per SKU.
SKU tanpa riwayat atau yang tidak merespons mendapat 1,0, bukan dipaksa angka global.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAMP_CSV = ROOT / "data" / "demand" / "sku_ramps.csv"


def main() -> int:
    s = pd.read_csv(ROOT / "data" / "catalog" / "sales.csv", parse_dates=["date"])
    s = s[(s.date >= "2023-01-02") & (s.date < "2026-04-01")].copy()
    hari = s.date.dt.day
    s["payday"] = ((hari >= 25) & (hari <= 28)) | (hari <= 5)

    on = s[s.payday].groupby("sku").units.mean()
    off = s[~s.payday].groupby("sku").units.mean()
    faktor = (on / off.replace(0, np.nan)).fillna(1.0).rename("faktor")

    ramps = pd.read_csv(RAMP_CSV)
    ramps = ramps[ramps.event != "Payday"].copy()
    rows = pd.DataFrame({
        "sku": faktor.index,
        "event": "Payday",
        "peak_mult": faktor.values.round(4),
        "days_to_peak": 0.0,
        "build_slope": 0.0,
        "decay_slope": 0.0,
        "occurrences": 39.0,
        "ramp_class": "recurring",
    })
    out = pd.concat([ramps, rows], ignore_index=True)
    out.to_csv(RAMP_CSV, index=False)
    q = rows.peak_mult
    print(f"Payday per SKU ditulis: {len(rows)} baris ke {RAMP_CSV}")
    print(f"faktor level hari: median {q.median():.3f} | p10 {q.quantile(.1):.3f} "
          f"| p90 {q.quantile(.9):.3f} | >= 1.30: {int((q >= 1.30).sum())} SKU | <= 1.02: {int((q <= 1.02).sum())} SKU")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
