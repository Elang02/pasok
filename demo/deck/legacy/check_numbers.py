"""Check every number on the Demo Day deck against the artefact that owns it.

    .venv/bin/python demo/deck/check_numbers.py

Fails when a slide quotes a figure the artefacts do not produce, or when an artefact has moved
and the deck still carries the old value.
"""
import json
import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path("/home/ubuntu/pasok")
DECK = ROOT / "demo/deck/Pasok_DemoDay_2026.pptx"


def j(rel):
    return json.loads((ROOT / rel).read_text())


prs = Presentation(DECK)
slides = [" ".join(sh.text_frame.text for sh in s.shapes if sh.has_text_frame) for s in prs.slides]


def slide_text(n):
    return slides[n - 1]


pos = j("data/stock/position_summary.json")
ordr = j("data/orders/order_summary.json")
red = j("data/orders/redirect_summary.json")
learn = j("data/agents/learn_summary.json")
sap = j("data/sap/rpt_summary.json")
rat = j("data/sap/rationale_summary.json")
dec = j("data/agents/decision_summary.json")
one = j("data/agents/one_pass.json")
e2 = j("experiments/e2_results.json")["E2a_event_ramp"]
sim = j("simulation/results.json")
import csv

with (ROOT / "data/agents/supplier_reliability.csv").open() as f:
    sup = list(csv.DictReader(f))

checks = []


def want(slide, token, value, fmt, source):
    shown = fmt(value)
    ok = shown == token and token in slide_text(slide)
    checks.append((slide, token, shown, source, ok))


want(2, "600", pos["n_skus"], lambda v: f"{v}", "position_summary.n_skus")
want(2, "9 of 12", sum(1 for r in sup if float(r["fill_rate_observed"]) < 0.95),
     lambda v: f"{v} of 12", "supplier_reliability.csv fill<0.95")
want(8, f'{learn["observed_fill_rate_mean"]*100:.2f}%', learn["observed_fill_rate_mean"] * 100, lambda v: f"{v:.2f}%", "learn_summary.observed_fill_rate_mean")
p02 = next(r for r in sup if r["principal_id"] == "P02")
ramps = list(csv.DictReader((ROOT / "data/demand/sku_ramps.csv").open()))
xmas = [r for r in ramps if r["event"] == "Christmas"]
import statistics as _st
_want = [float(r["peak_mult"]) for r in xmas]
want(5, "one passes", 1, lambda v: "one passes", "fixed prose for the 2.5x count")
want(5, "1.60", _st.median(_want), lambda v: f"{v:.2f}", "median peak_mult, Christmas")
want(5, "2.63", max(_want), lambda v: f"{v:.2f}", "max peak_mult, Christmas")
sys.path.insert(0, str(ROOT))
import pasok_answers as pan
nxt = pan._event_calendar()[0]
want(5, f"{nxt['days']} days", nxt["days"], lambda v: f"{v} days", "pasok_answers._event_calendar next event")
want(8, "81.1%", float(p02["otif"]) * 100, lambda v: f"{v:.1f}%", "supplier_reliability P02 otif")
want(12, f"{ordr['skus_with_order']} orders", ordr["skus_with_order"], lambda v: f"{v} orders", "order_summary.skus_with_order")
want(12, f"{ordr['auto_issued']} went out", ordr["auto_issued"], lambda v: f"{v} went out", "order_summary.auto_issued")
want(12, "30.27 bn", ordr["auto_value_idr"] / 1e9, lambda v: f"{v:.2f} bn", "order_summary.auto_value_idr")
want(12, "414", red["excess_skus"], lambda v: f"{v}", "redirect_summary.excess_skus")
want(12, "7.78 bn", red["transfer_value_idr"] / 1e9, lambda v: f"{v:.2f} bn", "redirect_summary.transfer_value_idr")
held = j("data/agents/targets.json")
_mr = next(t for t in held["targets"] if t["id"] == "manual_review")
want(12, f"0 of {held['review_lines_examined']:,}",
     held["review_lines_over_credit"], lambda v: f"0 of {held['review_lines_examined']:,}",
     "targets.review_lines_over_credit")

want(10, "0.895", sap["agreement_with_agent_below_reorder"], lambda v: f"{v:.3f}", "rpt_summary.agreement")
want(10, "577", sap["predicted_expiry_yes"], lambda v: f"{v}", "rpt_summary.predicted_expiry_yes")
want(10, "10.73 s", sap["elapsed_s"], lambda v: f"{v:.2f} s", "rpt_summary.elapsed_s")
want(10, "40/40", rat["orchestration_ok"], lambda v: f"{v}/{v}", "rationale_summary.orchestration_ok")
want(9, "1.33x → 0.36x", (dec["amplification"]["raw"], dec["amplification"]["guarded"]),
     lambda v: f"{v[0]:.2f}x → {v[1]:.2f}x", "decision_summary.amplification")
want(3, "2.68x", sim["unguarded"]["amplification"], lambda v: f"{v:.2f}x", "simulation/results.json unguarded")
want(3, "0.24x", sim["guarded"]["amplification"], lambda v: f"{v:.2f}x", "simulation/results.json guarded")
want(7, "0.0775", e2["overall_wape"]["ramp"], lambda v: f"{v:.4f}", "e2 overall_wape.ramp")
want(7, "0.1161", e2["overall_wape"]["flat_bump"], lambda v: f"{v:.4f}", "e2 overall_wape.flat_bump")
want(7, "30,490", e2["n_series_aggregated"], lambda v: f"{v:,}", "e2 n_series_aggregated")
want(7, "154", e2["windows_tested"], lambda v: f"{v}", "e2 windows_tested")
nov = j("experiments/e2_results.json")["E2b_novelty"]
want(7, "120 of 120", nov["detected"], lambda v: f"{v} of {nov['injections']}", "e2b detected/injections")
want(7, "0.65", nov["fp_days_per_100"], lambda v: f"{v:.2f}", "e2b fp_days_per_100")
want(6, "2,092", one["issue"]["qty"], lambda v: f"{v:,.0f}", "one_pass.issue.qty")
want(6, "15.9M", one["issue"]["value_idr"] / 1e6, lambda v: f"{v:.1f}M", "one_pass.issue.value_idr")
want(6, "95.1M", one["issue"]["credit_limit_idr"] / 1e6, lambda v: f"{v:.1f}M", "one_pass.issue.credit_limit_idr")
want(6, "97.70%", one["learn"]["observed_fill_rate"] * 100, lambda v: f"{v:.2f}%", "one_pass.learn.observed_fill_rate")
want(6, "48", one["learn"]["shortfall_units"], lambda v: f"{v:,.0f}", "one_pass.learn.shortfall_units")

bad = [c for c in checks if not c[4]]
for slide, token, shown, source, ok in checks:
    print(("OK  " if ok else "FAIL"), f"s{slide:02d}", f"{token!r:22}", f"<- {source} = {shown}")
print(f"\n{len(checks) - len(bad)}/{len(checks)} figures match the artefacts")
raise SystemExit(1 if bad else 0)
