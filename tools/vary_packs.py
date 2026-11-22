"""Give each product form its own realistic pack ladder.

The first pass picked pack sizes per category, so 600 SKUs collapsed onto 146 product
names. A distributor carries one product in several sizes; that is what makes a catalogue
readable and what makes price bands realistic.

This changes pack and price, therefore it invalidates any replay made before it. Rebuild
classes and replay after running.

Run: .venv/bin/python tools/vary_packs.py
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_catalog_v2 import ANCHORS  # noqa: E402

CAT = ROOT / "data" / "catalog" / "catalog.csv"

PACKS = {
    ("biskuit", "chocolate"): [0.065, 0.09, 0.12, 0.15, 0.3],
    ("biskuit", "gift tin"): [0.3, 0.4, 0.5],
    ("biskuit", "plain biscuit"): [0.1, 0.15, 0.2, 0.3],
    ("biskuit", "wafer"): [0.05, 0.075, 0.1, 0.15],
    ("snack", "chocolate"): [0.05, 0.068, 0.09],
    ("snack", "gift tin"): [0.25, 0.35],
    ("snack", "plain biscuit"): [0.05, 0.068, 0.085, 0.1],
    ("snack", "wafer"): [0.05, 0.075, 0.1],
    ("kopi_teh", "gift set"): [0.2, 0.3],
    ("perawatan_diri", "gift set"): [0.25, 0.4],
    ("beras", "standard"): [1.0, 2.0, 5.0, 10.0],
    ("gula", "standard"): [0.5, 1.0, 2.0],
    ("minyak_goreng", "standard"): [0.9, 1.0, 2.0, 5.0],
    ("mie_instan", "standard"): [0.07, 0.075, 0.085],
    ("minuman", "standard"): [0.25, 0.35, 0.5],
    ("air_mineral", "standard"): [0.33, 0.6, 1.5],
    ("kopi_teh", "standard"): [0.1, 0.165, 0.2],
    ("bumbu", "standard"): [0.135, 0.34, 0.52],
    ("perawatan_diri", "standard"): [0.075, 0.1, 0.17],
    ("perawatan_rumah", "standard"): [0.4, 0.8, 1.0],
    ("susu", "standard"): [0.19, 0.4, 1.0],
}


def seed(s: str) -> int:
    return int(hashlib.sha256(s.encode()).hexdigest(), 16)


def main() -> int:
    df = pd.read_csv(CAT)
    before_names = df["name"].nunique()
    for i, r in df.iterrows():
        key = (r["category"], r["product_form"])
        options = PACKS.get(key) or PACKS.get((r["category"], "standard")) or [float(r["pack_size"])]
        # Keep every SKU inside the price band the demand history and credit limits were
        # built for (Rp 3,500-38,000). A 12-pack of 5 kg rice would be a Rp 900k line,
        # which no warung orders and no credit limit here covers.
        anchor0, _u0, _b0, _s0 = ANCHORS[r["category"]]
        disc0 = 0.90 + (seed(str(r["sku"]) + "d") % 7) / 100
        cands = []
        for p_ in options:
            for n_ in (1, 3, 6, 12):
                c_ = anchor0 * p_ * n_ * disc0
                if 3_500 <= c_ <= 38_000:
                    cands.append((p_, n_))
        if not cands:
            cands = [(options[0], 1)]
        pack, isi = cands[seed(str(r["sku"]) + "pk") % len(cands)]
        # A real catalogue also carries multipacks: same product, different case count.
        # Without this, 600 SKUs collapse onto ~150 names and a reader cannot tell two
        # lines apart. Price scales with the case count because cost is per unit.
        anchor, unit, _basis, _source = ANCHORS[r["category"]]
        disc = 0.90 + (seed(str(r["sku"]) + "d") % 7) / 100
        cost = round(anchor * pack * isi * disc / 50) * 50
        df.at[i, "pack_size"] = round(pack * isi, 3)
        df.at[i, "unit_cost_idr"] = cost
        u = "ml" if unit == "L" else "g"
        total = int(round(pack * isi * 1000))
        suffix = f" isi {isi} ({total} {u})" if isi > 1 else ""
        df.at[i, "name"] = f"{r['brand']} {r['subcategory']} {int(round(pack * 1000))} {u}{suffix}"
    df.to_csv(CAT, index=False)
    print(f"names {before_names} -> {df.name.nunique()} | prices {df.unit_cost_idr.nunique()} distinct")
    print(df.groupby("category").unit_cost_idr.agg(["min", "median", "max"]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
