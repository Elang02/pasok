#!/usr/bin/env python
"""Jalankan distributor satu hari demi satu hari, dengan agen sebagai pelakunya.

Dua mode, dua pertanyaan berbeda:

    replay  dunia bergerak dari riwayat penjualan dan pengiriman yang tercatat, dan agen
            keputusan berjalan di atasnya tiap hari. Dunia ini setia: dunia untuk 11 Okt 2026
            menghasilkan keputusan yang sama persis dengan pipeline asli. Gunanya membuktikan
            mesinnya benar.
    closed  dunia bergerak dari KEPUTUSAN AGEN. Order hari ini masuk perjalanan dan mendarat
            setelah lead time. Kehilangan penjualan tiap hari jadi nilai rapor agen itu
            sendiri. Ini yang dipakai untuk kalimat "agen ini jalan sejak awal tahun".

Hari pertama mode closed disemai dari riwayat sampai sehari sebelumnya, plus pengiriman yang
sudah dalam perjalanan saat itu, karena barang itu memang sudah dipesan sebelum agen mulai.
Setelah itu tidak ada lagi yang diambil dari catatan: yang datang hanya yang dipesan agen.

Pakai:
    .venv/bin/python tools/simulate.py --mode replay snapshot --day 2026-10-11
    .venv/bin/python tools/simulate.py --mode closed run --from 2026-01-01 --days 284
    .venv/bin/python tools/simulate.py --mode closed status
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
STOCK = ROOT / "data" / "stock"
CAT = ROOT / "data" / "catalog"
SIM = ROOT / "data" / "sim"

PY = str(ROOT / ".venv" / "bin" / "python")

VELOCITY_WINDOW = 28
SAFETY_DAYS = 7
CONFIRM_DELAY = 7
# Agen itu sendiri meninjau tiap tujuh hari; kalimat di tiap kartunya menyebut "7 days until
# the next review". Dunia bergerak tiap hari, keputusan diambil pada hari tinjauan saja, dan
# log menandai hari mana yang tinjauan supaya tidak ada yang tersembunyi.
REVIEW_EVERY = int(os.environ.get("PASOK_REVIEW_EVERY", 7))
# Kiriman bertahap untuk barang berumur pendek: satu pesanan dipecah menjadi beberapa
# kedatangan berjarak TRANCH_EVERY_DAYS hari, dan hanya barang dengan umur simpan di bawah
# TRANCH_SHELF_DAYS yang dipecah. Ambient goods tidak perlu, karena menahan stok bukan
# masalahnya.
TRANCH_EVERY_DAYS = int(os.environ.get("PASOK_TRANCH_EVERY", 3))
TRANCH_SHELF_DAYS = int(os.environ.get("PASOK_TRANCH_SHELF", 60))
SEED_DAYS_AHEAD = 60
COLUMNS = ["sku", "principal_id", "on_hand_units", "in_transit_units", "open_po_units",
           "sellable_units", "velocity_units_day", "days_of_cover", "lead_time_days",
           "lead_trigger_days", "shelf_life_days", "below_reorder", "expiry_risk",
           "lost_sales_total", "snapshot", "oldest_lot_age_days", "usable_units",]


class World:
    """Satu direktori dunia per mode. Tidak ada berkas asli yang ditulis."""

    def __init__(self, mode: str, name: str | None = None):
        # name memisahkan dua catatan yang memakai mesin sama: catatan Oktober (agen mulai
        # 1 Oktober) tidak boleh menimpa uji balik setahun yang sudah ada.
        self.mode = mode
        self.name = name or mode
        self.dir = SIM / self.name
        self.world = self.dir / "world"
        self.log = self.dir / "days.csv"
        self.clock = self.dir / "clock.txt"
        self.world.mkdir(parents=True, exist_ok=True)

    def daily_path(self) -> pathlib.Path:
        return self.world / "stock_daily.csv"

    def daily(self) -> pd.DataFrame:
        p = self.daily_path()
        src = p if p.exists() else STOCK / "stock_daily.csv"
        d = pd.read_csv(src, parse_dates=["date"])
        d["sku"] = d["sku"].astype(str)
        return d

    def day(self) -> pd.Timestamp:
        if self.clock.exists():
            return pd.Timestamp(self.clock.read_text().strip())
        return self.daily()["date"].max()

    def start(self) -> pd.Timestamp:
        p = self.dir / "start.txt"
        if p.exists():
            return pd.Timestamp(p.read_text().strip())
        return self.daily()["date"].max()


_REAL: pd.DataFrame | None = None
_LEAD: tuple | None = None
_FILL: dict | None = None


def fill_rates() -> dict:
    """Berapa bagian dari pesanan yang benar benar dikirim tiap pemasok, dari catatan.

    Di catatan, 91,6 persen kiriman datang kurang dari pesanan. Selama ini simulasi selalu
    mengirim utuh, jadi dunianya lebih lunak dari catatannya sendiri. Angka ini yang dipakai
    supaya kedatangannya sebagian, sama seperti yang tercatat.
    """
    global _FILL
    if _FILL is None:
        rec = pd.read_csv(CAT / "receiving.csv")
        g = rec.groupby("principal_id").agg(o=("ordered_units", "sum"),
                                            r=("received_units", "sum"))
        _FILL = (g["r"] / g["o"].replace(0, np.nan)).clip(lower=0.5, upper=1.0).to_dict()
    return _FILL


def real_daily() -> pd.DataFrame:
    """Riwayat penjualan asli, dibaca sekali per proses. Membacanya tiap hari berarti 1,4
    detik kali tiga ratus hari untuk berkas yang isinya tidak pernah berubah."""
    global _REAL
    if _REAL is None:
        d = pd.read_csv(STOCK / "stock_daily.csv", parse_dates=["date"])
        d["sku"] = d["sku"].astype(str)
        _REAL = d
    return _REAL


def lead_times() -> tuple[dict, dict]:
    """Lead time rata rata mengantar barang, p90 memicu pesanan, sama seperti langkah posisi."""
    global _LEAD
    if _LEAD is None:
        rec = pd.read_csv(CAT / "receiving.csv")
        mean = rec.groupby("principal_id")["actual_lead_d"].mean().round().astype(int).to_dict()
        p90 = rec.groupby("principal_id")["actual_lead_d"].quantile(0.90).round(0).to_dict()
        _LEAD = (mean, p90)
    return _LEAD


def position(w: World, day: pd.Timestamp) -> pd.DataFrame:
    """Posisi 600 SKU pada hari itu, aturan sama dengan src/agents/stock_position.py."""
    d = w.daily()
    hist = d[d["date"] <= day]
    if hist.empty or (hist["date"] == day).sum() == 0:
        raise SystemExit(f"tidak ada riwayat untuk {day.date()}")
    catalog = pd.read_csv(CAT / "catalog.csv").set_index("sku")
    lead_mean, lead_p90 = lead_times()

    piv = hist.pivot_table(index="date", columns="sku", values="sales", aggfunc="sum")
    vel = piv.rolling(VELOCITY_WINDOW, min_periods=7).mean().iloc[-1]
    lost = hist.groupby("sku")["lost_sales"].sum()
    last = hist[hist["date"] == day].set_index("sku")

    pos = pd.DataFrame(index=last.index)
    pos["principal_id"] = catalog["principal_id"]
    pos["on_hand_units"] = last["on_hand"].round(1)
    pos["in_transit_units"] = last["in_transit"].round(1)
    pos["open_po_units"] = last["open_po"].round(1)
    pos["sellable_units"] = (last["on_hand"] + last["in_transit"] + last["open_po"]).round(1)
    pos["velocity_units_day"] = vel.round(2)
    cover = pos["sellable_units"] / pos["velocity_units_day"].replace(0, np.nan)
    pos["days_of_cover"] = cover.round(1)
    pos["lead_time_days"] = pos["principal_id"].map(lead_mean).fillna(10).astype(int)
    pos["lead_trigger_days"] = [float(lead_p90.get(p, l)) for p, l in
                               zip(pos["principal_id"], pos["lead_time_days"])]
    # Umur simpan yang dilihat agen harus sama dengan yang dipakai dunia untuk menua lot.
    # Sebelumnya baris ini membaca katalog langsung, jadi pada skenario what-if dengan
    # PASOK_SHELF_OVERRIDE dunia membusukkan barang di 21 hari sementara agen merencanakan
    # seolah tahan 180 hari: plafon umurnya tidak pernah menyala dan semua perbandingan
    # lengan jadi identik. shelf_days() sudah menerapkan override itu.
    pos["shelf_life_days"] = pd.Series(shelf_days()).reindex(pos.index).astype(int)
    pos["below_reorder"] = cover < (pos["lead_time_days"] + SAFETY_DAYS)
    pos["expiry_risk"] = cover.notna() & (cover > pos["shelf_life_days"])
    pos["lost_sales_total"] = lost.reindex(pos.index).fillna(0).astype(int)
    # Umur lot masuk sebagai masukan loop, bukan perbaikan terpisah. Stok yang sisa umurnya
    # tidak akan sampai ke kedatangan berikutnya tidak bisa dipakai melayani permintaan, dan
    # kalau tetap dihitung bisa dijual, agen memesan terus di belakang stok yang menua sampai
    # barang baru rusak mengantre. Lot yang sudah ada di gudang saat dunia disemai tidak punya
    # tanggal di catatan, jadi lotnya diberi tanggal hari penyemaian.
    lots_path = w.dir / "lots.csv"
    if lots_path.exists():
        lots = pd.read_csv(lots_path, parse_dates=["arrive"])
        lots["umur"] = (day - lots["arrive"]).dt.days
        sisa_umur = lots["sku"].map(pos["shelf_life_days"]) - lots["umur"]
        pos["oldest_lot_age_days"] = (lots.groupby("sku")["umur"].max()
                                      .reindex(pos.index).fillna(0).astype(int))
        bisa = lots[sisa_umur >= lots["sku"].map(pos["lead_trigger_days"])]
        pos["usable_units"] = (bisa.groupby("sku")["qty"].sum()
                               .reindex(pos.index).fillna(0).round(1))
        # Saklar ukur: PASOK_NO_LIFE_FILTER=1 menghitung seluruh stok sebagai bisa dipakai,
        # untuk membandingkan perilaku sebelum filter umur lot ada.
        if os.environ.get("PASOK_NO_LIFE_FILTER"):
            pos["usable_units"] = pos["on_hand_units"].round(1)
    else:
        pos["oldest_lot_age_days"] = 0
        pos["usable_units"] = pos["on_hand_units"]
    pos["snapshot"] = str(day.date())
    return pos.reset_index().rename(columns={"index": "sku"})[COLUMNS]


def write_world(w: World, day: pd.Timestamp) -> pd.DataFrame:
    pos = position(w, day)
    pos.to_csv(w.world / "position_snapshot.csv", index=False)
    w.clock.write_text(str(day.date()))
    return pos


def manual_decisions(w: World, day: pd.Timestamp) -> pd.DataFrame:
    """Kebijakan yang dijalankan orang hari ini, tanpa agen.

    Aturannya diambil dari kasus yang terbit, bukan dikarang: tinjauan sepekan sekali dan
    pesanan di awal minggu (Luju 2020), pesan ketika stok hampir habis lalu isi sampai
    sebulan penjualan menurut pengalaman, tanpa klasifikasi ABC sehingga semua SKU
    diperlakukan sama (Savitri dkk. 2022, PT ABC, 371 SKU). Tidak ada forecast, tidak ada
    kalender event, tidak ada plafon umur simpan, tidak ada gerbang kredit, satu kiriman
    per pesanan. Parameter dan sumbernya ada di data/demand/current_practice.json.
    """
    pos = pd.read_csv(w.world / "position_snapshot.csv")
    cfg = json.loads((ROOT / "data" / "demand" / "current_practice.json").read_text())
    review_days = int(os.environ.get("PASOK_MANUAL_REVIEW", cfg["review_days"]))
    safety_days = float(os.environ.get("PASOK_MANUAL_SAFETY", cfg["safety_days"]))
    target_cover = float(os.environ.get("PASOK_MANUAL_COVER", cfg["order_up_to_days"]))
    order_point = pos["lead_time_days"] + review_days + safety_days
    need = (pos["velocity_units_day"].fillna(0) * target_cover - pos["sellable_units"]).clip(lower=0)
    fire = pos["days_of_cover"].fillna(0) <= order_point
    qty = np.where(fire, np.floor(need.fillna(0)), 0.0)
    dec = pd.DataFrame({
        "sku": pos["sku"],
        "principal_id": pos["principal_id"],
        "guarded_order": qty,
        "action": np.where(qty > 0, "SIZE", "HOLD_ONE_CYCLE"),
        "cap_from": "manual rule",
        "guardrail_flags": "",
        # The manual rule has no forecast. Its implicit one is the rate the shelf is
        # moving at today, which is what a buyer reads off the stock card, and the
        # tranche split needs a daily rate to size deliveries against.
        "forecast_daily_eff": pos["velocity_units_day"].fillna(0.0),
    })
    out = w.dir / f"day-{day.strftime('%Y%m%d')}"
    out.mkdir(parents=True, exist_ok=True)
    dec.to_csv(out / "decisions.csv", index=False)
    return dec


def run_loop(w: World, day: pd.Timestamp) -> pd.DataFrame:
    """Jalankan agen keputusan asli pada dunia hari itu."""
    if os.environ.get("PASOK_POLICY") == "manual":
        return manual_decisions(w, day)
    out = w.dir / f"day-{day.strftime('%Y%m%d')}"
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PASOK_STOCK=str(w.world), PASOK_AGENT_OUT=str(out))
    r = subprocess.run([PY, str(ROOT / "src" / "agents" / "decision.py")],
                       env=env, capture_output=True, text=True, cwd=str(ROOT))
    if r.returncode != 0:
        print(r.stdout[-600:], r.stderr[-600:], file=sys.stderr)
        raise SystemExit(f"decision.py gagal untuk {day.date()}")
    return pd.read_csv(out / "decisions.csv")


def day_row(w: World, day: pd.Timestamp, dec: pd.DataFrame, sold: float, lost: float,
            arrived: float, on_hand: float, demand_source: str = "recorded") -> dict:
    cost = pd.read_csv(CAT / "catalog.csv").set_index("sku")["unit_cost_idr"]
    qty = dec["guarded_order"].fillna(0)
    value = (qty * dec["sku"].map(cost)).fillna(0)
    pos = pd.read_csv(w.world / "position_snapshot.csv")
    return {
        "mode": w.mode,
        "day": str(day.date()),
        "skus": int(len(dec)),
        "sold_units": int(sold),
        "lost_units": int(lost),
        "arrived_units": int(arrived),
        "on_hand_units": int(on_hand),
        "cover_median": round(float(pos["days_of_cover"].median()), 1),
        "out_of_stock": int((pos["on_hand_units"] <= 0).sum()),
        "in_transit_skus": int((pos["in_transit_units"] > 0).sum()),
        "decided_skus": int(qty.gt(0).sum()),
        "decided_units": int(qty.sum()),
        "decided_value_idr": int(value.sum()),
        "held_skus": int((dec["action"] == "HOLD_ONE_CYCLE").sum()),
        "review": 1, "demand_source": demand_source,
        "capped_fallback": int(dec["cap_from"].ne("own rhythm").sum()) if "cap_from" in dec else 0,
        "flagged_skus": int(dec["guardrail_flags"].fillna("").ne("").sum()),
    }


# Urutan kolom log ditetapkan di sini, bukan mengikuti urutan kunci dict pembuat baris.
# Dua pembuat baris (hari tinjauan dan hari biasa) menyusun kuncinya dengan urutan berbeda,
# dan pandas menulis berdasarkan posisi, jadi nilainya bergeser kolom: "demand_source" hari
# biasa mendarat di kolom lain. Satu daftar tetap menutup celah itu untuk selamanya.
LOG_COLUMNS = ["mode", "day", "skus", "sold_units", "lost_units", "arrived_units",
               "on_hand_units", "cover_median", "out_of_stock", "in_transit_skus",
               "decided_skus", "decided_units", "decided_value_idr", "held_skus",
               "flagged_skus", "capped_fallback", "in_transit_units", "review",
               "demand_source", "expired_units"]


def append_log(w: World, row: dict) -> None:
    hdr = not w.log.exists()
    pd.DataFrame([{k: row.get(k) for k in LOG_COLUMNS}]).to_csv(w.log, mode="a", header=hdr,
                                                                index=False)


# ------------------------------------------------------------------ mode replay ---
def step_replay(w: World, day: pd.Timestamp) -> dict:
    """Dunia dari riwayat: posisi dan kiriman datang dari catatan, bukan dari agen."""
    write_world(w, day)
    dec = run_loop(w, day)
    today = real_daily()
    today = today[today["date"] == day]
    row = day_row(w, day, dec, today["sales"].sum(), today["lost_sales"].sum(),
                  today["arrivals"].sum(), today["on_hand"].sum())
    append_log(w, row)
    return row


# ------------------------------------------------------------------ mode closed ---
def closed_init(w: World, start: pd.Timestamp) -> None:
    """Semai dunia sekali: riwayat sampai sehari sebelumnya, plus barang yang sedang jalan.

    Barang yang sudah dalam perjalanan pada hari pertama memang dipesan sebelum agen mulai,
    jadi jadwal kedatangannya diambil dari catatan. Setelah rentang itu habis, yang mendarat
    hanya barang yang dipesan agen.
    """
    if (w.dir / "queue.csv").exists():
        return
    real = real_daily()
    seed = real[real["date"] < start]
    seed.to_csv(w.daily_path(), index=False)
    last_day = seed["date"].max()
    opening = seed[seed["date"] == last_day].set_index("sku")
    opening[["on_hand", "in_transit", "open_po"]].to_csv(w.dir / "opening_state.csv")

    # Barang yang boleh dianggap sudah dalam perjalanan: sebanyak in_transit + open_po pada
    # hari terakhir riwayat, tidak lebih. Waktunya mengikuti catatan kedatangan, tapi begitu
    # jatah satu SKU habis, tidak ada lagi yang datang dari luar agen. Menjadwalkan seluruh
    # catatan dua bulan ke depan membuat dunia terlihat penuh stok dan agen jadi tidak
    # memesan sama sekali, itu bukan gambaran yang jujur.
    budget = (opening["in_transit"].fillna(0) + opening["open_po"].fillna(0)).round(0).to_dict()
    sched = real[(real["date"] >= start)][["date", "sku", "arrivals"]].sort_values("date")
    sched = sched[sched["arrivals"] > 0]
    rows = []
    for r in sched.itertuples():
        left = budget.get(r.sku, 0)
        if left <= 0:
            continue
        take = min(float(r.arrivals), left)
        budget[r.sku] = left - take
        rows.append({"date": r.date, "sku": r.sku, "arrivals": take})
        if all(v <= 1 for v in budget.values()):
            break
    inherited = pd.DataFrame(rows, columns=["date", "sku", "arrivals"])
    inherited.to_csv(w.dir / "inherited_arrivals.csv", index=False)
    pd.DataFrame({"arrives": pd.Series(dtype="datetime64[ns]"),
                  "sku": pd.Series(dtype=str),
                  "qty": pd.Series(dtype=float)}).to_csv(w.dir / "queue.csv", index=False)
    (w.dir / "start.txt").write_text(str(start.date()))
    print(f"disemai: {len(seed):,} baris riwayat sampai {last_day.date()}, "
          f"{int((opening['on_hand'] > 0).sum())} SKU berstok, "
          f"barang dalam perjalanan {int(sum(budget.values()) + inherited['arrivals'].sum()):,} unit "
          f"tersebar di {inherited['date'].nunique()} tanggal sampai "
          f"{inherited['date'].max().date() if len(inherited) else '-'}", flush=True)


def rest_row(w: World, day: pd.Timestamp, today_sales: pd.Series, shortfall: pd.Series,
             arriving: pd.Series, on_hand: pd.Series, in_transit: pd.Series,
             open_po: pd.Series, hist: pd.DataFrame, demand_source: str = "recorded",
              expired=None) -> dict:
    """Baris log untuk hari tanpa tinjauan: dunia bergerak, agen tidak dipanggil.

    Stok tersisa dan cover dihitung dari keadaan yang memang sudah ada di sini, bukan dengan
    membaca ulang seluruh riwayat dan menulis ulang berkas 50 MB untuk satu baris log.
    """
    tail = hist[hist["date"] > day - pd.Timedelta(days=VELOCITY_WINDOW)]
    vel = (tail.pivot_table(index="date", columns="sku", values="sales", aggfunc="sum")
           .mean())
    sellable = (on_hand + in_transit.reindex(on_hand.index).fillna(0)
                + open_po.reindex(on_hand.index).fillna(0))
    cover = (sellable / vel.reindex(on_hand.index).replace(0, np.nan)).median()
    return {
        "mode": w.mode, "day": str(day.date()), "skus": int(len(today_sales)),
        "sold_units": int(today_sales.sum()), "lost_units": int(shortfall.sum()),
        # Barang rusak harus ikut dihitung di hari biasa juga. Dulu angka ini hanya
        # masuk di hari tinjauan, jadi log mingguan melaporkan sepertujuh dari yang
        # sebenarnya dan sepuluh detiknya hilang. Rincian per SKU selalu lengkap, dan
        # sekarang log hariannya juga.
        "expired_units": int(expired.sum()) if expired is not None else 0,
        "arrived_units": int(arriving.sum()), "on_hand_units": int(on_hand.sum()),
        "cover_median": round(float(cover), 1) if pd.notna(cover) else None,
        "out_of_stock": int((on_hand <= 0).sum()),
        "in_transit_skus": int((in_transit > 0).sum()),
        "decided_skus": 0, "decided_units": 0, "decided_value_idr": 0,
        "held_skus": int(len(today_sales)), "flagged_skus": 0, "capped_fallback": 0,
        "in_transit_units": int(in_transit.sum()), "review": 0,
        "demand_source": demand_source,
    }


_SHELF: dict | None = None


def shelf_days() -> dict:
    """Umur simpan tiap SKU dalam hari, dari katalog.

    PASOK_SHELF_OVERRIDE bisa menunjuk berkas (sku, days) untuk menimpa umur simpan. Itu
    dipakai skenario what-if, misalnya kalau rentangnya menyertakan barang segar berumur
    pendek, tanpa menyentuh katalog aslinya sama sekali.
    """
    global _SHELF
    if _SHELF is None:
        c = pd.read_csv(CAT / "catalog.csv")
        _SHELF = dict(zip(c["sku"].astype(str), (c["shelf_life_months"] * 30).astype(int)))
        p = os.environ.get("PASOK_SHELF_OVERRIDE")
        if p and pathlib.Path(p).exists():
            o = pd.read_csv(p)
            _SHELF.update(dict(zip(o["sku"].astype(str), o["days"].astype(int))))
    return _SHELF


def load_lots(w: World) -> pd.DataFrame:
    p = w.dir / "lots.csv"
    if p.exists():
        d = pd.read_csv(p, parse_dates=["arrive"])
        d["sku"] = d["sku"].astype(str)
        return d
    return pd.DataFrame(columns=["sku", "arrive", "qty"])


def advance_lots(w: World, day: pd.Timestamp, arriving: pd.Series, demand: pd.Series,
                 opening: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Stok sebagai lot bertanggal: masuk, tua dibuang, lalu dijual yang paling tua dulu.

    Sampai sekarang stok cuma satu angka per SKU, jadi tidak ada barang yang bisa benar benar
    kedaluwarsa: stok hanya bisa terjual atau menganggur. Di sini tiap kiriman jadi satu lot
    dengan tanggal kedatangan, lot yang umurnya melewati umur simpan barang dibuang sebagai
    kedaluwarsa, dan penjualan memakan lot tertua dulu.

    Catatan jujur: stok yang sudah ada saat dunia disemai tidak punya tanggal di catatan, jadi
    lotnya diberi tanggal hari penyemaian. Artinya kedaluwarsa hanya terukur pada barang yang
    datang selama simulasi berjalan, dan itu memang satu satunya bagian yang datanya ada.
    """
    shelf = shelf_days()
    lots = load_lots(w)
    if not len(lots) and len(opening):
        seed = opening[opening > 0].rename("qty").reset_index()
        seed.columns = ["sku", "qty"]
        seed["arrive"] = day
        lots = seed[["sku", "arrive", "qty"]]

    add = arriving[arriving > 0].rename("qty").reset_index()
    add.columns = ["sku", "qty"]
    if len(add):
        add["arrive"] = day
        lots = pd.concat([lots, add[["sku", "arrive", "qty"]]], ignore_index=True)

    lots["shelf"] = lots["sku"].map(shelf).fillna(3650)
    age = (day - lots["arrive"]).dt.days
    dead = age > lots["shelf"]
    expired = lots[dead].groupby("sku")["qty"].sum()
    lots = lots[~dead][["sku", "arrive", "qty"]]
    lots = lots[lots["qty"] > 0].sort_values(["sku", "arrive"])

    need = demand.reindex(sorted(set(demand.index) | set(lots["sku"]))).fillna(0).to_dict()
    keep = []
    for sku, grp in lots.groupby("sku", sort=False):
        left = float(need.get(sku, 0.0))
        for arrive, qty in zip(grp["arrive"], grp["qty"]):
            q = float(qty)
            take = min(q, left)
            left -= take
            if q - take > 1e-9:
                keep.append((sku, arrive, q - take))
        need[sku] = left

    kept = pd.DataFrame(keep, columns=["sku", "arrive", "qty"])
    kept.to_csv(w.dir / "lots.csv", index=False)
    on_hand = kept.groupby("sku")["qty"].sum().reindex(demand.index).fillna(0) if len(kept) \
        else pd.Series(0.0, index=demand.index)
    sold = (demand - short_series(need, demand)).clip(lower=0)
    short = short_series(need, demand)
    return on_hand, sold, short, expired.reindex(demand.index).fillna(0)


def short_series(need: dict, demand: pd.Series) -> pd.Series:
    return pd.Series(need, dtype=float).reindex(demand.index).fillna(0)


def modelled_demand(real: pd.DataFrame, day: pd.Timestamp, skus) -> pd.Series:
    """Permintaan untuk hari yang TIDAK ada di catatan penjualan.

    Diambil dari rata rata penjualan hari sejenis (nama hari yang sama) selama empat minggu
    terakhir yang tercatat, per SKU. Dipakai hanya untuk melanjutkan dunia melewati hari
    terakhir catatan, dan setiap barisnya ditandai modelled supaya tidak tertukar dengan
    catatan asli.
    """
    tail = real[real["date"] > day - pd.Timedelta(days=28)]
    same = tail[tail["date"].dt.dayofweek == day.dayofweek]
    return same.groupby("sku")["sales"].mean().reindex(skus).fillna(0.0)


def step_closed(w: World, day: pd.Timestamp) -> dict:
    """Dunia dari keputusan agen: yang dipesan hari ini mendarat setelah lead time."""
    real = real_daily()
    rec = real[real["date"] == day]
    if len(rec):
        today_sales, demand_source = rec.set_index("sku")["sales"], "recorded"
    else:
        skus = real[real["date"] == real["date"].max()]["sku"].unique()
        today_sales, demand_source = modelled_demand(real, day, skus), "modelled"
    lead_mean, _ = lead_times()

    hist = w.daily()
    if day in set(hist["date"].unique()):
        raise SystemExit(f"hari {day.date()} sudah ada di riwayat dunia; tidak ditulis dua kali")
    prev = hist[hist["date"] < day]
    opening = prev[prev["date"] == prev["date"].max()].set_index("sku")
    queue = pd.read_csv(w.dir / "queue.csv", parse_dates=["arrives"]) \
        if (w.dir / "queue.csv").exists() else pd.DataFrame(columns=["arrives", "sku", "qty"])
    inh_path = w.dir / "inherited_arrivals.csv"
    inherited = pd.read_csv(inh_path, parse_dates=["date"]) if inh_path.exists() \
        else pd.DataFrame(columns=["date", "sku", "arrivals"])

    due = (queue[queue["arrives"] == day].groupby("sku")["qty"].sum()
           .add(inherited[inherited["date"] == day].set_index("sku")["arrivals"], fill_value=0))
    begin = opening["on_hand"].reindex(today_sales.index).fillna(0)
    arriving = due.reindex(today_sales.index).fillna(0)
    # Stok dipegang sebagai lot bertanggal: yang tua dibuang kalau lewat umur simpan, lalu
    # penjualan memakan lot tertua dulu. Barang bisa benar benar kedaluwarsa sekarang.
    on_hand, sold_today, shortfall, expired = advance_lots(w, day, arriving, today_sales, begin)
    sold_today = sold_today.reindex(today_sales.index).fillna(0)
    if len(expired[expired > 0]):
        ex = expired[expired > 0].rename("qty").reset_index()
        ex.columns = ["sku", "qty"]
        ex.insert(0, "date", day.date().isoformat())
        ex.to_csv(w.dir / "expired.csv", mode="a",
                  header=not (w.dir / "expired.csv").exists(), index=False)

    live = queue[queue["arrives"] > day].copy() if len(queue) else queue.copy()
    if len(live):
        live["arrives"] = pd.to_datetime(live["arrives"])
        days_out = (live["arrives"] - day).dt.days
        in_transit = live[days_out > CONFIRM_DELAY].groupby("sku")["qty"].sum()
        open_po = live[days_out <= CONFIRM_DELAY].groupby("sku")["qty"].sum()
    else:
        in_transit = pd.Series(dtype=float)
        open_po = pd.Series(dtype=float)

    # kiriman warisan yang belum mendarat tetap barang yang sedang dalam perjalanan. Kalau
    # tidak dihitung, agen melihat stok lebih tipis dari kenyataan dan memesan berlebihan.
    inh_live = inherited[inherited["date"] > day] if len(inherited) else inherited
    if len(inh_live):
        inh_out = (inh_live["date"] - day).dt.days
        in_transit = in_transit.add(
            inh_live[inh_out > CONFIRM_DELAY].groupby("sku")["arrivals"].sum(), fill_value=0)
        open_po = open_po.add(
            inh_live[inh_out <= CONFIRM_DELAY].groupby("sku")["arrivals"].sum(), fill_value=0)

    row_df = pd.DataFrame({
        "date": day,
        "sku": today_sales.index,
        "sales": sold_today.values,
        "on_hand": on_hand.reindex(today_sales.index).values,
        "in_transit": in_transit.reindex(today_sales.index).fillna(0).values,
        "open_po": open_po.reindex(today_sales.index).fillna(0).values,
        "arrivals": arriving.reindex(today_sales.index).values,
        "ordered": 0.0,
        "lost_sales": shortfall.reindex(today_sales.index).values,
    })
    row_df.to_csv(w.daily_path(), mode="a", header=False, index=False)

    review = ((day - w.start()).days % REVIEW_EVERY) == 0
    if not review:
        # Hari biasa: dunia bergerak, agen tidak dipanggil. Menjalankan agen tiap hari berarti
        # 10,8 detik kali tiga ratus hari untuk keputusan yang aturannya sendiri baru berubah
        # setelah tujuh hari, dan memanggilnya lebih sering dari itu bukan kesetiaan, itu
        # pemborosan. Barisnya tetap dicatat supaya jurangnya kelihatan.
        row = rest_row(w, day, today_sales, shortfall, arriving, on_hand, in_transit,
                       open_po, hist, demand_source, expired)
        # Jam dunia harus selalu maju. Dulu hanya hari tinjauan yang menulis jamnya, jadi
        # setelah sebelas hari jamnya masih di hari tinjauan terakhir, dan perintah lanjut
        # memulai dari tanggal yang salah lalu menulis ulang satu hari (9 Oktober dobel).
        w.clock.write_text(str(day.date()))
        append_log(w, row)
        return row

    write_world(w, day)
    dec = run_loop(w, day)
    qty = dec["guarded_order"].fillna(0)
    new = dec[qty > 0][["sku", "guarded_order", "principal_id"]].copy()
    if len(new):
        new["lead"] = new["principal_id"].map(lead_mean).fillna(10).astype(int)
        new["promised"] = day + pd.to_timedelta(new["lead"], unit="D")
        # Kedatangan sungguhan diberi variasi sesuai sebaran lead time yang tercatat untuk
        # pemasok itu, sama seperti langkah posisi memberi jitter. Kalau tidak, semua kiriman
        # selalu datang tepat waktu dan klaim soal ketepatan jadi artefak model, bukan bukti.
        rng = np.random.default_rng(int(day.strftime("%Y%m%d")) * 1000 + len(new))
        jitter = rng.integers(-1, 3, size=len(new))
        new["arrives"] = new["promised"] + pd.to_timedelta(np.maximum(jitter, -new["lead"] + 1),
                                                           unit="D")
        new = new.rename(columns={"guarded_order": "qty"})
        # Sebagian, bukan utuh: pemasok ini mengirim sebesar fill rate tercatatnya, dengan
        # variasi kecil per kiriman. Yang masuk antrean adalah jumlah yang akan tiba, bukan
        # jumlah yang dipesan, dan deliveries.csv menyimpan keduanya.
        fill = new["principal_id"].map(fill_rates()).fillna(1.0).astype(float)
        # Stress run: from PASOK_STRESS_FROM the principals ship less than their record says,
        # the way a supplier behaves in a bad quarter. The policy still reads the recorded fill,
        # so this measures what happens when reality is worse than the record, not when the
        # record is edited.
        _stress_from = os.environ.get("PASOK_STRESS_FROM", "")
        _stress_mult = float(os.environ.get("PASOK_STRESS_FILL", "1"))
        if _stress_from and _stress_mult != 1 and pd.Timestamp(day) >= pd.Timestamp(_stress_from):
            fill = fill * _stress_mult
        land = (new["qty"].astype(float) * fill
                * (1.0 + rng.normal(0.0, 0.04, size=len(new)))).clip(lower=0).round(0)
        new["landed_qty"] = land
        # Kiriman bertahap. Satu pesanan besar untuk barang berumur pendek tidak bisa
        # ditahan di rak: roti 30 hari yang datang sekaligus delapan hari permintaan
        # menghabiskan sisa umurnya di gudang. Pesanannya tetap satu, kedatangannya yang
        # dipecah menjadi tranche berjarak tiga hari, jadi rak tidak pernah menumpuk lebih
        # dari beberapa hari jual dan tidak pernah kosong menunggu kiriman berikutnya.
        # Barang berumur panjang tetap datang sekali, karena menahan stok bukan masalahnya.
        shelf = shelf_days()
        f_eff = dec.set_index("sku")["forecast_daily_eff"].reindex(new["sku"]).fillna(0.0)
        cover_d = new["landed_qty"].to_numpy() / np.maximum(f_eff.to_numpy(), 1.0)
        # Berapa hari jualan yang bisa dibawa SATU kiriman: umur simpan dikurangi lead, karena
        # jam barang mulai berjalan saat mendarat. Ini yang membatasi ukuran kiriman, bukan
        # umur simpannya sendiri.
        _, lead_p90_map = lead_times()
        lead_p90_sku = new["principal_id"].map(lambda p: float(lead_p90_map.get(p, 10)))
        lot_window = np.maximum(2.0, new["sku"].map(shelf).fillna(365).to_numpy()
                                - lead_p90_sku.to_numpy())
        n_tr = np.clip(np.ceil(cover_d / lot_window), 1, 6)
        # A person places one order and takes one delivery. Splitting arrivals is a
        # capability of the agent under test, so letting it happen in the manual
        # baseline would measure the feature against itself and flatter the result.
        manual_policy = os.environ.get("PASOK_POLICY", "agent") == "manual"
        if manual_policy:
            n_tr = np.ones_like(n_tr)
        # Jarak antar tranche mengikuti cover, bukan angka tetap: tranche pertama sampai
        # berikutnya harus memakai stok yang ada, jadi jaraknya = cover / jumlah tranche.
        # Versi pertama memakai jarak tetap 3 hari untuk semua barang di bawah 60 hari, dan itu
        # membuat barang 60 hari menerima tetesan lebih lambat daripada laju jualnya: inflow
        # 792 unit/hari melawan permintaan 1.200, sehingga rak kosong sambil barang masih di
        # jalan (SKU0366, Maret 2026).
        spacing = np.clip(cover_d / n_tr, 2.0, 30.0)
        rows, drec = [], []
        for (_, r), k, gap in zip(new.iterrows(), n_tr.astype(int), spacing):
            part_land = float(r["landed_qty"]) / k
            part_ord = float(r["qty"]) / k
            for j in range(k):
                drop = r["arrives"] + pd.Timedelta(days=round(float(gap) * j))
                rows.append({"arrives": drop, "sku": r["sku"], "qty": part_land})
                drec.append({"order_date": day.date().isoformat(), "placed_by": "a person" if manual_policy else "the agent",
                             "sku": r["sku"], "qty": part_ord, "landed_qty": part_land,
                             "promised": r["promised"], "arrives": drop})
        if drec:
            pd.DataFrame(drec).to_csv(w.dir / "deliveries.csv", mode="a",
                                      header=not (w.dir / "deliveries.csv").exists(),
                                      index=False)
        new = pd.DataFrame(rows, columns=["arrives", "sku", "qty"])
        queue = pd.concat([live, new], ignore_index=True)
    else:
        queue = live
    queue.to_csv(w.dir / "queue.csv", index=False)

    # catat apa yang dipesan hari ini, supaya agen tidak memesan hal yang sama dua kali
    ordered = row_df.copy()
    ordered["ordered"] = qty.reindex(ordered["sku"]).fillna(0).values
    keep = hist[hist["date"] < day]
    pd.concat([keep, ordered], ignore_index=True).to_csv(w.daily_path(), index=False)

    row = day_row(w, day, dec, sold_today.sum(), shortfall.sum(), arriving.sum(), on_hand.sum(),
                  demand_source)
    row["expired_units"] = int(expired.sum())
    row["in_transit_units"] = int(in_transit.sum())
    row["demand_source"] = demand_source
    append_log(w, row)
    return row


def step_for(w: World):
    return step_closed if w.mode == "closed" else step_replay


def line(w: World, row: dict) -> str:
    return (f"[{w.mode}] {row['day']}: hilang {row['lost_units']:,} unit, "
            f"datang {row['arrived_units']:,}, sisa {row['on_hand_units']:,}, "
            f"kosong {row['out_of_stock']} SKU | agen memutuskan {row['decided_skus']} SKU "
            f"senilai Rp {row['decided_value_idr']:,}")


def cmd_extend(w: World, to: pd.Timestamp) -> int:
    """Teruskan dunia yang sudah ada sampai tanggal tertentu.

    Dipakai untuk melanjutkan catatan yang berhenti di hari terakhir riwayat penjualan.
    Hari yang tidak punya catatan memakai permintaan model dan ditandai di log, jadi tidak
    ada satu baris pun yang bisa tertukar dengan catatan asli.
    """
    awal = max(w.day(), pd.Timestamp(w.daily()["date"].max()))
    cur = awal
    n_mod = 0
    while cur < to:
        cur = cur + pd.Timedelta(days=1)
        row = step_for(w)(w, cur)
        if row.get("demand_source") == "modelled":
            n_mod += 1
        if row.get("review"):
            print(line(w, row), flush=True)
    print(f"[{w.mode}] lanjut {int((cur - awal).days)} hari sampai {cur.date()}: "
          f"{n_mod} hari permintaannya model", flush=True)
    return 0


def cmd_step(w: World, advance: bool = True) -> int:
    cur = w.day()
    if w.mode == "closed":
        closed_init(w, cur)
    if advance:
        real = real_daily()
        nxt = real[real["date"] > cur]["date"].min()
        if pd.isna(nxt):
            print(f"riwayat habis di {cur.date()}")
            return 1
        cur = pd.Timestamp(nxt)
    row = step_for(w)(w, cur)
    print(line(w, row), flush=True)
    return 0


def cmd_run(w: World, start: str, days: int) -> int:
    cur = pd.Timestamp(start)
    if w.mode == "closed":
        closed_init(w, cur)
    step = step_for(w)
    for _ in range(days):
        print(line(w, step(w, cur)), flush=True)
        real = real_daily()
        nxt = real[real["date"] > cur]["date"].min()
        if pd.isna(nxt):
            break
        cur = pd.Timestamp(nxt)
    return cmd_status(w)


def cmd_status(w: World) -> int:
    if not w.log.exists():
        print(f"[{w.mode}] belum ada hari yang dijalankan")
        return 0
    log = pd.read_csv(w.log)
    print(f"[{w.mode}] jam {w.day().date()} | {len(log)} hari, "
          f"{int(log['review'].sum()) if 'review' in log else 0} hari tinjauan "
          f"({log.day.min()} sampai {log.day.max()})")
    print(log[["day", "sold_units", "lost_units", "arrived_units", "on_hand_units",
               "cover_median", "out_of_stock", "decided_skus"]].tail(10).to_string(index=False))
    demand = log.sold_units.sum() + log.lost_units.sum()
    print(f"total: terjual {log.sold_units.sum():,} unit | hilang {log.lost_units.sum():,} "
          f"({log.lost_units.sum() / max(demand, 1) * 100:.2f} persen) | agen memutuskan "
          f"{log.decided_skus.sum():,} baris SKU, {log.decided_units.sum():,} unit, "
          f"Rp {log.decided_value_idr.sum():,}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="dunia hari demi hari")
    ap.add_argument("--mode", choices=["replay", "closed"], default="replay")
    ap.add_argument("--name", default=None, help="nama direktori catatan, mis. live")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot")
    s.add_argument("--day", required=True)
    st = sub.add_parser("step")
    st.add_argument("--stay", action="store_true", help="ulang hari yang sama, jangan maju")
    sr = sub.add_parser("run")
    sr.add_argument("--from", dest="start", required=True)
    sr.add_argument("--days", type=int, default=30)
    se = sub.add_parser("extend")
    se.add_argument("--to", required=True)
    sub.add_parser("status")
    a = ap.parse_args()
    w = World(a.mode, getattr(a, "name", None))

    # Dua proses yang menulis ke satu direktori dunia saling menghapus berkas satu sama lain:
    # itu sudah terjadi sekali, dan satu proses lama yang masih hidup merusak jendela hari
    # yang dijalankan proses baru. Kuncinya sederhana dan menolak, bukan menimpa.
    lock = w.dir / "run.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            holder = int(lock.read_text().strip())
            os.kill(holder, 0)
            print(f"dunia {a.mode} sedang dipakai proses {holder}; hentikan dulu", file=sys.stderr)
            return 2
        except (ValueError, ProcessLookupError, PermissionError):
            lock.unlink(missing_ok=True)
    lock.write_text(str(os.getpid()))
    try:
        if a.cmd == "snapshot":
            d = pd.Timestamp(a.day)
            if a.mode == "closed":
                closed_init(w, d)
            pos = write_world(w, d)
            print(f"[{w.mode}] dunia {d.date()}: {len(pos)} SKU, stok "
                  f"{pos.on_hand_units.sum():,.0f} unit, cover median "
                  f"{pos.days_of_cover.median():.1f} hari, kosong "
                  f"{int((pos.on_hand_units <= 0).sum())} SKU")
            return 0
        if a.cmd == "step":
            return cmd_step(w, advance=not a.stay)
        if a.cmd == "run":
            return cmd_run(w, a.start, a.days)
        if a.cmd == "extend":
            return cmd_extend(w, pd.Timestamp(a.to))
        return cmd_status(w)
    finally:
        if lock.exists() and lock.read_text().strip() == str(os.getpid()):
            lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
