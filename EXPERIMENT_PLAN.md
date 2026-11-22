# EXPERIMENT PLAN - ReplenishAgent (Road to Glory, 1-30 Okt 2026)
*Grounded in FINAL_PROPOSAL.md + REVIEW_SUMMARY.md · 5 Sep 2026*

## Prinsip

Semua eksperimen menjawab klaim dari FINAL_PROPOSAL (C1-C4), bukan ekplorasi terbuka. Angka anchor dari simulasi internal (2,7x vs 0,23x) divalidasi ulang pada demand retail publik supaya klaim tidak berdiri di atas simulator sendirian. Simplicity check (C3) wajib - kalau 1 agen monolitik sama bagusnya, cerita berubah; lebih baik kita temukan sendiri sekarang daripada juri.

## E1 - Anchor result (C1): guardrail effectiveness [PRIORITAS 1]

- **Setup**: reorder agent (forecast smoothing -> order sizing -> damping -> cap) di atas demand sintetis 250 hari, 3 profil (stabil ABCX, volatil XYZ-Z, musiman Ramadan-like). Metrik: variance amplification Var(order)/Var(demand), fill rate, holding cost.
- **Lari**: (a) tanpa guardrail; (b) smoothing saja; (c) + damping; (d) full guardrail; (e) full + cap.
- **Gate lanjut**: full guardrail menjaga amplifikasi <= 2,0 pada semua profil DAN fill rate tidak turun > 0,5 poin vs (a). Kalau gagal -> perbaiki damping coefficient, jangan tambah komponen.
- **Metrik event window (profil Ramadan-like)**: laporkan TERPISAH dua angka - (i) amplifikasi di luar event window (target ~1,5x, baseline claim), (ii) tracking ratio di dalam event window = Var(order)/Var(demand termasuk surge) + rasio order aktual vs kurva (target mendekati 1, tanpa order-overhang pasca-event). Ini memisahkan klaim guardrail (feedforward stabil) dari perilaku event (feedforward tracking), sehingga klaim proposal tidak over-extend.

## E2 - Novelty isolation (C2): bukan cuma "LLM-nya yang bagus" [PRIORITAS 1]

- **Setup**: demand yang sama, bandingkan (a) policy klasik (s, S) deterministik; (b) LLM agent TANPA guardrail; (c) LLM agent + guardrail.
- **Gate**: (c) > (a) pada metrik service-cost gabungan, dan (c) >> (b) pada stabilitas. Kalau (a) >= (c): proposal harus jujur repositioning - nilai utama ada di eksekusi + auditability, bukan keunggulan keputusan. (Ini info penting, bukan kegagalan.)

## E3 - Simplicity check (C3): 4 agen vs 1 monolitik [PRIORITAS 2]

- **Setup**: satu prompt monolitik melakukan seluruh loop vs orkestrasi 4 agen (AgentCore multi-agent collaboration). Bandingkan kualitas keputusan (crossover error rate vs policy ground-truth), auditability (kelengkapan rationale), dan biaya token.
- **Gate**: orkestrasi menang minimal di auditability & consistency; kalau tidak -> sederhanakan arsitektur proposal (masih bisa menang via cost & clarity).

## E4 - Data reality (C4): M5 public data + injeksi pola Indonesia [PRIORITAS 2]

- **Data**: M5 Forecasting (Walmart, 3.049 item x 10 toko, publik di Kaggle) sebagai demand riil; subsample 2.500 series untuk mirror scale pilot. Suntikkan pola: spike akhir pekan panjang (Idul Fitri shift ±11 hari antar tahun, long weekend), musim hujan.
- **Setup**: jalankan E1 penuh di atas data ini; laporkan amplifikasi & service level per kelas ABC-XYZ.
- **Gate**: guardrail tetap <= 2,0x amplifikasi pada >= 80% kelas; klaim proposal direvisi ke rentang yang terukur di sini.

## E5 - Frontier necessity check

- **Frontier primitive** (LLM): test eksplisit LLM kecil (Nova Lite class) vs LLM besar pada Decision Agent reasoning; kalau kecil cukup -> proposal makin murah & feasible (student budget angle). Non-frontier components (statistical forecast, ERP MCP tools) tidak butuh justification tambahan.

## Run order, budget, decision gates

1. E1 (2-3 hari kerja, CPU only, synthetic) -> gate C1
2. E2 (1-2 hari, same harness) -> gate C2
3. E3 (perlu kredensial AgentCore; paralel dengan E4 data prep) -> gate C3
4. E4 (download M5 via Kaggle API ~1 GB; run E1 harness) -> gate C4
5. E5 (tersier, hanya kalau waktu tersisa)

Total budget komputasi: CPU lokal + Bedrock free tier/credits hackathon. Semua hasil masuk `refine-logs/EXPERIMENT_TRACKER.md`.

## Mitigasi risiko eksperimen

- Simulator bias -> M5 sebagai data eksternal (E4) menutup celah "klaim di atas simulator sendiri".
- AgentCore access belum aktif di Road to Glory -> E1/E2/E4 jalan full di harness lokal (policy-identik), E3 ditunda sampai credits cair; proposal tidak bergantung pada E3.
