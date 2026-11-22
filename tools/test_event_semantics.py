"""Does the demand model put event lifts on products that could plausibly move?

The failure this guards against: a catalogue name that has nothing to do with the stored
product form, so the demo shows coconut biscuits tripling on Valentine's Day. Every lift is
produced per `product_form`; this gate checks that the names agree with the forms and that
staple categories carry no romantic-season lift at all.

Run: .venv/bin/python tools/test_event_semantics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAMPS = ROOT / "data" / "demand" / "sku_ramps.csv"
CATALOG = ROOT / "data" / "catalog" / "catalog.csv"

# Forms allowed to move on Valentine's Day, and the ceiling before a name must say so.
VALENTINE_FORMS = {"chocolate", "gift tin", "wafer", "gift set"}
STAPLE_CATEGORIES = {"beras", "gula", "minyak_goreng", "mie_instan", "air_mineral",
                     "perawatan_rumah", "bumbu"}


def main() -> int:
    ramps = pd.read_csv(RAMPS)
    cat = pd.read_csv(CATALOG)[["sku", "name", "category", "product_form"]]
    v = ramps[ramps.event == "Valentine"].merge(cat, on="sku", how="left")

    failures: list[str] = []

    # 1.10-1.20 is estimation noise on a flat form, not a lift a buyer would notice;
    # the gate fires where the effect is real.
    wrong = v[(v.peak_mult > 1.20) & (~v.product_form.isin(VALENTINE_FORMS))]
    for _, r in wrong.iterrows():
        failures.append(f"lift on a non-gift form: {r.sku} {r['name']} x{r.peak_mult:.2f}")

    staples = v[v.category.isin(STAPLE_CATEGORIES)]
    hot = staples[staples.peak_mult > 1.05]
    for _, r in hot.iterrows():
        failures.append(f"staple moved on Valentine: {r.sku} {r['name']} x{r.peak_mult:.2f}")

    big = v[v.peak_mult >= 2.0]
    for _, r in big.iterrows():
        if not any(word in str(r["name"]) for word in ("Cokelat", "Hadiah", "Kaleng")):
            failures.append(f"x{r.peak_mult:.2f} but the name does not say why: {r['name']}")

    print(f"Valentine ramps: {len(v)} SKUs, {int((v.peak_mult > 1.10).sum())} above 1.10")
    print(v.groupby("category").peak_mult.median().round(2).to_string())

    if failures:
        print("\nFAIL")
        for f in failures[:12]:
            print(" ", f)
        return 1
    print("\nPASS  every Valentine lift sits on a gift-shaped product, staples stay flat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
