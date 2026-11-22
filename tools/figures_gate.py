"""Gate demo/figures.md against the artefacts each row cites.

The sheet used to be hand-maintained, so every rebuild left a handful of rows
quoting the previous generation. This gate rebuilds the Value column from the
files themselves: the doc cannot drift from the run without failing here.

    cd /home/ubuntu/pasok
    .venv/bin/python tools/figures_gate.py          # check, exit 1 on drift
    .venv/bin/python tools/figures_gate.py --write  # rewrite the Value column

`--write` only touches the table body; the header and the Notes section are
hand-written prose and stay where they are.
"""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "demo" / "figures.md"
ROW = re.compile(r"^\| (F\d+) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$")


# --------------------------------------------------------------------- loaders ---
@lru_cache(maxsize=None)
def load_json(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text())


@lru_cache(maxsize=None)
def load_rows(rel: str) -> list[dict]:
    with (ROOT / rel).open(newline="") as fh:
        return list(csv.DictReader(fh))


def num(x: float, dp: int = 1) -> str:
    """English number style, matching the rest of the sheet: 6,285.8 not 6.285,8."""
    return f"{x:,.{dp}f}"


def whole(x: float) -> str:
    return f"{int(round(x)):,}"


def idr(x: float) -> str:
    return f"IDR {whole(x)}"


# --------------------------------------------------------------------- figures ---
def spec(dec: dict, order: dict, pos: dict, learn: dict) -> dict[str, str]:
    """Every value the sheet quotes, computed once from the artefacts."""
    g = {}

    sim = load_json("simulation/results.json")
    g["F1"] = f"{sim['unguarded']['amplification']:.2f}x demand variance"
    g["F2"] = f"{sim['guarded']['amplification']:.2f}x demand variance"
    g["F3"] = f"{sim['unguarded']['fill_rate']:.4f}"
    g["F4"] = f"{sim['guarded']['fill_rate']:.4f}"
    g["F5"] = f"{sim['days']} days ({sim['warmup']} warmup)"

    e2 = load_json("experiments/e2_results.json")
    a = e2["E2a_event_ramp"]
    g["F6"] = f"{a['overall_wape']['ramp']:.4f}"
    g["F7"] = f"{a['overall_wape']['flat_bump']:.4f}"
    g["F8"] = f"+{a['improvement_pct']['ramp_vs_flat_bump_pct']:.2f}%"
    g["F9"] = whole(a["windows_tested"])

    g["F10"] = f"{dec['n_skus']} SKUs"
    g["F11"] = whole(dec["orders_placed"])
    amp = dec["amplification"]
    g["F12"] = f"{amp['guarded']:.2f}x (raw {amp['raw']:.2f}x)"
    g["F13"] = f"-{amp['reduction_pct']:.1f}%"

    g["F14"] = f"{order['auto_issued']} of {order['skus_with_order']}"
    g["F15"] = f"{order['escalated']}, worth {idr(order['escalated_value_idr'])}"
    g["F16"] = idr(order["total_value_idr"])

    cap = order["policy"]["cover_cap_days"]
    g["F17"] = (
        "the sizing policy itself: p90 lead + 7-day review + class buffer, capped by "
        f"class cover (A {cap['A']:.0f} / B {cap['B']:.0f} / C {cap['C']:.0f} days). "
        "A person signs only when an order exceeds the item's own peak envelope "
        "(normal day x its best event over the days it covers); the rupiah credit line is "
        "information, not a gate"
    )

    br = order["escalation_reason_breakdown"]
    tail = (
        " (no line carries both)"
        if order["escalated"] and int(br.get("above_peak", 0)) + br["supplier_switch"] == order["escalated"]
        else ""
    )
    near = int(br.get("near_expiry", 0) or 0)
    g["F18"] = (
        f"{int(br.get('above_peak', 0) or 0)} above the item's peak envelope, "
        f"{br['supplier_switch']} supplier-switch decision, "
        f"{near} near-expiry hold{tail}"
    )

    sc = pos["sellable_composition"]
    g["F19"] = (
        f"on-hand {num(sc['on_hand_total'], 0)} + in-transit {num(sc['in_transit_total'])} "
        f"+ open PO {num(sc['open_po_total'])} = {num(sc['sellable_total'])} u"
    )
    g["F20"] = f"{sc['skus_with_open_po']} / {sc['skus_with_in_transit']}"

    z = dec["buffer_model"]["z_by_class"]
    g["F21"] = (
        "z by class · sqrt(lead_var^2 + forecast_err^2), min 2 d, capped by shelf life; "
        f"A {z['A']}, B {z['B']}, C {z['C']}"
    )

    pp = dec["buffer_model"]["per_principal"]
    days = [v["buffer_days"] for v in pp.values()]
    g["F22"] = f"per principal, {min(days):.0f} to {max(days):.0f} days across {len(pp)} principals"

    notif = load_json("data/orders/notification_summary.json")["by_status"]
    _st = notif.get("by_status", notif)
    g["F23"] = f"{_st.get('SENT', 0)} SENT / {_st.get('HELD_FOR_APPROVAL', 0)} HELD_FOR_APPROVAL"

    red = load_json("data/orders/redirect_summary.json")
    g["F24"] = f"{red['excess_skus']} SKUs across {red['depots_used']} depots"

    g["F25"] = whole(load_json("data/orders/supplier_switch_summary.json")["proposals"])

    sd = learn["score_distribution"]
    g["F26"] = f"{learn['n_decisions']} rows, one per PO ({', '.join(f'{k} {v}' for k, v in sd.items())})"
    g["F27"] = f"{learn['observed_fill_rate_mean']:.4f}"

    base = [float(r["wape_best"]) for r in load_rows("data/demand/baselines.csv") if r["wape_best"]]
    base.sort()
    med = (base[len(base) // 2] + base[(len(base) - 1) // 2]) / 2
    g["F28"] = (
        f"{learn['forecast_wape_best_median']:.4f} median on the {learn['n_decisions']} SKUs this run "
        f"decided; {med:.4f} across all {len(base)} in baselines.csv"
    )

    rpt = load_json("data/sap/rpt_summary.json")
    g["F29"] = f"{rpt['agreement_with_agent_below_reorder']:.3f}"

    rat = load_rows("data/sap/rationales.csv")
    model = next((r["model"] for r in rat if r.get("model")), "the orchestration deployment")
    n_tpl = sum(1 for r in rat if r.get("source") != "orchestration")
    held = {r["sku"] for r in load_rows("data/orders/approval_queue.csv")}
    g["F30"] = (
        f"{len(rat)} lines written by {model} via SAP orchestration, {n_tpl} template fallback "
        f"(queue of 21 Oct; 0 of today's {len(held)} held lines re-called)"
    )

    curve = load_rows("data/agents/learn_curve.csv")
    g["F31"] = f"{len(curve)} months in `learn_curve.csv`"
    wapes = [float(r["wape"]) for r in curve]
    g["F32"] = f"{min(wapes):.4f} to {max(wapes):.4f}, mean {sum(wapes) / len(wapes):.3f}"

    events = {r["date"][:7] for r in load_rows("data/catalog/events.csv")}
    worst = sorted(curve, key=lambda r: -float(r["wape"]))[:8]
    hit = sum(1 for r in worst if r["month"] in events)
    g["F33"] = f"{hit} of top-8"

    g["F34"] = "Mantle endpoint; native Converse is account-gated"

    ramp = load_json("data/demand/ramp_summary.json")["ramp_class_counts"]
    g["F35"] = f"ramped {whole(ramp['ramped'])} / step {whole(ramp['step'])}"

    g["F36"] = "SIZE / HOLD_ONE_CYCLE, then AUTO_ISSUE / DEFER / ESCALATE / REDIRECT"

    intake = load_json("data/orders/intake_summary.json")
    g["F37"] = (
        f"{intake['submitted']} submitted, {intake['accepted_full']} full + "
        f"{intake['accepted_partial']} partial, {intake['rejected_by_system']} refused; "
        f"{whole(intake['units_accepted'])} of {num(intake['units_ordered'])} units accepted "
        f"({100 * intake['units_accepted'] / intake['units_ordered']:.1f}%)"
    )

    g["F38"] = (
        f"{num(order['warehouse_capacity_m3'], 0)} m3 usable, {num(order['warehouse_occupancy_m3'])} committed, "
        f"{num(order['order_volume_m3'])} m3 ordered, {num(order['warehouse_headroom_m3'])} free"
    )

    cls = load_rows("data/demand/sku_classes.csv")
    per = {}
    share = {}
    for c in ("A", "B", "C"):
        rows = [r for r in cls if r["class_volume"] == c]
        per[c] = len(rows)
        share[c] = sum(float(r["total_value_idr"]) for r in rows)
    total = sum(share.values())
    g["F39"] = (
        f"{per['A']} A / {per['B']} B / {per['C']} C; "
        f"A carries {100 * share['A'] / total:.1f}% of value"
    )

    def replay_line(name: str) -> str:
        days = load_rows(f"data/sim/{name}/days.csv")
        sold = sum(float(d["sold_units"]) for d in days)
        lost = sum(float(d["lost_units"]) for d in days)
        decided = sum(float(d["decided_skus"]) for d in days)
        return (
            f"{len(days)} days, sold {whole(sold)} u, lost {whole(lost)} u "
            f"({100 * lost / (sold + lost):.2f}%), {whole(decided)} decided lines"
        )

    # the canonical replay moves as policy changes; read it from one place
    canon = os.environ.get("PASOK_REPLAY", "replay2026_v29")
    g["F40"] = replay_line(canon)
    o = load_json("data/agents/outcomes.json")
    out = o["outcomes"]
    g["F41"] = (
        f"fill A {out['fill_A']['value'] * 100:.1f}% vs 92% retail shelf availability; "
        f"{out['dio_days']['value']:.0f} days of inventory vs 57 at Indofood CBP; "
        f"expiry {out['expiry_pct_of_cogs']['value'] * 100:.2f}% of cost vs 2.70% shrink"
    )

    econ = load_json("data/agents/economics.json")["scenarios"]["dpo30"]
    cost = econ["cost"]
    lost_margin = econ["lost_demand"]["margin_lost_idr"]["10pct"]
    g["F42"] = (
        f"physical carrying {idr(cost['physical_carrying_idr'])}; financing "
        f"{idr(cost['financing_idr'])} at DPO 30; total {idr(cost['total_idr'])}; "
        f"lost margin {idr(lost_margin)} at a 10% assumption"
    )
    return g


def compare_replays() -> str:
    """F41: the three-way comparison, read from the tool that defines it."""
    out = {}
    for a, b in (("replay2026_v2", "replay2026_v3"), ("replay2026_v3", "replay2026_v4")):
        res = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "compare_replays.py"),
             str(ROOT / "data" / "sim" / a), str(ROOT / "data" / "sim" / b)],
            capture_output=True, text=True, cwd=ROOT, check=True,
        )
        for line in res.stdout.splitlines():
            if line.startswith(("replay2026_v2", "replay2026_v3", "replay2026_v4")):
                parts = line.split()
                out[parts[0]] = (float(parts[4]), float(parts[6]))
    order = ["replay2026_v2", "replay2026_v3", "replay2026_v4"]
    bits = [f"v{name[-1]} {out[name][0]:.3f}% lost at Rp {out[name][1]:.1f}bn inventory" for name in order]
    return "; ".join(bits)


# ------------------------------------------------------------------------ main ---
def main() -> int:
    write = "--write" in sys.argv
    text = SHEET.read_text()
    lines = text.splitlines()

    dec = load_json("data/agents/decision_summary.json")
    order = load_json("data/orders/order_summary.json")
    pos = load_json("data/stock/position_summary.json")
    learn = load_json("data/agents/learn_summary.json")
    want = spec(dec, order, pos, learn)

    seen, drift, out = set(), [], []
    for line in lines:
        m = ROW.match(line)
        if not m:
            out.append(line)
            continue
        fid, label, old, source, regen = m.groups()
        seen.add(fid)
        new = want.get(fid)
        if new is None:
            drift.append(f"{fid}: no spec in this gate, row is unverified")
            out.append(line)
            continue
        if new != old:
            drift.append(f"{fid}: doc says {old!r}, artefacts say {new!r}")
            out.append(f"| {fid} | {label} | {new} | {source} | {regen} |")
        else:
            out.append(line)

    missing = sorted(set(want) - seen, key=lambda f: int(f[1:]))
    if missing:
        drift.append(f"rows missing from the sheet: {', '.join(missing)}")

    if write and drift:
        SHEET.write_text("\n".join(out) + "\n")
        print(f"WROTE {SHEET.relative_to(ROOT)}: {len(drift)} row(s) brought in line")
        for d in drift:
            print(f"  {d}")
        return 0

    if drift:
        print(f"FAIL: {SHEET.relative_to(ROOT)} disagrees with the artefacts")
        for d in drift:
            print(f"  {d}")
        print("\nrun: .venv/bin/python tools/figures_gate.py --write")
        return 1

    print(f"PASS: {len(want)} figures in {SHEET.relative_to(ROOT)} match the artefacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
