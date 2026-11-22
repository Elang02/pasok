"""Masukkan umur lot ke masukan loop harian.

Masalahnya: potret gudang yang dibaca agen cuma punya satu angka stok bisa dijual, tanpa umur
lot. Akibatnya agen terus memesan walau stok di gudang sudah dalam, barang baru mendarat,
mengantre di belakang lot tua karena penjualan memakan yang tertua dulu, lalu rusak sebelum
sempat terjual. Terukur pada uji umur 21 hari: 709.312 unit barang yang datang saat uji
berjalan rusak justru karena celah ini.

Yang ditambahkan, tiga hal dan tidak lebih:

1. `position()` di simulate.py sekarang menulis dua kolom baru dari lot bertanggal:
   `oldest_lot_age_days` (umur lot tertua) dan `usable_units` (stok yang masih akan hidup
   sampai kedatangan berikutnya, yaitu lot yang sisa umurnya masih menutup lead time).
2. `sellable_units` TIDAK diubah, karena namanya sudah benar dan konsol membacanya. Agen
   keputusan yang memilih memakai `usable_units` kalau kolomnya ada, ditambah barang dalam
   perjalanan dan pesanan terbuka.
3. Dua nama kolom baru didaftarkan di daftar kolom keluaran supaya tidak terbuang saat potret
   ditulis.

Kalau ada satu titik pun yang tidak ketemu, skrip berhenti tanpa menulis apa pun.

Jalan: python3 tools/lot_age_into_loop.py
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SIM = ROOT / "tools" / "simulate.py"
DEC = ROOT / "src" / "agents" / "decision.py"

LOT_FIELDS = '''    # Umur lot masuk sebagai masukan loop, bukan perbaikan terpisah. Stok yang sisa umurnya
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
    else:
        pos["oldest_lot_age_days"] = 0
        pos["usable_units"] = pos["on_hand_units"]
'''


def main() -> int:
    sim, dec = SIM.read_text(), DEC.read_text()

    anchor = '    pos["snapshot"] = str(day.date())\n'
    if anchor not in sim:
        print("BERHENTI: titik sisip di position() tidak ketemu"); return 1
    sim = sim.replace(anchor, LOT_FIELDS + anchor, 1)

    m = re.search(r'COLUMNS\s*=\s*\[(.*?)\]', sim, re.S)
    if not m:
        print("BERHENTI: daftar COLUMNS tidak ketemu"); return 1
    if "usable_units" not in m.group(1):
        sim = sim.replace(m.group(0), 'COLUMNS = [' + m.group(1).rstrip().rstrip(",") +
                          ', "oldest_lot_age_days", "usable_units",]', 1)

    old = '        sellable = float(s["sellable_units"])'
    if old not in dec:
        print("BERHENTI: baris sellable di decision.py tidak ketemu"); return 1
    dec = dec.replace(old, '''        # Stok yang bisa dipakai melayani permintaan hari ini adalah yang masih akan hidup
        # sampai kedatangan berikutnya, ditambah barang dalam perjalanan dan pesanan terbuka.
        # Kalau potretnya tidak menyediakan umur lot, jatuh kembali ke angka lama.
        if "usable_units" in s:
            sellable = (float(s["usable_units"]) + float(s.get("in_transit_units", 0))
                        + float(s.get("open_po_units", 0)))
        else:
            sellable = float(s["sellable_units"])''', 1)

    SIM.write_text(sim)
    DEC.write_text(dec)
    print("ditulis ke", SIM.name, "dan", DEC.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
