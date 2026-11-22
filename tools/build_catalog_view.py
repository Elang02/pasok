#!/usr/bin/env python
"""Build the human catalogue: names, sell prices, packs, and the event trend.

The pipeline catalogue carries cost, shelf life and volatility but no product
attributes of its own (its ``product_form_basis`` column says so). This script
adds the layer a buyer actually reads, without touching the pipeline catalogue:

    sku, name, category, pack, principal_id, unit_cost_idr, sell_price_idr,
    margin_pct, shelf_life_months, base_daily_demand, yoy_growth_pct,
    top_event, peak_mult, days_to_peak, ramp_class

Everything is derived from artefacts that already exist:

    data/catalog/catalog.csv        cost, shelf life, principal, product form
    data/demand/sku_ramps.csv       per-SKU per-event peak and days to peak
    data/catalog/sales.csv          unit sales, used for the year-on-year trend

Names are generated deterministically from the SKU (pseudo-brands, so the file
never implies these are real products), and the sell price is derived from cost
with a category margin band, so the catalogue is consistent rather than typed.

    .venv/bin/python tools/build_catalog_view.py
    .venv/bin/python tools/build_catalog_view.py --check     # report drift only
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog" / "catalog.csv"
RAMPS = ROOT / "data" / "demand" / "sku_ramps.csv"
SALES = ROOT / "data" / "catalog" / "sales.csv"
OUT = ROOT / "data" / "catalog" / "catalog_view.csv"

BRANDS = {
    "biscuits": ["Kriuk", "Biskita", "Renyah", "Malkris", "Cemilku", "Gurihmas"],
    "instant_noodles": ["Mioku", "Sedapku", "Kuahmu", "Rebusin", "Mienya", "Segerku"],
    "beverages": ["Tehkita", "Segarmu", "Airku", "Rasaku", "Dinginnya", "Sirupku"],
    "personal_care": ["Sabunku", "Freshmu", "Wangiku", "Mandiku", "Bersihnya", "Lembutku"],
    "household": ["Bersihku", "Kilauku", "Wangiin", "Pelmu", "Cuciin", "Rumahku"],
    "snacks": ["Gurihku", "Kriuknya", "Camilin", "Asinmu", "Pedasku", "Renyahnya"],
    "dairy": ["Susuku", "Krimmu", "Segarnya", "Manisku", "Putihmu", "Lemakku"],
    "frozen": ["Bekuku", "Dinginku", "Siapku", "Frozenya", "Praktisku", "Segarpku"],
}

VARIANTS = {
    "biscuits": ["Cokelat", "Keju", "Vanila", "Kelapa", "Kacang", "Susu", "Pandan",
                 "Stroberi", "Madu", "Tiramisu", "Moka", "Karamel", "Cappuccino",
                 "Cokelat Keju", "Kelapa Pandan", "Susu Madu", "Vanila Kacang", "Keju Susu"],
    "instant_noodles": ["Ayam Bawang", "Soto Ayam", "Mi Goreng", "Kari Ayam", "Sambal Matah",
                        "Rendang", "Ayam Jerit", "Kaldu Jamur", "Seafood", "Ayam Pedas",
                        "Tomyam", "Bakso Sapi", "Cumi Pedas", "Ayam Bakar", "Sate Ayam",
                        "Iga Penyet", "Kwetiau", "Bihun Ayam"],
    "beverages": ["Teh Melati", "Jeruk", "Leci", "Mangga", "Stroberi", "Kopi Susu",
                  "Cokelat", "Vanila", "Anggur", "Markisa", "Sirsak", "Melon",
                  "Teh Tarik", "Lemon", "Kelapa Muda", "Biru", "Guava", "Alpukat"],
    "personal_care": ["Lemon", "Mint", "Mawar", "Melati", "Aloe Vera", "Susu",
                      "Charcoal", "Tea Tree", "Lavender", "Bengkoang", "Sereh",
                      "Kopi", "Madu", "Wangi Bunga", "Fresh", "Herbal", "Vitamin C", "Bambu"],
    "household": ["Lemon", "Jeruk Nipis", "Mint", "Mawar", "Pinus", "Sereh",
                  "Antibakteri", "Puti", "Bunga", "Lavender", "Kayu Manis", "Tea Tree",
                  "Karbol", "Jasmine", "Ocean", "Apple", "Lime", "Vanila"],
    "snacks": ["Original", "Pedas", "Keju", "Rumput Laut", "Jagung Bakar", "Balado",
               "Sambal", "Asin", "Manis", "Karamel", "Cokelat", "Pandan",
               "Udang", "Ayam", "Tomat", "Barbeque", "Seaweed", "Keju Pedas"],
    "dairy": ["Plain", "Cokelat", "Stroberi", "Vanila", "Moka", "Karamel",
              "Kelapa", "Madu", "Kurma", "Susu Full Cream", "Low Fat", "Original",
              "Cokelat Kacang", "Vanila Madu", "Stroberi Susu", "Moka Cokelat",
              "Plain Manis", "Susu Segar"],
    "frozen": ["Ayam", "Sapi", "Udang", "Ikan", "Sayur", "Kentang",
               "Nugget Ayam", "Sosis Sapi", "Bakso Ikan", "Dimsum", "Pangsit",
               "Keju", "Jagung", "Kacang", "Cokelat", "Kelapa", "Durian", "Nanas"],
}

PACKS = {
    "biscuits": ["120g", "225g", "330g", "650g"],
    "instant_noodles": ["70g", "85g", "5 x 75g"],
    "beverages": ["250ml", "500ml", "1L", "2L"],
    "personal_care": ["100ml", "250ml", "450ml"],
    "household": ["400ml", "800ml", "1.5L"],
    "snacks": ["60g", "120g", "250g"],
    "dairy": ["115g", "200ml", "1L"],
    "frozen": ["250g", "500g", "1kg"],
}

MARGIN = {
    "biscuits": (0.10, 0.15),
    "instant_noodles": (0.08, 0.12),
    "beverages": (0.09, 0.14),
    "personal_care": (0.12, 0.18),
    "household": (0.10, 0.16),
    "snacks": (0.11, 0.16),
    "dairy": (0.08, 0.12),
    "frozen": (0.09, 0.13),
}

DEFAULT_MARGIN = (0.10, 0.14)


def _seed(sku: str, salt: str = "") -> int:
    return int(hashlib.sha256((sku + salt).encode()).hexdigest()[:8], 16)


def _pick(seq: list[str], seed: int) -> str:
    return seq[seed % len(seq)]


def _price(cost: float, category: str, seed: int) -> tuple[int, float]:
    lo, hi = MARGIN.get(category, DEFAULT_MARGIN)
    margin = lo + (hi - lo) * ((seed % 1000) / 1000)
    raw = cost * (1 + margin)
    # retail prices land on familiar steps: nearest 100 for cheap goods, 500 above 50k
    step = 100 if raw < 50_000 else 500
    sell = int(round(raw / step) * step)
    return sell, round((sell / cost - 1) * 100, 1)


def build() -> pd.DataFrame:
    cat = pd.read_csv(CATALOG)
    ramps = pd.read_csv(RAMPS)
    sales = pd.read_csv(SALES, usecols=["sku", "date", "units"])
    sales["date"] = pd.to_datetime(sales["date"])

    top = (ramps.sort_values("peak_mult", ascending=False)
                .drop_duplicates("sku")[["sku", "event", "peak_mult", "days_to_peak", "ramp_class"]])

    end = sales["date"].max()
    last = sales[sales["date"] > end - pd.Timedelta(days=365)].groupby("sku")["units"].sum()
    prev = sales[(sales["date"] <= end - pd.Timedelta(days=365)) &
                 (sales["date"] > end - pd.Timedelta(days=730))].groupby("sku")["units"].sum()
    yoy = ((last / prev - 1) * 100).round(1)

    rows = []
    for _, r in cat.iterrows():
        sku, category = r["sku"], r["category"]
        form = str(r.get("product_form", "") or "").strip()
        # Name and pack come from the catalogue itself. This builder used to invent its own
        # labels, which is how a "Produk Original" ended up carrying a Valentine ramp.
        name = str(r["name"])
        pack = f"{int(round(float(r['pack_size']) * 1000))} {'ml' if r.get('pack_unit') == 'L' else 'g'}"
        sell, margin_pct = _price(float(r["unit_cost_idr"]), category, _seed(sku, "m"))
        rows.append({
            "sku": sku,
            "sku_code": str(r.get("sku_code", "")),
            "name": name,
            "brand": str(r.get("brand", "")),
            "category": category,
            "product_form": form,
            "pack": pack,
            "principal_id": r["principal_id"],
            "unit_cost_idr": int(r["unit_cost_idr"]),
            "sell_price_idr": sell,
            "margin_pct": margin_pct,
            "shelf_life_months": int(r["shelf_life_months"]),
            "base_daily_demand": round(float(r["base_daily_demand"]), 2),
            "yoy_growth_pct": float(yoy.get(sku, 0.0)),
            "top_event": top.loc[top["sku"] == sku, "event"].squeeze() if sku in set(top["sku"]) else "",
            "peak_mult": round(float(top.loc[top["sku"] == sku, "peak_mult"].squeeze()), 2) if sku in set(top["sku"]) else 1.0,
            "days_to_peak": float(top.loc[top["sku"] == sku, "days_to_peak"].squeeze()) if sku in set(top["sku"]) else 0.0,
            "ramp_class": top.loc[top["sku"] == sku, "ramp_class"].squeeze() if sku in set(top["sku"]) else "",
        })
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    df = build()
    if args.check:
        if not OUT.exists():
            print("catalog_view.csv missing; run without --check")
            return 1
        old = pd.read_csv(OUT)
        same = old.shape == df.shape and old.fillna("").equals(df.fillna(""))
        print(f"rows {len(df)} | check {'clean' if same else 'DRIFT'}")
        return 0 if same else 1

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)} rows={len(df)}")
    print(df.head(5)[["sku", "name", "category", "sell_price_idr", "margin_pct",
                      "yoy_growth_pct", "top_event", "peak_mult", "days_to_peak"]].to_string(index=False))
    print("\nprice band:", int(df['sell_price_idr'].min()), "-", int(df['sell_price_idr'].max()),
          "| name uniqueness:", df['name'].nunique(), "of", len(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
