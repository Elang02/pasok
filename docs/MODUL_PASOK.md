# Modul Belajar Pasok

## 1. Gambaran besar dalam satu menit

Pasok mengurus satu pekerjaan yang diulang terus oleh distributor: memutuskan barang apa yang harus dipesan, berapa banyak, dan kapan.

Pekerjaan itu dikerjakan dalam satu putaran lima langkah. Lihat posisi stok. Forecast penjualan. Putuskan order. Kirim ke sistem order. Nilai hasilnya setelah barang datang.

Putaran itu dijalankan sebelas program berurutan, dari menyiapkan kalender sampai menulis jejak satu SKU contoh. Semuanya berjalan tanpa akun cloud dan hasilnya bisa dibuat ulang dengan satu perintah.

**Angka kunci jalan terakhir**
- 600 SKU diperiksa.
- 139 baris order diputuskan.
- 121 baris keluar otomatis, 18 baris menunggu manusia.
- Nilai order otomatis Rp13.421.740.570. Nilai yang menunggu manusia Rp3.437.202.355. Totalnya Rp16.858.942.925.

**Kalau ditanya**
"Cara kerjanya seperti apa?" Jawab: satu putaran lima langkah, dijalankan sebelas program berurutan, dan hasilnya bisa dibuat ulang kapan saja.

**Daftar fitur**

1. Satu angka sellable.
2. Forecast penjualan dengan ramp per SKU.
3. Kalender event yang tanggalnya benar.
4. Menilai supplier dari kenyataan.
5. Menghitung jumlah order.
6. Guardrail order.
7. Memilih action dan menulis alasannya.
8. Exception queue dan notifikasi.
9. Mengirim ke sistem order.
10. Redirect stok berlebih ke cabang lain.
11. Learn, menilai keputusan sendiri.
12. Konsol tanya jawab.

Bacanya berurutan. Fitur 1 sampai 6 adalah satu rantai hitungan. Fitur 7 sampai 9 adalah keputusan dan pengirimannya. Fitur 10 sampai 12 adalah tindak lanjut dan cara memeriksanya.

![Peta dua belas fitur](assets/peta-modul.svg)

**Bagan 1. Peta dua belas fitur. Tiga kelompok kerja dan satu tempat bertanya. Angka di cabang adalah jumlah fitur di kelompok itu.**

---

## 2. Fitur 1: satu angka sellable

**Apa yang dilakukan.** Menghitung satu angka bernama sellable untuk tiap SKU, yaitu barang yang benar-benar bisa dijual hari ini.

**Masukan.** Catatan stok gudang, catatan barang yang sedang dikirim, dan open PO yang belum datang.

**Keluaran.** Angka sellable, days of cover, dan dua tanda bahaya yang berbeda.
- Tanda perlu order, kalau days of cover kurang dari lead time ditambah 7 hari kelonggaran.
- Tanda risiko kedaluwarsa, kalau days of cover melebihi umur simpan barang itu.

Dua tanda ini sering tertukar. Yang pertama soal barang habis. Yang kedua soal barang menumpuk terlalu lama. Di jalan terakhir, tanda pertama menyala di 65 SKU, tanda kedua nol dari 600 SKU.

**Contoh nyata dari jalan terakhir.** SKU0361 punya 4.707,6 unit di gudang, tidak ada barang di jalan, dan tidak ada open PO. Sellable-nya 4.707,6 unit. Velocity 703,18 unit per hari. Days of cover 6,7 hari, sedangkan lead time 7 hari ditambah 7 hari kelonggaran menjadi 14 hari. Karena itu SKU ini masuk daftar perlu order.

![Halaman Stock di konsol Pasok](shot/fig1_health.jpg)

**Gambar 1. Halaman Stock di konsol Pasok. Nilai stok, jumlah unit, dan days of stock left dibaca dari posisi stok, bukan diketik.**

**Kenapa fitur ini penting.** Banyak distributor hanya melihat stok gudang, lalu order lagi, padahal barangnya sudah dalam perjalanan. Dengan satu angka sellable, order ganda seperti itu tidak terjadi.

**Kalau ditanya**
"Bedanya dengan laporan stok biasa apa?" Jawab: laporan biasa memisahkan gudang, perjalanan, dan open PO. Di sini ketiganya dijumlahkan menjadi satu angka yang dipakai memutuskan.

**Uji diri**
1. Sellable terdiri atas apa saja?
2. SKU0361 punya days of cover berapa hari, dan ambangnya berapa?
3. Apa tanda bahaya yang keluar dari fitur ini?

Jawaban. Stok gudang, barang di jalan, dan open PO. Days of cover 6,7 hari, ambangnya 7 hari. Tanda perlu order dan tanda risiko kedaluwarsa.

---

## 3. Fitur 2: forecast penjualan dengan ramp per SKU

**Apa yang dilakukan.** Memperkirakan penjualan harian tiap SKU, lalu menyesuaikannya kalau ada event, dan menyertakan rentang ketidakpastian.

**Masukan.** Riwayat penjualan per SKU, kalender event Indonesia, dan kelas ramp yang sudah dipelajari.

**Keluaran.** Forecast dasar, forecast efektif setelah penyesuaian event, dan kelas ramp untuk tiap pasangan SKU dan event.

**Contoh nyata dari jalan terakhir.** SKU0361 masuk jendela payday. Forecast dasarnya 562 unit per hari. Pengali payday yang tercatat 1,015, jadi forecast efektifnya 570,4 unit per hari. Angka 1,015 itu bukan klaim lonjakan. Itu rata-rata sepanjang jendela jual 8 hari, dan hanya satu hari di antaranya tanggal gajian.

Pengali payday sekarang dimatikan dari perhitungan order. Alasannya ada di bagian 6.1. Riwayat tidak bisa menebak payday mana yang memuat SKU mana.

Kelas ramp yang dipelajari di seluruh katalog: 1.672 kombinasi masuk kelas step, yaitu naik sekali lalu turun. 1.328 kombinasi masuk kelas ramp, yaitu naik bertahap.

**Kenapa fitur ini penting.** Satu pola event untuk semua barang membuat forecast salah di dua arah. Barang biskuit naik tajam sebelum Lebaran, barang lain tidak naik sama sekali.

**Kalau ditanya**
"Forecast-nya pakai model bahasa?" Jawab: tidak. Forecast memakai metode statistik per SKU. Model bahasa hanya menulis alasan.
"Kenapa pengali payday cuma 1,015?" Jawab: karena itu rata-rata 8 hari jendela jual, dan hanya satu hari tanggal gajian. Pengali puncaknya 1,12 dari 39 bulan catatan, tetapi angka itu sekarang tidak dipakai untuk order.

**Uji diri**
1. Apa beda forecast dasar dan forecast efektif?
2. Berapa kombinasi yang masuk kelas ramp?
3. Kenapa satu pola untuk semua barang keliru?

Jawaban. Forecast efektif sudah dikali event multiplier. Jumlahnya 1.328. Karena bentuk kenaikan tiap barang berbeda.

---

## 4. Fitur 3: kalender event yang tanggalnya benar

**Apa yang dilakukan.** Menyediakan tanggal event resmi Indonesia untuk dipakai fitur forecast.

**Masukan.** Keputusan bersama tiga menteri untuk hari libur nasional, tanggal tahun baru lunar untuk Imlek, dan aturan tunjangan hari raya.

**Keluaran.** Daftar tanggal event per tahun, dipakai sebagai jendela perencanaan.

**Contoh nyata dari jalan terakhir.** Lebaran jatuh 9 April 2024, 30 Maret 2025, dan 20 Maret 2026. Tanggal bergerak, dan pergerakannya tidak boleh ditebak.

**Kenapa fitur ini penting.** Versi pertama sistem menghitung tanggal dengan rumus sederhana, dan hasilnya salah. Imlek 2024 dihitung 13 Februari, padahal tanggal sebenarnya 10 Februari. Ramadan 2025 meleset satu hari. Kalender yang salah membuat seluruh penyesuaian event ikut salah.

**Kalau ditanya**
"Kenapa tidak dihitung sendiri saja?" Jawab: karena pernah dicoba dan hasilnya meleset. Tanggal sekarang diambil dari sumber resmi.

**Uji diri**
1. Dari mana tanggal Lebaran diambil?
2. Apa akibat kalau tanggal event salah satu hari?

Jawaban. Dari keputusan bersama tiga menteri. Jendela perencanaan bergeser sehingga order datang sebelum atau sesudah puncak permintaan.

---

## 5. Fitur 4: menilai supplier dari kenyataan

**Apa yang dilakukan.** Mengukur lead time dan fill rate tiap supplier, lalu mendeteksi kalau ada drift.

**Masukan.** Catatan penerimaan barang, yaitu order dibandingkan barang yang benar-benar datang.

**Keluaran.** Lead time rata-rata, lead time p90, fill rate, dan tanda drift.

**Contoh nyata dari jalan terakhir.** Supplier P06 punya fill rate terendah, 83,2 persen. Lead time rata-ratanya 8,2 hari, dan kasus terburuknya 11 hari. Supplier yang paling sering terlambat justru P02: order lengkap dan tepat waktu hanya 61,1 persen, dengan rata-rata 21,5 hari dan kasus terburuk 25 hari.

![Halaman Suppliers di konsol Pasok](shot/fig2_suppliers.jpg)

**Gambar 2. Halaman Suppliers. Kolom delivery time dan delivers the order dihitung dari catatan penerimaan barang, dan baris yang kurang ditandai.**

**Kenapa fitur ini penting.** Janji di kontrak sering berbeda dari kenyataan. Sistem memakai angka kenyataan, jadi order untuk supplier yang sering kurang akan otomatis dibesarkan.

**Kalau ditanya**
"Kalau supplier membaik, angkanya ikut berubah?" Jawab: ya karena dihitung dari penerimaan terbaru, dan ada pendeteksian drift.

**Uji diri**
1. Dua angka apa yang dipakai menilai supplier?
2. Bagaimana angka itu memengaruhi jumlah order?

Jawaban. Lead time p90 dan fill rate. Order dibagi fill rate, jadi supplier yang sering kurang otomatis menerima order lebih besar.

---

## 6. Fitur 5: menghitung jumlah order

**Apa yang dilakukan.** Mengubah masukan tadi menjadi satu angka order.

**Masukan.** Lead time p90, review period, buffer, forecast efektif, sellable, dan fill rate supplier.

**Keluaran.** Order mentah, order setelah guardrail, dan alasan pemotongan kalau ada.

**Rumusnya tiga baris**
- Cover target sama dengan lead time p90, ditambah review period, ditambah buffer.
- Buffer mengikuti kelas barang. Kelas A memakai 1,645, kelas B 1,28, kelas C 0,84. Cap days of cover kelas A 45 hari, B 60 hari, C 90 hari.
- Order sama dengan cover target dikali forecast efektif, dikurangi sellable, lalu dibagi fill rate supplier.

**Contoh nyata dari jalan terakhir.** SKU0361. Lead time p90 7 hari, review period 7 hari, buffer 7 hari, jadi cover target 21 hari. Forecast efektif 570,4 unit per hari. Sellable 4.707,6 unit. Fill rate supplier 0,85.

Hitungannya: 21 kali 570,4 sama dengan 11.978,4. Dikurangi 4.707,6 sama dengan 7.270,8. Dibagi 0,85 sama dengan 8.554,9 unit. Order tercatat 8.554,6 unit, selisihnya pembulatan.

Kalau pengali payday dimatikan, angkanya menjadi 21 kali 562 sama dengan 11.802. Dikurangi 4.707,6 sama dengan 7.094,4. Dibagi 0,85 sama dengan 8.346,4 unit. Selisihnya 208 unit, atau 2,4 persen.

**Batas umur simpan.** Order juga dibatasi supaya barangnya habis sebelum kedaluwarsa. Plafonnya umur simpan dikurangi satu periode tinjauan 7 hari, dengan lantai 2 hari. Kalau order melewati plafon, sisanya tidak dipesan sekarang, melainkan menunggu tinjauan berikutnya. Untuk barang berumur pendek yang disiapkan bagi event jauh, inilah yang membuat pembeliannya bertahap. Tanpa aturan ini, menyiapkan event terlalu dini hanya menumpuk barang yang rusak sebelum laku.

Di jalan terakhir plafon ini tidak memotong satu baris pun karena umur simpan terpendek di katalog 180 hari. Aturannya tetap ada dan teruji di uji umur simpan 21 hari, dengan hasil susut turun dari 3,81 menjadi 2,68 persen.

**Kenapa dibagi fill rate.** Kalau supplier hanya mengirim 85 persen dari yang dipesan, memesan 100 unit berarti hanya 85 yang datang. Tanpa pembagian itu, order selalu kurang.

**Kalau ditanya**
"Siapa yang menghitung?" Jawab: rumus. Model bahasa tidak menyentuh angka order.

**Uji diri**
1. Untuk SKU0361, berapa cover target-nya?
2. Apa yang terjadi kalau fill rate supplier turun menjadi 0,7?
3. Kenapa buffer kelas A paling tebal?

Jawaban. Cover target 21 hari. Order membesar karena pembaginya mengecil. Karena barang kelas A menyumbang nilai penjualan terbesar, dan kehabisan barang itu paling mahal.

### 6.1 Payday: kenapa pengalinya dimatikan

Payday bukan event kalender. Tiap payday, barang yang didiskon berganti. Data penjualan tidak punya penanda promo, jadi sistem lama memakai satu angka gabungan per SKU dari 39 bulan.

Angka gabungan itu sudah diukur dan hasilnya tidak layak dipakai.
- Kenaikan payday per SKU per bulan tersebar dari 0,84 sampai 1,58.
- Simpangan baku dalam satu SKU 0,33.
- Seperempat bulan tidak ada kenaikan sama sekali, dan 34,3 persen bulan di bawah 1,05.
- Korelasi bulan ini dengan bulan depan minus 0,27. Bulan lalu bukan penunjuk bulan ini.

Karena itu pengali payday dimatikan dari perhitungan order. Ketidakpastiannya pindah ke buffer, diukur dari persentil 75 sampai 90 kenaikan payday SKU itu. Buffer tetap dibatasi cap days of cover dan shelf life.

Efeknya ke seluruh katalog: 116 dari 139 order membawa pengali payday, dan mematikannya memotong 55.465 unit dari 1.015.276 unit, yaitu 5,46 persen.

Syarat mengembalikannya ada satu. Jadwal promo harus datang sebelum payday, dan memuat SKU, kedalaman diskon, serta periodenya. Dengan daftar itu, kenaikan dihitung dari elastisitas per SKU, bukan dari riwayat.

Hasil replay 284 hari, 1 Januari sampai 11 Oktober 2026, memakai dua replay yang sama jendelanya. Dengan payday, permintaan hilang 806.996 unit atau 0,717 persen. Tanpa payday, 791.519 unit atau 0,703 persen. Nilai stok rata-rata bergerak dari Rp284,0 miliar menjadi Rp284,5 miliar, dan turns dari 6,41 menjadi 6,40. Jadi mematikan payday tidak menambah stok, dan barang yang hilang justru berkurang 15.477 unit.

Catatan jujur. Data penjualan di demo adalah data sintetis, jadi angka sebaran di atas adalah sifat dataset. Pola rotasi promonya tetap sama dengan dunia nyata, dan itulah yang membuat riwayat tidak bisa dipakai.

---

## 7. Fitur 6: guardrail order

**Apa yang dilakukan.** Menahan order supaya tidak bergoyang liar antar minggu.

**Masukan.** Forecast mingguan dan order sebelumnya.

**Keluaran.** Order yang sudah dihaluskan, beserta tanda guardrail mana yang aktif.

**Tiga guardrail yang dipakai**
- Forecast dihaluskan sebelum dipakai menghitung jumlah.
- Jumlah order ditarik sebagian ke arah order sebelumnya.
- Ada batas kenaikan per order.

Penting: kenaikan karena event tidak ditahan. Kalau Lebaran memang menaikkan permintaan, order boleh naik. Yang ditahan hanya goyangan yang bukan disebabkan permintaan.

**Contoh nyata dari jalan terakhir.** Di simulasi 250 hari memakai indeks penjualan ritel Bank Indonesia, order tanpa guardrail bergoyang 2,68 kali permintaan. Dengan guardrail, goyangan turun menjadi 0,24 kali. Fill rate turun sedikit, dari 98,93 menjadi 98,68 persen.

Angka 1,31 menjadi 0,36 itu berasal dari replay 104 hari di dalam sistem, bukan dari snapshot. Replay memutar ulang kebijakan pada data historis, dan di sana guardrail memang memotong.

**Di snapshot hidup, tidak satu pun dari tiga guardrail mengubah order.** Dari 600 baris, penanda guardrail tertulis none di semuanya, dan jumlah order sebelum serta sesudah guardrail sama persis. Cap variance memotong 0 unit. Penyebabnya dua. Fill rate terendah 0,832, sedangkan cap baru menyala di bawah 0,80. Dan snapshot ini adalah putaran pertama pada tanggal itu, jadi belum ada order sebelumnya untuk ditarik.

Kalimat yang benar untuk demo: guardrail bekerja di replay, dan pada snapshot ini tidak ada yang menyala.

![Agent panel di konsol Pasok](shot/fig3_panel.jpg)

**Gambar 3. Agent panel. Angka 1,31 kali tanpa guardrail dan 0,36 kali dengan guardrail tercetak di panel yang sama dengan jumlah order.**

**Kenapa fitur ini penting.** Amplification membuat supplier salah merencanakan produksi, dan biayanya kembali ke distributor dalam bentuk harga dan barang menumpuk.

**Kalau ditanya**
"Kenapa fill rate dikorbankan sedikit?" Jawab: karena amplification punya biaya yang muncul di tempat lain. Trade-off ini ditunjukkan, bukan disembunyikan.

**Uji diri**
1. Sebut tiga guardrail.
2. Kenapa kenaikan karena event dikecualikan?

Jawaban. Haluskan forecast, tarik ke order sebelumnya, batasi kenaikan. Karena itu permintaan sungguhan, bukan kepanikan stok.

---

## 8. Fitur 7: memilih action dan menulis alasannya

**Apa yang dilakukan.** Memilih satu dari empat action untuk tiap SKU, lalu menulis alasan dalam bahasa yang bisa dibaca buyer.

**Empat action**
- Order otomatis.
- Hold satu putaran karena stok yang ada sudah cukup.
- Redirect ke cabang lain yang stoknya berlebih.
- Escalate ke manusia.

**Contoh nyata dari jalan terakhir.** Untuk SKU0361, action-nya order otomatis. Alasannya ditulis seperti ini: order disusun untuk 21 hari stok, yaitu 7 hari pengiriman terburuk, 7 hari sampai review berikutnya, dan 7 hari kelonggaran untuk pergerakan lead time dan permintaan. SKU ini bisa menjual 4.708 unit, dan menjual sekitar 570 unit per hari. Guardrail tidak memotong order ini.

**Kenapa alasannya ditulis.** Buyer perlu tahu dasar keputusan sebelum menyetujui. Alasan juga menjadi jejak pemeriksaan kalau keputusan itu keliru.

**Kalau ditanya**
"Apakah alasannya dibuat model bahasa?" Jawab: ya, teksnya dibuat model bahasa, tetapi angkanya dari rumus. Teks yang salah tidak mengubah jumlah order.

**Uji diri**
1. Sebut empat action.
2. Apa isi alasan yang ditulis sistem?

Jawaban. Order otomatis, hold, redirect, escalate. Dasar hitungannya, ditambah keadaan stok dan velocity.

---

## 9. Fitur 8: exception queue dan notifikasi

**Apa yang dilakukan.** Memisahkan order yang boleh keluar sendiri dari order yang harus diputuskan orang.

**Masukan.** Credit limit per SKU, MOQ supplier, dan asumsi yang belum terbukti.

**Keluaran.** Dua daftar. Daftar keluar otomatis, dan daftar menunggu persetujuan, lengkap dengan alasan dan nilainya.

**Contoh nyata dari jalan terakhir.** 121 baris keluar otomatis dan supplier-nya diberi tahu, sedangkan 18 baris menunggu manusia dengan nilai Rp3.437.202.355. Rincian alasannya: 17 baris melewati credit limit, 1 baris butuh keputusan ganti supplier.

**Kenapa fitur ini penting.** Keputusan yang mengubah komitmen uang atau hubungan dagang tetap milik manusia. Sistem menyiapkan hitungan dan alasannya.

**Kalau ditanya**
"Exception queue kosong, berarti cuma slide?" Jawab dengan angka: di jalan terakhir ada 18 baris senilai Rp3,4 miliar. Kalau kosong, sebutkan sebabnya, misalnya tidak ada baris yang melewati batas hari itu.

**Uji diri**
1. Sebut dua alasan order masuk exception queue.
2. Berapa nilai yang menunggu manusia?

Jawaban. Dua alasannya melewati credit limit dan butuh ganti supplier. Nilainya Rp3.437.202.355.

---

## 10. Fitur 9: mengirim ke sistem order

**Apa yang dilakukan.** Mengirim order ke sistem order, menerima balasan, dan menyimpan nomor referensi.

**Masukan.** Daftar order yang sudah disetujui.

**Keluaran.** Nomor referensi dari sistem order, jumlah yang diterima, selisih, dan alasan selisih.

**Contoh nyata dari jalan terakhir.** 121 order dikirim, tidak ada yang ditolak. Semuanya diterima sebagian, 843.864 unit dari 845.242 unit, yaitu 99,8 persen. Selisih 1.377,8 unit terjadi karena pembulatan ke kelipatan pack. Contoh satu baris: order 27.693,2 unit diterima 27.672 unit karena dibulatkan ke kelipatan 24.

![Halaman Orders di konsol Pasok](shot/fig4_orders.jpg)

**Gambar 4. Halaman Orders. Run log mencatat setiap jalan, jumlah order, dan berapa yang menunggu manusia.**

**Kenapa fitur ini penting.** Order yang tidak tercatat di sistem order tidak dipercaya bisnis. Karena itu ada nomor referensi, promised delivery, dan tanda terima.

**Kalau ditanya**
"Kalau ERP-nya beda?" Jawab: penggantian cukup satu variabel lingkungan. Yang berbeda hanya cara mengirim, bukan isi pesannya.

**Uji diri**
1. Berapa persen order yang diterima sistem order?
2. Kenapa ada selisih jumlah?

Jawaban. Persentasenya 99,8. Karena pembulatan ke kelipatan pack supplier.

---

## 11. Fitur 10: redirect stok berlebih ke cabang lain

**Apa yang dilakukan.** Mencari SKU yang stoknya berlebih di satu gudang dan masih dibutuhkan di gudang lain.

**Masukan.** Posisi stok semua gudang dan cap days of cover per kelas.

**Keluaran.** Daftar usulan redirect antar gudang.

**Contoh nyata dari jalan terakhir.** 251 SKU dialihkan ke cabang lain, dengan nilai yang diselamatkan Rp7.652.757.323.

![Halaman Transfers di konsol Pasok](shot/fig5_transfers.jpg)

**Gambar 5. Halaman Transfers. Tiap baris adalah kota tujuan, jumlah move, nilai yang dipindahkan, dan pangsanya.**

**Kenapa fitur ini penting.** Membeli barang baru, padahal barang yang sama menumpuk di gudang lain adalah pemborosan paling mudah dihindari.

**Kalau ditanya**
"Kalau stoknya berlebih, kenapa tidak berhenti order saja?" Jawab: karena berhenti order di satu gudang tidak menolong gudang lain yang kekurangan. Redirect menyelesaikan keduanya.

**Uji diri**
1. Berapa SKU yang dialihkan?
2. Apa syarat SKU bisa dialihkan?

Jawaban. Jumlahnya 251 SKU. Stoknya melewati cap days of cover kelasnya, dan ada gudang lain yang membutuhkan.

---

## 12. Fitur 11: learn, menilai keputusan sendiri

**Apa yang dilakukan.** Setelah barang datang, membandingkan yang dipesan dengan yang diterima, lalu memberi score.

**Masukan.** Order, penerimaan barang, dan forecast.

**Keluaran.** Score per baris, fill rate yang diamati, selisih lead time, dan kurva WAPE per bulan.

**Contoh nyata dari jalan terakhir.** Dari 139 baris yang dinilai: 81 baris SUPPLY_SHORT, 29 baris ON_PLAN, 29 baris SUPPLY_AND_LEAD. Fill rate yang diamati 91,25 persen. WAPE median untuk SKU yang diputuskan 9,15 persen, sedangkan seluruh katalog 12,6 persen.

Kurva bulanan menunjukkan pola yang konsisten. Bulan dengan WAPE terbesar adalah bulan event. Bulan terburuk April 2024 dengan WAPE 78,05 persen, bulan terbaik Juni 2025 dengan 13,12 persen.

**Kenapa fitur ini penting.** Tanpa learn, sistem tidak pernah tahu apakah ordernya terlalu banyak atau terlalu sedikit. Score itu yang membuat putaran berikutnya lebih baik.

**Kalau ditanya**
"Sistemnya belajar dari mana?" Jawab: dari selisih antara order dan barang yang benar-benar datang, bukan dari opini.

**Uji diri**
1. Ada berapa label score?
2. Bulan apa yang WAPE-nya paling besar, dan kenapa?

Jawaban. Tiga label, yaitu SUPPLY_SHORT, ON_PLAN, dan SUPPLY_AND_LEAD. April 2024 karena bulan event.

---

## 13. Fitur 12: konsol tanya jawab

**Apa yang dilakukan.** Menjawab pertanyaan buyer dalam bahasa sehari-hari, dengan angka dari catatan.

**Enam jenis pertanyaan yang dikenali**
- SKU apa yang habis sebelum barang berikutnya datang.
- Berapa nilai stok yang mendekati kedaluwarsa.
- Supplier mana yang paling sering terlambat.
- Event apa yang terdekat dan berapa hari lagi.
- Berapa order yang menunggu manusia.
- Berapa WAPE untuk SKU yang baru diputuskan.

**Contoh jawaban sungguhan dari jalan terakhir**
- Pertanyaan soal stok habis dijawab: tidak ada yang habis sebelum barang berikutnya datang. Delapan SKU punya stok 7 hari atau kurang, dan kedelapan SKU itu sudah dipesan. Nilainya Rp806.890.340, dihitung dari jumlah order dikali harga satuan. Angka ini cocok dengan jawaban konsol setelah berkas test case dijalankan ulang. Sebelum dijalankan ulang, konsol menyebut Rp698.433.520 karena membaca berkas 19 Oktober, dua hari lebih tua dari keputusan hari ini.
- Pertanyaan soal supplier terlambat dijawab: P02 paling sering terlambat, tepat waktu 61,1 persen dengan rata-rata 21,5 hari. P06 punya fill rate terendah, 83,2 persen.
- Pertanyaan soal exception queue dijawab: 18 order menunggu manusia, nilainya Rp3.437.202.355, dan yang terbesar PO-0003 SKU0012 senilai Rp525.205.430.

![Konsol tanya jawab di Pasok](shot/fig6_console.jpg)

**Gambar 6. Konsol tanya jawab. Pertanyaan dijawab dengan angka dari catatan, dan jejak model tercetak di bawah jawaban.**

**Catatan jujur.** Jawaban untuk pertanyaan event masih bercampur bahasa Indonesia dan Inggris. Kalau demo memakai bahasa Inggris, bagian ini harus dibetulkan lebih dulu.

**Kenapa fitur ini penting.** Buyer tidak membaca tabel. Dia bertanya, lalu dapat satu paragraf yang bisa langsung dipakai.

**Uji diri**
1. Sebut empat dari enam jenis pertanyaan.
2. Dari mana angka di jawaban berasal?

Jawaban. Stok habis, kedaluwarsa, supplier terlambat, event terdekat, exception queue, dan WAPE. Dari catatan yang dihitung sistem.

### 13.1 Sebelas halaman konsol

Konsol bukan satu halaman. Ada sebelas, dan tiap halaman menjawab pertanyaan berbeda.

- `/` Konsol tanya jawab, sekaligus pintu depan.
- `/health` Stock. Nilai stok, jumlah unit, days of stock left, dan kelas ABC.
- `/orders` Orders. Run log tiap jalan, jumlah order, dan yang menunggu manusia.
- `/receiving` Receiving. Penerimaan barang dari sistem order.
- `/transfers` Transfers. Redirect antarkota, jumlah move, dan nilainya.
- `/suppliers` Suppliers. Lead time, fill rate, dan OTIF per principal.
- `/geography` Cities. Sebaran stok dan penjualan per kota.
- `/catalog` Catalogue. Daftar 600 SKU dengan kelasnya.
- `/loop` Loop. Riwayat jalan rantai dan kurva WAPE.
- `/panel` Agent panel. Keadaan agent, antrean persetujuan, dan jejak satu SKU.
- `/demo` Demo. Halaman yang dipakai saat presentasi.

---

## 14. Cara kerja satu putaran, program demi program

Rantai berjalan dengan satu perintah, `bash run_chain.sh`, dan menjalankan sebelas program berurutan. Labelnya 0, 0b, lalu 1 sampai 9.

1. registry_catalog. Menyiapkan kalender event dan katalog.
2. build_prep. Menyiapkan bahan awal, termasuk kelas barang dan shelf life.
3. stock_position. Menghitung posisi stok dan days of cover.
4. decision. Memutuskan order untuk tiap SKU.
5. consolidation. Menggabungkan order dari SKU yang satu supplier.
6. order_executor. Mengirim order dan menerima acknowledgment sistem order.
7. order_intake. Mencatat penerimaan order oleh sistem order.
8. notification. Mengirim notifikasi ke supplier atau menahan untuk persetujuan.
9. redirect. Mengalihkan stok berlebih ke cabang lain.
10. learn. Menilai semua keputusan.
11. one_pass. Menulis jejak satu SKU contoh.

Rantai berhenti di langkah yang gagal karena setiap program memakai keluaran program sebelumnya. Kalau semuanya lulus, baris terakhirnya CHAIN OK.

**Kalau ditanya**
"Kalau satu langkah gagal?" Jawab: rantai berhenti, dan tidak ada langkah berikutnya yang jalan.
"Berapa programnya?" Jawab: sebelas, berlabel 0, 0b, lalu 1 sampai 9.

**Uji diri**
1. Kenapa urutan langkah penting?
2. Apa tanda rantai selesai?

Jawaban. Karena tiap program memakai hasil program sebelumnya. Tandanya baris CHAIN OK.

---

## 15. Bukti, batasan, dan yang bukan klaim

**Tiga jenis data**
- Data publik: indeks penjualan ritel Bank Indonesia dan dataset M5 untuk uji ramp.
- Data sintetis: katalog 600 SKU, diizinkan panitia, dan tidak pernah disajikan sebagai hasil klien.
- Data hasil jalan sistem: order, penerimaan, dan score, bisa dibuat ulang di tempat.

**Tiga batasan yang disebut sendiri**
- Kuota AgentCore nol di akun ini, jadi jalur AWS memakai Lambda dengan Bedrock lewat endpoint Mantle.
- Sistem order di demo adalah pengganti, bukan ERP sungguhan. Penggantian cukup satu variabel lingkungan.
- Katalog masih 600 SKU, sedangkan target pasar 2.500 SKU. Yang pecah lebih dulu di skala itu adalah ruang gudang.

**Angka rapor dari replay 284 hari**
- Permintaan hilang 0,717 persen, atau 806.996 unit.
- Nilai stok rata-rata Rp284,0 miliar, turns 6,41 kali setahun, dan DIO 44,3 hari.
- Biaya simpan fisik Rp17,7 miliar, dan margin hilang Rp1,37 miliar pada asumsi margin 10 persen.
- Kebutuhan pembiayaan pada termin 30 hari Rp8,58 miliar.

**Yang perlu dibetulkan sebelum demo**
- Kalimat di jejak SKU contoh masih menyebut order melewati credit limit, padahal nilainya Rp65 juta dari batas Rp704,8 juta, dan statusnya tertulis keluar otomatis.
- Bagian nilai yang diterima di jejak SKU contoh membaca baris SKU lain karena satu nomor PO dipakai beberapa SKU.
- Jawaban konsol untuk pertanyaan event masih bercampur dua bahasa.
- Halaman Loop di konsol masih memuat angka 125 order dan 82,4 persen, sedangkan jalan terakhir mencatat 139 order. Angka di halaman itu perlu disegarkan dari artefak terbaru.
- Lambda yang terpasang masih membawa snapshot lama. Jawaban dari endpoint menyebut 125 keputusan dan WAPE 8,71 persen, sedangkan artefak lokal 139 keputusan dan 9,15 persen. Bundle perlu di deploy ulang sebelum demo.
- Jawaban konsol sempat membaca berkas test case yang tertinggal dua hari, jadi menyebut Rp698.433.520 untuk delapan SKU berstok tipis. Berkasnya sudah dijalankan ulang, dan sekarang angkanya Rp806.890.340 seperti artefak hari ini. Jalankan ulang sebelum demo kalau artefak berubah lagi.

**Uji diri**
1. Sebut tiga jenis data.
2. Apa yang pecah lebih dulu di 2.500 SKU?

Jawaban. Publik, sintetis, dan hasil jalan sistem. Ruang gudang.

---

## 16. Kelas produk ABC

Kelas ABC membagi SKU menurut sumbangan nilai penjualan, bukan jumlah unit. Caranya sederhana. Urutkan SKU dari nilai terbesar, hitung pangsa kumulatifnya, lalu potong di 80 persen dan 95 persen.

- Kelas A: 262 SKU, sumbangan nilai sampai 80 persen.
- Kelas B: 178 SKU, sumbangan 80 sampai 95 persen.
- Kelas C: 160 SKU, sisa 5 persen.

**Yang berubah per kelas**
- Service level. Nilai z kelas A 1,645, B 1,28, C 0,84. Makin besar z, makin tebal buffer, dan makin tahan barang itu kehabisan.
- Cap days of cover. Kelas A 45 hari, B 60 hari, C 90 hari. Barang mahal tidak boleh menumpuk lama. Barang lambat laku boleh lebih dalam.
- Prioritas. Kalau ruang gudang atau kredit sempit, baris kelas A didahulukan.

**Contoh dari jalan terakhir.** Dari 139 baris order, 69 baris kelas A dengan 730.086 unit. Kelas B 41 baris dengan 235.453 unit. Kelas C 29 baris dengan 49.737 unit. Jadi separuh baris membawa hampir tiga perempat unit.

**Catatan jujur.** Data juga punya kolom volatility untuk pembagian XYZ, tetapi seluruh 600 SKU tercatat Med. Artinya pembagian XYZ belum membedakan apa pun, dan jangan diklaim bekerja.

---

## 17. Loop dan empat agent

![Loop dan empat agent](assets/loop-agent.svg)

**Bagan 2. Loop dan empat agent. Tiga agent mengumpulkan masukan, Decision Agent memutuskan, guardrail menyaring, lalu order keluar. Garis putus-putus menandai SAP AI Core dan langkah learn yang menutup loop.**

Loop-nya lima langkah dan berulang. Lihat posisi stok, forecast permintaan, putuskan, kirim, lalu nilai hasilnya. Empat agent mengisi langkah itu.

**Demand Agent.** Masukannya riwayat penjualan per outlet, kalender event, dan kelas ramp. Keluarannya forecast per SKU, rentang ketidakpastian, dan deteksi kenaikan yang tidak dijelaskan event.

**Stock Position Agent.** Masukannya stok gudang, barang di jalan, dan open PO. Keluarannya sellable, days of cover, tanda perlu order, dan tanda risiko kedaluwarsa.

**Supplier Reliability Agent.** Masukannya catatan penerimaan barang. Keluarannya lead time p50 dan p90, fill rate, dan tanda drift.

**Decision Agent.** Masukannya tiga keluaran di atas, ditambah credit headroom, shelf life, dan holding cost. Keluarannya satu action per SKU, jumlah order, dan alasan yang bisa dibaca buyer.

Sesudah Decision Agent ada tiga guardrail. Baru order keluar. SAP AI Core memberi score pada exception queue dan menulis alasan. Joule menampilkan antrean itu ke buyer. Langkah learn menutup loop dengan membandingkan barang yang datang dengan forecast.

**Yang bukan agent.** Forecast, guardrail, dan hitungan order adalah kode deterministik. Model bahasa hanya menulis alasan dan menjawab pertanyaan konsol.

**Kalau ditanya**
"Berapa agent-nya?" Jawab: empat, yaitu Demand, Stock Position, Supplier Reliability, dan Decision.
"Siapa yang memutuskan jumlah order?" Jawab: Decision Agent memakai rumus. Model bahasa tidak menyentuh angkanya.

**Uji diri**
1. Sebut empat agent dan satu keluaran masing-masing.
2. Guardrail dipasang pada tahap apa?

Jawaban. Demand memberi forecast, Stock Position memberi sellable, Supplier Reliability memberi lead time dan fill rate, Decision memberi action dan jumlah. Guardrail dipasang antara Decision Agent dan order.

---

## 18. SAP dipakai untuk tiga hal

SAP di sini bukan cuma tempat menyimpan order. Ada tiga peran, dan ketiganya benar-benar jalan.

**Peran pertama, model scoring.** Deployment sap-rpt-1.6 menerima satu permintaan berisi 720 baris konteks berlabel dan 600 baris query. Model mengembalikan tiga keluaran sekaligus: kemungkinan stockout 14 hari ke depan, risiko kedaluwarsa, dan sisa days of cover. Jalan terakhir: HTTP 200, 600 prediksi, 10,73 detik.

**Peran kedua, penulis alasan dan jawaban.** gpt-5.4 lewat orchestration deployment menulis alasan untuk tiap baris exception queue, dan menulis jawaban konsol dari fakta yang sudah dihitung. Kalau panggilan gagal, sistem memakai template dan menandainya, bukan mengarang.

**Peran ketiga, sistem catatan.** Order harus hidup di sistem order. Di demo, sistem itu pengganti, bukan S/4 sungguhan.

**Catatan jujur.** Dua pandangan soal kedaluwarsa berbeda jauh. Agen menandai 0 SKU, sedangkan RPT menandai 577 dari 600. Penyebabnya beda definisi. Agen membandingkan days of cover dengan umur simpan penuh, sedangkan RPT dilatih pada label 14 hari ke depan. Untuk stockout, kecocokan keduanya 89,5 persen. Karena itu score RPT dipakai sebagai pendapat kedua, bukan gerbang keputusan.

**Kalau ditanya**
"SAP-nya cuma tempelan?" Jawab: tidak. Ada tiga panggilan nyata, yaitu scoring 600 SKU, penulisan alasan, dan penulisan jawaban konsol.

**Uji diri**
1. Tiga keluaran apa yang diberikan RPT-1.6?
2. Kenapa RPT menandai 577 SKU berisiko kedaluwarsa, sedangkan agen nol?

Jawaban. Stockout 14 hari, risiko kedaluwarsa, dan sisa days of cover. Karena definisinya beda, RPT memakai label 14 hari ke depan.

---

## 19. AWS dan yang belum disambung

**Yang jalan.** Lambda dengan URL `https://vyfesxclb5gwzqqkg5csbkgxeq0jdnpf.lambda-url.us-west-2.on.aws/`. Fungsi ini menjawab pertanyaan dari snapshot yang dibundel di dalam zip-nya, dan panggilan terakhir menjawab HTTP 200. Bedrock dipakai lewat endpoint Mantle karena Converse asli tertutup di akun ini.

**Yang belum.** AgentCore Runtime dan Memory terkunci di akun ini, kuotanya nol dan permintaan naik kuota ditolak. Joule juga belum disambung ke sistem, jadi antrean persetujuan masih ditampilkan di halaman `/panel`, bukan di Joule.

**Satu cacat yang perlu dibereskan.** Snapshot di dalam Lambda lebih tua dari artefak lokal. Jawabannya menyebut 125 keputusan, sedangkan jalan terakhir 139. Bundle harus di deploy ulang sebelum demo, kalau tidak angka di layar dan angka di Lambda akan berbeda.

---

## 20. Latihan menjawab

Aturannya satu. Jawab dulu, alasan kemudian, angka terakhir kalau perlu.

1. Ini cuma forecast? Bukan. Forecast satu dari sepuluh langkah. Sistem mengirim order, menerima barang, lalu menilai keputusannya sendiri.
2. Kenapa pakai model bahasa? Untuk menulis alasan yang dibaca buyer. Angka order tidak pernah dari model.
3. Apa yang mencegah order konyol? Cap days of cover, batas credit limit dan ruang, lalu gerbang yang melempar asumsi belum terbukti ke manusia.
4. Exception queue kosong? Di jalan terakhir ada 18 baris senilai Rp3,4 miliar, dengan alasan credit limit dan ganti supplier.
5. Lebih baik dari buyer? Replay 284 hari dengan stok awal sama, permintaan hilang 0,72 persen, amplification turun 72,9 persen.
6. Datanya asli? Tiga sumber, disebut jujur: publik, sintetis, dan hasil jalan sistem.
7. AWS dipakai atau cuma logo? Lambda jalan, Bedrock lewat Mantle. AgentCore tidak dipakai karena kuota nol.
8. SAP untuk apa? Dua hal. AI Core memberi score dan menulis alasan, lalu sistem order menyimpan PO. Yang di demo hanya sistem order pengganti.
9. Apa yang pecah di 2.500 SKU? Ruang gudang karena butuh data karton dan palet dari sistem gudang.
10. Soal kedaluwarsa? Shelf life terpendek 180 hari. Uji dengan barang 21 hari: susut turun dari 3,81 menjadi 2,68 persen, dengan biaya layanan 0,24 poin.
11. Kalau supplier telat terus? Buffer untuk supplier itu naik, dan order berikutnya membesar otomatis.
12. Payday masih dipakai? Tidak untuk order. Riwayat payday tersebar 0,84 sampai 1,58 dan korelasinya negatif, jadi pengalinya dimatikan dan ketidakpastiannya pindah ke buffer. Syarat mengembalikannya adalah jadwal promo sebelum payday.
13. Langkah berikutnya? Sambung ke ERP asli lewat satu variabel, lalu uji di satu gudang nyata dengan 2.500 SKU.

---

## 21. Glosarium

- SKU. Satu jenis barang dengan kode sendiri.
- Sellable. Barang yang bisa dijual sekarang: stok gudang, barang di jalan, dan open PO.
- Days of cover. Berapa hari stok habis pada velocity sekarang.
- Lead time. Jarak waktu dari order dikirim sampai barang tiba.
- p90. Batas lead time yang hanya dilewati 10 persen kasus terburuk.
- Fill rate. Berapa persen dari jumlah yang dipesan benar-benar dikirim supplier.
- Buffer. Stok tambahan untuk menutup ketidakpastian lead time dan forecast.
- Amplification. Order yang bergoyang lebih liar daripada permintaan.
- Guardrail. Aturan yang menahan goyangan order.
- Ramp. Pola permintaan naik bertahap menjelang event.
- Step. Pola permintaan naik sekali lalu turun.
- Exception queue. Daftar order yang menunggu keputusan manusia.
- MOQ. Jumlah order minimum yang mau dilayani supplier.
- WAPE. Ukuran kesalahan forecast, makin kecil makin bagus.
- Replay. Uji ulang kebijakan pada data historis.
- ABC. Pembagian SKU menurut sumbangan nilai penjualan: A sampai 80 persen, B sampai 95 persen, C sisanya.
- XYZ. Pembagian SKU menurut keragaman permintaan. Di katalog ini semua SKU tercatat Med, jadi belum membedakan.
- p50. Lead time tengah, separuh kedatangan lebih cepat dari angka ini.
- auto-issue. Order yang keluar sendiri tanpa persetujuan manusia.
- OTIF. Berapa persen order yang datang lengkap dan tepat waktu.
- Turns. Berapa kali stok berputar dalam setahun.
- DIO. Days inventory outstanding, berapa hari stok tersimpan sebelum terjual.
- DPO. Days payable outstanding, berapa hari tagihan supplier dibayar.
- SAP AI Core. Layanan SAP untuk menjalankan model, dipakai untuk scoring dan penulisan alasan.
- RPT-1.6. Model tabular SAP yang memberi score stockout, kedaluwarsa, dan sisa cover.
- Orchestration. Jalur SAP yang merangkai prompt lalu memanggil model bahasa.

---

## 22. Lembar cek sebelum demo

1. Bisa sebut lima langkah putaran tanpa catatan.
2. Bisa sebut empat agent dan tugasnya.
3. Bisa hitung satu order di kertas, termasuk pembagian fill rate.
4. Bisa jelaskan kenapa tanggal Lebaran tidak dihitung sendiri.
5. Bisa sebut tiga guardrail dan angka 2,68 lawan 0,24.
6. Bisa tunjukkan exception queue dengan 18 baris dan nilainya.
7. Bisa sebut tiga jenis data tanpa gugup.
8. Bisa sebut tiga batasan sebelum ditanya.
9. Bisa sebut batas nilai kelas A, B, dan C.
10. Bisa sebut empat agent dan satu keluaran masing-masing.
11. Bisa sebut tiga peran SAP tanpa melihat catatan.
12. Bisa sebut sebelas halaman konsol dan satu isi tiap halaman.
13. Bisa bilang terus terang bahwa guardrail tidak menyala di snapshot ini.
14. Bisa sebut cacat Lambda yang snapshot-nya masih lama.
