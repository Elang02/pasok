# Perbaikan deck dan konsol, catatan pemulihan ringkas

Ditulis 29 Okt 2026 karena dua ringkasan kompresi terpotong (b139, b140). Fakta di bawah
adalah yang hilang dari ringkasan itu, dan semuanya bisa diverifikasi di repo.

## Halaman 12, "Where the numbers come from"
Tiga kolom: generated (600 SKU, 120 outlet, 1.396 hari, 10 juta baris, seed 20261008),
real (harga PIHPS Okt 2026, kalender event, tanggal THR = Lebaran minus 7 hari), dan
asumsi (amplitudo uplift per kategori dari GAPMMI/Antara/NielsenIQ, 33 event lampau,
bentuk H-hari dari Wikipedia pageviews + Google Trends). Dua kolom pertama berlabel
"generated"/"real" supaya juri tahu mana yang sintetis.

## Pembaruan harness
dsh dinaikkan ke 0.2.1-rc.4 lewat `npm i -g @deepseek-ai/dsh@next`; 9 plugin profil web
kompatibel; layanan dsh-web di-restart dengan `systemd-run --user --on-active=20 ... systemctl --user restart dsh-web`.

## Bug yang ditutup
1. `peak_units` dibaca dengan `get(..., 0)` sehingga halaman 5 sempat menampilkan nol palsu.
2. `src/agents/decision.py:772` selalu menulis pengali event, jadi muncul "Christmas lifts
   demand to about 1.0 times normal"; sekarang <1,05 berbunyi "does not move this SKU above
   a normal week in this window" dan >=1,05 memakai dua desimal.
3. Konsol memeringkat mover menurut persentase sehingga contohnya barang bervolume 10 pcs;
   sekarang menurut unit di puncak (Kakao Sari Cokelat Batang 100 g 58 -> 79 memimpin).
   Ketiga belas mover Christmas semuanya `ramp_class=ramped`, terukur di 33 event lampau.
4. Halaman /order dan kolom kiri halaman 7 deck memakai istilah berbeda dari tangkapannya:
   "Order desk reference" -> "Ordering system reference", "within policy limits" ->
   "inside policy limits" (pemetaan di lapisan tampilan web/app.py dan build_deck.py,
   supaya data hasil rantai tidak perlu dijalankan ulang).

Commit terkait: ad87280 (mover dan rationale), ad67d4b (label dan tangkapan).
