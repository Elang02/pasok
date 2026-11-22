#!/usr/bin/env python
"""Satu riwayat order yang berkelanjutan: era manual, lalu era agen.

Dasar datanya bukan karangan:

    sebelum 1 Jan 2026  kolom `ordered` di data/stock/stock_daily.csv, yaitu pemesanan yang
                        tercatat di riwayat distributor, 2023 sampai 2025. Itu pesanan yang
                        diletakkan orang, dan memang begitu ceritanya: 566 SKU, 12 pemasok,
                        dipesan manual oleh bagian pembelian.
    sejak 1 Jan 2026    keputusan agen pada simulasi lingkaran tertutup
                        (data/sim/closed/day-*/decisions.csv), lengkap dengan alasan yang
                        agen tulis sendiri dan aturan yang menandainya.

Semua kolom lain diambil dari katalog dan catatan pengiriman yang sama seperti pipeline:
harga satuan per SKU, pemasok per SKU, dan lead time per pemasok.

Pakai:
    .venv/bin/python tools/build_order_history.py --manual-from 2025-01-01
    .venv/bin/python tools/build_order_history.py --manual-from 2023-01-02 --all
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
STOCK = ROOT / "data" / "stock"
CAT = ROOT / "data" / "catalog"
ORDERS = ROOT / "data" / "orders"
SIM = ROOT / "data" / "sim" / "live"
# Kapan agennya mengambil alih pembelian. Sebelum tanggal ini catatannya adalah pesanan
# pemilik barang sendiri (era manual), sesudahnya keputusan agen. Default 1 Oktober 2026:
# jadwal hackathon-nya Oktober. Bisa digeser lewat --agent-start saat memakai dunia replay,
# supaya seluruh era agen berasal dari satu versi kode.
AGENT_START = pd.Timestamp("2026-10-01")
AS_OF = None  # diisi dari --as-of; kalau kosong, dipakai clock.txt atau tanggal terakhir

OUT_COLUMNS = ["order_id", "date", "placed_by", "sku", "supplier", "qty", "unit_cost_idr",
               "value_idr", "lead_days", "promised_date", "arrived_date", "late_days",
               "landed", "cover_days", "reason", "basis"]


def lead_times() -> pd.DataFrame:
    """Lead time per pemasok dari catatan penerimaan, sama seperti langkah posisi."""
    rec = pd.read_csv(CAT / "receiving.csv")
    return pd.DataFrame({
        "lead_days": rec.groupby("principal_id")["actual_lead_d"].mean().round().astype(int),
    })


def cover_series(daily: pd.DataFrame) -> pd.Series:
    """Hari stok tersisa per SKU per hari, rumus sama dengan snapshot: sellable / velocity."""
    piv = daily.pivot_table(index="date", columns="sku", values="sales", aggfunc="sum")
    vel = piv.rolling(28, min_periods=7).mean()
    sell = daily.pivot_table(index="date", columns="sku",
                             values=["on_hand", "in_transit", "open_po"], aggfunc="sum")
    sellable = sell["on_hand"].add(sell["in_transit"], fill_value=0) \
                           .add(sell["open_po"], fill_value=0)
    return (sellable / vel).stack().rename("cover_days")


def deliveries() -> pd.DataFrame:
    """Janji versus kedatangan sungguhan, dari berkas yang agen tulis saat memesan."""
    p = SIM / "deliveries.csv"
    if not p.exists():
        return pd.DataFrame(columns=["order_date", "sku", "promised", "arrives"])
    d = pd.read_csv(p, parse_dates=["order_date", "promised", "arrives"],
                    dtype={"sku": str})
    return d


def allocate_arrivals(daily: pd.DataFrame, m: pd.DataFrame) -> pd.Series:
    """Pasangkan kedatangan yang tercatat dengan pesanan yang tercatat.

    Berkas pengiriman hanya menyimpan per pemasok per hari, bukan per SKU, jadi kedatangan
    per order dicocokkan dari kolom `arrivals` di riwayat harian: per SKU, kiriman yang
    mendarat dipakai untuk menutup pesanan paling lama yang belum terpenuhi. Ini pembagian
    ulang dari catatan, bukan angka baru, dan halaman menyebutnya begitu.
    """
    arrived = pd.Series(pd.NaT, index=m.index, dtype="datetime64[ns]")
    arr = daily[daily["arrivals"] > 0][["date", "sku", "arrivals"]]
    for sku, g in m.groupby("sku", sort=False):
        a = arr[arr["sku"] == sku].sort_values("date")
        if a.empty:
            continue
        waiting = [[row["date"], float(row["qty"]), idx]
                   for idx, row in g.sort_values("date").iterrows()]
        head = 0
        for day_in, qty_in in zip(a["date"], a["arrivals"]):
            left = float(qty_in)
            while left > 1e-9 and head < len(waiting):
                order_day = waiting[head][0]
                if day_in < order_day:            # kiriman sebelum pesanannya, bukan untuk itu
                    break
                take = min(waiting[head][1], left)
                waiting[head][1] -= take
                left -= take
                if waiting[head][1] <= 1e-9:
                    arrived.loc[waiting[head][2]] = day_in
                    head += 1
    return arrived


def manual_orders(daily: pd.DataFrame, catalog: pd.DataFrame, lead: pd.DataFrame,
                  since: pd.Timestamp, rec: pd.DataFrame) -> pd.DataFrame:
    m = daily[(daily["date"] < AGENT_START) & (daily["date"] >= since) & (daily["ordered"] > 0)]
    if m.empty:
        return pd.DataFrame(columns=OUT_COLUMNS)
    cover = cover_series(daily).reset_index()
    cover.columns = ["date", "sku", "cover_days"]
    m = m.merge(cover, on=["date", "sku"], how="left")
    m = m.merge(catalog[["sku", "principal_id", "unit_cost_idr"]], on="sku", how="left")
    m = m.merge(lead, left_on="principal_id", right_index=True, how="left")
    m["lead_days"] = m["lead_days"].fillna(10).astype(int)
    m = m.rename(columns={"ordered": "qty"})
    m["placed_by"] = "manual"
    m["reason"] = np.where(
        m["cover_days"] < m["lead_days"] + 7,
        "cover fell inside the delivery window",
        "ordered on the buyer's own judgement")

    # Kedatangan era manual: dicocokkan dari kiriman yang tercatat di riwayat harian, per
    # SKU dan urut lama dulu. Berkas pengiriman per pemasok dipakai sebagai cadangan kalau
    # SKU itu tidak punya catatan kedatangan sama sekali.
    m["arrived_date"] = allocate_arrivals(daily, m)
    rd = rec.copy()
    rd["order_date"] = pd.to_datetime(rd["order_date"])
    per = (rd.groupby(["order_date", "principal_id"])
             .apply(lambda g: pd.Series({
                 "actual_lead": float((g["actual_lead_d"] * g["ordered_units"]).sum()
                                      / max(float(g["ordered_units"].sum()), 1.0))}),
                    include_groups=False)
             .reset_index())
    m = m.merge(per, left_on=["date", "principal_id"],
                right_on=["order_date", "principal_id"], how="left")
    from_receiving = m["date"] + pd.to_timedelta(m["actual_lead"].round(0), unit="D")
    m["arrived_date"] = m["arrived_date"].where(m["arrived_date"].notna(), from_receiving)
    promised = m["date"] + pd.to_timedelta(m["lead_days"], unit="D")
    m["late_days"] = (m["arrived_date"] - promised).dt.days.clip(lower=0)
    return m


def agent_orders(catalog: pd.DataFrame, lead: pd.DataFrame) -> pd.DataFrame:
    if not SIM.exists():
        return pd.DataFrame(columns=OUT_COLUMNS)
    frames = []
    for d in sorted(SIM.glob("day-*")):
        p = d / "decisions.csv"
        if not p.exists():
            continue
        dec = pd.read_csv(p)
        if "guarded_order" not in dec:
            continue
        q = dec[dec["guarded_order"].fillna(0) > 0].copy()
        if q.empty:
            continue
        q["date"] = pd.Timestamp(d.name.replace("day-", ""))
        q["cover_days"] = (q["sellable_units"] /
                           q["forecast_daily_eff"].replace(0, np.nan)).round(1)
        frames.append(q[["date", "sku", "principal_id", "guarded_order", "rationale",
                         "cover_days"]])
    if not frames:
        return pd.DataFrame(columns=OUT_COLUMNS)
    a = pd.concat(frames, ignore_index=True)
    # Dari mana hari itu mengambil permintaannya. Sampai hari terakhir catatan penjualan,
    # dasarnya catatan. Hari hari setelahnya memakai permintaan model, dan barisnya membawa
    # penanda itu sampai ke halaman, jadi tidak ada yang bisa menyangka baris itu catatan.
    src = {}
    dp = SIM / "days.csv"
    if dp.exists():
        dd = pd.read_csv(dp)
        if "demand_source" in dd.columns:
            src = dict(zip(dd["day"], dd["demand_source"]))
    a["basis"] = a["date"].dt.strftime("%Y-%m-%d").map(src).fillna("recorded")
    a = a.merge(catalog[["sku", "unit_cost_idr"]], on="sku", how="left")
    a = a.merge(lead, left_on="principal_id", right_index=True, how="left")
    a["lead_days"] = a["lead_days"].fillna(10).astype(int)
    a["placed_by"] = "by the agent"
    a["reason"] = a["rationale"].fillna("sized and sent by the loop")
    a = a.rename(columns={"guarded_order": "qty"})
    d = deliveries()
    if len(d):
        d = d.rename(columns={"order_date": "date"})
        a = a.merge(d[["date", "sku", "promised", "arrives"]], on=["date", "sku"], how="left")
        a["arrived_date"] = a["arrives"]
        a["late_days"] = (a["arrives"] - a["promised"]).dt.days.clip(lower=0)
    return a


def finish(df: pd.DataFrame) -> pd.DataFrame:
    if "basis" not in df.columns:
        df["basis"] = "recorded"
    df["basis"] = df["basis"].fillna("recorded")
    if "supplier" not in df.columns:
        df["supplier"] = df["principal_id"] if "principal_id" in df else ""
    df["qty"] = df["qty"].round(0).astype(int)
    df["unit_cost_idr"] = df["unit_cost_idr"].fillna(0).astype(int)
    df["value_idr"] = (df["qty"] * df["unit_cost_idr"]).astype(int)
    df["promised_date"] = df["date"] + pd.to_timedelta(df["lead_days"], unit="D")
    df["arrived_date"] = pd.to_datetime(df.get("arrived_date"), errors="coerce")
    df["late_days"] = pd.to_numeric(df.get("late_days"), errors="coerce")
    clock = AS_OF or (pd.Timestamp((SIM / "clock.txt").read_text().strip())
                      if (SIM / "clock.txt").exists() else df["date"].max())
    df["landed"] = df["arrived_date"].notna() & (df["arrived_date"] <= clock)
    df["cover_days"] = df["cover_days"].round(1) if "cover_days" in df else np.nan
    df = df.sort_values(["date", "sku"]).reset_index(drop=True)
    df["order_id"] = [f"{'MN' if b == 'manual' else 'AG'}-{i:06d}"
                      for i, b in enumerate(df["placed_by"], start=1)]
    df["date"] = df["date"].dt.date.astype(str)
    df["promised_date"] = df["promised_date"].dt.date.astype(str)
    df["arrived_date"] = df["arrived_date"].dt.date.astype(str).where(
        df["arrived_date"].notna(), "")
    return df[[c for c in OUT_COLUMNS if c in df.columns]]


def main() -> int:
    global SIM, AGENT_START, AS_OF

    ap = argparse.ArgumentParser(description="riwayat order berkelanjutan")
    ap.add_argument("--manual-from", default="2025-01-01")
    ap.add_argument("--out", default=str(ORDERS / "order_history.csv"))
    ap.add_argument("--sim", default=str(SIM),
                    help="dunia simulasi yang dipakai untuk era agen (default data/sim/live)")
    ap.add_argument("--agent-start", default=str(AGENT_START.date()),
                    help="tanggal agen mengambil alih pembelian")
    ap.add_argument("--as-of", default="",
                    help="tanggal potret untuk kolom landed; kosong = clock.txt")
    a = ap.parse_args()

    SIM = pathlib.Path(a.sim)
    AGENT_START = pd.Timestamp(a.agent_start)
    AS_OF = pd.Timestamp(a.as_of) if a.as_of else None

    daily = pd.read_csv(STOCK / "stock_daily.csv", parse_dates=["date"])
    daily["sku"] = daily["sku"].astype(str)
    catalog = pd.read_csv(CAT / "catalog.csv")
    lead = lead_times()
    rec = pd.read_csv(CAT / "receiving.csv")

    man = manual_orders(daily, catalog, lead, pd.Timestamp(a.manual_from), rec)
    ag = agent_orders(catalog, lead)
    df = finish(pd.concat([man, ag], ignore_index=True))
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)

    print(f"riwayat order: {len(df):,} baris -> {a.out}")
    for who, g in df.groupby("placed_by"):
        print(f"  {who:9s} {len(g):>7,} baris | {g.qty.sum():>12,} unit | "
              f"Rp {g.value_idr.sum():>18,} | {g.date.min()} sampai {g.date.max()}")
    by_supplier = df.groupby("supplier").agg(baris=("qty", "size"), unit=("qty", "sum"),
                                             nilai=("value_idr", "sum"))
    print(f"  {len(by_supplier)} pemasok terpakai, terbesar:")
    for s, r in by_supplier.sort_values("nilai", ascending=False).head(3).iterrows():
        print(f"    {s}: {r.baris:,} baris, {r.unit:,} unit, Rp {r.nilai:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
