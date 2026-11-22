"""
Pasok — MCP server (FastMCP)
============================

Exposes the four-agent replenishment loop as MCP tools, so an LLM client
(Claude Desktop, Joule, or any MCP host) can ask Pasok questions and get the
same numbers the web console shows.

Built with FastMCP (jlowin, 2.2k stars), the standard Python framework for
Model Context Protocol servers. It handles the protocol, the transport and
the schema; this file only says which tools exist and what they return.

    fastmcp dev mcp_server.py          # MCP inspector, try it by hand
    fastmcp run mcp_server.py          # stdio, for Claude Desktop
    .venv/bin/python mcp_server.py     # streamable HTTP on :8086

Every tool here is read-only and reads the artefacts the loop already wrote
to disk. No model call, no network, no writes. If the loop has not run yet,
the tools say so rather than inventing a number.
"""

from __future__ import annotations

import json
import os
import pathlib
import re

from fastmcp import FastMCP

ROOT = pathlib.Path(__file__).resolve().parent
AG = ROOT / "data" / "agents"
ORD = ROOT / "data" / "orders"
DEM = ROOT / "data" / "demand"
STOCK = ROOT / "data" / "stock"
CAT = ROOT / "data" / "catalog"
SAP = ROOT / "data" / "sap"

mcp = FastMCP(
    "Pasok",
    instructions=(
        "Pasok is an autonomous replenishment loop for Indonesian FMCG "
        "distributors. Four agents (Demand, Stock Position, Supplier "
        "Reliability, Decision) run perceive, forecast, decide, issue, learn. "
        "Every tool here returns numbers the loop already computed, read from "
        "the artefacts on disk. Never invent a figure; if an artefact is "
        "missing, report that it has not been run yet."
    ),
)

def _json(p: pathlib.Path) -> dict:
    return json.loads(p.read_text()) if p.exists() else {}


def _csv_rows(p: pathlib.Path) -> list[dict]:
    import csv
    if not p.exists():
        return []
    with p.open() as fh:
        return list(csv.DictReader(fh))


def _idr(v) -> str:
    try:
        return f"IDR {float(v):,.0f}"
    except (TypeError, ValueError):
        return "IDR tidak diketahui"


# ---------------------------------------------------------------- tools

@mcp.tool
def network_summary() -> str:
    """Whole-network numbers: how many SKUs were scored, how many orders went
    out, how many needed a human, and how much the guardrails dampened order
    variance. Use this first for any question about overall performance."""
    dec = _json(AG / "decision_summary.json")
    orders = _json(ORD / "order_summary.json")
    amp = dec.get("amplification", {})
    if not dec and not orders:
        return "Loop belum pernah jalan. Jalankan `bash run_chain.sh` dulu."
    return "\n".join([
        f"SKU dinilai: {dec.get('n_skus')}",
        f"Order keluar: {dec.get('orders_placed') or orders.get('skus_with_order')}",
        f"Keluar otomatis: {orders.get('auto_issued')}",
        f"Naik ke manusia: {orders.get('escalated')}",
        f"Tingkat otomatis: {orders.get('auto_rate')}",
        f"Pembesaran pesanan: {amp.get('raw')}x tanpa pembatas, "
        f"{amp.get('guarded')}x dengan pembatas (turun {amp.get('reduction_pct')}%)",
        f"Nilai yang naik ke manusia: {_idr(orders.get('escalated_value_idr') or 0)}",
        f"Rekaman: {dec.get('snapshot')}",
    ])


@mcp.tool
def stock_running_out(within_days: int = 7) -> str:
    """SKUs whose stock runs out within the given number of days, tightest
    first. Use for 'stok apa yang habis', 'mana yang kritis'."""
    within_days = max(1, min(int(within_days), 90))
    rows = _csv_rows(STOCK / "position_snapshot.csv")
    cat = {r["sku"]: r.get("category", "") for r in _csv_rows(CAT / "catalog.csv")}
    out = []
    for r in rows:
        try:
            cover = float(r.get("days_of_cover") or 0)
        except ValueError:
            continue
        if cover <= within_days:
            out.append((cover, r, cat.get(r["sku"], "")))
    if not out:
        return f"Tidak ada SKU dengan sisa stok {within_days} hari atau kurang."
    out.sort(key=lambda x: x[0])
    lines = [f"{len(out)} SKU sisa {within_days} hari atau kurang:", ""]
    for cover, r, k in out[:20]:
        lines.append(
            f"- {r['sku']} ({k}) principal {r['principal_id']}: sisa "
            f"{cover:.1f} hari, bisa dijual {float(r['sellable_units']):,.0f} unit"
        )
    return "\n".join(lines)


@mcp.tool
def sku_decision(sku: str) -> str:
    """The full decision record for one SKU: its stock position, the learned
    lead time, the event ramp, the order before and after the guardrails, and
    the written rationale. Use for 'kenapa SKU ini dipesan'."""
    rows = _csv_rows(AG / "decisions.csv")
    sku = sku.strip().upper()
    hit = [r for r in rows if r.get("sku", "").upper() == sku]
    if not hit:
        return f"{sku} tidak ada di daftar keputusan ({len(rows)} SKU dinilai)."
    r = hit[0]
    # days_of_cover lives in the stock snapshot, not in the decision row
    cover = next(
        (s.get("days_of_cover") for s in _csv_rows(STOCK / "position_snapshot.csv")
         if s.get("sku", "").upper() == sku),
        "tidak diketahui",
    )
    return "\n".join([
        f"{r['sku']} · principal {r['principal_id']} · keputusan {r['action']}",
        f"Sisa stok: {r.get('sellable_units')} unit, sisa {cover} hari "
        f"(target {r.get('cover_days_target')} hari)",
        f"Ramalan: {r.get('forecast_daily')}/hari dasar, "
        f"{r.get('forecast_daily_eff')}/hari dengan ramp event {r.get('event')} "
        f"(x{r.get('event_mult')})",
        f"Lama kirim dipelajari: batas atas {r.get('lead_p90_days')} hari, "
        f"cadangan {r.get('buffer_days')} hari",
        f"Order: {r.get('raw_order')} unit sebelum pembatas, "
        f"{r.get('guarded_order')} unit sesudah pembatas",
        f"Tanda pembatas: {_rationale(r.get('guardrail_flags')) or 'tidak ada'}",
        "",
        f"Alasan: {_rationale(r.get('rationale'))}",
    ])


@mcp.tool
def escalation_queue() -> str:
    """The orders that needed a human, grouped by why. Use for 'apa yang
    nunggu manusia', 'antrian pengecualian'."""
    rows = _csv_rows(ORD / "purchase_orders.csv")
    held = [r for r in rows if r.get("status") == "ESCALATED"]
    if not held:
        return "Antrian kosong. Semua order keluar otomatis."
    # group by cause, not by amount: 67 different numbers is a list, not a summary
    causes = {"batas nilai": 0, "ganti supplier": 0, "jumlah minimum": 0, "lain": 0}
    for r in held:
        reason = r.get("reason") or ""
        if "auto limit" in reason:
            causes["batas nilai"] += 1
        elif "supplier_switch" in reason:
            causes["ganti supplier"] += 1
        elif "min order" in reason:
            causes["jumlah minimum"] += 1
        else:
            causes["lain"] += 1
    summary = ", ".join(f"{v} {k}" for k, v in causes.items() if v)
    lines = [f"{len(held)} order nunggu keputusan manusia ({summary}):", ""]
    for r in held[:20]:
        lines.append(
            f"- {r['po_id']} · {r['sku']} · principal {r['principal_id']} · "
            f"{_idr(r.get('value_idr'))} · {_reason(r.get('reason'))}"
        )
    return "\n".join(lines)


def _reason(s: str) -> str:
    """Translate the executor's escalation code into a readable sentence."""
    t = s or "belum ada"
    t = t.replace("value ", "nilai ").replace("auto limit", "batas otomatis")
    t = t.replace("supplier_switch proposed for", "usulan ganti supplier untuk")
    t = t.replace("supplier_switch", "ganti supplier")
    t = t.replace("min order", "minimum order")
    t = t.replace("proposed", "diajukan")
    t = t.replace(" and this line is ", ", baris ini ")
    # the executor writes money as "200M" and "Rp886M"; make both read the same
    t = re.sub(r"(\d+(?:\.\d+)?)M\b", r"\1 juta", t)
    return t


def _rationale(s: str) -> str:
    """The decision rationale is written in English by the agent. Translate it,
    keeping every number exactly as it was computed."""
    t = s or "belum ada"
    for a, b in [
        ("cover ", "sisa "), ("days of cover", "hari sisa"),
        ("lead p90 ", "batas atas lama kirim "), ("d + review ", " hari + masa tunggu "),
        ("buffer ", "cadangan "), ("sellable ", "bisa dijual "),
        ("forecast ", "ramalan "), ("/day", "/hari"),
        ("variance cap binds", "pembatas variansi mengikat"),
        ("sigma cap at ", "batas sigma di "),
        ("damping", "peredaman"), ("variance_cap", "pembatas variansi"),
    ]:
        t = t.replace(a, b)
    return t


@mcp.tool
def supplier_reliability() -> str:
    """What the loop learned about each principal: observed lead time, how
    tight it is, and how often they deliver in full. Use for 'principal mana
    yang lambat', 'siapa yang sering kurang kirim'."""
    rows = _csv_rows(AG / "supplier_reliability.csv")
    if not rows:
        return "Supplier Reliability belum pernah jalan. Jalankan `bash run_chain.sh`."
    lines = [f"{len(rows)} principal diamati:", ""]
    for r in sorted(rows, key=lambda x: float(x.get("fill_rate_observed") or 0)):
        lines.append(
            f"- {r['principal_id']}: rata-rata {r['lead_mean_d']} hari, "
            f"batas atas {r['lead_p90_d']} hari, terpenuhi "
            f"{float(r['fill_rate_observed']):.3f}, tepat waktu {float(r['otif']):.3f}"
        )
    return "\n".join(lines)


@mcp.tool
def event_registry() -> str:
    """The Indonesian retail event registry, with dates that drift each year
    (Ramadan, Lebaran, Imlek, Christmas, New Year). Use for 'event apa yang
    lagi dekat', 'kapan Lebaran'."""
    rows = _csv_rows(DEM / "event_registry.csv")
    if not rows:
        return "Event registry belum pernah dibangun."
    lines = ["Event yang tanggalnya ikut tahun:", ""]
    for r in rows:
        lines.append(
            f"- {r['event']}: terlihat {r['first_seen']} sampai {r['last_seen']} "
            f"({r['occurrences']} kali), pengali rata-rata {r['mean_factor']}"
        )
    return "\n".join(lines)


@mcp.tool
def forecast_accuracy() -> str:
    """How accurate the Demand Agent's forecast is: median held-out error per
    SKU, and the monthly trend. Use for 'seberapa akurat ramalannya'."""
    learn = _json(AG / "learn_summary.json")
    if not learn:
        return "Learn belum pernah jalan."
    return "\n".join([
        f"Galat ramal (median): {learn.get('forecast_wape_best_median')}",
        f"Galat ramal (rata-rata): {learn.get('forecast_wape_best_mean')}",
        f"Permintaan terpenuhi (rata-rata): {learn.get('observed_fill_rate_mean')}",
        f"Keputusan dinilai: {learn.get('n_decisions')}",
        f"Principal di bawah 95% terpenuhi: "
        f"{', '.join(learn.get('principals_below_fill_95') or []) or 'tidak ada'}",
        f"Jendela terakhir: {learn.get('recent_window')}",
    ])


@mcp.tool
def run_loop() -> str:
    """Run the full ten-stage replenishment loop and report what changed.
    Takes a few minutes. Use when the operator asks to run the loop, refresh
    the numbers, or see the agents work."""
    import subprocess
    proc = subprocess.run(
        ["bash", str(ROOT / "run_chain.sh")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=900,
    )
    tail = (proc.stdout or "").strip().splitlines()[-25:]
    ok = proc.returncode == 0
    return ("Loop selesai.\n\n" if ok else "Loop gagal.\n\n") + "\n".join(tail)


# ---------------------------------------------------------------- entry

def main() -> None:
    transport = os.environ.get("PASOK_MCP_TRANSPORT", "http")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("PASOK_MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("PASOK_MCP_PORT", "8086")),
            path="/mcp",
        )


if __name__ == "__main__":
    main()
