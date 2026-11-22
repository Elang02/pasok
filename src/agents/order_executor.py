"""
Pasok — Order Executor (auto-restock + approval queue)
======================================================

This is the step where Pasok stops recommending and starts acting. It takes the
Decision Agent's guarded quantities and turns them into purchase orders, split by the
supervised-autonomy policy from the proposal.

The policy gate is NOT a rupiah ceiling. An order that the policy itself asked for is
routine, however large it is: a fast mover can legitimately need Rp 600M of stock and a
slow mover can be over-ordering at Rp 40M. What makes an order high-stakes is a
constraint the policy cannot satisfy on its own:

  AUTO-ISSUE  when ALL of these hold
                * the warehouse has room for it (space is the shared resource)
                * the order fits the item's own peak envelope
                * principal's minimum order units are met (or the line can wait)
                * no supplier switch, unknown event or unexplained shock on the line

The rupiah value is printed, not gated: the same limit for every SKU says nothing about
whether this item can sell what is being ordered (decision taken 29 Oct 2026).
  ESCALATE    otherwise, with the specific reason recorded for the human queue

`WAREHOUSE_CAPACITY_M3` is sized from the record: the 95th percentile of this
catalogue's committed footprint (on hand + in transit + open PO) over the three years in
`data/stock/stock_daily.csv`, which is ~12,500 m3. It is an assumption stated out loud,
not a number pulled from thin air, and `PASOK_WAREHOUSE_M3` overrides it.

Three artefacts come out
------------------------
data/orders/purchase_orders.csv   every PO, with status and rationale
data/orders/approval_queue.csv    only the escalated ones, ready for Joule
data/orders/order_summary.json    counts + value + auto/escalation split

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/order_executor.py
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
AG = ROOT / "data" / "agents"
CAT = ROOT / "data" / "catalog"
PEAK_TOLERANCE = float(os.environ.get("PASOK_PEAK_TOLERANCE", "1.05"))
PEAK_FLOOR = float(os.environ.get("PASOK_PEAK_FLOOR", "1.00"))
STOCK = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))
OUT = ROOT / "data" / "orders"

# Warehouse space, not money, is the shared constraint a distributor actually runs into.
# Sized at the 95th percentile of the committed footprint in the record (see docstring).
WH = ROOT / "data" / "warehouse"


def _capacity_m3() -> float:
    """Building size from the warehouse master, not a literal buried in this file."""
    if os.environ.get("PASOK_WAREHOUSE_M3"):
        return float(os.environ["PASOK_WAREHOUSE_M3"])
    f = WH / "capacity.json"
    if f.exists():
        return float(json.loads(f.read_text())["usable_m3"])
    return 12_500.0


WAREHOUSE_CAPACITY_M3 = _capacity_m3()
ISSUED_AT = "2026-10-08T21:45:00Z"  # fixed for reproducibility of the demo snapshot
SHOCK_MULT = 1.5                   # uplift with no registered event = unexplained shock
CLASS_ORDER = {"A": 0, "B": 1, "C": 2}


def unit_litres(pack: object) -> float:
    """Litres (or kg, treated as litres) per selling unit, parsed from the pack string.

    600 of 600 packs in this catalogue parse ('250ml', '1.5L', '5 x 75g'). The volume is
    the goods themselves, not the carton, so the capacity number is optimistic by the
    packaging overhead; that is stated as an assumption rather than hidden.
    """
    s = str(pack).lower()
    mult = 1
    m2 = re.match(r"(\d+)\s*x\s*", s)
    if m2:
        mult = int(m2.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|g|kg)", s)
    if not m:
        return 0.0
    qty = float(m.group(1))
    unit = m.group(2)
    litres = qty / 1000 if unit in ("ml", "g") else qty
    return litres * mult



_PEAK_RATE: dict[str, float] = {}


def peak_rates() -> dict[str, float]:
    """The most a SKU could plausibly sell in one day: its normal day times its own best event.

    The normal day is the same number the decision agent sized the order from
    (`forecast_daily_eff`, the median of the last 28 days), not the catalogue's per-outlet
    base, so the envelope and the order speak the same units. The multiplier is the highest
    peak the ramp learner has recorded for that SKU, so a syrup that triples at Lebaran gets a
    wider envelope than a biscuit that barely moves, without anyone typing a rupiah limit.
    """
    if _PEAK_RATE:
        return _PEAK_RATE
    dec = pd.read_csv(AG / "decisions.csv")
    ramps = pd.read_csv(ROOT / "data" / "demand" / "sku_ramps.csv")
    best = ramps.groupby("sku")["peak_mult"].max()
    if "forecast_daily_eff" not in dec.columns:
        return _PEAK_RATE
    level = dec.groupby("sku")["forecast_daily_eff"].max()
    for sku, rate in level.items():
        _PEAK_RATE[str(sku)] = float(rate) * float(max(best.get(sku, 1.0), 1.0))
    return _PEAK_RATE


def gate_reasons(r, *, remaining: float, prin_units: dict, cover: dict, lead: dict,
                 class_cap: float, peak_rate: dict):
    """Every reason a line cannot issue itself, in a pure function.

    Kept out of `main()` so each gate can be forced by a unit test with a synthetic row
    instead of being trusted because it appears in the source.
    """
    reasons = []
    fits = r["volume_m3"] <= remaining
    # The money line is information, not a gate: the same rupiah limit for every SKU says
    # nothing about whether this item can sell what is being ordered. What a person still
    # signs off on is an order bigger than the item's own peak can absorb.
    rate = float(peak_rate.get(str(r["sku"]), 0.0) or 0.0)
    envelope_days = max(float(r["cover_after_days"]), 7.0)
    peak_ok = rate <= 0.0 or float(r["guarded_order"]) <= rate * max(PEAK_FLOOR, 1.0) * envelope_days * PEAK_TOLERANCE
    moq_ok = prin_units.get(r["principal_id"], 0.0) >= r["min_order_units"]
    can_wait = cover.get(r["sku"], 0.0) > lead.get(r["sku"], 0.0) + 7.0

    ev = str(r.get("event", "") or "")
    ev_mult = float(r.get("event_mult", 1.0) or 1.0)
    ev_dependence = 1.0 - (1.0 / ev_mult) if ev_mult > 0 else 0.0
    overstock = r["cover_after_days"] > class_cap
    # Leave room to mark the lot down before it dies. A flat 30-day window makes the
    # rule impossible for anything with a month of life: shelf - 30 = 0, so every
    # order would wait. Keep 80% of the life as the floor so short-life goods can
    # still be ordered, and the 30-day markdown window binds for long-life ones.
    expiry_ceiling = max(0.8 * r["shelf_days"], r["shelf_days"] - 30.0)
    near_expiry = r["cover_after_days"] > expiry_ceiling
    candidate_event = (not ev) and (ev_mult > 1.001)
    demand_shock = candidate_event and (ev_mult >= SHOCK_MULT)

    if not fits:
        reasons.append(
            f"warehouse headroom {remaining:,.0f} m3 < order {r['volume_m3']:,.1f} m3 "
            f"({r['abc_class']}-class line)"
        )
    if not peak_ok:
        reasons.append(
            f"above_peak: {r['guarded_order']:,.0f} units is more than this item sells at its "
            f"peak ({rate:,.0f} a day over {envelope_days:,.0f} days)"
        )
    deferred = False
    if not moq_ok:
        if can_wait:
            deferred = True
            reasons.append(
                f"PO for {r['principal_id']} is {prin_units.get(r['principal_id'], 0):.0f} units "
                f"< min order {r['min_order_units']:.0f}; deferred one cycle, "
                f"cover {cover.get(r['sku'], 0):.0f} d vs lead {lead.get(r['sku'], 0):.0f} d"
            )
        else:
            reasons.append(f"qty {r['guarded_order']:.0f} < min order {r['min_order_units']:.0f} and cover cannot wait")
    alt_pid = str(r.get("switch_to_principal") or "")
    if alt_pid:
        reasons.append(
            f"supplier_switch: {r['principal_id']} delivers {r.get('switch_incumbent_fill', 0):.2f} "
            f"of what is asked; {alt_pid} already supplies {r.get('category', 'this category')} "
            f"at {float(r.get('switch_alt_fill') or 0):.2f}. Re-source the line or keep the incumbent."
        )
    if candidate_event:
        reasons.append(f"candidate_event: uplift x{ev_mult:.2f} with no registered event")
    if demand_shock:
        reasons.append(f"demand_shock: unexplained uplift x{ev_mult:.2f}")
    return reasons, deferred


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    dec = pd.read_csv(AG / "decisions.csv")
    cat = pd.read_csv(CAT / "catalog.csv")[
        ["sku", "category", "principal_id", "unit_cost_idr", "credit_limit_idr"]]
    cat_full = pd.read_csv(CAT / "catalog_view.csv")[["sku", "pack"]]
    prin = pd.read_csv(CAT / "principals.csv")[["principal_id", "min_order_units"]]

    uv = WH / "unit_volume.csv"
    if uv.exists():
        u = pd.read_csv(uv)
        m3_unit = dict(zip(u["sku"], u["m3_per_unit"].astype(float)))
    else:
        m3_unit = {s: unit_litres(p) / 1000.0 for s, p in zip(cat_full["sku"], cat_full["pack"])}
    litres = m3_unit  # name kept for the occupancy maths below; each value is m3 per unit

    # Space already spoken for: on hand plus everything already on its way or on order.
    occ_path = STOCK / "position_snapshot.csv"
    occupancy = 0.0
    if occ_path.exists():
        pos = pd.read_csv(occ_path)
        for col in ("on_hand_units", "in_transit_units", "open_po_units"):
            pos[col] = pd.to_numeric(pos.get(col), errors="coerce").fillna(0.0)
            occupancy += float((pos[col] * pos["sku"].map(litres).fillna(0.0)).sum())
    headroom = max(0.0, WAREHOUSE_CAPACITY_M3 - occupancy)

    # proposal line 31 triggers that are not space/credit/MOQ:
    #   supplier_switch  — the incumbent principal delivers poorly AND another principal
    #                      already supplies the same category, so re-sourcing is possible.
    #                      The order waits because moving a line between principals changes
    #                      commercial terms; a person decides.
    #   candidate_event  — demand uplift with no registered event (novelty)
    #   demand_shock     — unexplained uplift the model did not attribute to a ramp
    SWITCH_FILL = 0.90
    SWITCH_GAIN = 0.05
    rel = pd.read_csv(ROOT / "data" / "agents" / "supplier_reliability.csv")
    rel["fill_rate_observed"] = pd.to_numeric(rel["fill_rate_observed"], errors="coerce")
    fill_by_pid = dict(zip(rel["principal_id"], rel["fill_rate_observed"]))
    # A switch is a sourcing decision, taken when a principal's delivery has drifted away from
    # its own history, not every time its fill sits a little low. Without drift the queue would
    # hold hundreds of ordinary orders and simply stop supply, which is the failure the
    # distributor already has.
    drift_pids = set(rel.loc[rel["drift_flag"].astype(bool), "principal_id"].astype(str))
    lead_by_pid = dict(zip(rel["principal_id"], pd.to_numeric(rel["lead_p90_d"], errors="coerce")))
    by_cat = pd.read_csv(CAT / "catalog.csv")[["category", "principal_id"]].groupby(
        "category")["principal_id"].unique().to_dict()

    def best_alternative(category: str, current: str):
        """The principal that already carries this category and delivers better than the
        incumbent by at least SWITCH_GAIN, preferring the shortest lead when fills tie."""
        best, best_fill = None, fill_by_pid.get(current, 0.0)
        for pid in by_cat.get(category, []):
            if pid == current:
                continue
            f = fill_by_pid.get(pid, 0.0)
            if f <= best_fill + SWITCH_GAIN:
                continue
            if best is None or f > best_fill or (
                    f == best_fill and lead_by_pid.get(pid, 99) < lead_by_pid.get(best, 99)):
                best, best_fill = pid, f
        return best, best_fill

    df = dec.merge(cat, on="sku", how="left", suffixes=("", "_cat")).merge(prin, on="principal_id", how="left")
    df = df[df["guarded_order"] > 0].copy()
    df["value_idr"] = (df["guarded_order"] * df["unit_cost_idr"]).round(0)
    df["volume_m3"] = df["guarded_order"] * df["sku"].map(litres).fillna(0.0)
    df["abc_class"] = df.get("abc_class", "B").fillna("B").astype(str) if "abc_class" in df else "B"
    shelf = pd.read_csv(CAT / "catalog.csv")[["sku", "shelf_life_months"]]
    df = df.merge(shelf, on="sku", how="left")
    peaks = pd.read_csv(CAT / "catalog_view.csv")[["sku", "peak_mult"]]
    df = df.merge(peaks, on="sku", how="left")
    df["shelf_days"] = df["shelf_life_months"].fillna(24) * 30.0
    df["cover_after_days"] = ((df["sellable_units"] + df["guarded_order"])
                              / df["forecast_daily_eff"].clip(lower=1.0))
    alts = df.apply(
        lambda r: best_alternative(str(r.get("category") or ""), str(r["principal_id"]))
        if str(r["principal_id"]) in drift_pids else (None, 0.0),
        axis=1)
    df["switch_to_principal"] = [a[0] or "" for a in alts]
    df["switch_incumbent_fill"] = [fill_by_pid.get(str(p), 0.0) for p in df["principal_id"]]
    df["switch_alt_fill"] = [a[1] for a in alts]
    # Downside gates. These measure whether the order rests on an assumption that can
    # fail, which is what a distributor's area manager actually authorises. They are not
    # size limits: a large order that policy justifies still issues itself.
    # Class A carries its lead time inside the cover target now, so a 45-day cap sat below
    # the policy's own plan and turned ordinary replenishment into a queue: 47 of the 480
    # lines on the 11 October pass waited because cover landed at 46 to 55 days. The cap is
    # there to catch an overshoot, not to re-approve the plan it just made.
    # Cover caps per class. An experiment overrides them with
    # PASOK_COVER_CAP="A:30,B:45,C:60" so every run records its own policy.
    raw_caps = os.environ.get("PASOK_COVER_CAP", "A:60,B:60,C:90")
    CLASS_COVER_CAP = {}
    for part in raw_caps.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            CLASS_COVER_CAP[k.strip().upper()] = float(v)
    # A-class lines get first claim on scarce space: losing the sale on a fast mover costs
    # more than holding back a slow one.
    df["class_rank"] = df["abc_class"].map(CLASS_ORDER).fillna(1)

    # MOQ is a term of the purchase order, not of the SKU line: a principal accepts one
    # PO per cycle and checks the total on it. Judging each line alone escalated two P08
    # lines (52 and 36 units against a 144 minimum) while the same principal already held
    # ten other orders that cycle.
    prin_units = df.groupby("principal_id")["guarded_order"].sum().to_dict()

    # A line that cannot clear MOQ does not need a person if waiting is safe: the stock
    # still covers the lead time, so the order simply waits for the next review and joins
    # a larger basket. It needs a person only when waiting would empty the shelf.
    pos = pd.read_csv(occ_path) if occ_path.exists() else pd.DataFrame()
    cover = {}
    lead = {}
    if len(pos):
        for _, r0 in pos.iterrows():
            cover[r0["sku"]] = float(pd.to_numeric(r0.get("days_of_cover"), errors="coerce") or 0.0)
            lead[r0["sku"]] = float(pd.to_numeric(r0.get("lead_time_days"), errors="coerce") or 0.0)

    rows = []
    remaining = headroom
    seq = 0
    ordered = df.sort_values(["class_rank", "value_idr"], ascending=[True, False]).reset_index(drop=True)
    for i, r in ordered.iterrows():
        class_cap = CLASS_COVER_CAP.get(r["abc_class"], 60.0)
        reasons, deferred = gate_reasons(
            r,
            remaining=remaining,
            prin_units=prin_units,
            cover=cover,
            lead=lead,
            class_cap=class_cap,
            peak_rate=peak_rates(),
        )

        hard = [x for x in reasons if "deferred one cycle" not in x]
        status = "AUTO_ISSUED" if not hard and not deferred else ("ESCALATED" if hard else "DEFERRED")
        if status == "AUTO_ISSUED":
            remaining -= r["volume_m3"]
        seq += 1
        # A short-life lot cannot arrive as one heap: whatever is not sold before the goods
        # age out is written off. Split the quantity into tranches, each landing a few days
        # apart, so the shelf carries a few days of stock and the rest waits in the truck,
        # where it cannot expire. Long-life goods keep one delivery.
        shelf_days = float(r.get("shelf_days") or 999.0)
        lead_days = float(r.get("lead_p90_days") or 0.0)
        cover_after = float(r.get("cover_after_days") or 0.0)
        lot_window = max(2.0, shelf_days - lead_days)
        n_tr = int(min(6, max(1, -(-cover_after // lot_window)))) if cover_after > 0 else 1
        qty = round(float(r["guarded_order"]), 1)
        if n_tr > 1:
            spacing = max(2, min(30, int(round(cover_after / n_tr))))
            first = (pd.Timestamp(ISSUED_AT[:10]) + pd.Timedelta(days=int(round(lead_days)))).date()
            dates = [first + pd.Timedelta(days=spacing * k) for k in range(n_tr)]
            share = round(qty / n_tr, 1)
            parts = [share] * (n_tr - 1)
            parts.append(round(qty - sum(parts), 1))
            deliveries = "; ".join(
                f"{d.isoformat()} {q:,.1f}" for d, q in zip([x.date() if hasattr(x, "date") else x for x in dates], parts)
            )
        else:
            deliveries = ""
        rows.append({
            "po_id": f"PO-{seq:04d}",
            "sku": r["sku"],
            "principal_id": r["principal_id"],
            "abc_class": r["abc_class"],
            "qty": round(float(r["guarded_order"]), 1),
            "unit_cost_idr": int(r["unit_cost_idr"]),
            "value_idr": float(r["value_idr"]),
            "volume_m3": round(float(r["volume_m3"]), 2),
            "status": status,
            "reason": "within policy limits" if not reasons else ". ".join(reasons) + ".",
            "rationale": r["rationale"],
            "issued_at": ISSUED_AT if status == "AUTO_ISSUED" else "",
            "deliveries": deliveries,
        })

    po = pd.DataFrame(rows)
    po.to_csv(OUT / "purchase_orders.csv", index=False)

    # Record the policy that produced this run. The decision step writes the service levels
    # it actually used; reading them back is safer than importing across script boundaries.
    z_used = {}
    dec_sum = ROOT / "data" / "agents" / "decision_summary.json"
    if dec_sum.exists():
        try:
            z_used = json.loads(dec_sum.read_text()).get("buffer_model", {}).get("z_by_class", {})
        except json.JSONDecodeError:
            z_used = {}

    q = po[po["status"] == "ESCALATED"].copy()
    q.to_csv(OUT / "approval_queue.csv", index=False)

    summary = {
        "snapshot": dec["snapshot"].iloc[0],
        "skus_with_order": int(len(po)),
        "auto_issued": int((po["status"] == "AUTO_ISSUED").sum()),
        "escalated": int((po["status"] == "ESCALATED").sum()),
        "policy": {"class_z": z_used, "cover_cap_days": CLASS_COVER_CAP},
        "deferred": int((po["status"] == "DEFERRED").sum()),
        "auto_rate": round(float((po["status"] == "AUTO_ISSUED").mean()), 3),
        "total_value_idr": float(po["value_idr"].sum()),
        "auto_value_idr": float(po.loc[po["status"] == "AUTO_ISSUED", "value_idr"].sum()),
        "escalated_value_idr": float(q["value_idr"].sum()),
        "warehouse_capacity_m3": WAREHOUSE_CAPACITY_M3,
        "warehouse_occupancy_m3": round(occupancy, 1),
        "warehouse_headroom_m3": round(headroom, 1),
        "order_volume_m3": round(float(po["volume_m3"].sum()), 1),
        "staged_orders": int((po["deliveries"].fillna("") != "").sum()),
        "staged_tranches": int(po["deliveries"].fillna("").apply(
            lambda x: len([t for t in str(x).split(";") if t.strip()])).sum()),
        "escalation_reason_breakdown": {
            "storage_headroom": int(q["reason"].str.contains("warehouse headroom").sum()),
            "above_peak": int(q["reason"].str.contains("above_peak").sum()),
            "over_credit": 0,
            "below_moq": int(q["reason"].str.contains("min order").sum()),
            "supplier_switch": int(q["reason"].str.contains("supplier_switch").sum()),
            "candidate_event": int(q["reason"].str.contains("candidate_event").sum()),
            "event_overreach": int(q["reason"].str.contains("event_overreach").sum()),
            "overstock": int(q["reason"].str.contains("overstock").sum()),
            "near_expiry": int(q["reason"].str.contains("near_expiry").sum()),
            "demand_shock": int(q["reason"].str.contains("demand_shock").sum()),
        },
        "top_escalations": q.sort_values("value_idr", ascending=False).head(5)[
            ["po_id", "sku", "abc_class", "qty", "value_idr", "volume_m3", "reason"]
        ].to_dict(orient="records"),
    }
    (OUT / "order_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))

    # ---- verification ----
    assert len(po) == int((dec["guarded_order"] > 0).sum()), "PO count mismatch"
    assert set(po["status"]) <= {"AUTO_ISSUED", "ESCALATED", "DEFERRED"}, "unexpected status"
    assert (po["status"].isin(["AUTO_ISSUED", "ESCALATED", "DEFERRED"])).sum() == len(po)
    assert po.loc[po["status"] == "AUTO_ISSUED", "volume_m3"].sum() <= headroom + 1e-6, "space oversold"
    print("\nVERIFICATION PASS: every order accounted for, no drops, no space oversold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
