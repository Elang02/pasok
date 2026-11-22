
## 9. Uji luar kasus: barang 21 hari dengan lead time 15 hari

Aturan konsumsi bertahap `staged-consumption` hanya untuk barang umur simpan
pendek, dan tesnya menembus aturan itu sendiri. Pada katalog normal aturan ini
tidak pernah mengikat (0 dari 600 keputusan menyentuh plafon) dan tidak
mengubah satu angka pun di sembilan halaman. Maka katalog masa pakai
sebenarnya diuji di luar kasusnya, dan skenario khusus dibuat untuk
mengujinya: 140 SKU, umur simpan 21 hari, lead time P90 15 hari,
kebijakan tinjauan tetap tujuh hari.

Hasilnya jujur dan bukan keunggulan, tiga kebijakan dihitung dari populasi
yang sama (90 hari simulasi):

| Kebijakan | Hilang terjual | Kedaluwarsa |
|---|---|---|
| Tanpa aturan | 5,65 persen | 203.224 unit |
| Aturan versi pertama (plafon = umur simpan - lead - tinjauan) | 9,85 persen | 79.332 unit |
| Aturan versi benar (plafon = umur simpan - lead) | 8,04 persen | 118.755 unit |

Yang pertama kali ditulis rumusnya memotong tinjauan dua kali dan plafonnya
tinggal dua hari permintaan; untuk barang 21 hari dengan lead 15 hari
aturannya memakan penjualan lebih banyak daripada barang rusak yang
dicegahnya (9,85 persen berbanding 5,65 persen). Sesudah diperbaiki
menjadi umur simpan dikurangi lead saja, sisanya tetap: aturan bertahap
memangkas barang kedaluwarsa 42 persen tetapi menambah kehilangan
penjualan 2,39 poin. Itu pertukaran, bukan kemenangan.

Kesimpulan yang dipakai di demo: pada lead time 15 hari tidak ada tinjauan
mingguan yang sehat untuk barang 21 hari, karena barang mendarat hanya
bermasa enam hari. Batasnya adalah irama, bukan plafonnya. Jawaban yang
benar adalah meninjau barang pendek lebih sering dari sekali seminggu,
bukan memperketat plafon lagi. Angka di halaman konsole tetap katalog
biasa; skenario ini disimpan di `data/sim/scen_*` sebagai bahan
pertanyaan juri, bukan angka klaim.


## Plafon konsumsi bertahap tidak mengikat di katalog normal

Diukur: 0 dari 600 keputusan menyentuh plafon pada katalog penuh, karena umur simpan terpendek
yang benar-benar dipakai (21 sampai 45 hari) selalu di atas lead time ditambah periode tinjauan.
Artinya aturan ini adalah jaring pengaman untuk katalog umur pendek, bukan pengungkit angka di
katalog sekarang, dan itu harus dikatakan begitu di demo, bukan diklaim sebagai sumber
perbaikan. Ketika diuji di skenario umur 21 hari, aturannya benar-benar bekerja dan hasilnya
pertukaran yang jujur: barang rusak turun 42 persen, penjualan hilang naik 2,4 poin.
