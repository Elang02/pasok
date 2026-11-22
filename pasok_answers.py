"""
Pasok: agent answers, read only
===============================

Turns the artefacts produced by the four agents into short markdown answers so
the A2A server (and SAP Joule behind it) can talk in words. No model call runs
here: these are the numbers the agents wrote, shown and merged.

    answer(intent="summary")            network summary
    answer(intent="sku", target=...)    one SKU's decision
    answer(intent="exceptions")         the SKU exception queue
    answer(intent="order", target=...)  where a PO ends up
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
AG = ROOT / "data" / "agents"
ORD = ROOT / "data" / "orders"
DEM = ROOT / "data" / "demand"
STOCK = ROOT / "data" / "stock"
SAP = ROOT / "data" / "sap"


def _json(p: pathlib.Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def _idr(v: float) -> str:
    return f"IDR {v:,.0f}"


def _decisions() -> pd.DataFrame:
    """Decision rows joined with the stock position they were made against."""
    d = pd.read_csv(AG / "decisions.csv")
    snap = pd.read_csv(STOCK / "position_snapshot.csv")
    keep = [c for c in ("sku", "days_of_cover", "expiry_risk", "on_hand_units",
                        "in_transit_units", "open_po_units") if c in snap.columns]
    return d.merge(snap[keep], on="sku", how="left")


ACTION_PLAIN = {
    "SIZE": "an order was placed",
    "ISSUE_PO": "an order was placed",
    "HOLD_ONE_CYCLE": "no order this cycle, the stock on hand already covers the horizon",
    "ESCALATE_TO_HUMAN": "waiting for a person to decide",
    "REDIRECT_TO_OTHER_SKU": "the order went to another SKU instead",
}


def _plain_event(v) -> str:
    """A missing event arrives as NaN and would print as nan."""
    s = "" if v is None else str(v)
    if s.strip().lower() in ("", "nan", "none", "no_event", "no event"):
        return "none"
    return s.replace("_", " ")


def _plain_units(v) -> str:
    """17521.3u is not a number a reader can use."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "0 units"
    if f != f:
        return "0 units"
    return f"{f:,.0f} units"


def _plain_pct(v) -> str:
    """0.850 is a share. A buyer reads 85%."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "unknown"
    if f != f:
        return "unknown"
    return f"{f * 100:.1f}%" if 0.0 <= f <= 1.0 else f"{f:.1f}%"


def _plain_reason(s) -> str:
    """The queue stores its reason as a machine comparison. Say it in words."""
    import re
    t = str(s or "").strip()
    m = re.match(r"value\s+([\d.,]+)M\s*>\s*auto limit\s+([\d.,]+)M", t)
    if m:
        return (f"the order is worth about IDR {float(m.group(1).replace(',', '')) * 1e6:,.0f}, "
                f"over the IDR {float(m.group(2).replace(',', '')) * 1e6:,.0f} ceiling for "
                f"orders placed without a person")
    m = re.match(r"qty\s+([\d.,]+)\s*<\s*min order\s+([\d.,]+)", t)
    if m:
        return (f"{float(m.group(1).replace(',', '')):,.0f} units is under that supplier's "
                f"minimum of {float(m.group(2).replace(',', '')):,.0f} units")
    return t.replace("_", " ")


def _plain_action(v) -> str:
    """A stored action value is not a sentence. Never let the code reach the reader."""
    s = "" if v is None else str(v)
    if s in ("", "nan", "None"):
        return "no decision recorded"
    return ACTION_PLAIN.get(s, s.replace("_", " ").lower())


def summary() -> str:
    dec = _json(AG / "decision_summary.json")
    orders = _json(ORD / "order_summary.json")
    rpt = _json(SAP / "rpt_summary.json")
    amp = dec.get("amplification", {})
    esc = orders.get("escalated", 0)
    placed = dec.get("orders_placed") or orders.get("skus_with_order", 0)
    return "\n".join([
        "## Pasok network summary",
        "",
        f"- **{dec.get('n_skus')} SKUs** assessed",
        f"- Orders placed: **{placed}**, of them {orders.get('auto_issued')} without a "
        f"person and {esc} waiting for one",
        f"- Share the system placed on its own: **{_plain_pct(orders.get('auto_rate'))}**",
        f"- Value placed this morning: **{_idr(float(_json(ORD / 'last_run.json').get('value_placed_idr') or 0))}**",
        *(
            ["- Nothing is waiting for a person: every line cleared its gates, so the approval "
             "queue is empty"]
            if not esc else
            [f"- Value awaiting approval: {_idr(orders.get('escalated_value_idr') or 0)}"]
        ),
        f"- How much orders swing compared with demand: **{amp.get('raw')} times** without "
        f"the order rule, **{amp.get('guarded')} times** with it, "
        f"a {amp.get('reduction_pct')}% drop",
        f"- The SAP RPT-1.6 model agreed with our own reorder signal on "
        f"{_plain_pct(rpt.get('agreement_with_agent_below_reorder'))} of the "
        f"{rpt.get('n_predictions')} SKUs it scored",
    ])


def sku_decision(sku: str) -> str:
    d = _decisions()
    row = d[d["sku"].str.upper() == sku.upper()]
    if row.empty:
        return f"`{sku}` is not in the decision list ({len(d)} SKUs assessed)."
    r = row.iloc[0]
    out = [
        f"## {r['sku']}: {_plain_action(r.get('action'))}",
        "",
        f"- Stock left: **{r.get('days_of_cover')} days**, against the {r.get('cover_days_target')} "
        f"days this SKU is planned to hold",
        f"- Supplier {r.get('principal_id')} worst-case delivery time: "
        f"**{r.get('lead_p90_days')} days**. On top of that the planner adds "
        f"{r.get('buffer_days')} days, {r.get('buffer_lead_var_contrib_d')} for how much "
        f"delivery time varies and {r.get('buffer_forecast_err_contrib_d')} for how much "
        f"the forecast misses",
        f"- Demand event in that window: "
        f"**{_plain_event(r.get('event'))}**",
        f"- Forecast: {_plain_units(r.get('forecast_daily'))} a day normally, "
        f"{_plain_units(r.get('forecast_daily_eff'))} a day once the event is counted",
        f"- Order: {_plain_units(r.get('raw_order'))} asked for, "
        f"**{_plain_units(r.get('guarded_order'))}** after the order rule",
    ]
    flags = r.get("guardrail_flags")
    if isinstance(flags, str) and flags.strip() and flags.strip().lower() not in ("nan", "none", "[]"):
        out.append(f"- Order rule flags: {flags}")
    if isinstance(r.get("rationale"), str) and r["rationale"]:
        out += ["", "**Why:** " + str(r["rationale"])]
    return "\n".join(out)


def exceptions(limit: int = 10) -> str:
    d = _decisions()
    esc = d[d["action"].astype(str).str.contains("ESCALAT|HOLD|REDIRECT", case=False, na=False)]
    if esc.empty:
        esc = d.nsmallest(limit, "days_of_cover")
    head = esc.head(limit)
    # Two different states were merged under one label. The approval queue holds the
    # orders that genuinely wait for a person (six of them); the held SKUs need nothing
    # from anyone, because the stock on hand already covers the horizon. Calling all of
    # them "waiting for a person" overstated the human workload by two orders of magnitude,
    # and the queued SKUs are not even in the held set.
    q = ORD / "approval_queue.csv"
    try:
        waiting = pd.read_csv(q) if q.exists() else pd.DataFrame()
    except Exception:                                          # noqa: BLE001
        waiting = pd.DataFrame()
    held = esc
    value = float(waiting["value_idr"].sum()) if len(waiting) else 0.0
    lines = [
        f"## {len(held) + len(waiting)} SKUs need a look, {len(waiting)} of them a person", "",
        f"- **{len(waiting)} orders are waiting for a person** to decide, worth {_idr(value)}. "
        f"Each is either over the ceiling for orders placed without a person, or under the "
        f"supplier's minimum order.",
        f"- **{len(held)} SKUs were held**: the stock on hand already covers the horizon, so "
        f"an order now would add stock they cannot sell in time. Nobody has to look at these.",
        "",
        "| decision | order | SKU | principal | value | why a person is needed |",
        "|---|---|---|---|---|---|",
    ]
    for _, r in waiting.head(limit).iterrows():
        lines.append(f"| approve or reject | {r.get('po_id')} | {r.get('sku')} | "
                     f"{r.get('principal_id')} | {_idr(float(r.get('value_idr') or 0))} | "
                     f"{_plain_reason(r.get('reason'))} |")
    lines += ["",
              f"First {min(limit, len(held))} of the {len(held)} held SKUs:", "",
              "| SKU | days of stock left | principal | demand event | why it was held |",
              "|---|---|---|---|---|"]
    for _, r in held.head(limit).iterrows():
        lines.append(f"| {r['sku']} | {r.get('days_of_cover')} | {r.get('principal_id')} | "
                     f"{_plain_event(r.get('event'))} | the stock on hand already covers "
                     f"the horizon |")
    return "\n".join(lines)


def order_status(po: str) -> str:
    p = ORD / "order_acks.csv"
    if not p.exists():
        return "Order Intake has never run: no order_acks.csv file."
    a = pd.read_csv(p)
    hit = a[a["po_id"].str.upper() == po.upper()]
    if hit.empty:
        return (f"`{po}` is not in the intake record: the order may never have been "
                f"issued, or it is awaiting approval and still undecided.")
    r = hit.iloc[0]
    return "\n".join([
        f"## {r['po_id']}: {r.get('status', 'sent')}",
        "",
        f"- Reference number from the ordering system: **{r.get('reference')}**",
        f"- SKU {r.get('sku')}, principal {r.get('principal_id')}",
        f"- Units ordered {_plain_units(r.get('units_ordered'))}, "
        f"**{_plain_units(r.get('units_accepted'))}** accepted"
        + ("" if str(r.get("acceptance")) in ("FULL", "full", "nan", "") else
           " (" + str(r.get("acceptance")).replace("_", " ").lower() + ")"),
        f"- Value {_idr(float(r.get('value_idr') or 0))}",
        f"- Promised delivery: {r.get('promised_delivery')}",
    ])


def _rows(p):
    """Every row of a csv artefact, or nothing when the file is not there."""
    import csv as _csv
    try:
        with p.open() as fh:
            return list(_csv.DictReader(fh))
    except Exception:                                          # noqa: BLE001
        return []


def _f(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _order_value(rows) -> float:
    """What the orders in `rows` are worth, at the catalogue's unit cost."""
    import csv as _csv
    try:
        cost = {r["sku"]: float(r["unit_cost_idr"])
                for r in _csv.DictReader((ROOT / "data" / "catalog" / "catalog.csv").open())}
    except Exception:                                          # noqa: BLE001
        return 0.0
    total = 0.0
    for r in rows:
        try:
            total += float(r.get("order") or 0) * cost.get(r.get("sku"), 0.0)
        except (TypeError, ValueError):
            continue
    return total


def stockout_within_a_week(limit: int = 12) -> str:
    """TC-1: what runs out of stock within a week (from the test-case run)."""
    tc = _json(AG / "test_cases.json").get("tc1")
    if not tc:
        return "The test cases have never run: `python tools/test_cases.py`."
    s = tc["summary"]
    lines = [
        "## Stock that runs out in the next seven days",
        "",
        f"- **{s['skus_cover_le_7d']} of {s['total_skus']} SKUs** have 7 days of stock left or less",
        f"- **{s['of_which_die_before_next_delivery']}** of them run out before the next "
        f"delivery could arrive, which is the case where ordering now is already too late",
        # This line used to read "Value of the stock that runs out: IDR 0", which tells a
        # reader nothing: the stock does run out, and the zero only means none of it runs
        # out before the next delivery. The value that carries meaning is what the loop is
        # spending to cover those SKUs, so that is the number here.
        f"- Value of the orders the loop placed for them: "
        f"{_idr(_order_value(tc['top']))}",
        f"- The loop placed an order for {s['given_an_order_by_the_loop']} of "
        f"{s['skus_cover_le_7d']}: {s['po_auto_issued']} without a person, "
        f"{s['po_escalated_to_a_human']} waiting for one",
        "",
        "| SKU | category | principal | available now | sold per day | days of stock left | delivery time | ordered |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in tc["top"][:limit]:
        lines.append(f"| {r['sku']} | {r['category']} | {r['principal']} | "
                     f"{r['sellable']:.0f} | {r['velocity_day']:.0f} | {r['cover_d']} | "
                     f"{r['lead_d']} | {r['order']:.0f} |")
    return "\n".join(lines)


def spike_within_a_month(limit: int = 12) -> str:
    """TC-2: what needs more stock for a spike arriving within a month."""
    tc = _json(AG / "test_cases.json").get("tc2")
    if not tc:
        return "The test cases have never run: `python tools/test_cases.py`."
    s = tc["summary"]
    ev = s["event_windows_in_horizon"]
    ev_txt = ", ".join(
        f"{e['event']} peaks on {e['peak_day_the_loop_planned_for']}, when demand runs "
        f"{e['ramp_mult_min']} to {e['ramp_mult_max']} times normal" for e in ev) or "none"
    lines = [
        "## Stock that needs topping up for a spike within a month",
        "",
        f"- Snapshot {s['snapshot_date']}, horizon to {s['horizon_end']}",
        f"- Demand events in that horizon: **{ev_txt}**",
        f"- **{s['skus_with_a_spike']} SKUs** sell more during those events",
        f"- Extra units those events call for: **{s['extra_units_implied']:,.0f}** "
        f"({_idr(s['extra_value_implied_idr'])})",
        f"- Of those, {s['already_covered_by_the_loop']} got an order and "
        f"{s['skus_with_a_spike'] - s['already_covered_by_the_loop']} were held, because "
        f"the stock on hand already covers that horizon",
        "",
        "| SKU | category | principal | demand event | times normal | usual per day | during the event | extra units |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in tc["top"][:limit]:
        lines.append(f"| {r['sku']} | {r['category']} | {r['principal']} | {r['event']} | "
                     f"{r['ramp_uplift']} | {r['base_day']:.0f} | {r['spiked_day']:.0f} | "
                     f"{r['extra_units']:,.0f} |")
    return "\n".join(lines)


# ------------------------------------------------------------------- routing
INTENT_WORDS = [
    ("event", ["lebaran", "idul fitri", "ramadan", "ramadhan", "imlek", "natal",
               "christmas", "tahun baru", "new year", "event", "musim",
               "lonjakan saat", "saat lebaran"]),
    ("supplier", ["principal", "supplier", "lambat", "terlambat", "kurang kirim",
                  "lead time", "tepat waktu", "fill rate", "paling lambat"]),
    ("accuracy", ["akurat", "akurasi", "wape", "galat", "ramalan", "seberapa benar",
                  "seberapa akurat", "salah ramal", "forecast"]),
    ("stockout", ["run out", "runs out", "habis", "stockout", "kehabisan", "kosong"]),
    ("spike", ["spike", "lonjak", "ramp", "within a month", "bulan depan"]),
    ("receiving", ["datang", "diterima", "penerimaan", "kiriman", "received",
                   "arrived", "telat", "late", "short delivery", "missing goods"]),
    ("geography", ["kota", "city", "cities", "outlet", "warung", "minimarket", "kiosk",
                   "jakarta", "tangerang", "bekasi", "bogor", "depok", "mana yang menjual",
                   "where does it sell"]),
    ("transfers", ["transfer", "pindah stok", "depot", "gudang", "cabang", "redistribusi",
                   "kirim ke cabang"]),
    ("health", ["kedaluwarsa", "kadaluarsa", "expiry", "expire", "umur simpan", "shelf life",
                "menumpuk", "lambat laku", "slow moving", "overstock", "kelebihan stok",
                "nilai stok", "stock value", "berapa stok", "kelas abc", "abc"]),
    ("exceptions", ["exception", "queue", "antrian", "pengecualian", "escalat",
                    "manusia", "waiting for a person"]),
    ("summary", ["perform", "network", "jaringan", "keseluruhan", "ringkas", "summary"]),
]

EVENT_NAMES = ("lebaran", "idul fitri", "ramadan", "ramadhan", "imlek", "natal",
               "christmas", "tahun baru", "new year")


def route_question(text: str) -> tuple:
    """Which set of facts a question is asking about, and about what.

    ONE router for the console. There used to be two: this word list lived in the chat
    lane while the answer lane kept an older, narrower copy with no event, supplier or
    accuracy words. Asking the console "what is the nearest event" therefore fell through
    to the network summary, and the model had to open its answer by saying the facts it was
    given did not answer the question.
    """
    import re
    low = (text or "").lower()
    m = re.search(r"SKU\d+", text or "", re.IGNORECASE)
    if m:
        return "sku", m.group(0).upper()
    m = re.search(r"PO-?\s?\d+", text or "", re.IGNORECASE)
    if m:
        d = re.search(r"\d+", m.group(0))
        return "order", f"PO-{d.group(0)}" if d else ""
    named = next((w for w in EVENT_NAMES if w in low), "")
    for intent, words in INTENT_WORDS:
        if any(w in low for w in words):
            return intent, named
    return "summary", ""


def _snapshot_day():
    """The date the loop's numbers describe, read from an artefact, never typed here."""
    for p in (AG / "decision_summary.json", AG / "learn_summary.json"):
        try:
            d = json.loads(p.read_text())
        except Exception:                                      # noqa: BLE001
            continue
        for k in ("snapshot", "snapshot_date", "as_of", "latest_window"):
            if d.get(k):
                try:
                    return pd.Timestamp(str(d[k])[:10])
                except Exception:                              # noqa: BLE001
                    continue
    return None


def _event_calendar() -> list:
    """The next occurrence of each event after the snapshot, earliest first.

    The step rule lives in src/agents/decision.py, so one place decides when an event
    happens. A date is what makes this answer usable: "Lebaran" on its own is not an
    answer to an ordinary reader, and here it was also the wrong event.
    """
    snap = _snapshot_day()
    if snap is None:
        return []
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "src" / "agents"))
        import decision as _d
        cal = pd.read_csv(DEM / "event_registry.csv")
        ramps = pd.read_csv(DEM / "sku_ramps.csv")
        out = [{"event": e, "date": d, "days": int((d - snap).days), "factor": float(f)}
               for e, d, f in _d.event_windows(cal, ramps, snap)]
    except Exception:                                          # noqa: BLE001
        return []
    out.sort(key=lambda x: x["days"])
    return out


def event_impact(event: str = "", limit: int = 15) -> str:
    """Which goods a named Indonesian event hits hardest, and when it happens.

    A question that names no event gets the NEXT one, with its date. Answering "Lebaran"
    for "what is the nearest event" was wrong twice over: Lebaran is the fifth nearest
    (156 days out, behind Christmas at 72), and no answer carried a date at all.

    Reads the ramp the Demand Agent learned for that event out of
    sku_ramps.csv, so the answer is per-SKU evidence instead of a claim that
    everything moves together.
    """
    import csv as _csv
    p = DEM / "sku_ramps.csv"
    if not p.exists():
        return "The per-SKU event uplift has never been built. Run `bash run_chain.sh`."
    rows = list(_csv.DictReader(p.open()))

    want = (event or "").strip().lower()
    alias = {
        "lebaran": "Lebaran", "idul fitri": "Lebaran", "raya": "Lebaran",
        "ramadan": "Ramadan", "ramadhan": "Ramadan", "puasa": "Ramadan",
        "imlek": "Imlek", "tahun baru imlek": "Imlek",
        "natal": "Christmas", "christmas": "Christmas",
        "tahun baru": "NewYear", "new year": "NewYear", "newyear": "NewYear",
    }
    cal = _event_calendar()

    def has_movers(event: str) -> bool:
        return any(float(r.get("peak_mult") or 0) > 1.10
                   for r in rows if (r.get("event") or "").lower() == event.lower())

    # The nearest event is not always one that moves anything: payday sits two weeks out
    # and moves no line above noise. Say that, then answer the question the reader meant.
    preamble = ""
    if not want and cal and not has_movers(cal[0]["event"]):
        nearest = cal[0]
        mover = next((c for c in cal if has_movers(c["event"])), None)
        if mover:
            preamble = (f"The nearest event is {nearest['event']} on "
                        f"{nearest['date']:%d %B %Y}, {nearest['days']} days away, and it moves no "
                        f"product above noise. The next event that does is {mover['event']} on "
                        f"{mover['date']:%d %B %Y}, {mover['days']} days away. ")

    name = alias.get(want, want.title()) if want else ""
    if not name and cal:
        name = (next((c["event"] for c in cal if has_movers(c["event"])), cal[0]["event"]))
    if not name:
        name = "Lebaran"
    when = next((c for c in cal if c["event"].lower() == name.lower()), {})

    def num(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    hits = [(num(r.get("peak_mult")), r) for r in rows
            if (r.get("event") or "").lower() == name.lower()]
    if not hits:
        have = sorted({(r.get("event") or "") for r in rows})
        out = [preamble + f"We have no demand pattern for {name}.",
               f"What we do have: {', '.join(have)}."]
        # Even when the event asked about is unknown, the reader still deserves the date of
        # the next one that IS known, rather than a dead end.
        if cal:
            n = cal[0]
            out.append(f"The nearest of them is {n['event']} on "
                       f"{n['date']:%d %B %Y}, {n['days']} days from this snapshot.")
        return " ".join(out)

    # Biggest movers first, not the biggest percentage: a 1.69x on a product that sells
    # 10 a day is worth less than a 1.35x on one that sells 58, and the page reads oddly
    # if the first example is a line nobody buys much of. Ties go to the larger multiple.
    _base = {}
    for r in _csv.DictReader((ROOT / "data" / "catalog" / "catalog.csv").open()):
        _base[r["sku"]] = _f(r.get("base_daily_demand"), 0.0)
    hits.sort(key=lambda x: (-_base.get(x[1]["sku"], 0.0) * x[0], -x[0]))
    # A holiday does not lift the whole catalogue: the ramp only moves the SKUs whose
    # category the event touches, and inside a category only a share of them. The page
    # and the answer say how many actually move instead of "600 SKUs".
    SPIKE = 1.10  # strictly above: the table's own 1.10 rows are not a spike
    spiking = [h for h in hits if h[0] > SPIKE]
    quiet = len(hits) - len(spiking)
    # Names, not codes: a buyer reads "Bimoli Minyak Goreng 1,000 ml", not SKU0063, and the
    # daily rate on a normal day is what makes "spikes" mean something.
    goods = {}
    for r in _csv.DictReader((ROOT / "data" / "catalog" / "catalog.csv").open()):
        goods[r["sku"]] = {
            "name": r.get("name", ""),
            "brand": r.get("brand", ""),
            "pack": r.get("pack_size", ""),
            "uom": r.get("uom", ""),
            "normal": _f(r.get("base_daily_demand"), 0.0),
            "category": r.get("category", ""),
        }
    cat = {k: v["category"] for k, v in goods.items()}

    def label(sku):
        g = goods.get(sku, {})
        name = (g.get("name") or "").strip()
        brand = (g.get("brand") or "").strip()
        pack = (g.get("pack") or "").strip()
        uom = (g.get("uom") or "").strip()
        if brand and not name.lower().startswith(brand.lower()):
            name = f"{brand} {name}"
        return name.strip() or sku

    def rates(sku, mult):
        g = goods.get(sku, {})
        normal = g.get("normal") or 0.0
        return normal, normal * mult

    snap = _snapshot_day()
    lines = [f"## {name}"]
    if when and snap is not None:
        lines += ["",
                  f"The next {name} is on **{when['date']:%d %B %Y}**, "
                  f"**{when['days']} days** from this snapshot "
                  f"({snap:%d %B %Y})."]
        after = [c for c in cal if c["event"].lower() != name.lower()][:2]
        if after:
            lines.append(
                "After that: " + ", ".join(
                    f"{c['event']} on {c['date']:%d %B %Y} ({c['days']} days away)"
                    for c in after) + ".")
    _top = spiking[0] if spiking else (1.0, {"sku": ""})
    _top_mult, _top_row = _top[0], _top[1]
    _top_g = goods.get(_top_row.get("sku", ""), {})
    _top_name = label(_top_row.get("sku", "")) if _top_row.get("sku") else "no product"
    _top_normal = _top_g.get("normal", 0.0) or 0.0
    _top_peak = _top_normal * _top_mult
    lines += [
        "",
        f"**{len(spiking)} of {len(hits)} SKUs** move for this event, and the other "
        f"{quiet} barely do.",
        "",
        f"- The largest of them is **{_top_name}**: {_top_normal:,.0f} pcs on a normal day, "
        f"**{_top_peak:,.0f} pcs at the peak** ({_top_mult:.2f} times). Across the movers the "
        f"multiple runs {min((h[0] for h in spiking), default=1.0):.2f} to "
        f"{max((h[0] for h in spiking), default=1.0):.2f} times normal",
        f"- A spike counts from {SPIKE:.2f} times normal, and the rest of the catalogue "
        f"stays within 10% of a normal day",
    ]
    # how many days BEFORE the peak demand already starts climbing. This is the
    # number that decides whether an order placed today arrives in time, so it
    # belongs in the answer rather than buried in the ramp table.
    lead = [num(r.get("days_to_peak")) for _, r in spiking] or [num(r.get("days_to_peak")) for _, r in hits]
    lo, hi = min(lead), max(lead)
    med = sorted(lead)[len(lead) // 2]
    if hi == 0:
        lines.append(f"- Starts climbing: **on the peak day itself** "
                     f"(an immediate jump, no run-up)")
    elif lo == hi:
        lines.append(f"- Starts climbing: **{int(lo)} days before the peak**")
    else:
        lines.append(f"- Starts climbing: **{int(med)} days before the peak** "
                     f"(range {int(lo)} to {int(hi)} days across SKUs)")
    if when:
        if when["days"] > 30:
            lines.append(
                f"- No order has been stretched for it yet. The loop sizes for events "
                f"inside its 30-day horizon, so it picks this one up when the horizon "
                f"reaches it, about {when['days'] - 30} days from now.")
        else:
            lines.append(
                "- This event falls inside the loop's 30-day horizon, so orders have "
                "already been stretched for it.")
    # One line per product, in the shape a buyer reads out loud: what it sells on a
    # normal day, what it sells at the peak, and how many days from now that peak is.
    # The previous markdown table read as "31 to 51 pcs, 11 to 15 pcs, ..." once the
    # model turned it into prose, which is why the lines are sentences now.
    seen = {}
    for m, r in spiking[:5]:
        normal, peak = rates(r["sku"], m)
        lab = label(r["sku"])
        seen[lab] = seen.get(lab, 0) + 1
        if seen[lab] > 1:  # two SKUs can share a name; the code tells them apart
            lab = f"{lab} ({r['sku']})"
        lines.append(
            f"- **{lab}**: a normal day is {normal:,.0f} pcs, and the peak day is "
            f"{peak:,.0f} pcs ({m:.2f} times), with the peak "
            f"{r.get('days_to_peak', '?')} days after the climb starts")
    rest = spiking[5:]
    if rest:
        buckets, used = {}, set(seen)
        for m, r in rest[:limit]:
            lab = label(r["sku"])
            if lab in used:
                lab = f"{lab} ({r['sku']})"
            used.add(lab)
            buckets.setdefault(round(m, 2), []).append(lab)
        for m, names in sorted(buckets.items(), reverse=True):
            lines.append(f"- {len(names)} more move by {m:.2f} times normal: "
                         + ", ".join(names))
    return (preamble + "\n".join(lines)) if preamble else "\n".join(lines)


def transfers() -> str:
    """Stock moved between depots instead of bought again."""
    s = _json(ORD / "redirect_summary.json") or {}
    rows = _rows(ORD / "branch_depot_ledger.csv")
    if not rows:
        return "No depot transfer has run. Run `bash run_chain.sh`."
    to_totals = {}
    for r in rows:
        k = r.get("to_depot") or ""
        to_totals[k] = to_totals.get(k, 0.0) + _f(r.get("value_idr"), 0.0)
    biggest = sorted(rows, key=lambda r: -_f(r.get("value_idr"), 0.0))[:5]
    lines = [
        f"## Stock moved between depots: {len(rows)} moves",
        "",
        f"Instead of buying again, the loop moved **{_idr(s.get('value_protected_idr'))}** of "
        f"stock that was already paid for from the central depot to the city depots that sell "
        f"it faster.",
        "",
        f"- Stock sitting where it does not sell: {_idr(s.get('excess_value_at_risk_idr'))} "
        f"across {s.get('excess_skus')} SKUs",
        f"- A SKU counts as having too much only when it holds more than "
        f"{s.get('min_excess_days_threshold')} days beyond what it needs",
        f"- Depots receiving stock: " + ", ".join(
            f"{k} ({_idr(v)})" for k, v in sorted(to_totals.items(), key=lambda kv: -kv[1])),
        "",
        "The five biggest moves:",
    ]
    for r in biggest:
        lines.append(f"- {r.get('sku')} from {r.get('from_depot')} to {r.get('to_depot')}: "
                     f"{_f(r.get('qty'), 0):,.0f} units, "
                     f"{_idr(_f(r.get('value_idr'), 0.0))}")
    return "\n".join(lines)


def receiving() -> str:
    """What arrived, against what was promised.

    A shortage that reaches the shelf started here, so this is the answer to "why did it run
    out when we ordered it". Only receipts dated up to the snapshot are counted.
    """
    rec = _rows(AG.parent / "catalog" / "receiving.csv")
    princ = {r.get("principal_id"): r for r in _rows(AG.parent / "catalog" / "principals.csv")}
    snap = (_json(ORD / "order_summary.json") or {}).get("snapshot") or ""
    counted = [r for r in rec if (not snap or (r.get("order_date") or "")[:10] <= snap[:10])]
    if not counted:
        return "No receipt is recorded yet. Run `bash run_chain.sh`."
    short = [r for r in counted
             if _f(r.get("received_units"), 0) < _f(r.get("ordered_units"), 0)]
    units_short = sum(_f(r.get("ordered_units"), 0) - _f(r.get("received_units"), 0) for r in short)
    late = []
    per = {}
    for r in counted:
        pid = r.get("principal_id") or ""
        b = per.setdefault(pid, {"n": 0, "days": 0.0,
                                 "promised": _f((princ.get(pid) or {}).get("lead_mean_d"), 0.0)})
        b["n"] += 1
        b["days"] += _f(r.get("actual_lead_d"), 0.0)
        if b["promised"] and _f(r.get("actual_lead_d"), 0.0) > b["promised"]:
            late.append(pid)
    worst = sorted(((pid, b["days"] / b["n"] - b["promised"]) for pid, b in per.items()
                    if b["n"] and b["promised"]), key=lambda kv: -kv[1])[:4]
    acked = _rows(ORD / "order_acks.csv")
    promised = {}
    for a in acked:
        d = (a.get("promised_delivery") or "")[:10]
        if d:
            promised[d] = promised.get(d, 0) + 1
    lines = [
        f"## What arrives, against what was promised",
        "",
        f"Of **{len(counted):,} deliveries** recorded up to {snap}, "
        f"**{len(short):,} came in short** of what was ordered, by "
        f"{units_short:,.0f} units in total, and **{len(late):,} took longer** than the "
        f"delivery time the supplier promised.",
        f"- An order that is sized correctly still ends as empty shelf when the goods arrive "
        f"short or late",
        "- Suppliers whose deliveries take longest beyond their promise: " + ", ".join(
            f"{pid} ({d:+.1f} days)" for pid, d in worst),
        f"- Still on the way: {sum(promised.values())} orders against "
        f"{len(promised)} promised dates",
    ]
    if promised:
        lines.append("   " + ", ".join(f"{d} ({n} orders)"
                                       for d, n in sorted(promised.items())))
    return "\n".join(lines)


def geography() -> str:
    """Where the goods sell, by city."""
    dem = _rows(AG.parent / "catalog" / "sku_city_demand.csv")
    outlets = _rows(AG.parent / "catalog" / "outlets.csv")
    if not dem:
        return "The demand history by city is missing."
    city = {}
    for r in dem:
        c = r.get("city") or ""
        city[c] = city.get(c, 0.0) + _f(r.get("units"), 0.0)
    total = sum(city.values()) or 1.0
    counts = {}
    for r in outlets:
        c = r.get("city") or ""
        b = counts.setdefault(c, {"n": 0, "warung": 0})
        b["n"] += 1
        if (r.get("outlet_type") or "").lower() == "warung":
            b["warung"] += 1
    lines = [
        f"## Where it sells, by city",
        "",
        f"Across {len(city)} cities and {sum(b['n'] for b in counts.values())} outlets "
        f"(of them {sum(b['warung'] for b in counts.values())} warung), counted over the "
        f"whole demand history.",
        "",
        "| city | share of demand | outlets | warung |",
        "|---|---|---|---|",
    ]
    for c, u in sorted(city.items(), key=lambda kv: -kv[1]):
        b = counts.get(c, {"n": 0, "warung": 0})
        lines.append(f"| {c} | {u / total * 100:.1f}% | {b['n']} | {b['warung']} |")
    lines += ["", "A city that sells a lot while its depot holds little is where the next "
                  "shortage comes from, which is why stock is moved between depots."]
    return "\n".join(lines)


def stock_health() -> str:
    """What the stock is worth and what will not sell in time."""
    pos = {r.get("sku"): r for r in _rows(AG.parent / "stock" / "position_snapshot.csv")}
    cat = {r.get("sku"): r for r in _rows(AG.parent / "catalog" / "catalog.csv")}
    cls = {r.get("sku"): r for r in _rows(AG.parent / "demand" / "sku_classes.csv")}
    if not pos:
        return "The stock snapshot is missing."
    units = value = daily = 0.0
    by_class, at_risk_units, at_risk_value, slow = {}, 0.0, 0.0, 0
    for sku, p in pos.items():
        c, k = cat.get(sku, {}), cls.get(sku, {})
        vel = _f(p.get("velocity_units_day"), 0.0)
        onhand = _f(p.get("on_hand_units"), 0.0)
        cost = _f(c.get("unit_cost_idr"), 0.0)
        cover = _f(p.get("days_of_cover"), 0.0)
        units += onhand
        value += onhand * cost
        daily += vel * cost
        key = (k.get("class_volume") or "?") + (k.get("class_volatility") or "?")
        b = by_class.setdefault(key, {"skus": 0, "value": 0.0})
        b["skus"] += 1
        b["value"] += onhand * cost
        life = _f(c.get("shelf_life_months"), 0.0) * 30.4
        if life:
            at_risk_units += max(0.0, onhand - min(onhand, vel * life))
        if vel <= 0 or cover > 90:
            slow += 1
    days = units / sum(_f(p.get("velocity_units_day"), 0.0) for p in pos.values()) \
        if sum(_f(p.get("velocity_units_day"), 0.0) for p in pos.values()) else 0.0
    risk_value = 0.0
    for sku, p in pos.items():
        c = cat.get(sku, {})
        life = _f(c.get("shelf_life_months"), 0.0) * 30.4
        if not life:
            continue
        onhand, vel = _f(p.get("on_hand_units"), 0.0), _f(p.get("velocity_units_day"), 0.0)
        risk_value += max(0.0, onhand - min(onhand, vel * life)) * _f(c.get("unit_cost_idr"), 0.0)
    _lives = [_f(c.get("shelf_life_months"), 0.0) for c in cat.values()]
    _lives = [x for x in _lives if x]
    _life_lo = min(_lives) if _lives else 0.0
    _life_hi = max(_lives) if _lives else 0.0
    _expiry_n = sum(1 for p in pos.values() if str(p.get("expiry_risk", "")).lower() == "true")
    lines = [
        "## What the stock is worth",
        "",
        f"The network holds **{_idr(value)}** of stock, about {units:,.0f} units, and sells "
        f"{_idr(daily)} of it a day.",
        f"- Stock covers about **{days:,.1f} days** of selling at this rate",
        f"- On-hand stock that would outlive its date at today's selling rate: {_idr(risk_value)}. "
        f"Shelf life runs {_life_lo:.0f} to {_life_hi:.0f} months, and {_expiry_n} SKUs are flagged "
        f"because their cover (on hand, in transit and on order together) runs past that date; "
        f"those are the lines the redirect engine moves first.",
        f"- Stock that sits more than 90 days: {slow} SKUs",
        "",
        "By class (A is the biggest seller, Low to High is how steady the selling is):",
        "",
        "| class | SKUs | value |",
        "|---|---|---|",
    ]
    for k in sorted(by_class):
        lines.append(f"| {k} | {by_class[k]['skus']} | {_idr(by_class[k]['value'])} |")
    return "\n".join([ln for ln in lines if ln != ""])


def supplier_reliability() -> str:
    """What the loop learned about each principal, worst first."""
    import csv as _csv
    p = AG / "supplier_reliability.csv"
    if not p.exists():
        return "Supplier Reliability has never run. Run `bash run_chain.sh`."
    rows = list(_csv.DictReader(p.open()))

    def num(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    rows.sort(key=lambda r: num(r.get("fill_rate_observed"), 1))
    lines = [f"## {len(rows)} suppliers, the ones delivering least first", "",
             "| supplier | average delivery time | worst-case delivery time | "
             "share of the order delivered | delivered complete and on time |",
             "|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['principal_id']} | {num(r.get('lead_mean_d')):.1f} days | "
            f"{num(r.get('lead_p90_d')):.1f} days | "
            f"{_plain_pct(r.get('fill_rate_observed'))} | {_plain_pct(r.get('otif'))} |")
    worst = rows[0]
    lines += [
        "",
        f"**{worst['principal_id']}** delivers least, "
        f"{_plain_pct(worst.get('fill_rate_observed'))} of each order. The planner allows "
        f"this supplier more delivery time, so its automatic orders come out larger.",
    ]
    return "\n".join(lines)


def _baseline_wape_median():
    """Median forecast miss across every SKU, from the demand baselines file."""
    try:
        b = pd.read_csv(DEM / "baselines.csv")
        return float(pd.to_numeric(b["wape_best"], errors="coerce").median())
    except Exception:                                          # noqa: BLE001
        return None


def _all_baseline_skus() -> int:
    try:
        return len(pd.read_csv(DEM / "baselines.csv"))
    except Exception:                                          # noqa: BLE001
        return 0


def forecast_accuracy() -> str:
    """How accurate the Demand Agent's forecast is, month over month."""
    import csv as _csv
    ls = _json(AG / "learn_summary.json")
    if not ls:
        return "Learn has never run. Run `bash run_chain.sh`."
    lines = [
        "## How accurate the forecast is",
        "",
        # Two forecast misses exist and they are over different populations. Both are real,
        # so both are named with their population rather than merged into one ambiguous
        # number: a reader comparing this with the proposal would otherwise think one of
        # them is wrong.
        f"- Forecast miss, the SKUs the loop ordered for: "
        f"**{_plain_pct(ls.get('forecast_wape_best_median'))}** of units sold",
        f"- Forecast miss, all {_all_baseline_skus()} SKUs in the catalogue: "
        f"**{_plain_pct(_baseline_wape_median())}**",
        f"- Share of each order the suppliers deliver: "
        f"**{_plain_pct(ls.get('observed_fill_rate_mean'))}**",
        f"- Decisions assessed: {ls.get('n_decisions')}",
        f"- Suppliers delivering less than 95% of the order: "
        f"{', '.join(ls.get('principals_below_fill_95') or []) or 'none'}",
        f"- Latest window: {ls.get('recent_window')}",
        "",
    ]
    curve = AG / "learn_curve.csv"
    if curve.exists():
        rows = list(_csv.DictReader(curve.open()))
        if len(rows) > 1:
            # Percentages, not the raw decimal from the file: the contract says a share
            # reads as a share, and the model was copying "0.1316" straight into an answer.
            lines += ["Forecast miss by month:", "",
                      "| month | forecast miss |", "|---|---|"]
            for r in rows[-12:]:
                lines.append(f"| {r.get('month')} | "
                             f"{_plain_pct(_f(r.get('wape')))} |")
    return "\n".join(lines)


def answer(intent: str = "summary", target: str = "") -> str:
    intent = (intent or "summary").lower()
    if intent.startswith("sku") and target:
        return sku_decision(target)
    if intent.startswith("order") and target:
        return order_status(target)
    if intent.startswith("exception"):
        return exceptions()
    if intent.startswith("sku"):
        return exceptions()
    if intent.startswith("supplier") or intent.startswith("principal"):
        return supplier_reliability()
    if intent.startswith("accuracy") or intent.startswith("akurat"):
        return forecast_accuracy()
    if intent.startswith("event") or intent.startswith("lebaran") \
            or intent.startswith("ramadan") or intent.startswith("imlek"):
        # NOT `target or "Lebaran"`: that default is why "what is the nearest event" was
        # answered with Lebaran, 156 days away, while Christmas sat 72 days away. An empty
        # target now means the nearest event.
        return event_impact(target or "")
    if intent.startswith("stockout") or intent.startswith("runs_out"):
        return stockout_within_a_week()
    if intent.startswith("spike") or intent.startswith("ramp"):
        return spike_within_a_month()
    if intent.startswith("receiv") or intent.startswith("datang"):
        return receiving()
    if intent.startswith("geograph") or intent.startswith("kota"):
        return geography()
    if intent.startswith("transfer"):
        return transfers()
    if intent.startswith("health"):
        return stock_health()
    return summary()
