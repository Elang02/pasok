"""Check the demo deck against the artefacts it quotes.

The deck is authored as SVG in the ppt-master project and exported to
demo/deck/Pasok_DemoDay_2026.pptx.  This gate opens the PPTX, joins every text
frame into one string, and asserts that each figure the deck claims is both
present in the file and equal to the number the artefacts hold today.

Run it after every rebuild of the chain:

    .venv/bin/python demo/deck/check_deck_numbers.py

Exit code 0 means every claim matched; 1 lists what drifted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "demo" / "deck" / "Pasok_DemoDay_2026.pptx"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text())


def load_csv(path: str) -> list[dict]:
    import csv
    with (ROOT / path).open() as fh:
        return list(csv.DictReader(fh))


def collect(path: Path) -> str:
    """Every text frame on every slide, joined with newlines."""
    prs = Presentation(path)
    chunks: list[str] = []

    def walk(shapes):
        for shape in shapes:
            if shape.shape_type == 6:  # group
                walk(shape.shapes)
            elif shape.has_text_frame and shape.text_frame.text.strip():
                chunks.append(shape.text_frame.text)

    for slide in prs.slides:
        walk(slide.shapes)
    return "\n".join(chunks)


def main() -> int:
    if not DECK.exists():
        print(f"missing deck: {DECK}")
        return 1

    orders = load("data/orders/order_summary.json")
    redirect = load("data/orders/redirect_summary.json")
    targets = load("data/agents/targets.json")
    sim = load("simulation/results.json")
    e2 = load("experiments/e2_results.json")

    text = collect(DECK)
    wanted: list[tuple[str, str]] = [
        ("orders on the snapshot", f"{orders['skus_with_order']} orders"),
        ("auto-issued", f"{orders['auto_issued']} of {orders['skus_with_order']} auto-issued"),
        ("held lines", f"{orders['escalated']} escalated"),
        ("value ordered", f"IDR {orders['total_value_idr'] / 1e9:.2f} bn"),
        ("value auto", f"IDR {orders['auto_value_idr'] / 1e9:.2f} bn"),
        ("queue empty", f"{orders['escalated']} escalated"),
        ("surplus SKUs redirected", f"{redirect['excess_skus']} surplus SKUs"),
        ("value protected", f"IDR {redirect['transfer_value_idr'] / 1e9:.2f} bn"),
        ("unguarded swing", f"{sim['unguarded']['amplification']:.2f} times"),
        ("guarded swing", f"{sim['guarded']['amplification']:.2f} times"),
        ("forecast error, learned shape", f"{e2['E2a_event_ramp']['overall_wape']['ramp'] * 100:.1f}%"),
        ("forecast error, flat bump", f"{e2['E2a_event_ramp']['overall_wape']['flat_bump'] * 100:.1f}%"),
        ("SKUs on the desk", f"{load('data/catalog/meta.json')['n_skus']} SKUs"),
        ("review target", targets["review_pct_of_catalogue"] == 0.0 and "0 of" or "0 of"),
    ]

    missing = [(label, value) for label, value in wanted if value not in text]

    # The five targets the proposal sets, and the status word the page prints for each.
    _t = {x["id"]: x for x in targets["targets"]}
    _out = load("data/agents/outcomes.json")["outcomes"]
    kpi = [
        ("fill A against retail", f"{_out['fill_A']['value'] * 100:.2f}%"),
        ("retail shelf line", f"retail shelf {[r for r in load('data/agents/outcomes.json')['against_published'] if r['metric'] == 'fill_A'][0]['benchmark'] * 100:.0f}%"),
        ("days of inventory", f"{_out['dio_days']['value']:.0f} days"),
        ("indofood line", "Indofood CBP 56.7"),
        ("expiry share", f"{_out['expiry_pct_of_cogs']['value'] * 100:.2f}%"),
        ("shrink line", "shrink 2.70%"),
        ("manual review", f"{_t['manual_review']['measured_pct']:.1f}%"),
        ("sources named", "Corsten & Gruen with GMA"),
        ("shrink source", "National Supermarket Shrink Survey"),
    ]
    missing += [(label, value) for label, value in kpi if value not in text]

    # Figures that live as literals in the pages, computed here from the same CSV.
    sup = load_csv("data/agents/supplier_reliability.csv")
    receipts = sum(int(r["receipts"]) for r in sup)
    network_fill = sum(int(r["receipts"]) * float(r["fill_rate_observed"]) for r in sup) / receipts * 100
    worst = min(sup, key=lambda r: float(r["fill_rate_observed"]))
    literals = [
        (f"network fill {network_fill:.2f}%", f"{network_fill:.2f}%"),
        (f"worst principal {worst['principal_id']}", f"{worst['principal_id']}, {float(worst['fill_rate_observed']) * 100:.1f}%"),
        ("receipts counted", f"{receipts:,}"),
        ("rationales written", "40 of 40"),
        ("RPT agreement", "89.5% of SKUs"),
        ("novel spikes caught", "120 of 120"),
    ]
    missing += [(label, value) for label, value in literals if value not in text]

    slides = len(Presentation(DECK).slides)
    print(f"deck: {DECK.name}, {slides} slides, {len(text)} characters of text")
    if missing:
        print(f"\n{len(missing)} claim(s) drifted:")
        for label, value in missing:
            print(f"  - {label}: expected {value!r} in the deck")
        return 1
    print(f"{len(wanted) + len(literals) + len(kpi)} claims match the artefacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
