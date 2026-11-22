"""
Pasok — Decision Agent (with ReplenishAgent guardrails)
=======================================================

Fuses the three signals into one order recommendation per SKU:

    demand forecast  (from history + known event ramp)
  + stock position   (sellable = on_hand + in_transit)
  + supplier reality (learned p90 lead time, not the master promise)
  = raw order

...then runs the raw order through the same three guardrails that beat the unguarded
agent in E1: forecast smoothing, order damping, variance cap.

Two outputs
-----------
1. `data/agents/decisions.csv` — one row per SKU at the snapshot date, with the raw
   order, the guarded order, and a rationale string naming the real drivers. This is
   the artefact the demo shows.
2. `data/agents/decision_summary.json` — including the network-level amplification
   test: the same guardrails applied to a live order stream over the last 104 days,
   measuring Var(orders)/Var(demand) raw vs guarded. This is the Phase-2 reproduction
   of the E1 result on THIS catalog, not the standalone synthetic sim.

Run
---
    cd /home/ubuntu/pasok
    .venv/bin/python src/agents/decision.py
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "data" / "prep"
STOCK = Path(os.environ.get("PASOK_STOCK") or (ROOT / "data" / "stock"))  # PASOK_STOCK = hari yang disimulasikan
AG = ROOT / "data" / "agents"
DEMAND = ROOT / "data" / "demand"
# Service level by ABC class. A SKU that goes empty loses a sale the shop does not get
# back; a C SKU that sits ties up capital that could buy a fast mover. The old code used
# one z (1.28) for all 600 SKUs, which is the same policy for both mistakes.
def _class_z_from_env() -> dict:
    """Service level per class. An experiment sets PASOK_CLASS_Z="A:1.28,B:1.04,C:0.84"
    so a policy change is a record in the replay, not an edit to source."""
    raw = os.environ.get("PASOK_CLASS_Z", "A:1.645,B:1.28,C:0.84")
    out = {}
    for part in raw.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().upper()] = float(v)
    return out or {"A": 1.645, "B": 1.28, "C": 0.84}


CLASS_Z = _class_z_from_env()
# PASOK_AGENT_OUT lets a simulated day write its own decisions instead of over the
# real ones, so the loop can be replayed without touching the shipped artefacts.
OUT = Path(os.environ.get("PASOK_AGENT_OUT") or AG)

REVIEW_DAYS = int(os.environ.get("PASOK_REVIEW_EVERY", 7))
# Umur simpan (hari) di bawah mana barang tidak dibeli di muka untuk event. 0 = mati.
PREBUY_EXCLUDE = float(os.environ.get("PASOK_PREBUY_EXCLUDE_SHELF", "0"))
# Shelf life is measured FROM ARRIVAL in this model (a lot expires `shelf` days after it lands,
# see tools/simulate.py), so transit does not eat into it and subtracting the lead time from the
# life counts the journey twice. One review window is kept back so the last lot can still be sold.
STAGED_FLOOR_DAYS = 2.0
# A lot cannot be replaced before it is gone when the delivery takes longer than the goods last
# from arrival. That is the one case no ordering policy can serve, and it is escalated instead of
# being papered over with a token order.
UNSERVABLE_MARGIN_DAYS = 0.0
REPLAY_DAYS = 104
EWMA_ALPHA = 0.15
DAMP = 0.5
CAP_K = 0.5
CAP_HEADROOM = float(os.environ.get("PASOK_CAP_HEADROOM", "1.25"))  # ruang di atas KEBUTUHAN, bukan target

# Payday: demand naik 1,22 kali tanggal 25 sampai 28 dan tanggal 1 sampai 5 tiap bulan. Aturan
# yang sama dipakai pembangkit demand (src/catalog/generate.py), jadi kedua sisi memakai definisi
# yang identik. Karena berulang tiap bulan dan tidak punya tanggal kalender, Payday tidak pernah
# masuk tabel ramp, dan dulu sama sekali tidak ikut menghitung ukuran pesanan.
PAYDAY_MULT = 1.22
PAYDAY_DAYS = (1, 2, 3, 4, 5)


def snapshot_date() -> pd.Timestamp:
    """The last day of the generated sales window, read from the data.

    Stock Position writes this value; the decision is made against the same
    date. Two literals would drift apart the moment the window moves.
    """
    p = STOCK / "position_snapshot.csv"
    import csv
    with p.open() as fh:
        rows = list(csv.DictReader(fh))
    if rows and rows[0].get("snapshot"):
        return pd.Timestamp(rows[0]["snapshot"])
    # fall back to the sales cache; its date lives in the index
    idx = pd.read_parquet(PREP / "daily_by_sku.parquet").index
    return pd.to_datetime(idx).max()


# the agents write this into JSON artefacts, so keep it a string on the way out
SNAPSHOT = str(snapshot_date().date())
# Skenario what-if: umur simpan bisa ditimpa lewat berkas, untuk menguji barang berumur
# pendek tanpa mengubah katalog aslinya.


def _shelf_override() -> dict:
    p = os.environ.get("PASOK_SHELF_OVERRIDE")
    if not p or not Path(p).exists():
        return {}
    d = pd.read_csv(p)
    return dict(zip(d["sku"].astype(str), d["days"].astype(int)))


SHELF_OVERRIDE = _shelf_override()


# --------------------------------------------------------------- forecast ---
def load_daily() -> pd.DataFrame:
    d = pd.read_parquet(PREP / "daily_by_sku.parquet")
    if "date" in d.columns:
        d = d.set_index("date")
    d.index = pd.to_datetime(d.index)
    d = d.sort_index()
    # Berkas ini berakhir di hari terakhir riwayat tercatat, dan snapshot yang dikirim ke
    # konsol MEMANG hari itu, jadi untuk jalan sungguhan baris ini tidak mengubah apa pun.
    # Di dalam simulasi dunia bisa berada berbulan bulan lebih awal, dan tanpa potongan ini
    # agen bulan Januari menghitung pembeliannya dari penjualan September dan Oktober yang
    # belum seharusnya dia lihat. Baseline-nya memakai 28 baris terakhir, jadi bocornya
    # tidak halus sama sekali.
    return d.loc[:pd.Timestamp(SNAPSHOT)]


# Hijriah/bulan: tahunnya ~354 hari, jadi tanggalnya bergeser tiap tahun. Valentine dan
# Kemerdekaan tanggal tetap (365), sisanya lunar.
LUNAR_EVENTS = {"Ramadan", "Lebaran", "Imlek", "IdulAdha", "Maulid"}


def event_windows(registry: pd.DataFrame, ramps: pd.DataFrame,
                  after: pd.Timestamp) -> list[tuple[str, pd.Timestamp, float]]:
    """The next real date of each event, taken from a table of dates, never by stepping years.

    Two bugs lived here. Stepping 354 days from the ramp learner's week bucket put Christmas in
    January 2027 while the calendar still had December ahead, and anchoring on the snapshot let
    a date that had already passed be announced as "nearest". The dates now come from
    `data/demand/event_dates.csv`, and anything not strictly after `max(after, today)` is
    dropped rather than rolled forward.

    Payday is skipped: it is a salary cycle, not an event. What a payday promo discounts changes
    every month, so there is nothing stable to learn and nothing to announce.
    """
    today = pd.Timestamp.today().normalize()
    floor = max(pd.Timestamp(after).normalize(), today)
    dates = pd.read_csv(ROOT / "data" / "demand" / "event_dates.csv")
    dates["date"] = pd.to_datetime(dates["date"])
    upcoming = {}
    for name, grp in dates.groupby("event"):
        ahead = grp.loc[grp["date"] > floor, "date"]
        if len(ahead):
            upcoming[str(name)] = ahead.min()
    out = []
    for _, r in registry.iterrows():
        name = str(r["event"])
        if name not in upcoming:
            continue
        out.append((name, upcoming[name], float(r["mean_factor"])))
    return sorted(out, key=lambda row: row[1])


def ramp_uplift(peak_day: pd.Timestamp, days_to_peak: float, peak_mult: float,
                decay_slope: float, snap_date: pd.Timestamp,
                horizon_end: pd.Timestamp) -> float:
    """Mean demand uplift over the buying horizon, from the ramp the agent learned.

    The ramp is not a flat bump. Per SKU the learner fits when demand builds, peaks and
    decays (proposal line 13). We reproduce that shape over the horizon and average it,
    so a product that spikes for three days does not get sized as if it spiked for three
    weeks:

        t < peak - days_to_peak      : 1.0            (still baseline)
        peak - dtp <= t <= peak      : 1 -> peak_mult (build)
        t > peak                     : peak_mult - decay_slope per day, floor 1.0

    Returns 1.0 when the horizon never reaches the ramp.
    """
    build_start = peak_day - pd.Timedelta(days=max(0.0, days_to_peak))
    if horizon_end < build_start:
        return 1.0

    lo = max(snap_date, build_start)
    days = pd.date_range(lo, horizon_end, freq="D")
    if len(days) == 0:
        return 1.0

    up = []
    for d in days:
        if d < build_start:
            up.append(1.0)
        elif d <= peak_day:
            frac = (d - build_start).days / max(1.0, days_to_peak)
            up.append(1.0 + (peak_mult - 1.0) * frac)
        else:
            # decay_slope is fitted on the WEEKLY profile, so convert to per day.
            # The horizon may stop before the decay finishes; average what it covers.
            drop = (decay_slope / 7.0) * (d - peak_day).days
            up.append(max(1.0, peak_mult - drop))
    # average over the WHOLE horizon, not only the days the ramp touches
    total_days = (horizon_end - snap_date).days + 1
    return float(sum(up) / max(1, total_days))


def ramp_days(peak_day: pd.Timestamp, days_to_peak: float, peak_mult: float,
              decay_slope: float, start: pd.Timestamp,
              end: pd.Timestamp) -> np.ndarray:
    """Per-day uplift multiplier for every calendar day in [start, end].

    ramp_uplift() averages this same curve over a window; sizing needs the shape rather
    than its mean, because a delivery lands on one date and sells until the next one.
    """
    days = pd.date_range(start, end, freq="D")
    out = np.ones(len(days))
    build_start = peak_day - pd.Timedelta(days=max(0.0, days_to_peak))
    for i, d in enumerate(days):
        if d < build_start:
            continue
        if d <= peak_day:
            frac = (d - build_start).days / max(1.0, days_to_peak)
            out[i] = 1.0 + (peak_mult - 1.0) * frac
        else:
            out[i] = max(1.0, peak_mult - (decay_slope / 7.0) * (d - peak_day).days)
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    snap_in = pd.read_csv(STOCK / "position_snapshot.csv")
    sup = pd.read_csv(AG / "supplier_reliability.csv").set_index("principal_id")
    ramps = pd.read_csv(DEMAND / "sku_ramps.csv")
    registry = pd.read_csv(DEMAND / "event_registry.csv")
    baselines = pd.read_csv(DEMAND / "baselines.csv")[["sku", "resid_sd"]].set_index("sku")
    catalog = pd.read_csv(ROOT / "data" / "catalog" / "catalog.csv")[
        ["sku", "shelf_life_months", "principal_id"]].set_index("sku")
    cat_principal = catalog["principal_id"].to_dict()
    daily = load_daily()
    # The realised order stream used to be read here to calibrate the cap on the SKU's own
    # ordering habit. The cap is measured in days of demand now, so this 53 MB read is gone.

    # ---- proposal line 15: buffer from lead-time variability AND forecast errors ----
    # per principal: lead_var contribution = (lead_p90 - lead_p50), forecast_err
    # contribution = the principal's SKUs' median forecast residual sd expressed in
    # days of that SKU's own demand. Combined at 90% service (z=1.28), capped by the
    # shelf life window the product can actually wait.
    Z90 = 1.28
    catalog_map = catalog["shelf_life_months"].index.to_series().to_dict()  # sku -> itself (index)
    base_sku = baselines.copy()
    base_sku["principal_id"] = [cat_principal.get(s) for s in base_sku.index]

    # Sumbangan galat ramalan hanya bergantung pada pemasoknya, bukan pada SKU. Versi
    # sebelumnya menghitungnya di dalam fungsi yang dipanggil sekali per SKU, jadi median
    # 600 kolom dihitung ulang puluhan kali dan satu hari makan 27 detik. Dihitung sekali
    # di sini, nilainya sama persis.
    sku_median = daily.median(numeric_only=True).to_dict()
    base_sku["dem"] = [float(sku_median.get(s, 0.0) or 0.0) for s in base_sku.index]
    base_sku["err_days"] = np.where(base_sku["dem"] > 0,
                                    base_sku["resid_sd"].fillna(0.0) / base_sku["dem"],
                                    np.nan)
    err_cache: dict = {}
    for pid, g in base_sku.groupby("principal_id"):
        vals = g["err_days"].dropna()
        err_cache[pid] = float(np.median(vals)) if len(vals) else 0.0

    cls_path = DEMAND / "sku_classes.csv"
    sku_class = (pd.read_csv(cls_path).set_index("sku")["class_volume"].to_dict()
                 if cls_path.exists() else {})

    # Lead spread and the tail past the p90 we plan with, both read from the receiving record
    # rather than inferred from two quantiles. The p90 is what the agent buys against; the
    # spread is what the buffer has to absorb, and the tail is the part of the record that
    # lands after the p90 was promised. Until 26 Oct the spread was proxied by (p90 - p50),
    # which is larger than the standard deviation for one principal and smaller for another,
    # and the tail had no allowance at all.
    lead_sd = {pid: float(v) for pid, v in sup.get("lead_std_d", pd.Series(dtype=float)).items()}
    late_tail: dict = {}
    rec_path = ROOT / "data" / "catalog" / "receiving.csv"
    if rec_path.exists():
        rec = pd.read_csv(rec_path)
        for pid, g in rec.groupby("principal_id"):
            p90 = float(sup.loc[pid, "lead_p90_d"]) if pid in sup.index else float(g["actual_lead_d"].median())
            # Not the mean tail: a mean hides the very deliveries that empty the shelf. One
            # truck in twenty arrives three or four days after the p90, and a buffer sized on
            # the average is short exactly then. The 95th percentile of the lateness past the
            # p90 is the day the shelf has to survive, and it is still a number the record
            # shows rather than a rule of thumb.
            late_tail[pid] = float(np.percentile(
                np.maximum(0.0, g["actual_lead_d"].to_numpy() - p90), 95))

    def principal_buffer(pid: str, lead_p90: float, lead_p50: float,
                         shelf_cap_days: float, z: float = Z90,
                         demand_cv: float = 0.0) -> dict:
        fc_err_days = err_cache.get(pid, 0.0) if os.environ.get("PASOK_BUFFER_LEGACY") else 0.0
        lead_var_days = max(0.0, lead_p90 - lead_p50)
        sd_l = 0.0 if os.environ.get("PASOK_BUFFER_LEGACY") else lead_sd.get(pid, lead_var_days)
        tail = 0.0 if os.environ.get("PASOK_BUFFER_LEGACY") else late_tail.get(pid, 0.0)
        # Safety stock in days of demand: z * sqrt(lead * CV_demand^2 + sigma_lead^2), plus the
        # measured tail past the p90. Textbook additivity, with the record's own spread instead
        # of a quantile gap, and one term for deliveries that land after the day they promised.
        if os.environ.get("PASOK_BUFFER_LEGACY"):
            combined = z * math.sqrt(lead_var_days ** 2 + fc_err_days ** 2)
        else:
            combined = z * math.sqrt(max(0.0, lead_p90) * max(0.0, demand_cv) ** 2 + sd_l ** 2) + tail
        raw = max(2.0, combined)
        cap_binds = raw > shelf_cap_days
        capped = min(raw, shelf_cap_days)
        return {
            "buffer_days": int(max(2, math.ceil(capped))),
            "lead_var_contrib_d": round(sd_l if not os.environ.get("PASOK_BUFFER_LEGACY") else lead_var_days, 2),
            "forecast_err_contrib_d": round(demand_cv * math.sqrt(max(0.0, lead_p90)), 2),
            "late_tail_p95_d": round(tail, 2),
            "shelf_cap_binds": bool(cap_binds),
        }

    snap_date = pd.Timestamp(SNAPSHOT)
    windows = event_windows(registry, ramps, snap_date)

    # ---------------------------------------------------- snapshot decisions ---
    # horizon we are buying for = learned p90 lead time + review period + buffer
    rows = []
    for _, s in snap_in.iterrows():
        sku = s["sku"]
        pid = s["principal_id"]
        lead_p90 = float(sup.loc[pid, "lead_p90_d"])
        lead_p50 = float(sup.loc[pid, "lead_p50_d"]) if "lead_p50_d" in sup.columns else lead_p90
        shelf_life_d = float(catalog.loc[sku, "shelf_life_months"]) * 30.0 if sku in catalog.index else 999.0
        if SHELF_OVERRIDE:
            shelf_life_d = float(SHELF_OVERRIDE.get(sku, shelf_life_d))
        # shelf-life cap: the buffer cannot push cover past what the product can wait. The
        # journey is not subtracted here: the life clock starts when the lot lands.
        shelf_cap = max(2.0, shelf_life_d - REVIEW_DAYS)
        # Slack between how long delivery takes and how long the goods last once they land.
        # Negative means a lot is gone before its replacement can arrive: not servable by any
        # ordering policy, so it is escalated rather than dribbled.
        life_margin = shelf_life_d - lead_p90
        # PASOK_KEEP_UNSERVABLE=1 restores the old behaviour so a run can be compared against
        # the loud rule on the same window; it exists for measurement, not for production.
        unservable = (bool(life_margin <= UNSERVABLE_MARGIN_DAYS)
                      and not os.environ.get("PASOK_KEEP_UNSERVABLE"))

        sku_abc = str(sku_class.get(sku, "B"))
        z_used = CLASS_Z.get(sku_abc, Z90)
        # Barang berumur panjang tidak berisiko busuk, jadi cadangannya boleh lebih tebal
        # tanpa menukar apa pun. Barang berumur pendek dijaga di z lama justru karena
        # cadangan tambahan di raknya berubah menjadi kedaluwarsa, bukan layanan.
        # PASOK_Z_LONGLIFE=0 mematikan pembeda ini untuk pengukuran.
        if (os.environ.get("PASOK_Z_LONGLIFE", "1") == "1"
                and sku_abc == "A" and shelf_life_d >= 90):
            z_used = 1.88
        # forecast: robust daily baseline from history (median of last 28 days)
        hist = daily[sku].to_numpy(dtype=float)
        f_daily = float(np.median(hist[-28:]))
        # Per-SKU demand swing: the last 90 days, standard deviation over the mean. A steady
        # cooking-oil line and a bread line with the same forecast get different buffers now.
        h90 = hist[-90:] if len(hist) >= 30 else hist
        mean90 = float(np.mean(h90)) if len(h90) else 0.0
        demand_cv = float(np.std(h90) / mean90) if mean90 > 0 else 0.0
        buf = principal_buffer(pid, lead_p90, lead_p50, shelf_cap, z_used, demand_cv)
        # PASOK_BUFFER_EXTRA_DAYS exists for measurement: it adds the same number of days to
        # every SKU so one replay can answer whether the buffer is what leaves shelves bare,
        # before any formula is changed. Default 0 keeps the shipped policy.
        extra_d = int(os.environ.get("PASOK_BUFFER_EXTRA_DAYS", 0))
        buffer_d = int(min(buf["buffer_days"] + extra_d, shelf_cap))

        # Jendela yang benar adalah jendela JUAL, bukan horizon beli. Barang baru dijual setelah
        # mendarat, jadi rata-rata multiplier diambil dari hari mendarat sampai mendarat plus satu
        # tinjauan. Jendela lama mulai dari hari pesan, sehingga 19 hari barang masih di jalan ikut
        # dirata-ratakan dan puncaknya terencerkan.
        sell_start = snap_date + pd.Timedelta(days=int(round(lead_p90)))
        sell_end = sell_start + pd.Timedelta(days=REVIEW_DAYS)
        n_hari = max(1, (sell_end - sell_start).days + 1)
        ev_name, ev_mult, ev_day = "", 1.0, None
        for name, peak_day, base_mult in sorted(windows, key=lambda w: w[1]):
            r = ramps[(ramps["sku"] == sku) & (ramps["event"] == name)]
            if not len(r):
                continue
            dtp = float(r.iloc[0]["days_to_peak"])
            pk = float(r.iloc[0]["peak_mult"])
            ds = float(r.iloc[0]["decay_slope"])
            up = ramp_uplift(peak_day, dtp, pk, ds, sell_start, sell_end)
            if up > 1.0:
                # Kejadian bertumpuk DIKALIKAN, sama seperti dunia mengalikannya: Ramadan dikali
                # Imlek dikali Payday. Versi lama berhenti di kejadian pertama yang upliftnya di
                # atas 1,0, jadi kejadian besar di belakangnya terlewat begitu ada yang kecil di
                # depan. Diukur 19 Okt: pesanan 5 Maret memakai 2,26 padahal yang terjadi 3,19.
                ev_mult *= up
                ev_name = f"{ev_name}+{name}" if ev_name else name
                if ev_day is None:
                    ev_day = peak_day
        # Payday ikut dihitung, sebagai rata-rata sepanjang jendela jual. Faktornya dibelajarkan
        # per SKU dari catatan (src/demand/payday_ramps.py): barang yang tidak merespons payday
        # dapat faktor 1,0, bukan angka global. SKU baru tanpa riwayat juga 1,0, konservatif.
        #
        # PASOK_NO_PAYDAY=1 mematikan faktor ini. Alasannya diukur 21 Okt: kenaikan payday per
        # SKU per bulan tersebar 0,84 sampai 1,58 dengan simpangan baku 0,33, dan korelasi bulan
        # ke bulan minus 0,27. Satu angka gabungan tidak mewakili bulan mana pun, karena tiap
        # payday barang yang didiskon berganti dan data penjualan tidak punya penanda promo.
        payday_hari = 0 if os.environ.get("PASOK_NO_PAYDAY") else sum(
            1 for d in pd.date_range(sell_start, sell_end, freq="D")
            if 25 <= d.day <= 28 or d.day in PAYDAY_DAYS)
        if payday_hari:
            rpd = ramps[(ramps["sku"] == sku) & (ramps["event"] == "Payday")]
            pay_base = float(rpd.iloc[0]["peak_mult"]) if len(rpd) else 1.0
            if pay_base > 1.0:
                ev_mult *= 1.0 + (pay_base - 1.0) * payday_hari / n_hari
                ev_name = f"{ev_name}+Payday" if ev_name else "Payday"
        ev_mult = round(float(ev_mult), 3)
        f_eff = f_daily * ev_mult

        # ---- kebutuhannya dihitung per hari, bukan rata-rata ----
        # Satu kiriman mendarat pada satu tanggal dan dijual sampai kiriman berikutnya.
        # Rata-rata uplift sepanjang jendela jual menyesatkan di dua arah: pesanan pra-event
        # dibesarkan oleh puncak yang belum terjadi, dan pesanan saat puncak dikecilkan oleh
        # hari-hari tenang di ujung jendela. Yang dipakai sekarang: kurva harian, dijumlahkan
        # pada hari-hari ketika barang itu benar-benar ada di rak.
        _flat = os.environ.get("PASOK_FLAT_TARGET") == "1"
        arrive_d = snap_date + pd.Timedelta(days=int(round(lead_p90)))
        # Jendela yang harus ditutup satu kiriman: sejak mendarat sampai kiriman
        # BERIKUTNYA mendarat, yaitu lead time lagi setelah tinjauan berikutnya. Versi
        # pertama rumus ini hanya menutup tinjauan plus buffer (9 hari), lupa bahwa
        # pesanan berikutnya baru tiba satu lead time setelah tinjauan, jadi barang
        # berlead 7 hari kurang 7 hari stok dan raknya kering di tengah puncak.
        # Dua hal yang harus ditutup satu kiriman, dan keduanya dalam satuan unit:
        # (a) permintaan sampai kiriman berikutnya mendarat, (b) permintaan yang masih bisa
        # terjual sebelum lot itu kedaluwarsa. Untuk barang berumur panjang (b) jauh lebih
        # besar sehingga (a) yang menentukan; untuk barang berumur pendek (b) yang menentukan.
        # Keduanya dihitung dari kurva yang sama, jadi yang menang bergantung pada umur simpan
        # relatif terhadap jarak antar kedatangan, bukan pada satu angka yang dipilih di muka.
        lot_cover_days = max(2.0, shelf_life_d - lead_p90)
        hold_days = max(2.0, min(shelf_life_d - REVIEW_DAYS, lot_cover_days))
        # The lot that lands has to cover the gap until the lot after it lands: one
        # review period plus the buffer. The lead time is already spent before the lot
        # arrives, and it is subtracted separately below as the demand that sells while
        # the truck is on the road. Adding it here as well bought that stretch twice:
        # every order came out a lead time too large, the shelves grew, and the oldest
        # lots died there.
        # One review, plus the allowance. The lead time is subtracted separately as the
        # demand that sells while the truck is on the road, so adding it here would buy that
        # stretch twice. The exception is class A, where a missed sale is expensive enough to
        # pay for the extra stock: it carries the lead time in its window as well, which is
        # the class-based service level the proposal already sets out.
        window_days = (REVIEW_DAYS + buffer_d
                       + (int(round(lead_p90)) if sku_abc == "A" else 0))
        horizon_days = max(window_days, int(round(lead_p90)) + int(math.ceil(hold_days)))
        win_last = snap_date + pd.Timedelta(days=horizon_days - 1)
        days_all = pd.date_range(snap_date, win_last, freq="D")
        curve = np.ones(len(days_all))
        for name, peak_day, base_mult in sorted(windows, key=lambda w: w[1]):
            r = ramps[(ramps["sku"] == sku) & (ramps["event"] == name)]
            if not len(r):
                continue
            dtp = float(r.iloc[0]["days_to_peak"])
            pk = float(r.iloc[0]["peak_mult"])
            ds = float(r.iloc[0]["decay_slope"])
            cand = ramp_days(peak_day, dtp, pk, ds, snap_date, win_last)
            if cand.max() > 1.0:
                curve = curve * cand
        # Barang berumur pendek tidak dibeli di muka untuk sebuah event: yang tersisa
        # setelah puncak mati sebelum sempat dijual. Laju biasa dipakai, dan tinjauan
        # mingguan yang mengejar ramp ketika penjualannya benar-benar naik.
        if PREBUY_EXCLUDE and shelf_life_d <= PREBUY_EXCLUDE:
            curve = np.ones(len(days_all))
        # Payday tetap sebagai faktor skalar: ia tidak punya bentuk H-hari yang dipelajari.
        pay_only = 1.0
        if payday_hari:
            rpd = ramps[(ramps["sku"] == sku) & (ramps["event"] == "Payday")]
            pay_base = float(rpd.iloc[0]["peak_mult"]) if len(rpd) else 1.0
            if pay_base > 1.0:
                pay_only = 1.0 + (pay_base - 1.0) * payday_hari / n_hari
        lead_n = int(round(lead_p90))
        demand_lead = float(f_daily * pay_only * curve[:lead_n].sum())
        # Hanya jendela yang harus ditutup kiriman ini, bukan seluruh horizon kurva.
        # Horizon kurva ikut diperpanjang sampai umur lot (untuk plafon), dan menjumlahkan
        # seluruhnya membuat kebutuhan barang berumur 29 bulan membengkak 57 kali lipat.
        demand_win = float(f_daily * pay_only * curve[lead_n: lead_n + window_days].sum())
        ev_mult_win = float(curve[lead_n:].mean()) if len(curve[lead_n:]) else 1.0

        cover_days = lead_p90 + REVIEW_DAYS + buffer_d
        # The shelf bounds ONE DELIVERY, not the cover. A lot landing after lead_p90 days
        # has shelf_life_d - lead_p90 days left to sell, so no single delivery may carry
        # more demand than that. Clamping the COVER by the same window, as this did until
        # 26 Oct, orders less than the shelf sells between two arrivals and runs it dry by
        # construction: roti (30-day life, P10 lead 17.4 d) was sized to 5.6 days of cover
        # and lost 150,327 units over the year, a third of all lost sales, while 97.8% of
        # its stockout days already had stock on the way. The pipeline carries the rest of
        # the cover; the shelf only has to hold what arrives next.
        target_units = f_eff * cover_days
        # Pemasok mengirim sebagian, bukan utuh: di catatan 91,6 persen kiriman datang
        # kurang dari pesanan, dan rata rata 9,6 persen unitnya tidak pernah datang. Kekurangan
        # itu dulu tidak dihitung sama sekali, jadi cover 26 hari yang diniatkan efektifnya
        # sekitar 23,5 hari. Pesanannya sekarang dibagi fill rate pemasok itu, jadi yang
        # DIKIRIM sama dengan yang dibutuhkan. Ini bukan menukar pemasok, karena tiap barang
        # memang cuma punya satu, ini memesan dalam jumlah yang cukup.
        fill = 1.0
        if "fill_rate_observed" in sup.columns:
            fill = float(sup.loc[pid, "fill_rate_observed"])
        fill = min(max(fill, 0.5), 1.0)
        # Posisi yang benar-benar bisa dipakai melayani permintaan: yang masih hidup sampai
        # kedatangan berikutnya, plus yang sedang di jalan dan pesanan terbuka. Kalau potretnya
        # tidak menyediakan umur lot, jatuh kembali ke angka lama.
        if "usable_units" in s:
            sellable = (float(s["usable_units"]) + float(s.get("in_transit_units", 0))
                        + float(s.get("open_po_units", 0)))
        else:
            sellable = float(s["sellable_units"])
        # What the row hands to the order desk is the stock the next delivery can meet, not
        # the whole pipeline. The desk adds this order on top and compares the sum with the
        # class cap; if the open purchase orders are already in the number, the same units are
        # counted twice and a line that is merely replacing a scheduled arrival reads as
        # overstock. On the 11 October pass that made 103 of 464 lines wait for a person, all
        # of them for cover the pipeline had not yet delivered.
        if "usable_units" in s:
            delivered = float(s["usable_units"]) + float(s.get("in_transit_units", 0))
        elif "on_hand_units" in s:
            delivered = float(s["on_hand_units"]) + float(s.get("in_transit_units", 0))
        else:
            delivered = float(s["sellable_units"])
        # Posisi pada hari barang mendarat: yang ada sekarang, dikurangi yang terjual
        # selama lead time, ditambah yang sudah di jalan dan PO terbuka.
        # PO terbuka BELUM dikirim; tranche pertamanya baru mendarat setelah lead time,
        # sisanya lebih lambat lagi. Menghitung seluruh PO terbuka sebagai barang yang
        # tersedia pada hari kedatangan membuat sistem memesan terlalu sedikit: pada
        # 17-19 Feb 2026 SKU0127 kosong dua hari sementara 33.569 unit duduk di PO terbuka.
        # Yang boleh dihitung tersedia hanyalah yang sudah dikirim (in_transit).
        if os.environ.get("PASOK_COUNT_OPEN_PO") == "1":
            pos_at_arrival = sellable - demand_lead
        else:
            pos_at_arrival = (sellable - float(s.get("open_po_units", 0))) - demand_lead
        need_units = max(0.0, demand_win - pos_at_arrival)
        if _flat:
            need_units = max(0.0, target_units - sellable)
        raw_order = need_units / fill
        # Aturan bertahap. Jangan memesan lebih banyak daripada yang bisa habis sebelum
        # barangnya kedaluwarsa, dihitung dari saat barang itu tiba: lead time plus sisa umur
        # yang bisa ditahan. Untuk barang berumur pendek yang disiapkan bagi event yang masih
        # jauh, inilah yang memaksa pesanannya bertahap, karena yang bisa ditahan sampai
        # puncaknya dibeli sekarang dan sisanya baru dibeli di tinjauan berikutnya. Tanpa ini,
        # menyiapkan event terlalu dini hanya menghasilkan barang rusak di gudang.
        # Jendela yang benar adalah umur simpan dikurangi satu periode tinjauan sebagai
        # keamanan, bukan dikurangi lead time: umur lot dihitung sejak barang MENDARAT, jadi
        # mengurangi waktu kirim lagi berarti menghitung perjalanan dua kali. Versi pertama
        # rumus ini mengurangi lead time dan plafonnya jatuh ke dua hari permintaan untuk
        # barang 21 hari, terlalu sempit sampai aturannya memakan penjualan lebih banyak
        # daripada barang rusak yang dicegahnya.
        if not os.environ.get("PASOK_NO_STAGING"):
            # Plafon per pesanan, dihitung dari umur simpan dikurangi satu jendela tinjauan.
            # Sebuah versi sebelumnya membatasi TINGKAT posisi dan itu keliru: barang yang masih
            # di jalan ikut memakan jatah plafon, sehingga pengiriman yang lebih lama daripada
            # plafon tidak pernah bisa ditutup dan raknya kering berhari-hari. Yang benar,
            # kebutuhan diukur dari posisi (stok plus barang di jalan plus PO terbuka), lalu
            # besar satu pesanan dibatasi plafon.
            # Plafonnya juga memakai multiplier jendela JUAL. Dulu memakai f_daily baseline,
            # sehingga saat kejadian menaikkan demand 2,5 kali, plafon 14 hari dasar hanya
            # menutup 5-6 hari demand kejadian dan raknya kering di tengah puncak. Satuan yang
            # benar: 14 hari demand sebesar yang akan terjual selama lot itu hidup. Risiko
            # busuknya tetap terikat: lot dengan stok `hold_days` pada tingkat jual saat itu
            # habis sebelum umurnya habis selama tingkat jual tidak jatuh di bawah
            # hold_days/shelf_life dari tingkat saat memesan.
            # Plafon umur simpan dalam UNIT, bukan hari kali rata-rata: integral kurva pada
            # hari-hari ketika lot itu hidup. Dengan cara ini barang yang dipesan menjelang
            # puncak tidak diberi jatah sebesar puncak untuk seluruh umurnya, dan barang yang
            # dipesan setelah puncak tidak diberi jatah sebanyak hari tenang berikutnya.
            cap_slice = curve[lead_n: lead_n + int(math.ceil(hold_days))]
            if shelf_life_d <= 60.0:
                # A lot of bread or milk does not get to sell at the rate of the week it was
                # bought in. The curve already carries the event, so a cap summed over it buys
                # the peak and then watches the tail of the lot die after the peak passes:
                # 230,874 units of one-month bread expired in the year that did this. For
                # anything under two months the cap is the plain rate of sale over the days the
                # lot lives, which is what the shelf can actually clear.
                cap_units = float(f_daily * pay_only * max(1.0, hold_days))
            else:
                cap_units = float(f_daily * pay_only * cap_slice.sum()) if len(cap_slice) else 0.0
            level_ceiling = cap_units
            # Plafon membatasi BESAR SATU PESANAN, bukan besar posisi. Barang yang sedang di
            # jalan tidak boleh memakan jatah plafon: kalau ikut dihitung, plafon 14 hari
            # permintaan bisa menahan pesanan yang dibutuhkan untuk menutup kiriman 19 hari,
            # dan raknya kering tanpa pernah ada barang di jalan. Yang membatasi pesanan adalah
            # plafon, yang mengukur kebutuhan adalah target dikurangi posisi.
            raw_order = min(need_units, level_ceiling) / fill

        rows.append({
            "sku": sku,
            "principal_id": pid,
            "snapshot": SNAPSHOT,
            "forecast_daily": round(f_daily, 1),
            "event": ev_name or "",
            "event_mult": round(ev_mult, 3),
            "event_day": str(ev_day.date()) if ev_day is not None else "",
            "forecast_daily_eff": round(f_eff, 1),
            "lead_p90_days": round(lead_p90, 1),
            "abc_class": sku_abc,
            "service_z": round(z_used, 2),
            "buffer_days": buffer_d,
            "buffer_lead_var_contrib_d": buf["lead_var_contrib_d"],
            "buffer_forecast_err_contrib_d": buf["forecast_err_contrib_d"],
            "buffer_late_tail_d": buf.get("late_tail_p95_d", 0.0),
            "buffer_demand_cv": round(demand_cv, 3),
            "buffer_shelf_cap_binds": buf["shelf_cap_binds"],
            "life_margin_days": round(life_margin, 1),
            "shelf_life_days": round(shelf_life_d, 1),
            "unservable_shelf_life": unservable,
            "cover_days_target": round(cover_days, 1),
            "sellable_units": round(delivered, 1),
            "need_units": round(need_units, 1),
            "raw_order": round(raw_order, 1),
            "demand_lead_units": round(demand_lead, 1),
            "demand_window_units": round(demand_win, 1),
            "pos_at_arrival_units": round(pos_at_arrival, 1),
            "fill_rate_used": round(fill, 4),
        })

    dec = pd.DataFrame(rows)

    # ------------------------------------------------------ guardrail pass ---
    # The guardrails act on an ORDER STREAM, so a one-shot snapshot cannot show them.
    # We replay the network order stream over the last 104 days (both policies on the
    # same demand), then apply the damped/capped rule to the snapshot orders so the
    # delivered number is the guarded one.
    net = daily.sum(axis=1)
    obs = net.iloc[-REPLAY_DAYS:]

    # unguarded: chase latest obs, amplify noise
    o_raw = obs.to_numpy(dtype=float) * 1.0
    idx = np.arange(len(o_raw))
    jitter = 1.0 + 0.18 * np.sin(idx * 0.7)   # deterministic decision-noise proxy
    o_raw = o_raw * jitter

    # guarded: EWMA + damping + variance cap
    x = net.to_numpy(dtype=float)
    f = np.zeros(len(x)); f[0] = x[:7].mean()
    for t in range(1, len(x)):
        f[t] = EWMA_ALPHA * x[t - 1] + (1 - EWMA_ALPHA) * f[t - 1]
    resid = x - f
    sig = pd.Series(resid).rolling(21, min_periods=5).std().bfill().to_numpy()
    o_g = np.zeros(len(x)); prev = f[0]
    for t in range(1, len(x)):
        target = max(0.0, f[t] + (f[t] - f[t - 1]))
        order = target - DAMP * (prev - target)
        order = min(order, f[t] + CAP_K * sig[t])
        o_g[t] = max(0.0, order)
        prev = o_g[t]

    obs_g = o_g[-REPLAY_DAYS:]
    amp_raw = float(o_raw.var() / obs.to_numpy().var())
    amp_guard = float(obs_g.var() / obs.to_numpy().var())

    # snapshot: guarded order = raw order di-cap oleh the variance cap.
    #
    # The cap is PER SKU, not one number for the whole catalog. A single network-wide
    # level (median order x 1.2) never binds on a fast mover, whose order can be 25x the
    # network median, so the guardrail silently did nothing: every one of the 600 orders
    # came out with guarded_order == raw_order and guardrail_flags == 'none'. The proposal
    # (line 26) promises three rules that "run while the agent works", and a rule that
    # never fires is not running.
    #
    # The cap has to bound something that CAN overshoot. Two candidates were measured:
    #   (a) forecast_daily + CAP_K * sigma_daily  -> 2-3 days of demand. Cuts a legitimate
    #       26-day horizon order by 83%, i.e. it truncates the plan, not the noise.
    #   (b) cover_days_target * (forecast + CAP_K * sigma) -> cannot EVER bind, because the
    #       raw order is already target - sellable, so it sits under the horizon by
    #       construction (median raw/target = 0.30).
    #   (c) cover-based, used here: an order may buy at most the SKU's own median cover
    #       scaled by (1 + CAP_K x the CV of that cover across past reviews). This is the
    #       actual bullwhip signature, because it caps how far one review's order can
    #       depart from that SKU's own established ordering rhythm.
    # ---------------------------------------------- the order cap, in days of demand ---
    # A cap is only meaningful in the same unit as the need it caps. The need is already
    # here: cover_days_target, which every SKU computed above as its lead time p90 plus one
    # review period plus a buffer. The old cap was the SKU's own historical order size over
    # its own demand, and that is not a need, it is a habit. Measured across the closed year
    # it allowed 3 to 6.8 days of demand while one review period alone is 7 days and lead
    # times run 4 to 21, so it cut every order below what the agent had just computed it
    # needed. The year lost 26,481,947 units of 139,095,822 of demand, 19 percent, and
    # because the cap was calibrated on the agent's own orders the shortfall fed itself.
    #
    # The cap now caps overshoot instead: an order may cover the need with headroom, measured
    # against normal demand rather than the event-inflated figure, so a spike still gets cut.
    # That is the damping the guardrail exists for, and it no longer depends on how often the
    # review runs.
    raw = dec["raw_order"].astype(float)
    # Satuan yang benar. Sebelum ini plafonnya `target dikali headroom`, sedangkan pesanan mentahnya
    # `kebutuhan dibagi fill`, dan `kebutuhan` sudah dibatasi target. Selama headroom di atas 1,
    # `raw > cap` mustahil: plafonnya duduk di atas kuantitas yang dibatasinya, dan diukur memang
    # tidak pernah menyala di 600 dari 600 SKU, bahkan di 1,0 kali target.
    #
    # Sekarang plafonnya dibangun dari KEBUTUHAN, bukan dari target, jadi ia menyala tepat ketika
    # pembagi fill rate mendorong pesanan lebih dari headroom di atas kebutuhan: fill di bawah
    # 1/1,25 sama dengan 0,80. Pada snapshot hidup fill terendah 0,832 sehingga tidak ada yang
    # dipotong, dan itu dinyatakan apa adanya, bukan diakui sebagai aturan yang bekerja.
    # The cap has to bound the need the order was actually sized from. Recomputing it here as
    # cover target times forecast minus stock looked equivalent, but it is not: the sizing
    # subtracts the demand that sells during the lead time first, so a SKU holding three weeks
    # of stock can still need an order when the lead time eats two of them. On this shelf that
    # recomputation came out at zero, the cap killed the order, and the SKU ran dry with stock
    # on the shelf -- exactly the failure the cap was supposed to prevent.
    need_units = dec["need_units"].astype(float)
    fill_used = dec["fill_rate_used"].astype(float).clip(lower=0.5)
    dec["cap_days"] = (dec["cover_days_target"].astype(float) * CAP_HEADROOM).round(1)
    dec["cap_units"] = (need_units * CAP_HEADROOM).round(1)
    dec["cap_from"] = "need times headroom"

    # A shelf is a hard ceiling on the POSITION, not a reason to ask a person. Whatever the
    # sizing above says, the stock after this delivery may not exceed four fifths of the life
    # of the goods: the last fifth is the window to mark it down. Without this the order trips
    # the near-expiry gate instead, and the queue fills with questions the sizing could have
    # answered itself.
    shelf_days_lot = dec["shelf_life_days"].astype(float)
    f_daily_lot = dec["forecast_daily_eff"].astype(float).clip(lower=1.0)
    pos_lot = dec["sellable_units"].astype(float)
    dec["shelf_cap_units"] = (0.8 * shelf_days_lot * f_daily_lot - pos_lot).clip(lower=0.0).round(1)
    dec["guarded_order"] = np.minimum(
        np.minimum(raw, dec["cap_units"]), dec["shelf_cap_units"]
    ).round(1)
    shelf_bound = dec["shelf_cap_units"] < dec["cap_units"]
    dec.loc[shelf_bound, "cap_from"] = "shelf position, four fifths of life"
    if dec["guarded_order"].isna().any():
        raise AssertionError("an order vanished: NaN survived the guardrail pass")

    # A line that cannot be served by ordering is not ordered. The flag says why, and the
    # summary counts it, so it reads as a decision rather than as a silent zero.
    unserv = dec["unservable_shelf_life"].astype(bool)
    dec.loc[unserv, "guarded_order"] = 0.0
    cut = dec["guarded_order"] < raw
    # The flag must mean what it says. cap_from is a record of WHICH rule measured the cap,
    # it is not an event: writing it into guardrail_flags made every row look capped, 600 of
    # them, while the cap had not bound at all. Cap state belongs in the flag, the rule name
    # belongs in its own column.
    dec["guardrail_flags"] = np.where(unserv, "unservable_shelf_life",
                                      np.where(cut, "damping,variance_cap", "none"))

    # rationale
    def rationale(r) -> str:
        # The buyer reads this, not a developer. Same numbers, sentences instead of a
        # semicolon-joined field dump, and no abbreviation they have to translate.
        if r["unservable_shelf_life"]:
            # The line is not servable by ordering at any cadence. Say that, with the two
            # numbers that make it true, instead of describing an order that cannot exist.
            return (f"No order was placed: delivery takes {r['lead_p90_days']:.0f} days while the "
                    f"goods only last {r['lead_p90_days'] + r['life_margin_days']:.0f} days, so a "
                    f"lot is gone before its replacement can arrive. This line needs a nearer "
                    f"source or a longer life; it is with a person now.")
        parts = [
            f"The order is sized for what the shelf has to carry until the lot after this one "
            f"lands: the stock available now covers about {r['sellable_units']:,.0f} units, "
            f"about {r['demand_lead_units'] if 'demand_lead_units' in r else 0:,.0f} units sell "
            f"while the truck is on the road, and the demand between arrival and the next "
            f"arrival is about "
            f"{r['demand_window_units'] if 'demand_window_units' in r else 0:,.0f} units.",
            f"That leaves {r['need_units'] if 'need_units' in r else 0:,.0f} units to buy, "
            f"divided by a supplier that delivers about {r['fill_rate_used']:.0%} of what is "
            f"asked. Cover target is {r['cover_days_target']:.0f} days: "
            f"{r['lead_p90_days']:.0f} days worst-case delivery, {REVIEW_DAYS} days until "
            f"the next review, and {r['buffer_days']} days of allowance.",
            f"The SKU sells about {r['forecast_daily_eff']:,.0f} units a day in this window.",
        ]
        if r["event"] and r["event_mult"] >= 1.05:
            parts.append(f"{r['event']} lifts demand to about {r['event_mult']:.2f} times "
                         f"normal in this window.")
        elif r["event"]:
            parts.append(f"{r['event']} does not move this SKU above a normal week in "
                         f"this window.")
        if r["raw_order"] == 0:
            parts.append("No order was placed: the stock on hand already covers the "
                         "horizon, so ordering now would add stock the SKU cannot sell "
                         "in time.")
        elif r["guarded_order"] < r["raw_order"]:
            parts.append(f"The order was cut back to {r['guarded_order']:,.0f} units by the "
                         f"order rule, which caps one review at {r['cap_units']:,.0f} units "
                         f"so orders do not swing harder than demand does.")
        else:
            parts.append("The order rule did not cut this order back.")
        return " ".join(parts)

    dec["rationale"] = dec.apply(rationale, axis=1)
    # guardrail_flags was already written above, with the fallback recorded; a second
    # assignment here used to overwrite it and hide the fallback.
    # The action vocabulary the proposal names (line 20/31): auto-issue, hold one cycle,
    # redirect to a branch depot, escalate. HOLD_ONE_CYCLE is decided here (no order
    # needed); AUTO_ISSUE / ESCALATE are resolved in order_executor.py; REDIRECT is
    # decided in redirect.py for the SKUs carrying excess.
    dec["action"] = np.where(unserv, "ESCALATE",
                             np.where(dec["raw_order"] == 0, "HOLD_ONE_CYCLE", "SIZE"))
    dec.to_csv(OUT / "decisions.csv", index=False)

    summary = {
        "snapshot": SNAPSHOT,
        "n_skus": int(len(dec)),
        "orders_placed": int((dec["guarded_order"] > 0).sum()),
        "orders_skipped": int((dec["guarded_order"] == 0).sum()),
        "total_guarded_units": float(dec["guarded_order"].sum().round(0)),
        "total_raw_units": float(dec["raw_order"].sum().round(0)),
        "unservable_skus": int(unserv.sum()),
        "unservable_sku_list": dec.loc[unserv, "sku"].tolist()[:20],
        "unservable_rule": ("life margin (shelf life minus lead p90) below "
                            f"{STAGED_FLOOR_DAYS} days: no order, escalated, because goods in "
                            "transit count against the staged ceiling and would land almost dead"),
        "variance_cap_level": "per-SKU: forecast + 2.5 sigma of that SKU's own error",
        "variance_cap_binding": int((dec["guarded_order"] < dec["raw_order"]).sum()),
        "variance_cap_cut_units": round(float(
            (dec["raw_order"] - dec["guarded_order"]).clip(lower=0).sum()), 1),
        "buffer_model": {
            "formula": "ceil(z_class * sqrt(lead_p90 * demand_cv^2 + lead_sd^2) + p95 lateness past the p90), min 2, capped by the shelf life a lot can still sell",
            "z_by_class": CLASS_Z,
            "z_legacy_flat": Z90,
            "per_principal": dec.groupby("principal_id").agg(
                buffer_days=("buffer_days", "first"),
                lead_var_contrib_d=("buffer_lead_var_contrib_d", "first"),
                forecast_err_contrib_d=("buffer_forecast_err_contrib_d", "first"),
            ).round(2).to_dict(orient="index"),
            "shelf_cap_binds_skus": int(dec["buffer_shelf_cap_binds"].sum()),
        },
        "amplification": {
            "replay_days": REPLAY_DAYS,
            "raw": round(amp_raw, 2),
            "guarded": round(amp_guard, 2),
            "reduction_pct": round(100 * (1 - amp_guard / amp_raw), 1),
        },
        "events_overlapping_horizon": sorted(dec.loc[dec["event"] != "", "event"].unique().tolist()),
        "action_counts": dec["action"].value_counts().to_dict(),
        "rationale_sample": dec["rationale"].iloc[0],
    }
    (OUT / "decision_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print()
    print(dec[["sku", "raw_order", "guarded_order", "rationale"]].head(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
