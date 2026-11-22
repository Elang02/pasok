"""Bentuk barang di katalog, dan pengali Valentine yang mengikutinya.

Katalog sebelumnya hanya tahu kategori (biskuit, minuman, mie, perawatan diri, rumah tangga)
dan tidak tahu bentuk barangnya. Akibatnya tidak ada cara mengenali cokelat dari datanya, dan
pengali Valentine jadi rata untuk semua SKU, padahal cokelat dan biskuit biasa jelas berbeda
saat Valentine. Sebaran kepekaan antar SKU di data juga sempit, hanya 2,08 sampai 2,68, jadi
variasi kecil per SKU tidak cukup.

Yang dilakukan di sini: bentuk barang diturunkan dari dua sifat yang memang ada di data, harga
satuan dan keragaman permintaan, lalu ditandai sebagai ASUMSI karena katalog kita bukan katalog
nyata. Urutannya di dalam kategori, jadi bentuknya relatif terhadap kategori itu sendiri.

Valentine memakai bentuk barang; Idul Adha, Kemerdekaan dan Maulid cukup di tingkat kategori
karena lonjakannya memang luas, bukan pada barang tertentu.

Jalan: .venv/bin/python tools/add_product_forms.py
"""
from __future__ import annotations

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMAND = ROOT / "data" / "demand"
CATALOG = ROOT / "data" / "catalog" / "catalog.csv"

# Bentuk barang per kategori: (nama, bagian terbawah yang masuk akal, pengali Valentine)
FORMS = {
    # biskuit: yang paling mahal dan paling naik turun adalah cokelat dan kaleng hadiah
    "biscuits": [("chocolate", 0.20, 3.00), ("gift tin", 0.15, 2.40),
                 ("wafer", 0.25, 1.35), ("plain biscuit", 1.00, 1.08)],
    # perawatan diri: set hadiah, biasanya parfum atau losion sekaligus
    "personal_care": [("gift set", 0.10, 1.60), ("standard", 1.00, 1.00)],
    "beverages": [("standard", 1.00, 1.06)],
    "instant_noodles": [("standard", 1.00, 1.00)],
    "household": [("standard", 1.00, 1.00)],
}
NOTE = "assumed from unit cost and demand variability, catalog carries no product attributes"


def main() -> int:
    cat = pd.read_csv(CATALOG)
    if "product_form" not in cat.columns:
        cat["product_form"] = "standard"
        cat["product_form_basis"] = NOTE
        for category, forms in FORMS.items():
            idx = cat.index[cat.category == category]
            sub = cat.loc[idx]
            score = (sub.unit_cost_idr.rank(pct=True) + sub.volatility.rank(pct=True)) / 2
            order = sub.assign(score=score).sort_values("score", ascending=False)
            n = len(order)
            start = 0
            for name, share, _mult in forms:
                end = n if share >= 1.0 else start + max(1, int(round(n * share)))
                cat.loc[order.index[start:end], "product_form"] = name
                start = end
        cat.to_csv(CATALOG, index=False)

    form_mult = {f: m for forms in FORMS.values() for f, _s, m in forms}
    ramps = pd.read_csv(DEMAND / "sku_ramps.csv")
    sens = ramps[ramps.event.isin(["Christmas", "Imlek", "NewYear"])].groupby("sku").peak_mult.mean()
    sens = ((sens / sens.mean()).clip(0.90, 1.10)).to_dict()
    forms = dict(zip(cat.sku.astype(str), cat.product_form))

    val = ramps[ramps.event == "Valentine"].copy()
    def val_mult(sku: str) -> float:
        base = form_mult.get(forms.get(sku, "standard"), 1.0)
        if base <= 1.0:
            return 1.0          # barang tanpa lonjakan Valentine tetap datar, tidak turun
        return round(min(base * sens.get(sku, 1.0), 3.40), 2)

    val["peak_mult"] = [val_mult(s) for s in val.sku]
    ramps = pd.concat([ramps[ramps.event != "Valentine"], val], ignore_index=True)
    ramps.to_csv(DEMAND / "sku_ramps.csv", index=False)

    reg = pd.read_csv(DEMAND / "event_registry.csv")
    v = val.peak_mult
    reg.loc[reg.event == "Valentine", "mean_factor"] = round(float(v.mean()), 4)
    reg.loc[reg.event == "Valentine", "median_factor"] = round(float(v.median()), 4)
    reg.to_csv(DEMAND / "event_registry.csv", index=False)

    print("bentuk barang per kategori:")
    print(cat.groupby(["category", "product_form"]).size().to_string())
    print()
    print("pengali Valentine sekarang:")
    print(val.peak_mult.describe().round(2).to_string())
    print("  SKU di atas 2x :", int((v > 2.0).sum()), "| di atas 2,5x :", int((v > 2.5).sum()),
          "| tertinggi :", float(v.max()))
    print("  contoh:", "; ".join(f"{s} {m}x" for s, m in
                                zip(val.sku.head(4), val.peak_mult.head(4))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
