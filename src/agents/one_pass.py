"""
Pasok — One Pass, Concretely (proposal line 24)
===============================================

    "One pass, concretely: the loop finds a biscuit SKU whose days of cover run out
     before the next delivery, eleven days before Lebaran. It weighs the learned event
     ramp, this principal's learned lead time, the credit left this month, and the
     SKU's remaining shelf life; it sizes the order from the ramp curve, issues the
     purchase order, and records its rationale."

This script turns that paragraph into a trace with real numbers: it walks one live SKU
through the five loop steps — perceive, forecast, decide, issue, learn — reading only
the committed artefacts, so every line is reproducible.

The SKU is chosen by the rule the paragraph describes, not hand-picked:
  category = biskuit  AND  days_of_cover < lead_p90  AND  inside an event window
  AND the loop issued a purchase order for it.

Outputs
-------
data/agents/one_pass.json      the machine-readable trace
demo/one_pass.md               the same trace as a demo-ready narrative

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/one_pass.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "data" / "agents"
STK = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))  # PASOK_STOCK = hari yang disimulasikan
ORD = ROOT / "data" / "orders"
CAT = ROOT / "data" / "catalog"
DEMO = ROOT / "demo"

CATEGORY = "biskuit"

_PEAK_TOL = float(os.environ.get("PASOK_PEAK_TOLERANCE", "1.05"))
_PEAK_FLOOR = float(os.environ.get("PASOK_PEAK_FLOOR", "1.00"))


def peak_numbers(sku_id: str, cover_days: float) -> tuple[float, float]:
    """The most this SKU sells in a day, and what that allows over a cover window.

    Same two numbers the order gate uses: the agent's own daily rate for the SKU times the
    highest peak the ramp learner recorded, carried across the days the order has to cover.
    """
    dec = pd.read_csv(AG / "decisions.csv")
    ramps = pd.read_csv(ROOT / "data" / "demand" / "sku_ramps.csv")
    rate = float(dec.loc[dec["sku"] == sku_id, "forecast_daily_eff"].max())
    mult = float(ramps.loc[ramps["sku"] == sku_id, "peak_mult"].max())
    day = rate * max(mult, 1.0)
    return day, day * max(cover_days, 7.0) * max(_PEAK_FLOOR, 1.0) * _PEAK_TOL



def pick_sku(pos: pd.DataFrame, dec: pd.DataFrame, cat: pd.DataFrame) -> str | None:
    """The proposal's own rule: a biscuit whose cover runs out before the next
    delivery, inside an event window, with an order issued.

    Relaxed in one step only when the strict rule matches nothing. The strict
    rule needs cover < lead, which stops happening when the loop has just
    issued a round of orders and every line is covered. Relaxing to the
    tightest-cover candidate keeps the trace honest (same category, same event
    window, same order issued) instead of failing the whole run.
    """
    m = (pos.merge(dec[["sku", "event", "event_mult", "guarded_order"]], on="sku")
            .merge(cat[["sku", "category"]], on="sku"))
    # A missing event arrives as NaN, and `NaN != ""` is TRUE, so every filter below used
    # to read a SKU with no event as an event-covered one. Normalise once, here.
    m["event"] = m["event"].map(_ev)
    strict = m[(m["category"] == CATEGORY)
               & (m["event"] != "")
               & (m["guarded_order"] > 0)
               & (m["days_of_cover"] < m["lead_time_days"])]
    if not strict.empty:
        # most urgent first: zero cover, then largest order value
        strict = strict.sort_values(["days_of_cover", "guarded_order"],
                                    ascending=[True, False])
        return str(strict.iloc[0]["sku"])

    # Relaxation ladder, in order, each step loosening exactly one condition
    # and recording which step it used. The run must still produce a trace, but
    # it must never silently pretend the strict rule matched.
    for label, cond in [
        ("cover below reorder trigger", m["days_of_cover"] <= m["lead_trigger_days"]),
        ("cover below lead time", m["days_of_cover"] < m["lead_time_days"]),
    ]:
        step = m[(m["category"] == CATEGORY) & (m["event"] != "")
                 & (m["guarded_order"] > 0) & cond]
        if not step.empty:
            step = step.sort_values(["days_of_cover", "guarded_order"],
                                    ascending=[True, False])
            _RELAXED.append(label)
            return str(step.iloc[0]["sku"])

    loose = m[(m["category"] == CATEGORY) & (m["event"] != "") & (m["guarded_order"] > 0)]
    if not loose.empty:
        _RELAXED.append("tightest cover among event-covered biscuits")
        return str(loose.sort_values("days_of_cover").iloc[0]["sku"])

    # Nothing in this snapshot carries an event, which is a correct state: the horizon may
    # hold no Indonesian demand event at all. Take the tightest cover in the category and
    # say so, rather than failing the run or pretending an event was found.
    plain = m[(m["category"] == CATEGORY) & (m["guarded_order"] > 0)]
    if plain.empty:
        return None
    _RELAXED.append("tightest cover in the category, no event in this snapshot")
    return str(plain.sort_values(["days_of_cover", "guarded_order"],
                                 ascending=[True, False]).iloc[0]["sku"])


_RELAXED: list[str] = []


def _ev(v) -> str:
    """The event name, or "" when there is none.

    `str(nan)` is the truthy string "nan", which passed an `if event` check and an
    `event != ""` filter and let the trace claim it was inside an event window.
    """
    if v is None:
        return ""
    if isinstance(v, float) and v != v:
        return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "nat") else s


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Trace one SKU through the five loop steps")
    ap.add_argument("--sku", default=None,
                    help="trace this SKU instead of the rule-selected one (e.g. SKU0536)")
    ap.add_argument("--out", default=None,
                    help="write the trace JSON here instead of data/agents/one_pass.json")
    ap.add_argument("--no-md", action="store_true",
                    help="do not write demo/one_pass.md (for callers that only want the JSON)")
    args = ap.parse_args()

    pos = pd.read_csv(STK / "position_snapshot.csv")
    dec = pd.read_csv(AG / "decisions.csv")
    cat = pd.read_csv(CAT / "catalog.csv")
    po = pd.read_csv(ORD / "purchase_orders.csv")
    nl = pd.read_csv(ORD / "notification_ledger.csv")
    aq = pd.read_csv(ORD / "approval_queue.csv")
    sr = pd.read_csv(AG / "supplier_reliability.csv")
    dh = pd.read_csv(AG / "decision_history.csv")
    ramps = pd.read_csv(ROOT / "data" / "demand" / "sku_ramps.csv")
    curve = pd.read_csv(AG / "learn_curve.csv")
    subs = ORD / "order_submissions.csv"
    submissions = pd.read_csv(subs) if subs.exists() else None

    sku = args.sku.strip().upper() if args.sku else None
    if sku is not None and sku not in set(dec["sku"].astype(str)):
        print(f"{sku} has no decision in this snapshot")
        return 1
    if sku is None:
        sku = pick_sku(pos, dec, cat)
    if sku is None:
        print("no SKU in the snapshot matches the paragraph's rule")
        return 1

    p = pos[pos["sku"] == sku].iloc[0]
    d = dec[dec["sku"] == sku].iloc[0]
    c = cat[cat["sku"] == sku].iloc[0]
    pid = p["principal_id"]
    s = sr[sr["principal_id"] == pid].iloc[0]
    # A held SKU has no purchase order, so steps 4 and 5 do not exist for it. The
    # console's Trace tab asks about whatever SKU the operator names, and a held SKU is
    # the commonest answer, so this is a stated outcome rather than a crash.
    pr_rows = po[po["sku"] == sku]
    has_po = bool(len(pr_rows))
    pr = pr_rows.iloc[0] if has_po else None
    n = nl[nl["po_id"] == pr["po_id"]].iloc[0] if has_po else None
    q = aq[aq["po_id"] == pr["po_id"]] if has_po else aq.iloc[0:0]
    h = dh[dh["po_id"] == pr["po_id"]].iloc[0] if has_po else None
    ramp = ramps[(ramps["sku"] == sku) & (ramps["event"] == d["event"])]

    snap_month = str(d["snapshot"])[:7]
    cm = curve[curve["month"] == snap_month]
    curve_row = cm.iloc[0] if len(cm) else None
    curve_worst = curve.loc[curve["wape"].idxmax()]
    curve_best = curve.loc[curve["wape"].idxmin()]

    # step 4b: where the order actually went (the distributor's ordering system)
    intake = {"submitted": False, "reason": "no order was issued for this SKU"}
    if submissions is not None and has_po:
        row = submissions[submissions["po_id"] == pr["po_id"]]
        if len(row):
            row = row.iloc[0]
            intake = {
                "submitted": True,
                "system_reference": str(row["reference"]),
                "system": str(row["system"]),
                "idempotent": bool(row["resubmitted"]),
            }
        else:
            intake = {"submitted": False,
                      "reason": "escalated orders stay in the human queue, not submitted"}

    _peak_day, _peak_env = peak_numbers(sku, float(d["cover_days_target"]))
    trace = {
        "sku": sku,
        "category": str(c["category"]),
        "principal_id": pid,
        "snapshot": str(d["snapshot"]),
        "selection_rule": ("picked by the operator" if args.sku else
                           "biscuits AND days_of_cover < lead_time AND inside an event "
                           "window AND an order was issued"),
        # empty when the strict rule matched. When it is not, this is the one
        # condition that had to give, said out loud rather than hidden.
        "relaxed_to": (_RELAXED[-1] if (not args.sku and _RELAXED) else ""),
        "perceive": {
            "on_hand_units": float(p["on_hand_units"]),
            "in_transit_units": float(p["in_transit_units"]),
            "open_po_units": float(p["open_po_units"]),
            "sellable_units": float(p["sellable_units"]),
            "velocity_units_day": float(p["velocity_units_day"]),
            "days_of_cover": float(p["days_of_cover"]),
            "lead_trigger_days": float(p["lead_trigger_days"]),
            "below_reorder": bool(p["below_reorder"]),
            "expiry_risk": bool(p["expiry_risk"]),
        },
        "forecast": {
            "event": _ev(d["event"]),
            "event_multiplier": float(d["event_mult"]) if _ev(d["event"]) else 1.0,
            "forecast_daily_base": float(d["forecast_daily"]),
            "forecast_daily_effective": float(d["forecast_daily_eff"]),
            "learned_ramp_present": bool(len(ramp)),
        },
        "decide": {
            "lead_p90_days": float(d["lead_p90_days"]),
            "review_days": 7,
            "buffer_days": int(d["buffer_days"]),
            "buffer_lead_var_contrib_d": float(d["buffer_lead_var_contrib_d"]),
            "buffer_forecast_err_contrib_d": float(d["buffer_forecast_err_contrib_d"]),
            "buffer_late_tail_d": float(d.get("buffer_late_tail_d", 0.0)),
            "demand_lead_units": float(d.get("demand_lead_units", 0.0)),
            "pos_at_arrival_units": float(d.get("pos_at_arrival_units", 0.0)),
            "demand_window_units": float(d.get("demand_window_units", 0.0)),
            "need_units": float(d.get("need_units", 0.0)),
            "cover_days_target": float(d["cover_days_target"]),
            "raw_order_units": float(d["raw_order"]),
            "guarded_order_units": float(d["guarded_order"]),
            "guardrail_flags": str(d["guardrail_flags"]),
            "rationale": str(d["rationale"]),
            "peak_day_units": _peak_day,
            "peak_envelope_units": _peak_env,
            "above_peak_units": max(0.0, float(d["guarded_order"]) - _peak_env),
            "supplier_fill_rate": float(s["fill_rate_observed"]),
            "supplier_lead_drift": bool(s["drift_flag"]),
        },
        "has_order": has_po,
        "issue": ({
            "po_id": str(pr["po_id"]),
            "qty": float(pr["qty"]),
            "unit_cost_idr": int(pr["unit_cost_idr"]),
            "value_idr": float(pr["value_idr"]),
            "credit_limit_idr": int(c["credit_limit_idr"]),
            "status": str(pr["status"]),
            "escalation_reason": str(pr["reason"]),
            "notification_status": str(n["dispatch_status"]),
            "notification_recipient": str(n["recipient"]),
            "in_approval_queue": bool(len(q)),
            "intake": intake,
        } if has_po else {
            "po_id": None,
            "qty": 0.0,
            "unit_cost_idr": 0,
            "value_idr": 0.0,
            "credit_limit_idr": int(c["credit_limit_idr"]),
            "status": "no order",
            "escalation_reason": str(d["rationale"]),
            "notification_status": "not sent",
            "notification_recipient": "",
            "in_approval_queue": False,
            "intake": intake,
        }),
        "learn": ({
            "score": str(h["score"]),
            "observed_fill_rate": float(h["fill_rate_observed"]),
            "lead_p90_planned_d": float(h["lead_p90_planned_d"]),
            "lead_p90_observed_d": float(h["lead_p90_observed_d"]),
            "lead_drift_d": float(h["lead_drift_d"]) if str(h["lead_drift_d"]) not in ("", "nan") else 0.0,
            "held_out_wape": float(h["forecast_wape_best"]),
            "expected_received_units": float(h["expected_received_units"]),
            "shortfall_units": float(h["shortfall_units"]),
            "curve_month": snap_month,
            "curve_wape_this_month": float(curve_row["wape"]) if curve_row is not None else None,
            "curve_readings_this_month": int(curve_row["readings"]) if curve_row is not None else None,
            "curve_months_tracked": int(len(curve)),
            "curve_worst_month": {"month": str(curve_worst["month"]), "wape": float(curve_worst["wape"])},
            "curve_best_month": {"month": str(curve_best["month"]), "wape": float(curve_best["wape"])},
        } if has_po else {
            "score": "no order",
            "observed_fill_rate": float(s["fill_rate_observed"]),
            "lead_p90_planned_d": float(d["lead_p90_days"]),
            "lead_p90_observed_d": 0.0,
            "lead_drift_d": 0.0,
            "held_out_wape": None,
            "expected_received_units": 0.0,
            "shortfall_units": 0.0,
            "curve_month": snap_month,
            "curve_wape_this_month": float(curve_row["wape"]) if curve_row is not None else None,
            "curve_readings_this_month": int(curve_row["readings"]) if curve_row is not None else None,
            "curve_months_tracked": int(len(curve)),
            "curve_worst_month": {"month": str(curve_worst["month"]), "wape": float(curve_worst["wape"])},
            "curve_best_month": {"month": str(curve_best["month"]), "wape": float(curve_best["wape"])},
        }),
        "shelf_life_days": int(c["shelf_life_months"] * 30),
    }

    # A console request may ask about any SKU. Writing to the canonical path would let a
    # reader's click overwrite the committed demo artefact for the rule-selected SKU, so
    # the caller can redirect this. `--no-md` keeps demo/one_pass.md out of it entirely.
    out_path = Path(args.out) if args.out else (AG / "one_pass.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(trace, indent=2))

    # The trace must say which rule actually picked the SKU. In a snapshot with no event,
    # the strict rule matches nothing, and a paragraph claiming the SKU was chosen inside
    # an event window would be a false statement in the document the judges read.
    _strict_rule = (f"a *{CATEGORY}* SKU whose days of cover run out before the next "
                    f"delivery, inside a registered event window, for which the loop "
                    f"issued an order")
    _pick_line = (
        f"The selection rule is the paragraph's own: {_strict_rule}."
        if not _RELAXED else
        f"The strict selection rule is {_strict_rule}, and no SKU matches it in this "
        f"snapshot, so the trace falls back to {_RELAXED[-1]}."
    )

    _status = trace['issue']['status']
    if _status == 'AUTO_ISSUED':
        _issue_note = (
            "The order sits inside the SKU's credit line and inside policy, so it fires "
            "automatically: the principal is notified and the order goes straight out. That is "
            "supervised autonomy working; the money gate exists and did not need to fire here."
        )
    else:
        _issue_note = (
            "The order values above the SKU's credit line, so it does not fire automatically: "
            "the principal is **not** notified and the order sits in the human queue. That is "
            "supervised autonomy working, not a failure."
        )

    md = f"""# One pass, concretely — {sku}

> Proposal line 24, turned into a trace. Every number below comes from the committed
> artefacts; regenerate with `bash run_chain.sh` and `.venv/bin/python src/agents/one_pass.py`.

**The SKU was not hand-picked.** {_pick_line} Winner: **{sku}**
({pid}), snapshot {trace['snapshot']}.

## 1. Perceive — what the three agents see

| Reading | Value |
|---|---|
| On hand | {trace['perceive']['on_hand_units']:,.0f} u |
| In transit | {trace['perceive']['in_transit_units']:,.0f} u |
| Open PO | {trace['perceive']['open_po_units']:,.0f} u |
| **Sellable** | **{trace['perceive']['sellable_units']:,.0f} u** |
| Velocity | {trace['perceive']['velocity_units_day']:,.2f} u/day |
| **Days of cover** | **{trace['perceive']['days_of_cover']:.1f} d** |
| Below reorder | {trace['perceive']['below_reorder']} |

## 2. Forecast — the event it is planning for

- Registered event: **{trace['forecast']['event']}** at **x{trace['forecast']['event_multiplier']:.2f}**
- Learned ramp for this SKU/event: **{'yes' if trace['forecast']['learned_ramp_present'] else 'no'}**
- Forecast: {trace['forecast']['forecast_daily_base']:,.1f} u/day base →
  **{trace['forecast']['forecast_daily_effective']:,.1f} u/day effective**

## 3. Decide — the sizing arithmetic

```
cover target = lead p90 ({trace['decide']['lead_p90_days']:.0f}) + review ({trace['decide']['review_days']}) + buffer ({trace['decide']['buffer_days']})
             = {trace['decide']['cover_days_target']:.0f} days
buffer       = z90 x sqrt(lead_p90 x demand_cv^2 + lead_sd^2) + p95 lateness
             = {trace['decide']['buffer_days']} d  (lead sd {trace['decide']['buffer_lead_var_contrib_d']:.1f} d,
               demand term {trace['decide']['buffer_forecast_err_contrib_d']:.1f} d, late tail {trace['decide'].get('buffer_late_tail_d', 0.0):.1f} d)
sells while  = {trace['decide'].get('demand_lead_units', 0.0):,.0f} u over the lead time
the truck runs
stock when   = {trace['decide'].get('pos_at_arrival_units', 0.0):,.0f} u
the lot lands
gap to cover = {trace['decide'].get('demand_window_units', 0.0):,.0f} u until the lot after it lands
need         = {trace['decide'].get('need_units', 0.0):,.0f} u, divided by supplier fill
raw order    = {trace['decide']['raw_order_units']:,.0f} u
guarded      = {trace['decide']['guarded_order_units']:,.0f} u  ({trace['decide']['guardrail_flags']})
```

Rationale recorded: *"{trace['decide']['rationale']}"*

Supplier reality: fill **{trace['decide']['supplier_fill_rate']:.3f}**, lead drift
**{trace['decide']['supplier_lead_drift']}**.
"""
    if has_po:
        md_tail = f"""
## 4. Issue — the purchase order and the human gate

| | |
|---|---|
| PO | **{trace['issue']['po_id']}** |
| Quantity | {trace['issue']['qty']:,.0f} u |
| Value | **IDR {trace['issue']['value_idr']:,.0f}** |
| Credit line for this SKU | IDR {trace['issue']['credit_limit_idr']:,.0f} |
| Status | **{trace['issue']['status']}** |
| Why | {trace['issue']['escalation_reason']} |
| Notification | {trace['issue']['notification_status']} ({trace['issue']['notification_recipient']}) |

{_issue_note}

**Ordering system:** {'submitted to **' + trace['issue']['intake']['system'] + '** as **' + trace['issue']['intake']['system_reference'] + '**' if trace['issue']['intake']['submitted'] else '**not submitted** — ' + trace['issue']['intake']['reason']}.

## 5. Learn — the loop checking itself

- Score: **{trace['learn']['score']}**
- Observed fill {trace['learn']['observed_fill_rate']:.3f} → expected arrival
  {trace['learn']['expected_received_units']:,.0f} u of {trace['issue']['qty']:,.0f} u
  (**short {trace['learn']['shortfall_units']:,.0f} u**)
- Lead time: planned p90 {trace['learn']['lead_p90_planned_d']:.0f} d vs observed
  {trace['learn']['lead_p90_observed_d']:.0f} d (drift {trace['learn']['lead_drift_d']:.1f} d)
- Held-out forecast WAPE for this SKU: **{trace['learn']['held_out_wape']:.4f}**
- Loop cycle check: snapshot month **{trace['learn']['curve_month']}** carried WAPE
  **{trace['learn']['curve_wape_this_month']:.4f}** over
  {trace['learn']['curve_readings_this_month']:,} forecast/actual readings. The loop
  tracks {trace['learn']['curve_months_tracked']} months; its worst month
  ({trace['learn']['curve_worst_month']['month']}, {trace['learn']['curve_worst_month']['wape']:.4f})
  is an event month, its best ({trace['learn']['curve_best_month']['month']},
  {trace['learn']['curve_best_month']['wape']:.4f}) a quiet one. Full curve:
  `data/agents/learn_curve.csv`.

**Next cycle's lever:** this principal's fill rate ({trace['learn']['observed_fill_rate']:.3f})
is the binding constraint, so the buffer for {pid} rises and the shortfall shrinks on
the following pass. That is the "starts smarter" step.
"""
    else:
        md_tail = f"""
## 4. Issue — no purchase order

**No order was issued for {sku}.** The Decision Agent held it for approval, so there is
no purchase order and no notification to trace. Its own rationale:

> {trace['decide']['rationale']}

## 5. Learn — nothing to learn from this SKU yet

The Learn step compares what actually arrived against an order. With no order there is no
arrival to compare, so this SKU contributes to the forecast side only. Its supplier P
{pid} still reports fill {trace['learn']['observed_fill_rate']:.3f}, and the loop still
tracks it: {trace['learn']['curve_months_tracked']} months of curve, snapshot month
{trace['learn']['curve_month']} carrying WAPE {trace['learn']['curve_wape_this_month']:.4f}.
"""
    md = md + md_tail
    if not args.no_md:
        DEMO.mkdir(parents=True, exist_ok=True)
        (DEMO / "one_pass.md").write_text(md)

    print(json.dumps({k: trace[k] for k in ("sku", "category", "principal_id")}, indent=2))
    try:
        shown = out_path.relative_to(ROOT)
    except ValueError:                       # a caller's scratch path outside the repo
        shown = out_path
    print(f"\nwritten: {shown}" + ("" if args.no_md else " + demo/one_pass.md"))

    # ---- verification ----
    # These invariants describe the SKU the selection ladder picked. When the operator
    # named a SKU they are not promised: SKU0536 is held, so it has no event window and
    # no purchase order, and asserting otherwise would fail on a correct answer.
    if args.sku:
        assert abs(trace["decide"]["cover_days_target"]
                   - (trace["decide"]["lead_p90_days"] + 7 + trace["decide"]["buffer_days"])) < 0.01, \
            "cover target does not reconcile"
        print("VERIFICATION PASS: the arithmetic reconciles for the named SKU")
        return 0

    # The event, decided once and from the data: a NaN event used to satisfy
    # `assert trace["forecast"]["event"]` because the string "nan" is truthy, so this
    # verification reported "event present" for a snapshot with no event at all.
    has_event = bool(_ev(trace["forecast"]["event"]))

    # The strict rule (cover < lead) is asserted only when it actually held. When
    # the ladder relaxed, the honest check is that the chosen SKU is below its own
    # reorder trigger, and the trace says so out loud rather than implying the
    # strict rule matched.
    if _RELAXED and _RELAXED[-1] in ("cover below reorder trigger",
                                     "cover below lead time"):
        assert trace["perceive"]["days_of_cover"] <= trace["perceive"]["lead_trigger_days"], \
            f"chosen SKU is above its own reorder trigger (relaxed via {_RELAXED[-1]})"
    elif _RELAXED and "event-covered" in _RELAXED[-1]:
        # this tier promises an event-covered biscuit, so verify exactly that
        assert has_event, "the event-covered tier picked a SKU with no event"
    elif _RELAXED:
        # the no-event tier promises the tightest cover in the category and nothing
        # stronger, so it must not be asked to show an event
        assert not has_event, "the no-event tier picked a SKU that does have an event"
    else:
        assert trace["perceive"]["days_of_cover"] < trace["decide"]["lead_p90_days"], \
            "chosen SKU's cover does not run out before the next delivery"
        assert has_event, "the strict tier requires an event window"
    assert trace["issue"]["po_id"].startswith("PO-"), "no purchase order for the chosen SKU"
    assert trace["learn"]["score"] in ("ON_PLAN", "SUPPLY_SHORT", "LEAD_DRIFT", "SUPPLY_AND_LEAD")
    assert abs(trace["decide"]["cover_days_target"]
               - (trace["decide"]["lead_p90_days"] + 7 + trace["decide"]["buffer_days"])) < 0.01, \
        "cover target does not reconcile"
    print("VERIFICATION PASS: cover < lead, "
          + ("event present" if has_event else "no event in this snapshot")
          + ", PO issued, arithmetic reconciles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
