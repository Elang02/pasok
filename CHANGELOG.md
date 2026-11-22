## 2026-10-18 — Plafon stok bertahap diperbaiki, plus skenario umur simpan pendek

Rumus plafon `hold_days` mengurangi satu periode tinjauan sekaligus lead time, jadi untuk barang
21 hari dengan lead 15 hari plafonnya tinggal 2 hari permintaan, terlalu sempit sampai aturannya
memakan penjualan lebih banyak daripada barang rusak yang dicegahnya. Diperbaiki menjadi
`max(2, umur_simpan - lead)`, yaitu jendela sejak barang mendarat.

Skenario 90 hari, 60 SKU dipaksa umur simpan 21 hari dengan lead 15 hari:

| kebijakan | hilang penjualan | kedaluwarsa |
| --- | --- | --- |
| tanpa aturan | 5,65 persen | 203.224 unit |
| plafon versi pertama | 9,85 persen | 79.332 unit |
| plafon versi diperbaiki | 8,04 persen | 118.755 unit |

Penting: plafon ini TIDAK PERNAH mengikat pada katalog normal (0 dari 600 keputusan), karena
umur simpan di atas lead plus tinjauan. Jadi angka dashboard dan sembilan halaman konsol tidak
berubah dan seluruh gate tetap lulus. Batas sebenarnya baru terlihat di skenario, dan bentuknya
menunjuk ke hal lain: barang yang cuma punya 6 hari masa pakai setelah mendarat tidak bisa
dilayani kebijakan tinjauan mingguan, pemesanan harus lebih sering.

## [Belum dirilis] - 2026-10-18 (r)

### Ditambah

- **Riwayat order berkelanjutan di halaman Orders.** Halaman menampilkan satu catatan yang
  tidak terputus: dari 2 Januari 2023 sampai 29 Desember 2025 pemesanan dilakukan manusia
  (32.314 baris, 406,9 juta unit, Rp 6.506 miliar, dari kolom `ordered` riwayat harian), dan
  sejak 1 Januari 2026 oleh loop (4.773 baris per 9 Januari, Rp 106 miliar, dari keputusan
  agen pada simulasi lingkaran tertutup). Tiap baris memuat siapa yang memesan, tanggal
  janji, tanggal kedatangan, dan berapa hari telat. Enam fakta era di atas tabelnya
  membandingkan persentase keterlambatan era manual (49,9 persen) dengan era agen (27,4
  persen, catatan masih muda).
- **`/api/order_history`** membaca ledger itu dengan filter era dan pencarian.
- **Kedatangan era agen diberi variasi** sesuai sebaran lead time pemasok yang tercatat,
  seeded per hari, dan tiap order dicatat di `data/sim/closed/deliveries.csv` saat
  dikeluarkan. Tanpa itu, semua kiriman selalu tepat waktu dan klaim ketepatan jadi
  artefak model.
- **Kedatangan era manual dicocokkan dari catatan**: per SKU, kiriman yang tercatat di
  kolom `arrivals` dipakai untuk menutup pesanan paling lama yang belum terpenuhi, dengan
  catatan pengiriman per pemasok sebagai cadangan. Ini pembagian ulang dari catatan, dan
  halaman menyebutnya.

### Diubah

- Halaman Orders tidak lagi menampilkan ledger PO dengan judul "Order history"; bagian itu
  diganti catatan yang berkelanjutan. Endpoint `/api/orders` tetap ada untuk pemanggil lain.
- Backfill satu tahun mode `closed` dijalankan ulang dari 1 Januari supaya variasi
  kedatangan berlaku sejak hari pertama.

### Diverifikasi

- Lima gate hijau; halaman diuji di Chrome sungguhan: 150 baris terender, tombol era
  menyaring, fakta era terisi dari API.
## [Belum dirilis] - 2026-10-18 (q)

### Diubah

- **Grafik dihapus dari jawaban chat.** Operator: "Yang chart 600 SKUs one decision each itu
  jelek banget, ngeganggu, masa tiap chat muncul itu". Jalur jawaban menempelkan sebaran 600
  SKU ke setiap jawaban yang menyebut ringkasan keputusan, jadi pembaca yang bertanya satu hal
  tetap mendapat dinding titik. Mesin grafiknya dibuang dari halaman chat: 141 baris JS dan 20
  baris CSS, dua tempat pemanggilan, dan pembukuan hover yang mengantre. `_charts_for`
  sekarang mengembalikan kosong dengan alasannya tertulis.
- Grafiknya tetap ada di `/demo`, halaman yang dibuka juri.

### Diverifikasi di browser nyata

- Pertanyaan yang sama menghasilkan jawaban 402 karakter dengan jejak empat langkah, jumlah
  elemen grafik di halaman **0**, dan tidak ada error JavaScript.

## [Belum dirilis] - 2026-10-18 (p)

### Ditambah

- **`demo/REHEARSAL.md`**: alur demo 15 menit bahasa Inggris, urutan tujuh layar beserta apa
  yang dibuktikan masing masing dan alokasi waktunya, tiga pertanyaan yang diajukan verbatim
  beserta jawaban yang akan muncul, empat angka yang disebut lisan, dan daftar hal yang
  TIDAK boleh dikatakan (ramp pada M5 sebagai kontrol negatif, tiga aturan guardrail yang
  tidak semuanya bekerja, cakupan angka penerimaan).
- **`tools/demo_shots.py`**: menyiapkan tangkapan layar lewat Chrome DevTools Protocol.
  Tiap halaman dibuka di tab sendiri, ditunggu sampai selesai membaca endpoint, lalu diukur
  tinggi halamannya dan dihitung jumlah barisnya supaya halaman kosong tidak bisa lolos jadi
  tangkapan. Halaman konsol diajukan pertanyaan lebih dulu, jejak berpikirnya dibuka, baru
  dipotret.
- **`shots/demo-*.png`**: 12 berkas, termasuk versi terpotong `02-orders-top` dan
  `05-transfers-top` untuk slide, karena halaman aslinya setinggi 14.970 dan 5.724 piksel.

### Catatan

- Tangkapan konsol membuktikan jejaknya hidup: "Thought for 4.3s", empat langkah, dan langkah
  terakhir berbunyi "12 of 12 numbers found in the records. Every number matched".

## [Belum dirilis] - 2026-10-18 (o)

### Ditambah

- **Halaman `/receiving`**: 1.911 kiriman sampai snapshot, 1.749 datang kurang, 706 lewat
  janji, kekurangan 38.932 unit, kinerja tiap supplier, kiriman yang lewat janji, dan 116
  order yang masih di jalan dengan delapan tanggal kirim yang dijanjikan.
- **Halaman `/geography` (Cities)**: lima kota, 120 outlet dengan 86 warung, permintaan
  sepanjang riwayat 404 juta unit senilai Rp 6,23 triliun, bar bagian per kota, lima barang
  teratas per kota, dan kelebihan stok per kota yang menjadi bahan perpindahan antar depot.

### Diubah

- **Nav sembilan entri identik di semua halaman**: Console, Orders, Receiving, Stock,
  Transfers, Suppliers, Cities, Loop, Agent panel.
- **Kedua gate daftar halaman kini memuat sembilan halaman konsol.**

### Diverifikasi

- Enam gate hijau: bahasa 14 berkas, sistem desain 9 halaman, kebenaran 31 angka, jawaban 13
  kasus, audit integrasi 11 dari 11, test case lolos. Sepuluh URL menjawab 200.

## [Belum dirilis] - 2026-10-18 (n)

### Diperbaiki

- **Endpoint penerimaan salah menghitung snapshot.** Ia membaca `order_summary.json` memakai
  pembaca CSV, jadi snapshot-nya kembali kosong, filter tanggalnya terlewat, dan semua 1.956
  baris dihitung padahal 45 di antaranya bertanggal setelah snapshot. Angka yang benar:
  **1.911 penerimaan** sampai 11 Oktober 2026, 1.749 datang kurang, 706 lewat janji, dan
  kekurangan 38.932 unit. Sekarang cocok dengan jawaban konsol.
- **"kiriman telat" tidak dikenali** dan jatuh ke ringkasan jaringan. Kata kunci penerimaan
  diperluas, dan urutannya tetap menaruh pertanyaan bersupplier di depan sehingga
  "supplier mana yang lambat" tetap dijawab agen supplier.

### Ditambah

- Konsol bisa menjawab soal penerimaan dan soal kota: niat `receiving` dan `geography` plus
  fungsi fakta `receiving()` dan `geography()`.
- Nav sembilan entri di tujuh halaman yang sudah ada: Console, Orders, Receiving, Stock,
  Transfers, Suppliers, Cities, Loop, Agent panel.

## [Belum dirilis] - 2026-10-18 (m)

### Ditambah

- **Endpoint `/api/receiving`**: apa yang benar benar datang dibanding yang dijanjikan.
  Hanya penerimaan bertanggal sampai snapshot yang dihitung, karena kiriman setelah tanggal
  itu belum terjadi pada hari yang digambarkan angka ini. Tercatat 1.956 penerimaan, **1.792
  di antaranya datang kurang dari yang dipesan**, 721 lewat janji, kekurangan 39.667 unit,
  dan 116 order sedang jalan dengan delapan tanggal kirim yang dijanjikan supplier.
- **Endpoint `/api/geography`**: mana kota yang menjual banyak. Lima kota, 120 outlet (86
  warung), permintaan sepanjang riwayat data 404.211.032 unit senilai Rp 6,23 triliun.
  Jakarta 25,5 persen, Tangerang 21,3, Bekasi 18,5, Bogor 18,5, Depok 16,2.

### Catatan

- `data/catalog/receiving.csv` memuat tanggal sampai 2026-11-01, yaitu melewati tanggal
  snapshot 2026-10-11. Baris setelah snapshot sengaja tidak dihitung dan itu disebutkan di
  endpoint, supaya tidak ada kiriman yang dihitung dua kali atau dihitung sebelum waktunya.

## [Belum dirilis] - 2026-10-18 (l)

### Ditambah

- **Halaman `/health` (Stock health)**: nilai stok, jumlah unit, berapa hari stok menutup
  penjualan, nilai yang terjual per hari, tabel kelas ABC-XYZ enam baris, pemeriksaan
  kedaluwarsa, barang lambat laku, dan 40 SKU bernilai terbesar.
- **Halaman `/transfers` (Depot transfers)**: nilai stok yang diselamatkan dengan memindahkan
  barang, nilai kelebihan yang jadi masalah, 395 pergerakan, rincian ke lima depot kota
  Jakarta Tangerang Bekasi Bogor Depok beserta porsinya, dan ledger 60 baris dengan alasannya
  yang sudah diterjemahkan ke bahasa pembeli.
- **Halaman `/suppliers`**: kinerja 12 supplier, cakupan tiap supplier (jumlah barang,
  kategori, waktu datang, pesanan terkecil), kiriman yang dijanjikan supplier beserta
  nilainya, dan apa yang sudah dikirim ke mereka versus yang masih menunggu orang.

### Diubah

- **Nav tujuh entri identik di seluruh halaman**: Console, Orders, Stock health, Depot
  transfers, Suppliers, Loop, Agent panel.
- **Kedua gate daftar halaman diperluas** ke ketujuh halaman konsol, jadi halaman baru tidak
  bisa lolos dari aturan sistem desain dan kebenaran angka.

### Catatan jujur dari halaman baru

- Pemeriksaan kedaluwarsa menunjukkan **nol** SKU berisiko, dan barang lambat laku juga
  **nol**. Itu hasil yang benar: umur simpan di katalog 6 sampai 35 bulan sementara stok
  menutup 15,4 hari. Ambangnya ditulis di halaman supaya angka nol itu terbaca sebagai hasil
  pemeriksaan, bukan bagian yang kosong.
- Tiga halaman baru menjawab HEAD selain GET, karena FastAPI tidak menambahkan HEAD pada
  `@app.get` sehingga `curl -sI` ke halaman lama menjawab 405. Halaman lama belum diubah.

## [Belum dirilis] - 2026-10-18 (k)

Operator: "saya mau chatnya itu ada reasoningnya kayak chatgpt, saya mau biar kayak demand agent
ini ngapain, agent lain ngapain, dan berpikir seperti apa, tapi tampilannya kayak yang di
chatgpt gitu". Juga: batas kredit supplier tidak perlu, usulan ganti supplier tidak perlu,
karena supplier sudah tetap untuk tiap barang.

### Ditambah

- **Jejak berpikir di chat konsol.** Setiap jawaban sekarang membawa empat langkah yang benar
  benar terjadi, masing masing dengan waktu aslinya: router membaca pertanyaan dan
  mengarahkannya ke agen yang tepat, agen membaca catatan yang dibutuhkannya (disebut namanya
  dalam bahasa pembeli, misalnya "the event calendar and how each SKU has moved in past
  events"), agen menulis jawabannya bersama model, lalu **agen memeriksa setiap angka di
  jawaban terhadap catatan**. Baris terakhir itu verifikasi nyata, bukan hiasan: pada satu
  percobaan ia melaporkan "17 of 17 numbers found in the records. Every number matched".
- Tampilannya seperti asisten chat: satu baris terlipat "Thought for 4.6s", diklik untuk
  membuka daftar langkah beserta nama agennya.

### Diubah

- `/api/suppliers` sekarang juga melaporkan berapa barang yang dipasok tiap supplier
  (`skus`), berapa kategori (`categories`), dan pesanan terkecil yang diterima
  (`smallest_order_units`), supaya halaman bisa menunjukkan cakupan supplier, bukan usulan
  ganti supplier.

### Catatan data (dijawab dari berkas, bukan dari ingatan)

- Tiap barang sudah punya tepat satu supplier sejak awal: 600 SKU, nol tanpa supplier, 12
  supplier, masing masing memasok 39 sampai 65 barang dan melayani 5 kategori. Waktu datang
  barang 4 sampai 21 hari tergantung supplier, dan pesanan terkecil yang diterima 24 sampai
  144 unit.

## [Belum dirilis] - 2026-10-18 (j)

Operator: "bagian loop itu bisa perbagus biar lebih clean? Gausah ada jargon jargon gitu di
web, oiya saya mau loop itu jalan tiap hari, misalnya jam berapa gitu, dan nanti ada tab yang
menampilkan historinya, kayak SKU apa saja yang dipesan, berapa, dan alasannya apa".

### Ditambah

- **Jadwal harian nyata.** `pasok-loop.timer` (systemd user) menjalankan
  `tools/record_run.py` tiap hari 06:00 WIB, yaitu 07:00 waktu box karena box ini UTC+8.
  Setiap run mencatat satu baris ke `data/orders/run_log.csv`: kapan jalan, berapa lama,
  berapa order, berapa tanpa orang, berapa menunggu orang, nilai yang menunggu, berapa yang
  diakui supplier, kekurangan unit, dan exit code rantai. Run yang gagal dicatat gagal.
- **Halaman `/orders`**: jadwal dan run terakhir, tabel riwayat run, dan ledger order 121
  baris berisi SKU, kategori, supplier, jumlah, nilai, alasan dalam bahasa pembeli, status
  pengakuan supplier, dan tanggal kirim yang dijanjikan. Ada pencarian dan empat tombol urut
  yang benar benar memanggil ulang API.
- **Endpoint** `/api/runs`, `/api/orders`, `/api/stock_health`, `/api/transfers`,
  `/api/suppliers`.
- **Konsol bisa menjawab soal baru**: niat `transfers` dan `health` di router, plus fungsi
  fakta `transfers()` dan `stock_health()`.
- **Nav disamakan di semua halaman** jadi tujuh entri dengan urutan dan label yang sama
  persis, satu blok kanonik, supaya pindah halaman tidak terasa pindah produk.

### Diperbaiki

- **Halaman loop berhenti berbahasa insinyur.** Judul "Eleven hand-offs, all proven from
  files", "The two questions that must be answered", dan "Numbers you can check" diganti blok
  "When it runs" dan "What it checks" yang berisi empat pemeriksaan dalam satu kalimat
  masing-masing.
- **Enam angka yang ikut terhapus bersama prosa lama dikembalikan**, dan justru yang paling
  penting untuk demo: pengurangan ayunan order 72,6%, kiriman supplier 91,2%, forecast miss
  12,8%, order tanpa orang 95,9%, nilai order IDR 5,76M, dan 479 SKU yang tidak perlu apa pun.
  Angka yang berbentuk bagian sekarang tampil sebagai persen, bukan desimal mentah, jadi
  `auto_rate` 0,959 dan `fill_rate` 0,9122 tidak lagi muncul sebagai angka mesin.
- **Gate bahasa belajar membedakan kode dari teks.** `status == "ESCALATED"` sempat ditandai
  sebagai teks di layar, padahal itu membandingkan nilai tersimpan. Gate sekarang menyingkirkan
  literal yang dibandingkan (`==`, `.get(`) dan kunci kamus, bukan melonggarkan daftar jargon.

## [Belum dirilis] - 2026-10-18 (i)

Operator bertanya ke konsol "apa event terdekat" dan jawabannya: "Lebaran. 600 SKUs affected.
demand at peak 2.18 to 3.00 times normal." Komennya: "sangat tidak menjawab untuk user awam
kalo gini, gaada tanggal, gaada apa apa, cuman tiba tiba data yang ga jelas alasannya, apa,
ini kan kayak chatbot loh, kok ga interaktif gitu, namanya agentic ya bener bener kayak
ngobrol sama orang gak sih harusnya, dan infonya lengkap yang dibutuhkan".

### Diperbaiki

- **Ada DUA router pertanyaan dan konsol memakai yang lebih tua.** Daftar kata yang benar ada
  di lane chat, sementara lane jawaban menyimpan salinan lama tanpa kata "event", "supplier",
  atau "accuracy". Jadi "apa event terdekat" jatuh ke ringkasan jaringan, dan modelnya sendiri
  yang harus membuka jawaban dengan kalimat "fakta ini tidak menunjukkan event terdekat".
  Sekarang satu router di `pasok_answers.route_question()`, dipakai kedua lane.
- **Event terdekat selalu salah.** Pemanggilnya mengisi default "Lebaran" ketika pertanyaannya
  tidak menyebut nama event, padahal Lebaran itu ke-5 terjauh (156 hari) sementara Christmas
  72 hari. Sekarang target kosong berarti event terdekat, dihitung dengan aturan kalender yang
  sama dengan pipeline.
- **Tidak ada tanggal sama sekali.** `event_impact()` hanya melaporkan multiplier dan jumlah
  SKU. Sekarang setiap jawaban event memimpin dengan tanggal, jarak dalam hari, dua event
  sesudahnya, kapan permintaan mulai naik, dan apa yang sedang dilakukan sistem tentangnya.
  Event yang tidak dikenal pun tetap menyebut event terdekat yang dikenal beserta tanggalnya.
- **Prompt-nya yang membuat jawabannya telegrafis.** Prompt lama meminta "one short answer"
  dan menyuruh model berhenti saat angkanya habis. Sekarang prompt meminta satu kalimat
  pembuka yang menjawab pertanyaan dengan tanggal atau angkanya, lalu tiga sampai empat
  kalimat berisi apa artinya, berapa nilainya, apa yang sudah dikerjakan sistem, dan apa yang
  perlu dari pembacanya. Model juga diinstruksikan menjawab dalam bahasa pertanyaannya, jadi
  pertanyaan Indonesia dijawab Indonesia, pertanyaan Inggris dijawab Inggris.
- **Baris "Value of the stock that runs out: IDR 0"** tidak bermakna: stoknya memang habis,
  dan angka nol itu hanya berarti tidak ada yang habis sebelum kiriman berikutnya. Diganti
  jadi nilai order yang ditempatkan untuk SKU tersebut (IDR 533.842.700 untuk 8 SKU).
- **Angka bulanan keluar sebagai desimal mentah** ("0.1316") di jawaban akurasi. Sekarang
  persen, sesuai kontrak.

### Gate

- `ui_answer_gate` sekarang juga menuntut, bukan cuma melarang: jawaban event wajib memuat
  tanggal dan jarak hari, jawaban stok wajib memuat nilai rupiah, dan event terdekat wajib
  benar-benar yang terdekat menurut kalender. Ditambah larangan nol berlabel yang tak bisa
  ditindaklanjuti. 12 kasus menjadi 13.

## [Belum dirilis] - 2026-10-18 (h)

Operator melihat tombol urutan kedua dan bertanya: "Fastest selling first kurang akurat gak
sih? gaada normalisasi, kan kalo mie ya jelas penjualannya banyak, barang barang murah
apalagi, padahal kan ga cocok ya kalo gitu jadinya, stoknya emang banyak dan terjual banyak".

### Diubah

- **Urutan "Fastest selling first" diganti jadi "Selling faster than usual".** Mengurut unit
  per hari mentah bukan ukuran apa pun: unit cost di katalog membentang dari Rp 3.500 sampai
  Rp 38.000, jadi satu bungkus Rp 6.500 mengalahkan satu bungkus Rp 38.000 pada rupiah yang
  sama. Hasilnya **18 dari 20 baris teratas semuanya mie instan**. Sekarang tiap SKU
  dibandingkan dengan kebiasaannya sendiri: rata-rata 28 hari terakhir dibagi median 90 hari
  sebelumnya, dibaca dari seri harian yang sudah ditulis loop. Daftarnya menyebar ke lima
  kategori (biskuit 6, minuman 4, personal care 4, mie 4, rumah tangga 2 dari 20), dan yang
  muncul di puncak adalah SKU yang **sekaligus** mempercepat dan hampir habis: SKU0078,
  1,55x kebiasaannya dengan 6,0 hari stok. SKU itu juga baris pertama urutan "least cover",
  yang berarti tombol kedua sekarang menunjuk hal yang bisa ditindaklanjuti, bukan sekadar
  mengulang kategori terbesar.

### Catatan

- Rasio itu sudah ikut di payload `/api/skus` sebagai `usual_ratio`. Kolomnya belum
  ditampilkan di tabel, jadi kalau mau angkanya terlihat di baris, tinggal ditambah.

## [Belum dirilis] - 2026-10-18 (g)

### Diperbaiki

- **Event yang sudah lewat dijual sebagai spike yang akan datang.**
  `event_windows()` menempatkan kemunculan berikutnya dengan satu langkah tahun dari tanggal
  terakhir terlihat. Imlek terakhir 2025-02-10, event lunar melangkah 354 hari, hasilnya
  **2026-01-30**, sementara snapshot-nya **2026-10-11**. Fungsi itu tidak pernah memeriksa
  apakah hasilnya masih di depan, jadi loop mensizing order terhadap peak yang sudah lewat
  delapan bulan, dan TC-2 melaporkan tanggal itu di bawah kunci bernama
  `event_windows_in_horizon`. Langkahnya sekarang diulang sampai benar-benar di depan.
  Dampak terukur: 53 dari 600 SKU membawa event dengan multiplier sampai 2,43x, menambah
  **432.469 unit** (Rp 8,17 miliar). Setelah perbaikan: order 145 menjadi 121, otomatis 139
  menjadi 116, menunggu 6 menjadi 5, nilai antrian Rp 1.005.225.400 menjadi Rp 734.357.600.
- **Verifikasi yang lolos karena string "nan".** `one_pass.py` menyimpan `str(d["event"])`,
  yang untuk event kosong adalah string `"nan"`, dan string itu truthy, jadi
  `assert trace["forecast"]["event"]` lolos dan skrip mencetak "event present" untuk snapshot
  yang tidak punya event sama sekali. Perbandingan `NaN != ""` yang sama juga membuat setiap
  filter di tangga pemilihan SKU mengira sudah menemukan kandidat ber-event. Sekarang ada
  satu normalisasi di kedua file, dan verifikasinya menguji tiap tingkat tangga terhadap apa
  yang memang dijanjikannya.
- **Dokumen demo mengklaim ada event window.** `demo/one_pass.md` membuka dengan pernyataan
  bahwa SKU-nya dipilih di dalam event window terdaftar. Sekarang dokumen itu menyebut aturan
  ketatnya, lalu mengatakan terus terang bahwa tidak ada SKU yang cocok di snapshot ini dan
  tingkat mana yang dipakai.
- **`test_cases.py` punya penanganan NaN yang sama**, sehingga tabel spike mendaftar 600 SKU
  seolah semuanya melonjak dan mencetak `nan` di kolom event.
- **Dua angka forecast miss bukan konflik.** 0,0947 adalah median atas 145 SKU yang dapat
  order, 0,1277 median atas 600 SKU. Dua-duanya benar. Yang salah labelnya, dan sekarang
  jawabannya menyebut kedua populasi, ticker konsol menyebut populasi mana yang ditampilkan,
  dan label "forecast error" menjadi "forecast miss" sesuai kontrak bahasa.
- **`integration_audit` diperkuat, bukan dilonggarkan.** Check itu mensyaratkan ada minimal
  satu keputusan ber-event, yang mengunci perilaku salahnya. Sekarang ia menguji dua arah:
  kalau ada event di horizon, ramp-nya harus sampai ke ukuran order. Kalau tidak ada, ramp
  ditanya langsung untuk peak di dalam horizon dan harus mengembalikan lebih dari 1,0
  (hasilnya 1,36x).

### Diverifikasi

- Enam gate hijau: `ui_lang_gate` 9 file, `ui_truth_gate` 45 angka 0 gagal, `ui_system_gate`
  rc=0, `ui_answer_gate` 12 jawaban, `integration_audit` 11/0, `test_cases` ok.

### Catatan

- Konsekuensi yang perlu diputuskan operator: dengan tanggal yang benar, horizon 30 hari dari
  11 Oktober 2026 tidak memuat event Indonesia sama sekali, jadi jawaban Q2 ("apa yang perlu
  ditambah stoknya karena spike bulan depan") kini berbunyi jujur bahwa tidak ada event di
  horizon itu, bukan menampilkan lonjakan Imlek yang palsu.

## [Belum dirilis] - 2026-10-18 (f)

Operator melihat hasil pass sebelumnya dan bertanya "berarti console ga perlu? atau gimana
sih". Jawabannya: halaman ringkasan memang jadi nyaris kosong setelah kotak tanyanya
dipindah, isinya cuma penunjuk ke halaman lain dan footer dua angka. Duplikatnya belum
hilang, cuma berpindah bentuk.

### Diubah

- **Satu halaman depan, bukan dua.** `/` sekarang menyajikan halaman console itu sendiri,
  yang isinya ticker status hidup, tabel SKU, dan kotak tanya. Halaman ringkasan lama
  (`web/index.html`) dihapus, dan `/chat` dialihkan 307 ke `/` supaya tautan lama tetap
  hidup. Navigasi turun dari empat entri jadi tiga: Console, Loop map, Agent panel.
  Sebelumnya "Ask the agents" dan "Console" menunjuk ke dua halaman berbeda untuk pekerjaan
  yang sama, dan itu sumber kebingungannya.
- **Gate menyesuaikan**: `ui_truth_gate` memeriksa `/`, `/panel`, `/loop` (dari 47 angka
  jadi 45, karena dua angka footer ikut terhapus bersama halaman lama), `ui_system_gate`
  memeriksa tiga file halaman.

### Diverifikasi

- Enam gate hijau, dan permukaan tanya diukur dari halaman yang disajikan: `/` 200 dengan
  satu input, `/chat` 307, `/panel` 0 input, `/loop` 0 input, `/demo` 1 input (sampel
  halaman juri, sengaja).
- Diuji di browser sungguhan dengan mengetik pertanyaan lalu menekan Send: jawabannya
  muncul di halaman, berlabel DECISION AGENT, enam SKU dengan nomor PO, nilai, dan alasan
  masing-masing. Navigasi terbaca tiga tautan. Ticker berbunyi "145 orders placed, 96%
  placed without a person, 6 waiting for a person, 91.2% share of the order delivered,
  9.5% forecast error".

## [Belum dirilis] - 2026-10-18 (e)

### Diubah

- **Satu tempat bertanya, satu jalur jawaban.** Pertanyaan yang sama punya kotak di halaman
  ringkasan, di tab panel agen, dan di console, dilayani dua endpoint berbeda: `/api/ask`
  menjawab dari template dan `/api/reason` menanya model, jadi satu pertanyaan bisa punya
  dua jawaban berbeda tergantung tombol mana yang ditekan, dan hanya jalur model yang bisa
  mengaku tidak punya jawaban. Sekarang satu jalur: `/api/ask` mengambil fakta dari artefak
  lalu meminta gpt-5.4 menulis jawabannya. `/api/reason` jadi nama kedua untuk jalur yang
  sama supaya sampel di halaman demo tetap jalan. Kotak tanya di halaman ringkasan dan tab
  panel dihapus, berikut CSS mati dan dua fungsi yang cuma melayaninya.
- **Tidak ada yang disave.** Setiap panggilan membaca ulang artefak dan menanya model lagi.
  Yang tetap menulis ke disk hanya state, yaitu approval dan artefak rantai.
- **Fakta ikut dikirim bersama jawaban.** Kalau modelnya tidak bisa dihubungi, responsnya
  membawa `answer: null`, alasannya, dan faktanya, dan console menampilkan fakta itu.
  Template yang dipresentasikan sebagai jawaban model akan jadi kebohongan.

### Diperbaiki

- **Dua tombol panel memang mati.** Tombol "Ask" di tab panel memanggil `askQ()` dan
  `reasonQ()`, dan tidak satu pun fungsi itu ada di file itu, jadi tombolnya tidak pernah
  bekerja.
- **Angka salah karena labelnya salah.** Tombol "Waiting for a person" mengembalikan 455
  SKU, karena intent-nya menyaring keputusan yang ditahan sekaligus yang dieskalasi.
  Approval queue isinya enam order, dan keenam SKU itu tidak ada di himpunan yang ditahan.
  Jawabannya sekarang memisahkan keduanya: enam menunggu orang, lengkap dengan order,
  nilainya, dan alasan tiap satunya, dan 455 ditahan yang tidak perlu dilihat siapa pun.
- **`SIZE` bocor ke pembaca** sebagai kata "size", karena tabel padanan hanya tahu dua kode
  yang lain.
- **Model yang terlihat mati.** Konsolnya service systemd user (`pasok-web.service`,
  enabled) dan drop-in `10-sap.conf` membawa kredensial SAP. Setiap server yang dijalankan
  manual di sesi ini tidak punya variabel itu, jadi `/api/reason` menjawab "SAP AI Core
  unreachable" padahal service-nya bisa. Membunuh prosesnya juga tidak berefek karena
  systemd langsung menyalakannya kembali, dan itulah yang membuat server basi terus
  memegang port. Restart yang benar: `systemctl --user restart pasok-web`.

### Diverifikasi

- Enam gate hijau: `ui_lang_gate` 9 file bersih, `ui_truth_gate` 47 angka 0 gagal,
  `ui_system_gate` rc=0, `ui_answer_gate` 12 jawaban bersih, `integration_audit` 11/0,
  `test_cases` ok.
- Lewat service yang jalan: `/api/ask` `source=model`, `gpt-5.4-2026-03-05`, 4 sampai 5
  detik, angka persis seperti di file. `/api/chat` dijawab model. `/api/reason` menjawab.
- Permukaan tanya diukur dari halaman yang disajikan: `/` 0 input, `/panel` 0, `/chat` 1,
  `/demo` 1 (halaman demo sengaja tetap punya sampel modelnya sendiri).

## [Belum dirilis] - 2026-10-18 (d)

Operator membaca konsolnya sendiri dan menemukan jawaban agennya berbunyi seperti ini:
"0 of them run out before the next delivery can arrive, so the shortfall is real", dengan
`nan`, `HOLD_ONE_CYCLE`, `->` dan `17521.3u` di sekitarnya. Permintaannya: "saya gamau ada
jargon jargon gitu di dalam jawabannya maupun di web ini, saya mau responnya tuh yang
dibutuhkan aja, benar benar informasi nyata".

### Ditambahkan

- **`docs/PLAIN_LANGUAGE.md` - kontrak bahasa untuk semua yang dibaca orang.** Dua aturan
  isi (jawab yang ditanya lalu berhenti, jangan mengklaim lebih dari yang dibawa angkanya),
  satu larangan keluaran mesin (`nan`, enum, `->`, `u`, `x1.40`, titik koma), satu tabel
  padanan untuk istilah yang tetap dipakai proposal, dan tabel kalimat untuk keempat nilai
  action yang tersimpan.
- **`tools/ui_answer_gate.py`** - memeriksa 12 jawaban (termasuk kasus yang salah: SKU yang
  tidak ada, PO yang tidak ada, event yang tidak dikenal) terhadap kebocoran mesin, jargon
  dan pengisi. Halaman diperiksa `ui_lang_gate.py`, jawaban diperiksa gate ini, karena
  jawaban dibangun di Python dan tidak pernah lewat HTML.

### Diubah

- **Prompt model ditulis ulang** (`src/sap/rationale.py`). Prompt lama menyebut dirinya
  asisten dan mengirim label berjargon ("Sellable now", "Velocity", "learned supplier lead
  time p90"), dan model memakai ulang kata yang dikirim ke ia, jadi jargon masuk kembali
  keluar dari mulutnya. Prompt baru menyebut pembacanya (orang yang membeli stok, punya 60
  baris lain menunggu), urutannya (keputusan dulu, angka kedua, sisanya tidak ada), dan
  label yang dikirim sekarang berbunyi "Available to sell now", "Sells per day",
  "Worst-case delivery time from this supplier". Nomor barisnya kini ditulis untuk orang.
- **Keenam jawaban plus tiga jawaban lain** jadi kalimat, bukan dump kolom. `nan` menjadi
  `none`, `HOLD_ONE_CYCLE` menjadi "no order this cycle, the stock on hand already covers
  the horizon", `->` hilang, `17521.3u` menjadi `17,521 units`, share menjadi persen
  (`0.850` menjadi `85.0%`), dan kolom tabel berbunyi "available now", "sold per day",
  "days of stock left", "delivery time".
- **Kalimat yang bertentangan dihapus.** Stockout menjawab "0 ... so the shortfall is
  real", yang menyimpulkan kebalikan dari angkanya. Sekarang: berapa yang kehabisan, dan
  berapa di antaranya kehabisan sebelum kiriman berikutnya bisa datang.
- **Rationale keputusan** (`src/agents/decision.py`) yang dulu satu baris dipisah titik
  koma berisi `cover 17.0d (lead p90 6.0d + review 7d + buffer 4d)` sekarang tiga kalimat
  yang menjelaskan ukuran ordernya, apa yang bisa dijual SKU itu, dan kenapa tidak ada
  order.
- **`ui_lang_gate.py` sekarang juga menolak jargon**, bukan cuma bahasa Indonesia, kode
  mesin dan pemisah. Satu frasa dikecualikan dengan sengaja: "Order stability guardrails",
  nama kontribusi di proposal sendiri.

### Diverifikasi

- `tools/ui_answer_gate.py` - 12 jawaban bersih.
- `tools/ui_lang_gate.py` - daftar kerja nyata untuk halaman (loop.html 18, chat.py 14,
  panel.html 3, app.py 2, live.py 2), dikerjakan di pass terpisah.
- `run_chain.sh` dijalankan ulang setelah rationale berubah: 600 SKU, 145 order, 6
  menunggu, angkanya **identik** dengan sebelum perubahan. Teks berubah, angka tidak.
- Diukur lewat HTTP pada server yang benar-benar jalan, bukan dari file.

### Catatan

- Dua kali konsol menyajikan teks lama bukan karena cache, tapi karena proses basi masih
  memegang port 8090 sehingga server baru gagal bind. `ss -ltnp | grep 8090` menyebut PID
  yang benar-benar melayani, dan `ps -ef | grep uvicorn` bisa menyesatkan. Pakai `pkill -f`
  lalu pastikan PID-nya.
- Gate bahasa hari ini salah empat kali dan selalu gate-nya, bukan halamannya. Pelajaran
  yang sama terulang di gate jawaban: "SAP RPT-1.6" itu nama produk yang dipakai juri,
  bukan singkatan, dan "so" hanya pengisi kalau membuka kalimat.

## [Belum dirilis] - 2026-10-18 (c)

Hackathon-nya dinilai dalam bahasa Inggris dan presentasinya bahasa Inggris, sementara
konsolnya berbahasa Indonesia. Operator juga meminta tampilannya lebih bersih: "gausah
terlalu banyak penjelasan yang ga perlu, kan itu nanti ada di presentasinya, ini web
agentnya loh, bukan presentasi".

### Ditambahkan

- **`tools/ui_lang_gate.py` - gate bahasa, menggantikan `ui_text_gate.py`.** Yang lama
  melarang istilah Inggris di konsol Indonesia, jadi arahnya dibalik: sekarang yang
  dilaporkan adalah sisa kata Indonesia, kode mesin yang tercetak ke pembaca
  (`ESCALATED`, `HOLD_ONE_CYCLE`, `WAPE`), em dash dan titik koma di teks yang tampil,
  serta angka yang masih digrup gaya Indonesia. Stripping-nya sama dengan gate lama,
  karena bagian yang sulit bukan daftar katanya melainkan memisahkan teks yang sampai ke
  layar dari teks yang cuma sampai ke pembaca kode.
- **`docs/ENGLISH_PASS.md`** - kontrak sekali pakai: dua aturan pemangkasan, tabel
  kosakata tetap, aturan tanpa em dash dan titik koma, dan daftar kunci `data-fig`.

### Diubah

- **Seluruh teks yang tampil jadi bahasa Inggris**, di lima halaman dan di
  `pasok_answers.py` (jawaban agen, yang selama ini jadi sebab produk setengah
  diterjemahkan: halamannya sudah bersih sementara jawabannya masih Indonesia).
- **Prosa penjelasan dihapus.** Yang dibuang adalah kalimat yang menerangkan apa itu
  sistemnya, kenapa ada, atau bahwa angkanya dari file, plus baris pemasaran di footer
  dan catatan yang mengulang fakta yang sudah ada di judul. Yang tetap: label, judul
  kolom, angka, satuan, tombol, dan state kosong, memuat, serta error yang menyebut
  sebab dan langkah berikutnya.
- **Angka di peta `/loop` diikat ke artefak.** Peta itu masih membawa angka dua generasi
  lalu (562 order, 507 otomatis, 55 nunggu manusia, 384 kena pembatas, 507 tanda terima)
  dan gate kebenaran tidak menangkapnya karena halaman itu tidak punya ikatan sama
  sekali. Sekarang 27 `data-fig` dipasang, dan gate kebenaran mengecek 47 angka, dari 16.
- **Format angka jadi Inggris** di `figures.py` (`458,861`, `0.959`, `IDR 7.56M`),
  termasuk `snapshot_line()` menjadi `Snapshot 11 October 2026 - 600 SKUs`.
- **`web/app.py`**: label enam tombol pertanyaan masih Indonesia di `ROUTES` dan
  disuntikkan ke halaman; sekarang labelnya Inggris pendek.

### Diperbaiki

- **`/api/trace` 500 untuk setiap SKU yang ditahan.** `src/agents/one_pass.py`
  mengasumsikan tiap SKU punya purchase order, jadi `po[po["sku"] == sku].iloc[0]`
  melempar `IndexError` untuk SKU yang ditahan, dan SKU yang ditahan itu justru jawaban
  paling umum. Sekarang langkah 4 dan 5 jadi hasil yang dinyatakan ("no purchase order",
  alasan keputusannya dikutip apa adanya), dan pengecekan di akhir skrip hanya berlaku
  untuk SKU yang dipilih otomatis, karena operator boleh menyebut SKU mana saja.
  Diverifikasi tiga jalur: SKU0536 ditahan, SKU0422 punya order, dan auto-pick.
- **`chat.py`: label fallback `"Agen"`** masih Indonesia dan bisa tampil, kini `"Agent"`.
- **`web/app.py`: pesan error `/api/reason`** memakai titik koma yang dibaca user.

### Diverifikasi

- `tools/ui_lang_gate.py` - kesembilan file bersih, "All visible text is English".
- `tools/ui_truth_gate.py` - 47 angka, 0 gagal.
- `tools/ui_system_gate.py` - rc=0. `integration_audit.py` - 11 lulus, 0 gagal.
  `py_compile` bersih untuk `web/*.py`, `pasok_answers.py`, `src/agents/one_pass.py`.
- Browser sungguhan, kelima halaman: teks yang dirender Inggris, masthead
  `Snapshot 11 October 2026 - 600 SKUs`, dan tidak ada `Edisi 1`, `28 Desember 2025`,
  `>562<`, `>507<`, `>384<`, `>137<` yang tersisa di HTML yang disajikan.
- `/api/trace/SKU0536` 200. `/api/ask?q=What runs out this week` menjawab Inggris.

### Catatan

- Gate bahasa gagal empat kali sebelum benar, dan tiap kali yang salah gate-nya, bukan
  halamannya: `panel` itu kata Inggris yang sah, satu grup angka (`458.861`) sama
  bentuknya dengan desimal Inggris (`0.959`), titik koma dari entitas `&nbsp;`, dan
  sepasang tanda kutip di JS bisa menangkap kode di antara dua string lalu melaporkan
  titik koma sebagai prosa. Prosa asli kelima halaman diukur terpisah: nol titik koma,
  nol em dash.
- `ui_text_gate.py` dihapus, digantikan `ui_lang_gate.py`. Rujukan lamanya di
  CHANGELOG dan catatan fase tetap sebagai riwayat.
- Tiga temuan pipeline masih belum disentuh, sama seperti sebelumnya: kalender event
  belum lewat 2025, dua angka WAPE median yang berbeda, dan halaman ini sendiri.

## [Belum dirilis] - 2026-10-18 (b)

Konsol terlihat seperti empat produk berbeda. Operator memakainya lalu melaporkan:
"pindah tab itu kayak pindah page, tampilannya beda banget", dan alas putihnya sendiri
"jelek". Diukur, keempat halaman memang tidak sepakat: kotak isinya 980px, 860px,
1080px, 1080px, skala judulnya 16, 17, 24px, dan masthead `/loop` ada di dalam kotak
isi sehingga lebar kepalanya berubah saat pindah halaman. Isi halaman bergeser 110px.

### Tambahan

- **`tools/ui_system_gate.py` - gate bentuk, bukan kata atau angka.** Statis, tanpa
  browser: satu stylesheet bersama, tidak ada max-width sendiri, masthead tidak di
  dalam kotak isi, tidak ada selector telanjang (`nav {`, `header {`) yang menembus
  keluar halaman, satu permintaan font, dan tidak ada sisa tema terang atau muka lama.

### Diubah

- **Konsol pindah ke sistem halaman demo.** Palet demo dipakai apa adanya (ground
  `#1c1c1c`, surface `#262626`, ink `#f1f1ef`, aksen `#8fa68e`, radius 0) dan mukanya
  Bricolage Grotesque, dengan IBM Plex Mono tetap untuk catatan. Halaman juri dan
  halaman operator sekarang satu produk.
- **`pasok.css`: satu kontainer, satu masthead, satu skala judul.** `.sheet` dan `.wrap`
  dideklarasikan bersama di `--page-width: 1080px` dengan satu gutter, masthead jadi
  penuh dengan gutter sendiri, dan dua tingkat judul didefinisikan sekali (`h2` untuk
  bagian, `.card h2, #out h2, .answer h2` untuk di dalam kotak).
- **Masthead `/loop` keluar dari `<main class="sheet">`.** Sebelumnya kepalanya 984px
  di halaman itu dan 1440px di tiga halaman lain.
- **Tiga aturan halaman yang bocor ke chrome bersama.** `nav { }` di `panel.html` juga
  menata masthead nav dan membuatnya rata kiri, jadi jadi `.tabs`. `header { }` di
  `index.html` menambah padding di atas padding masthead, dibuang. `footer { }` di
  `index.html` memaku gutter 22px, dibuang.
- **Warna SVG peta loop** (7 literal `oklch` terang) dan sisa tema terang di `chat.html`
  diganti token gelap.

### Diperbaiki

- **Kontras di halaman demo.** Diukur di browser atas 687 simpul teks: 16 gagal, kini 0.
  Tiga yang nyata: kartu order di dalam lapangan terang mewarisi tinta hampir hitam
  lapangan itu (`#1c1c1c` di atas `#262626`, rasio 1.13, praktis tidak terbaca), label
  batang puncak terang di atas batang aksen terang, dan label bulan tidak punya latar
  yang dideklarasikan. Pemisah `·` di konsol naik dari 1.77 ke 6.6.

### Diverifikasi

- Diukur di browser 1440: keempat halaman konsol melaporkan `bg rgb(28,28,28)`, muka
  Bricolage Grotesque, `--color-paper #1c1c1c`, `--color-accent #8fa68e`, `--radius 0px`,
  kotak isi 1080 di kiri 180, masthead 1440 di kiri 0, tanpa overflow.
- `ui_system_gate.py` rc=0. `ui_truth_gate.py` 16 angka 0 gagal. `ui_text_gate.py`
  bersih. `integration_audit.py` 11 lulus 0 gagal.

### Catatan

- `ui_system_gate.py` gagal di jalan pertamanya dan gate-nya yang salah: permintaan font
  menulis muka sebagai `Bricolage+Grotesque`, jadi pemeriksaannya mencocokkan spasi
  dengan plus. Diperbaiki di gate, aturannya tidak dilonggarkan.
- `/loop` menolak screenshot full-page dengan "Cannot take screenshot with 0 width",
  sebelum dan sesudah perubahan ini. DOM-nya bersih (`bodyScrollW` 1440), dan tangkapan
  viewport berhasil. Tercatat supaya tidak dikejar sebagai bug layout dua kali.
- Tidak ada angka pipeline, artefak, atau angka di layar yang berubah.

# Changelog

Semua perubahan penting pada repo Pasok dicatat di sini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan proyek ini memakai penanggalan berbasis versi.

## [Belum dirilis] - 2026-10-18

Halaman web tertinggal dari perbaikan angka 15 Oktober. Perbaikan itu menyinkronkan
`demo/*.md` ke artefak, tapi tidak menyentuh `web/`, jadi layar masih memuat dua
kebenaran lama sekaligus: empat halaman konsol menulis "rekaman 28 Desember 2025"
sementara datanya sudah 2026-10-11, dan `demo.html` masih mengutip 137 order, 130
otomatis, 7 nunggu manusia, saat loop sudah mengeluarkan 145/139/6.

### Ditambahkan

- **`web/figures.py` - satu sumber kebenaran untuk setiap angka di layar.** Halaman
  tidak lagi memuat angka di markupnya; ia memuat penanda, dan server mengisinya dari
  artefak saat request. Tiga bentuk penanda: `<!--SNAPSHOT-->` untuk baris edisi,
  `data-fig="kunci"` untuk satu angka, `<!--LEARN_BARS-->` untuk grafik batang.
  Tidak ada fungsi di sini yang mengarang angka; kalau artefaknya hilang, nilainya
  jadi `n/a` dan gate-nya gagal.
- **`tools/ui_truth_gate.py` - gate kebenaran layar.** Mengambil halaman dari server
  yang hidup, lalu memastikan setiap `data-fig` sama dengan artefaknya, baris edisi
  sama dengan snapshot, tidak ada penanda yang lolos ke response, tiap halaman
  memuat tepat satu stylesheet Google Fonts, dan tidak ada nav liar. Keluar 1 kalau
  ada temuan, jadi bisa dipasang di pre-commit.

### Diubah

- **Baris edisi di empat halaman konsol (`index`, `chat`, `loop`, `panel`).**
  Tanggal bertulis tangan "28 Desember 2025" diganti penanda yang diisi dari
  `decision_summary.json`. Sekarang keempatnya membaca "11 Oktober 2026".
- **`web/demo.html`: 16 angka diikat ke artefak.** Fragmen konsol (SKU dinilai, order
  keluar, nilai order), enam tile bukti, dan satu angka uji (0,0898 salah ramal
  SKU0421) sekarang diisi dari file, bukan diketik. Nilai lamanya (137, 130, 7,
  0,949, 80, 437.960, 7,71 M) diganti dengan yang ada di disk (145, 139, 6, 0,959,
  83, 458.861, 7,56 M).
- **Grafik batang `demo.html` dibangun dari `learn_curve.csv`.** Dua belas batang
  dengan tinggi dan label bertulis tangan diganti dua belas bulan terakhir yang
  dibaca dari artefak (25-11 sampai 26-10), plus caption yang menyebut file sumbernya.
- **`web/loop.html` kembali ke satu design system.** Nav ganda di atas masthead
  dibuang (href-nya bahkan menunjuk /chat dengan label "Peta loop"), permintaan font
  kedua (Fraunces, IBM Plex Sans, JetBrains Mono) dihapus, dan 20-an `font-family`
  di dalam SVG dikembalikan ke muka bersama (Newsreader, Switzer, IBM Plex Mono).
  Lebar lembar disamakan ke 1080.
- **`web/index.html`: kontrol dan badan jawaban masuk sistem.** Dua tombol `Tanya`
  dan `Tanya model` sekarang memakai `.btn` (sebelumnya default browser), badan
  jawaban pindah dari monospace 14px `pre-wrap` ke Newsreader 15px, dan dua warna
  keras (`#f3eee7`, `#5c3a21`) diganti token. Kedua tombol kini ikut ter-disable saat
  satu permintaan berjalan, bukan hanya tombol pertama.

### Diperbaiki

- **`demo.html` berhenti bisa di-scroll ke samping.** Dua sebab, keduanya sudah
  ada sebelum perubahan ini: `.proof` memakai `repeat(4, 1fr)` dan track `fr`
  punya lantai selebar min-content isinya, jadi satu tile yang lebar memaksa dua
  dari empat kolom jadi 916px dan grid-nya lari 884px keluar layar (dokumen jadi
  2804px). Sekarang `repeat(4, minmax(0, 1fr))`, keempat kolom 454px. Dan bentuk
  bleed di hero (`right: calc(var(--margin) * -1)`) memelintir dokumen 40px lagi,
  karena halaman ini memuat stylesheet-nya sendiri dan tidak ikut mendapat
  `overflow-x: clip` dari `pasok.css`. Ditambahkan `html, body { overflow-x: clip }`
  di halaman ini (clip, bukan hidden, supaya nav sticky tidak rusak).
  Diukur di browser: `bodyScrollW` 1920 sama dengan lebar viewport, tile
  [916, 454, 454, 454, 454, 454, 454].
- **`tools/ui_text_gate.py`: dua false positive.** Penanda HTML (`<!--SNAPSHOT-->`)
  dibaca sebagai teks yang tampil, dan subscript bersarang (`_CURVE[-1]["wape"]`) lolos
  dari aturan "baca kolom CSV". Keduanya kini dibersihkan sebelum pencocokan, jadi
  `figures.py` terbaca bersih tanpa melemahkan aturannya.

### Diverifikasi

- `tools/ui_truth_gate.py` - 0 gagal, 16 angka dicek di lima halaman.
- `tools/ui_text_gate.py web/` - exit 0, sembilan file bersih.
- `tools/integration_audit.py` - 11 lulus, 0 gagal (tidak ada regresi).
- Browser sungguhan: `/loop` nav 1 (dari 2), font link 1 (dari 2), font SVG
  Newsreader/Switzer/IBM Plex Mono; `/` badan jawaban Newsreader 15px; `/demo`
  fragmen dan tile membaca 145/139/6/Rp 7,56 M/0,959/83/458.861.

### Catatan

- `web/figures.py` diimpor saat proses start, jadi mengubahnya butuh restart
  `pasok-web`; mengubah file halaman cukup reload.
- Tiga temuan di luar lingkup web, belum disentuh: kalender event belum maju ke
  2026/2027 (jawaban "lonjakan dalam sebulan" menyebut Imlek 2026-01-30, di luar
  jendela), `learn_summary.json` menulis WAPE median 0,0947 sementara median
  `wape_best` di `baselines.csv` 0,1277, dan STATE.md masih menulis 137 order.

## [Belum dirilis] - 2026-10-15

### Diperbaiki

- **Working tree disinkronkan balik ke HEAD.** Sembilan file tracked masih memuat
  versi pra-perbaikan 12 Oktober: `src/demand/registry_catalog.py` (Nyepi ditandai
  "not modelled", dua exclusion barat hilang), `run_chain.sh` (kembali ke path
  absolut), `aws/GATES.md` (resep mint Bedrock hilang), `.gitignore` (ignore
  `.env` / `*.pem` / `*.key` / `credentials.json` hilang), `data/sap/*`, dan tiga
  dokumen `demo/*.md`. Efeknya build melaporkan 137 order dan WAPE 0.0852 padahal
  HEAD sudah 145 order dan 0.0947. Semua direstore dari HEAD.
- **`data/catalog/events.csv` di-regenerate.** Artefaknya masih 259 baris tanpa
  Nyepi, THR dan Payday, sementara `generate.py` (identik dengan HEAD) menulis 433.
  Karena itu overlay event cuma bisa menembak lima dari delapan driver dan tiga
  rampa tidak pernah menyala. `generate.py` lalu `run_chain.sh` dijalankan ulang;
  seluruh `data/` sekarang byte-identik dengan HEAD.
- **`web/app.py` tidak lagi menelan error handler.** `/api/reason` mencetak
  "SAP AI Core unreachable" untuk semua kegagalan, termasuk proses service yang
  memegang state basi. Sekarang error asli dari handler disurface.

### Diubah

- **`aws/lambda/pasok_agent/handler.py`: SAP AI Core jadi jalur utama.** `ask_sap`
  memakai endpoint chat `.../chat/completions?api-version=2024-12-01-preview` pada
  deployment `$SAP_CHAT_DEPLOYMENT` dan mengembalikan `{provider, text}`; Bedrock turun
  jadi fallback karena akun tim kena gate.
- **Angka demo disinkronkan ke artefak.** F12/F13 (1.31x -> 0.36x, -72.6%), F27
  (0.9119), F28 (0.0947), dan order split (145/139/6) di `demo/figures.md`,
  `demo/slides_outline.md`, `demo/script_en.md`, `demo/evals.md`, `demo/a2a.md`,
  dan `demo/architecture.md`. Angka lama dibiarkan hanya di catatan fase sebagai
  riwayat, ditandai superseded.

### Verifikasi

- `bash run_chain.sh` -> `CHAIN OK`, 145 PO, 139 SENT / 6 HELD_FOR_APPROVAL.
- `tools/integration_audit.py` -> 11 passed / 0 failed.
- `tools/test_cases.py` -> TC-1 8/8, TC-2 145 order.
- `tools/ui_text_gate.py web/` -> rc=0, bersih.
- `curl /api/ask` -> 200 dengan angka terkini; `curl /api/reason` -> 200,
  `provider: sap-ai-core/$SAP_CHAT_DEPLOYMENT`.

## [Belum dirilis] - 2026-10-16

### Ditambah

- **`web/demo.html` - halaman demo Demo Day.** Tampilan jalannya loop
  replenishment dengan status tiap tahap, permintaan persetujuan manusia,
  dan alasan keputusan dalam bahasa manusia.
- **`tools/ui_text_gate.py` - gate teks UI.** Sken sederhana yang membaca
  **hanya teks yang benar-benar kelihatan user**, bukan isi kode. Sengaja
  diabaikan: komentar HTML, isi `<script>`, nama variabel/class/method,
  key dict, baca kolom CSV (`r["wape"]`), argumen keyword mesin, dan
  anotasi tipe di dalam signature `def`. Yang disken: istilah Inggris dan
  jargon agen yang tidak boleh muncul di layar (Decision, Demand, Order
  Executor, rampa, Mercanine, Cicatricine, dan kawan-kawan). Keluar dengan
  exit code 1 kalau ada temuan, jadi bisa dipasang di pre-commit / CI.

### Diubah

- **Seluruh teks UI jadi bahasa Indonesia** - gaya "operator warung pakai
  AI", bukan bahasa marketing. Ini yang paling terasa di:
  - `web/panel.html`: tile bahan jadi Permintaan, Posisi stok, Keandalan
    supplier, Keputusan, Eksekusi, Antrian, Notifikasi, Belajar; template
    jejak agen jadi "1 - Baca / Agen Posisi Stok"; header run jadi
    "keluar otomatis" / "naik ke manusia".
  - `web/chat.py` dan `web/live.py`: tabel tahap agen (STAGES, STEPS) dan
    pemetaan intens jadi bahasa Indonesia.
  - `web/chat.html`: caption dan catatan bawah chart jadi bahasa Indonesia
    ("Salah ramal per bulan").
  - `web/loop.html`: 9 label `<text>` di SVG, aria-label, dan paragraf
    penjelas tiap panah ("Permintaan -> Keputusan lewat baselines.csv").
    "Rampa" diganti "Kenaikan" supaya tidak terdengar jargon internal.
  - `web/demo.html`: status dan alasan persetujuan manusia jadi kalimat
    manusia (contoh: "499,0 M > batas otomatis 200 M" jadi kalimat yang
    dibaca orang, bukan keluaran mesin).
  - `web/index.html`: status pill dan footer.

### Diperbaiki

- **Repo kembali stand-alone.** Working tree tanpa sengaja ter-reset balik
  ke path absolute lama `/home/ubuntu/agentic_ai_pasok/`, sementara HEAD
  sudah dipindah ke path relatif. Akibatnya 39 file tracked kembali memuat
  path lama dan 3 unit systemd (`pasok-web`, `pasok-mcp`, `pasok-a2a`)
  menunjuk direktori yang sudah tidak ada - service gagal start kalau
  di-deploy. 39 file itu direstore dari HEAD (versi relatif), dan 4 referensi
  basi yang masih ada di HEAD sendiri dibetulkan manual:
  `experiments/convert_m5.py`, `experiments/e2_event_ramp.py`,
  `briefing_demo_day.md`, `agentcore/EVIDENCE.md`, serta file untrack
  `agentcore/retry_deploy.sh`. Diverifikasi: tidak ada lagi referensi ke
  path lama di repo.

### Diverifikasi

- `tools/ui_text_gate.py web/` - exit 0, bersih.
- `python -m py_compile web/*.py experiments/convert_m5.py` - lolos.
- Semua route hidup: `/`, `/panel`, `/chat`, `/loop`, `/demo` - HTTP 200.
- Cek di browser sungguhan (bukan cek file): teks yang tampil di kelima
  halaman bersih dari istilah Inggris dan jargon yang dilarang.

### Catatan

- Masih ada perubahan lain yang belum di-commit dari sesi kerja sebelumnya
  (jalur SAP AI Core di `aws/lambda/pasok_agent/handler.py`, regenerasi
  `data/`, dan restrukturisasi `.gitignore`). Sengaja tidak ikut di commit
  ini karena bukan bagian dari pekerjaan di atas.
