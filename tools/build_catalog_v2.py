"""Rebuild the catalogue with the fields a distributor actually carries.

Names, brands, pack sizes and prices, on top of the existing 600 SKU identities so the
2023-2026 sales history still lines up. Prices are anchored, not invented per row:

- beras, gula, minyak: Bank Indonesia PIHPS median, `data/external/pihps_harga.csv`
- everything else: a category benchmark per kg or litre, recorded in
  `data/catalog/price_anchors.csv` with `basis=benchmark` so nobody mistakes it for a
  supplier price list.

Run: .venv/bin/python tools/build_catalog_v2.py
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "data" / "catalog"
PIHPS = ROOT / "data" / "external" / "pihps_harga.csv"

# category -> (anchor Rp per kg or L, unit, basis, source)
ANCHORS = {
    "beras": (16_300, "kg", "pihps", "PIHPS Beras Medium, median 2026-10-19"),
    "gula": (20_000, "kg", "pihps", "PIHPS Gula Pasir, median 2026-10-19"),
    "minyak_goreng": (24_000, "L", "pihps", "PIHPS Minyak Goreng Kemasan, median 2026-10-19"),
    "mie_instan": (22_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "biskuit": (55_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "snack": (75_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "minuman": (9_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    "air_mineral": (4_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    "kopi_teh": (70_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "bumbu": (30_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    "perawatan_diri": (95_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "perawatan_rumah": (28_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    "susu": (32_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    # Categories that carry a documented event lift, so the seasonal swing in the
    # catalogue is a property of the product, not one number spread over 600 SKUs.
    "sirup": (15_000, "L", "benchmark", "category benchmark, replace with supplier list"),
    "cokelat": (95_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    "kue_kering": (85_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
    # Short-life goods: a distributor carries them, and they are what makes expiry a
    # real constraint instead of a rounding error.
    "roti": (32_000, "kg", "benchmark", "category benchmark, replace with supplier list"),
}

# old category -> the finer categories it becomes (keeping the same 120 SKUs)
SPLIT = {
    "biscuits": ["biskuit", "biskuit", "snack", "kue_kering", "cokelat", "roti"],
    "instant_noodles": ["mie_instan", "mie_instan", "bumbu", "beras"],
    "beverages": ["minuman", "air_mineral", "kopi_teh", "susu", "minyak_goreng", "sirup"],
    "personal_care": ["perawatan_diri", "perawatan_diri", "kopi_teh"],
    "household": ["perawatan_rumah", "perawatan_rumah", "gula"],
}

BRANDS = {
    "beras": ["Nusa Tani", "Sari Bumi", "Pandan Raya"],
    "gula": ["Manis Nusa", "Gula Sari", "Tebu Raya"],
    "minyak_goreng": ["Minyak Sari", "Bening Nusa", "Goreng Raya"],
    "mie_instan": ["Mi Nusa", "Mi Sari", "Mi Raya"],
    "biskuit": ["Biskuit Sari", "Krim Nusa", "Renyah Raya"],
    "snack": ["Snack Nusa", "Keripik Sari", "Gurih Raya"],
    "minuman": ["Teh Nusa", "Sari Segar", "Minuman Raya"],
    "air_mineral": ["Air Nusa", "Sumber Sari", "Segar Raya"],
    "kopi_teh": ["Kopi Nusa", "Teh Sari", "Rasa Raya"],
    "bumbu": ["Bumbu Nusa", "Saus Sari", "Dapur Raya"],
    "perawatan_diri": ["Diri Nusa", "Bersih Sari", "Wangi Raya"],
    "perawatan_rumah": ["Rumah Nusa", "Bersih Sari", "Kilau Raya"],
    "susu": ["Susu Nusa", "Sari Murni", "Krim Raya"],
    "sirup": ["Sirup Nusa", "Sari Manis", "Rasa Raya"],
    "cokelat": ["Cokelat Nusa", "Kakao Sari", "Manis Raya"],
    "kue_kering": ["Kue Nusa", "Kering Sari", "Nastar Raya"],
    "roti": ["Roti Nusa", "Bakar Sari", "Gandum Raya"],
}

# category -> (product forms, pack sizes in kg or L)
PRODUCTS = {
    "beras": (["Beras Premium", "Beras Medium", "Beras Pandan Wangi"], [1.0, 2.0, 5.0, 10.0]),
    "gula": (["Gula Pasir Kristal", "Gula Pasir Halus"], [0.5, 1.0, 2.0]),
    "minyak_goreng": (["Minyak Goreng Kemasan", "Minyak Goreng Sawit"], [0.9, 1.0, 2.0, 5.0]),
    "mie_instan": (["Mi Goreng", "Mi Kuah Ayam", "Mi Kuah Soto"], [0.07, 0.075, 0.085]),
    "biskuit": (["Biskuit Kelapa", "Biskuit Cokelat", "Biskuit Marie"], [0.1, 0.15, 0.3]),
    "snack": (["Keripik Kentang", "Keripik Singkong", "Snack Jagung"], [0.05, 0.068, 0.1]),
    "minuman": (["Teh Melati", "Teh Lemon", "Minuman Rasa Buah"], [0.25, 0.35, 0.5]),
    "air_mineral": (["Air Mineral", "Air Mineral Dingin"], [0.33, 0.6, 1.5]),
    "kopi_teh": (["Kopi Bubuk", "Kopi Instan", "Teh Celup"], [0.1, 0.165, 0.2]),
    "bumbu": (["Kecap Manis", "Saus Sambal", "Saus Tomat"], [0.135, 0.34, 0.52]),
    "perawatan_diri": (["Pasta Gigi", "Sabun Mandi", "Sampo"], [0.075, 0.1, 0.17]),
    "perawatan_rumah": (["Deterjen Bubuk", "Sabun Cuci Piring", "Pembersih Lantai"], [0.4, 0.8, 1.0]),
    "susu": (["Susu UHT", "Susu Bubuk", "Susu Kental Manis"], [0.19, 0.4, 1.0]),
    "sirup": (["Sirup Markisa", "Sirup Cocopandan", "Sirup Melon"], [0.46, 0.63, 0.66]),
    "cokelat": (["Cokelat Batang", "Cokelat Bubuk", "Cokelat Koin"], [0.06, 0.1, 0.165]),
    "kue_kering": (["Nastar", "Kastengel", "Kue Semprit"], [0.25, 0.3, 0.5]),
    "roti": (["Roti Tawar", "Roti Manis", "Roti Gandum"], [0.3, 0.4, 0.55]),
}

CATEGORY_UNIT = {c: ("L" if c in {"minyak_goreng", "minuman", "air_mineral", "bumbu",
                                 "perawatan_rumah", "susu", "sirup"} else "kg")
                 for c in ANCHORS}

# Shelf life in months, by category, overriding the value inherited from the old
# five-category catalogue. Roti is one month: with monthly granularity that is the
# shortest honest representation of a fresh bakery line, and it is what forces the
# shelf-life cap to bind somewhere.
SHELF_OVERRIDE = {
    "roti": [1, 1, 2],
    "kue_kering": [3, 4, 6],
    "sirup": [12, 18, 24],
    "cokelat": [9, 12, 18],
    "susu": [2, 6, 9],
}


def stable_pick(seed: str, options: list):
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    return options[h % len(options)]


def build() -> pd.DataFrame:
    source = CAT / "catalog.pre_v2.csv"
    old = pd.read_csv(source if source.exists() else CAT / "catalog.csv")
    rows = []
    for _, r in old.iterrows():
        cats = SPLIT[r["category"]]
        cat = stable_pick(r["sku"], cats)
        forms, packs = PRODUCTS[cat]
        form = stable_pick(r["sku"] + "f", forms)
        pack = stable_pick(r["sku"] + "p", packs)
        brand = stable_pick(r["sku"] + "b", BRANDS[cat])
        anchor, unit, basis, source = ANCHORS[cat]
        # Distributor buys below the retail anchor; deterministic 0.90-0.96 by SKU.
        disc = 0.90 + (int(hashlib.sha256((r["sku"] + "d").encode()).hexdigest(), 16) % 7) / 100
        cost = anchor * pack * disc
        cost = round(cost / 50) * 50
        name = f"{brand} {form} {int(pack * 1000)} {'ml' if unit == 'L' else 'g'}"
        shelf = r["shelf_life_months"]
        if cat in SHELF_OVERRIDE:
            shelf = stable_pick(r["sku"] + "sl", SHELF_OVERRIDE[cat])
        rows.append({
            "sku": r["sku"],
            "sku_code": f"PSK-{r['sku'][-4:]}",
            "name": name,
            "brand": brand,
            "category": cat,
            "subcategory": form,
            "pack_size": pack,
            "uom": "pcs",
            "pack_unit": unit,
            "principal_id": r["principal_id"],
            "shelf_life_months": shelf,
            "base_daily_demand": r["base_daily_demand"],
            "unit_cost_idr": cost,
            "volatility": r["volatility"],
            "credit_limit_idr": r["credit_limit_idr"],
            "product_form": r["product_form"],
            "price_basis": basis,
            "price_source": source,
        })
    out = pd.DataFrame(rows)
    return out


def main() -> int:
    backup = CAT / "catalog.pre_v2.csv"
    if not backup.exists():
        shutil.copy(CAT / "catalog.csv", backup)
    df = build()
    df.to_csv(CAT / "catalog.csv", index=False)
    # The generator needs the fine category, shelf life and unit cost to know which
    # event amplitude applies to a SKU. It reads this file instead of re-deriving the
    # split, so the sales series and the catalogue cannot disagree.
    df[["sku", "category", "subcategory", "pack_size", "pack_unit",
        "unit_cost_idr", "shelf_life_months"]].to_csv(CAT / "sku_categories.csv", index=False)

    anchors = pd.DataFrame(
        [{"category": c, "anchor_idr_per_unit": a, "pack_unit": u, "basis": b, "source": s}
         for c, (a, u, b, s) in ANCHORS.items()]
    )
    anchors.to_csv(CAT / "price_anchors.csv", index=False)

    print(f"catalogue: {len(df)} SKUs, {df.category.nunique()} categories")
    print(df.groupby("category").unit_cost_idr.agg(["count", "min", "median", "max"]).to_string())
    print(f"price basis: {df.price_basis.value_counts().to_dict()}")
    print(f"unique prices: {df.unit_cost_idr.nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
