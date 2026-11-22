# REVIEW SUMMARY - ReplenishAgent
*5 Sep 2026 · 3 reviewer internal (novelty, feasibility, rigor)*

## Landscape terverifikasi (10+ sumber dibaca 5 Sep 2026)

| Sumber | Fokus | Beda dari kita |
|---|---|---|
| **Long, Simchi-Levi et al., arXiv 2605.17036 (Mei 2026)** | MIT Beer Game, agent bullwhip + decision bullwhip, GRPO post-training buat stabilisasi | Mereka diagnose masalah yang sama, solusi mereka RL post-training (berat); kita guardrail inference-time (ringan, deployable). Kita SITAT & posisikan diri sebagai jalur pragmatis. |
| **Timtong & Pannakkong, ACM APIT 2026 (Jul 2026)** | Decision-support LLM agent buat SME e-commerce Thailand; case study 1 SME; compare experience-based vs (Q,r) vs agent; trade-off procurement efficiency vs penalty | Domain online-platform penalty; output rekomendasi ke owner (human-in-command penuh). Kita: offline trade Indonesia, agen EKSEKUSI PO dengan guardrail, bukan sekadar rekomendasi. |
| Jannelli & Brintrup, IJPR 2025 | Protokol konsensus antar agen LLM | Bukan eksekusi; kita orkestrator + guardrail. |
| InvAgent (Quan & Liu 2024) | Zero-shot LLM 1 agen/node, gaya beer game | Tanpa stabilitas order; kita 4 agen per fungsi + guardrail. |
| Syed et al. 2025 (arXiv 2511.23366) | Negosiasi multi-agent, mart generik | Domain + mekanisme beda. |
| JD.com SCPA | Agen pembuat LAPORAN; manusia eksekusi | Kita agen eksekusi + human on exception. |
| BCG (Jun 2026), Dataiku (Feb 2026), olimp (Sep 2026) | Konsensus industri: 2026 tahun agentic supply chain; hype vs "disciplined operational execution" | Mengkonfirmasi timing & framing "execution > insight" kita. |
| Bullwhip klasik (Lee et al. 1997) + VMI/damping literatur | Amplifikasi variansi klasik | Grounding teori; kita tambah lapisan agen-LLM. |

## Verdict: **READY** (dengan 2 catatan wajib)

Kekuatan: problem anchor konkret dan Indonesia-specific; mekanisme smallest-adequate; satu kontribusi dominan; landscape terbaru (Mei-Jul 2026) sudah dipetakan dan posisi jelas.

Catatan wajib sebelum submit:
1. Angka 2,7x/0,23x WAJIB dilabel "dari simulasi kami" (bukan klaim universal) di proposal.
2. Tambahkan kalimat positioning terhadap Long et al. di bagian guardrails - menunjukkan kita tahu state-of-the-art Mei 2026 dan memilih jalur inference-time yang deployable. Ini MENINGKATKAN kredibilitas di mata juri, bukan melemahkan.

## Re-evaluasi pasca-literatur 12 sumber (5 Sep, lihat LITERATURE_DIGEST.md)

Naik:
- Orisinalitas bertahan vs 4 tetangga terdekat; trade-credit headroom = differentiator yang tak ada di literatur LLM-agent manapun.
- Problem statement terdokumentasi (nanostore POMS; IPSSJ; Bulog) - bukan cerita karangan.

Turun / risiko baru (jujur):
1. Simulasi 2,7x/0,23x berjalan TANPA fitur event-ramp + shelf life yang kini dijanjikan proposal. Klaim MVP = bukti guardrail, BUKAN bukti event learning. Kalau ditanya, jawab jujur: itu Road-to-Glory build (E4 M5).
2. Scope Road-to-Glory membengkak utk tim 3 orang. Prioritas demo: E2 (novelty isolation) + event-ramp learner di M5. Batch expiry/FEFO & credit headroom = desain-terjelaskan, bukan wajib-demo.
3. Baseline OR (YQ/MILP, truncated balancing) optim utk perishables - E2 menjadi eksperimen TERPENTING: kalau policy sederhana menyamai agen di baseline demand, nilai agen harus dari event+eksekusi+audit. Jalankan jujur.
4. Event-ramp learning sendiri BUKAN baru di OR (kalender feature klasik). Yang diklaim: integrasi end-to-end + guardrail + eksekusi. Jangan klaim ramp learning sebagai penemuan.
5. Validasi = data AS + injeksi pola Indonesia (sintetis). Jawaban jujur ada di pilot distributor; IPSSJ/Bulog jadi penopang realisme pola.

Skor kasar vs kriteria: Innovation kuat, Use of AWS/SAP kuat, Impact terkuantifikasi, Feasibility menengah-tinggi (staged). Lolos top-40: probabilitas tinggi. Top-3 track: ditentukan eksekusi demo Road-to-Glory, bukan dokumen.
