# FINAL PROPOSAL (Refined) - ReplenishAgent
*Pipeline run: 5 Sep 2026 · Track: Intelligence Supply Chain · Agentic AI Hackathon 2026*

## Problem Anchor

Distributor FMCG menengah di Greater Jakarta (2.500 SKU aktif, 400 warung/outlet, tim sales rute harian) mengambil keputusan reorder dengan spreadsheet: reorder point tetap per SKU, safety stock tahun lalu, lead time tiga hari berdasar tebakan. Demand per SKU volatil dan asimetris (spike akhir pekan panjang, geser Ramadan, musim hujan), jadi keputusan flat selalu salah dua arah: fast mover kehabisan (stockout) dan slow mover menumpuk sebagai modal kerja terikat. Data untuk keputusan yang lebih baik sudah ada di sistem (invoice per outlet, penerimaan barang per principal), tetapi ERP berhenti di laporan - manusia masih harus membaca alert, menimbang trade-off, dan menaruh PO. Dengan 2.500 SKU, review manusia maksimal mingguan; demand tidak menunggu review.

**Final Method Thesis (satu kalimat)**

**Empat agen LLM spesialis (demand, posisi stok, reliabilitas pemasok, keputusan) di Amazon Bedrock AgentCore yang mengeksekusi reorder rutin dengan antrean pengecualian manusia, belajar kurva ramp event (Imlek, Lebaran, dll) per SKU dari data historis sendiri, dan ditahan guardrail stabilitas order berbasis dampened feedback yang menjaga amplifikasi variansi demand di bawah 2x.**

## Dominant Contribution

**Order-stability guardrails pada agen reorder otonom** - mekanisme di layer keputusan (perataan forecast sebelum sizing, damping order terhadap order sebelumnya, cap per order) yang menjaga variansi order keluar gudang mendekati variansi demand masuk. Hasil simulasi 250 hari: 2,7x amplifikasi tanpa guardrail vs 0,23x dengan guardrail, tanpa kehilangan service level. Ini menjawab temuan terbaru bahwa agen LLM menderita *decision bullwhip* (Long et al., arXiv 2605.17036, Mei 2026): ketidakstabilan keputusan stokastik agen itu sendiri memperbesar variansi order bahkan saat demand konstan, dan averaging berulang TIDAK menyembuhkannya - yang dibutuhkan adalah mengubah kebijakan keputusan, persis yang dilakukan guardrail kita di inference-time tanpa perlu RL post-training.

## Complexity Intentionally Rejected

1. **RL post-training (GRPO)** seperti Long et al. - tidak masuk akal untuk tim mahasiswa dalam window lomba; guardrail inference-time mencapai tujuan stabilisasi yang sama pada level yang berbeda dan kami sebutkan ini sebagai future work.
2. **Multi-echelon** - satu echelon (distributor), bukan rantai beer-game; scope pilot nyata dan terukur.
3. **LLM sebagai forecaster** - forecast numerik tetap di model statistik klasik (terbukti untuk SKU stabil); LLM hanya me-reason di atasnya (ABC-XYZ, kepercayaan sinyal, trade-off). Kami menolak modernisasi yang tidak meningkatkan hasil.
4. **Negosiasi antar agen** - 4 agen per fungsi kolaboratif, bukan 1 agen per node yang menawar.

## Key Claims + Must-Run Ablations

- **C1 (anchor)**: Guardrail memegang amplifikasi variansi <= 1,5-2x dengan fill rate tetap dalam 0,5 poin, rata-rata cover turun dari 22 ke 2,5 hari. Ablasi: tanpa smoothing, tanpa damping, tanpa cap, full guardrail.
- **C2 (novelty isolation)**: Keunggulan berasal dari guardrail + eksekusi, bukan sekadar "pakai LLM". Ablasi: policy sederhana (s,R) tanpa LLM vs pipeline penuh, pada demand yang sama.
- **C3 (simplicity check)**: 4 agen > 1 agen tunggal monolitik. Ablasi: satu prompt monolitik vs orkestrasi 4 agen, ukur kualitas keputusan & auditability.
- **C4 (data reality)**: Pipeline tetap benar pada demand retail nyata (M5/Walmart, 3.049 item x 10 toko) dengan pola Indonesian trade (spike akhir pekan panjang, pergeseran Ramadan) disuntikkan.

## Remaining Risks

- **Verifikasi empiris C1 di luar simulasi kami sendiri**: Long et al. memberi precedent bahwa decision instability nyata, tetapi angka 2,7x/0,23x milik simulasi internal kami. Mitigasi: eksperimen M5 dijadwalkan sebagai Road-to-Glory deliverable, angka disajikan sebagai "our simulation", bukan universal claim.
- **Ketergantungan jury reading**: dua sumber kunci (ACM APIT 2026 Thai SME; Long et al.) membuktikan field-nya panas; proposal harus membedakan diri pada *execution + stability*, bukan klaim "pertama kali".
