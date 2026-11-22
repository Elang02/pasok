"""Rebuild data/prep from data/catalog/sales.csv.

The prep parquet is a cache: daily and weekly sales per SKU, wide. Every agent
reads it and nothing writes it, so when the sales window grows the cache goes
stale silently and the loop keeps answering from the old window. That is what
happened here: catalog ran to 2026-10-11 while prep stopped at 2025-12-28, so
the snapshot date was still December even after a full chain run.

Run after src/catalog/generate.py:

    .venv/bin/python tools/build_prep.py
"""

from __future__ import annotations

import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
CAT = ROOT / "data" / "catalog"
PREP = ROOT / "data" / "prep"


def main() -> int:
    src = CAT / "sales.csv"
    if not src.exists():
        print(f"no sales.csv at {src}; run src/catalog/generate.py first")
        return 1

    # 99M rows would not fit; read in chunks and fold each into a wide frame
    parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(src, chunksize=2_000_000, dtype={"units": "int32"}):
        chunk["date"] = pd.to_datetime(chunk["date"])
        parts.append(chunk.groupby(["date", "sku"], observed=True)["units"].sum().reset_index())

    long = pd.concat(parts, ignore_index=True)
    long = long.groupby(["date", "sku"], observed=True)["units"].sum().reset_index()

    PREP.mkdir(parents=True, exist_ok=True)

    daily = long.pivot(index="date", columns="sku", values="units").fillna(0).astype("int32")
    daily.index.name = "date"
    daily.to_parquet(PREP / "daily_by_sku.parquet")
    print(f"daily_by_sku.parquet  {daily.shape[0]} days x {daily.shape[1]} SKUs "
          f"({daily.index.min().date()} .. {daily.index.max().date()})")

    weekly = daily.resample("W-SUN").sum()
    weekly.index.name = "date"
    weekly.to_parquet(PREP / "weekly_by_sku.parquet")
    print(f"weekly_by_sku.parquet {weekly.shape[0]} weeks x {weekly.shape[1]} SKUs "
          f"({weekly.index.min().date()} .. {weekly.index.max().date()})")

    meta = CAT / "meta.json"
    if meta.exists():
        want = pd.read_json(meta, typ="series")["date_range"][1]
        got = str(daily.index.max().date())
        print(f"catalog ends {want}, prep ends {got} -> "
              f"{'match' if str(want) == got else 'MISMATCH'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
