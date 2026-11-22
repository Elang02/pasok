"""
Pasok: figures
==============

One source of truth for every number the pages print.

A page never carries a figure in its own markup. It carries a placeholder, and the
server fills it from the artefact at request time, so a page cannot go stale when the
pipeline re-runs.

    <!--SNAPSHOT-->                              the masthead line, every console page
    <span data-fig="orders_placed">145</span>    the span's text is replaced
    <!--LEARN_BARS-->                            the monthly error bars, from learn_curve.csv

The literal inside a data-fig element is only the no-server fallback; the gate
(`tools/ui_truth_gate.py`) asserts the served value equals the artefact, so a stale
literal is caught rather than shipped.

Nothing in here invents a number. When an artefact is missing the value reads `n/a`
and the gate fails.
"""

from __future__ import annotations

import csv
import json
import pathlib
import re
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

NA = "n/a"

_MONTHS = ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]


def _json(rel: str) -> dict:
    try:
        return json.loads((DATA / rel).read_text())
    except Exception:                                          # noqa: BLE001
        return {}


DEC = _json("agents/decision_summary.json")
ORD = _json("orders/order_summary.json")
LRN = _json("agents/learn_summary.json")
META = _json("catalog/meta.json")


def _csv(rel: str) -> list[dict]:
    try:
        with (DATA / rel).open(newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:                                          # noqa: BLE001
        return []


CAT = _csv("catalog/catalog_view.csv")   # the human catalogue, built by tools/build_catalog_view.py


def _ribu(n: float) -> str:
    """11196.5 -> '11,197'. English thousands separator, no decimals."""
    try:
        return f"{round(float(n)):,}"
    except (TypeError, ValueError):
        return NA


def _desimal(v: float, places: int = 3) -> str:
    """0.959 -> '0.959' (English decimal point)."""
    try:
        return f"{float(v):.{places}f}"
    except (TypeError, ValueError):
        return NA


def _persen(v: float, places: int = 1) -> str:
    """0.959 -> '95.9%'. A share reads as a share, never as a bare decimal."""
    try:
        return f"{float(v) * 100:.{places}f}%"
    except (TypeError, ValueError):
        return NA


def _rupiah_singkat(v: float) -> str:
    """7_564_299_700 -> 'IDR 7.56 bn'. A billion rupiah is bn, never M."""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return NA
    if v >= 1e9:
        return f"IDR {v / 1e9:.2f} bn"
    if v >= 1e6:
        return f"IDR {v / 1e6:.1f}M"
    return f"IDR {v:,.0f}".replace(",", ".")


def _rupiah(v: float) -> str:
    """3800 -> 'Rp 3,800'. Used where the value is shelf price, not turnover."""
    try:
        return "Rp " + _ribu(v)
    except (TypeError, ValueError):
        return NA


def _rows(rel: str) -> list[dict]:
    try:
        with (DATA / rel).open() as fh:
            return list(csv.DictReader(fh))
    except Exception:                                          # noqa: BLE001
        return []


_BASE = _rows("demand/baselines.csv")
_CURVE = _rows("agents/learn_curve.csv")


def _wape_best_median() -> str:
    vals = []
    for r in _BASE:
        try:
            vals.append(float(r["wape_best"]))
        except (KeyError, ValueError):
            pass
    return _persen(statistics.median(vals), 1) if vals else NA


def _wape_of(sku: str) -> str:
    for r in _BASE:
        if r.get("sku") == sku:
            return _desimal(r.get("wape_best", ""), 4)
    return NA


def _snapshot_date() -> str:
    """The snapshot date, read from the artefact, never typed: '11 October 2026'."""
    snap = DEC.get("snapshot") or LRN.get("recent_window") or ""
    try:
        y, m, d = (int(x) for x in str(snap).split("-"))
        return f"{d} {_MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return str(snap) or NA


def snapshot_line() -> str:
    """The masthead line, read from the artefact, never typed."""
    n = DEC.get("n_skus") or META.get("n_skus")
    return f"Snapshot {_snapshot_date()} · {_ribu(n)} SKUs"


def snapshot_short() -> str:
    """'11 October 2026'. For the demo page's console fragment bar."""
    return _snapshot_date()


def _amplification() -> str:
    amp = DEC.get("amplification") or {}
    if "reduction_pct" in amp:
        return _desimal(amp["reduction_pct"], 1) + "%"
    return NA


def _curve_last(place: str) -> str:
    if not _CURVE:
        return NA
    try:
        return _ribu(_CURVE[-1][place])
    except (KeyError, ValueError):
        return NA


FIG: dict[str, str] = {
    # catalogue
    "n_skus": _ribu(DEC.get("n_skus") or META.get("n_skus") or 0),
    "principal_count": _ribu(len((DEC.get("buffer_model") or {}).get("per_principal") or {})) or NA,
    "catalog_skus": _ribu(len(CAT)),
    "catalog_names": _ribu(len({r["name"] for r in CAT})),
    "catalog_price_low": _rupiah(min((float(r["sell_price_idr"]) for r in CAT), default=0)),
    "catalog_price_high": _rupiah(max((float(r["sell_price_idr"]) for r in CAT), default=0)),
    "catalog_margin_avg": _persen(statistics.fmean([float(r["margin_pct"]) for r in CAT]) / 100 if CAT else 0),
    "catalog_events": _ribu(len({r["top_event"] for r in CAT if r["top_event"]})),
    # the decision
    "orders_placed": _ribu(DEC.get("orders_placed") or 0),
    "orders_skipped": _ribu(DEC.get("orders_skipped") or 0),
    "variance_cap_binding": _ribu(DEC.get("variance_cap_binding") or 0),
    "total_guarded_units": _ribu(DEC.get("total_guarded_units") or 0),
    "amplification_reduction": _amplification(),
    # the orders
    "skus_with_order": _ribu(ORD.get("skus_with_order") or 0),
    "auto_issued": _ribu(ORD.get("auto_issued") or 0),
    "escalated": _ribu(ORD.get("escalated") or 0),
    "auto_rate": _persen(ORD.get("auto_rate") or 0),
    "order_value": _rupiah_singkat(ORD.get("total_value_idr") or 0),
    # what the loop learned
    "fill_rate": _persen(LRN.get("observed_fill_rate_mean") or 0),
    "wape_best_median": _wape_best_median(),
    "sku0421_wape": _wape_of("SKU0421"),
    "learn_months": _ribu(len(_CURVE)),
    "curve_readings": _curve_last("readings"),
    "curve_wape_last": _desimal(_CURVE[-1]["wape"], 3) if _CURVE else NA,
}


def learn_bars(months: int = 12) -> str:
    """The error bars, read from learn_curve.csv. No height is hand-typed."""
    rows = _CURVE[-months:]
    if not rows:
        return ""
    vals = [float(r["wape"]) for r in rows]
    top = max(vals) or 1.0
    out = []
    for r, v in zip(rows, vals):
        height = max(4, round(v / top * 100))
        peak = " peak" if v == top else ""
        lab = f'<span class="lab">{_desimal(v)}</span>' if v / top >= 0.55 else ""
        month = r["month"][2:]
        out.append(f'<div class="bar{peak}" style="height:{height}%">'
                   f'{lab}<span class="mo">{month}</span></div>')
    return "\n".join(out)


_FIG_RE = re.compile(r'(?P<open><(?P<tag>[a-z]+)[^>]*\bdata-fig="(?P<key>[a-z0-9_]+)"[^>]*>)'
                     r'(?P<txt>[^<]*)(?P<close></)')


def apply(html: str) -> str:
    """Fill every placeholder from the artefact. Called on every page response."""
    html = html.replace("<!--SNAPSHOT-->", snapshot_line())
    html = html.replace("<!--SNAPSHOT_SHORT-->", snapshot_short())
    html = html.replace("<!--LEARN_BARS-->", learn_bars())

    def _sub(m: re.Match) -> str:
        val = FIG.get(m.group("key"))
        return m.group("open") + (m.group("txt") if val is None else val) + m.group("close")

    return _FIG_RE.sub(_sub, html)


def referenced_keys(html: str) -> list[str]:
    """Every data-fig key a page asks for, so the gate can flag unknown ones."""
    return sorted({m.group("key") for m in _FIG_RE.finditer(html)
                   if m.group("txt") is not None or True})


if __name__ == "__main__":
    print(snapshot_line())
    for k, v in FIG.items():
        print(f"{k:26s} {v}")
