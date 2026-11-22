# LITERATURE DIGEST - Supply Chain (Global + Indonesia)
*5 Sep 2026 · buat pertahanan Demo Day, bukan semua masuk proposal*

## Peta sumber → insight → implikasi desain

| # | Sumber | Temuan inti | Implikasi buat ReplenishAgent |
|---|--------|-------------|-------------------------------|
| 1 | Long et al., arXiv 2605.17036 (MIT, Mei 2026) | Agent bullwhip: instabilitas keputusan agen memperbesar variansi order; averaging tidak menyembuhkan | Guardrail kita (smoothing+damping+cap) = jawaban inference-time; sudah diposisikan |
| 2 | Winkelmann et al., PLoS ONE 2026 (e-grocery perishable) | Spoilage itu STOKASTIK (suhu, handling), bukan cuma deterministic shelf life; lookahead policy; "value of probabilistic information" = panduan ketidakpastian mana yang worth dimodelkan | Stok harus granular per BATCH expiry (bukan total per SKU). Data ERP: batch/expiry wajib ada di MVP. Kalau batch data kotor → spoilage dimodelkan stochastic |
| 3 | Pauls-Worm, diss. Wageningen 2016 | Kontrol inventory perishable dgn demand non-stationary; kebijakan YQ (MILP); trade-off availability vs waste; ~1/3 makanan dunia terbuang (FAO) | Mengkonfirmasi desain staggered delivery barang pendek; forecast harus ROLLING (non-stationary) → loop belajar kita tepat |
| 4 | Double-batch policy, EJOR-track 2026 | Umur simpan lebih panjang ≠ otomatis order lebih besar; batch/cycle length interplay | Decision Agent jangan sederhanakan ke "shelf life panjang = aman order banyak" |
| 5 | MSOM 2023, Truncated Balancing (platelet) | State-of-art kebijakan order barang shelf-life sangat pendek | Referensi kalau juri tanya "policy optimalnya apa" — kita inference-time guardrail, bukan MILP, dan itu pilihan sadar |
| 6 | Escamilla, Fransoo, Tang, POMS 2021 (nanostore, 50jt toko global) | 5A nanostore supply chain; TRADE CREDIT = jantung ekonomi warung; credit line distributor ke warung & principal ke distributor | **Design addition**: Decision Agent harus menimbang headroom kredit per principal — order besar pra-event makan tempo kredit; jangan cuma holding cost |
| 7 | Chandra et al., IPSSJ (Prasetiya Mulya, data FMCG ID 2023) | Fluktuasi musiman FMCG Indonesia: naik tajam saat hari raya/libur, turun saat musim hujan & normal; solusi: persediaan adaptif, prediksi berbasis data | Validasi lokal problem statement; penulisnya mahasiswa Indonesia = sinyal riset ini fresh & relevan buat juri; kutip di Demo Day, tidak perlu masuk 3-halaman |
| 8 | Bulog AR 2025 + Sido Muncul AR | Bukti institusional: demand Ramadan mendorong lonjakan komoditas (April 2024) & produk herbal | Backup empiris event ramp Lebaran kalau digugat |
| 9 | Deloitte "Resilient by design" (Mar 2026) | Agentic SC: eksekusi otonom end-to-end + ELEVATE human roles | Framing "supervised autonomy" kita sejalan dengan narasi industri global |
| 10 | GEP/Accenture 2026 (early-warning procurement) | Risk sensing: sinyal eksternal (berita, cuaca, pasar) untuk deteksi dini | FUTURE WORK Supplier Reliability Agent v2 — keluar scope MVP, jangan dipromisakan |
| 11 | ACM APIT 2026 (Thai SME) | LLM decision-support inventory SME; rekomendasi, bukan eksekusi | Pembeda utama kita: eksekusi + guardrail (sudah di proposal) |
| 12 | InvAgent, Jannelli IJPR 2025, JD.com SCPA | Satu agen/node; protokol konsensus; agen pelapor | Sudah terpetakan di REVIEW_SUMMARY |

## Yang harus diantisipasi (checklist desain hasil bacaan)

1. **Batch-level expiry** — stok per SKU + tanggal kedaluwarsa per batch; FEFO saat mengeluarkan barang; markdown otomatis sebelum expiry. (Winkelmann; Pauls-Worm)
2. **Spoilage stochastic** — kalau data batch kotor, model kerusakan sebagai probabilistik, bukan tanggal pasti. (Winkelmann)
3. **Post-event trough** — turunnya permintaan setelah event = risiko overstock/markdown; kurva decay sudah di desain, pastikan dieksekusi di simulasi E1. (perishables lit)
4. **Trade credit / arus kas** — batas tempo kredit principal membatasi ukuran & timing order pra-event; warung bayar tempo → piutang distributor membengkak pasca-Lebaran. (POMS nanostore) → MASUK proposal sebagai "credit headroom"
5. **Demand non-stationary** — rolling relearn, jangan forecast sekali jalan. (Pauls-Worm)
6. **Ramadan & musiman terdokumentasi institusional** — Bulog/Sido Muncul/IPSSJ sebagai amunisi tanya-jawab. 
7. **Agen bisa panik** — guardrail + pengukuran amplifikasi (Long et al.) — sudah.
8. **Manusia dinaikkan perannya, bukan dihapus** — Deloitte; konsisten "supervised autonomy".

## Keputusan scope
- MASUK proposal: credit headroom (1 frasa di Decision Agent).
- TIDAK masuk (budget halaman): FEFO/markdown detail, MILP/YQ, risk sensing eksternal, sitasi IPSSJ/Bulog → tersimpan di file ini buat Demo Day.
