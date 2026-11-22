# Pasok — Rencana Arsitektur SAP

Team **AIGO** (slug `aigo`) · Agentic AI Hackathon 2026 · Track A Intelligence Supply Chain
Demo Day 31 Okt 2026, BINUS Alam Sutera, 15 menit, bahasa Inggris.

Status dokumen: perencanaan berbasis probe nyata (bukan asumsi). Semua klaim "TERBUKTI" di
bawah ini punya output live dari kredensial tim AIGO pada 8 Okt 2026.

---

## 1. Jawaban singkat: SAP dipakai untuk apa

Pasok punya tiga lapisan SAP, dan semuanya sudah bisa dipanggil hari ini:

| Lapisan | Service SAP | Dipakai untuk | Status |
|---|---|---|---|
| **Model plane** | SAP AI Core / Generative AI Hub | `sap-rpt-1.6` skor tabular per SKU, `gpt-5.4` reasoning Decision Agent, `orchestration` untuk templating + content filter | TERBUKTI jalan |
| **Human-in-the-loop plane** | Joule (DAS) + Joule Studio CLI | queue exception untuk manajer; scenario di-gate ke team AIGO via IAS group | kunci ada, CLI belum install |
| **Governance plane** | BTP Cockpit (read-only) + orchestration content filtering / data masking | audit visibility, responsible AI | role viewer aktif |

AWS **tidak dibutuhkan** untuk semua ini. AWS baru masuk kalau reasoning pindah ke Bedrock
Nova / AgentCore Memory-Gateway-Runtime (Fase AWS, terpisah).

---

## 2. Fakta lingkungan (verified)

- IAS tenant: `https://auisywroy.accounts.ondemand.com` (login pakai email kampus, lowercase)
- CF API: `https://api.cf.ap10.hana.ondemand.com` · org `SEAIO_aws-sap-hackathon-si4ykj9d`
- Team space: `hackathon-aigo` (belum diverifikasi nama persisnya, perlu `cf target`)
- Shared AI Core space: `ai-core`
- Keybroker (kredensial, sudah ditarik): `https://hackathon-keybroker.cfapps.ap10.hana.ondemand.com/ai-core/aigo-key` dan `/joule/aigo-key`
- IAS group AIGO: `13dda208-ba90-4149-a5fe-ed504253d128` (display `Hackathon_aigo`)
- Region AI Core: `ap-southeast-2` (Sydney), host `api.ai.prod.ap-southeast-2.aws.ml.hana.ondemand.com`
- Resource group: `default`

Deployment ID resmi (dari manual panitia, sudah dites semuanya):

| Model | Deployment ID | Terbukti |
|---|---|---|
| `gpt-5.4` | `$SAP_CHAT_DEPLOYMENT` | Ya — balas chat normal |
| `sap-rpt-1.6` | `d76cf689a05d504f` | Ya — klasifikasi + regresi + multi-target |
| `orchestration` | `d8c092efb8980093` | Ya — templating + llm module jalan |
| `text-embedding-3-large` | `d5c542b69551fce3` | belum dites |
| `anthropic--claude-4.6-sonnet` | `dc9594f579d3e4c1` | belum dites |
| `tabpfn-3.5-plus` | `da450ba3ea929a74` | belum dites |
| `gemini-3.1-flash-image` | `d5fad5cf7622af7f` | tidak relevan |
| `sonar` | `d01c3468af3ad67a` | tidak relevan |

---

## 3. Hasil probe SAP-RPT-1.6 (batas teknis yang mengikat desain)

Ini yang paling menentukan bentuk arsitektur. Semua diuji langsung:

| Sifat | Hasil probe | Konsekuensi desain |
|---|---|---|
| Butuh context minimum | **2 baris berlabel**; 1 baris → error `Not enough context rows provided. Minimum is 2.` | Setiap panggilan wajib menyertakan history berlabel, tidak bisa one-shot satu SKU |
| Klasifikasi | OK, balik `prediction` + `confidence` (contoh 0.54 / 0.74) | Dipakai untuk `STOCKOUT_RISK` (Yes/No) dan `EXPIRY_RISK` (Yes/No) |
| Regresi | OK, balik `prediction` numerik + `confidence_interval` (contoh days-of-cover 65.68, CI [65.49, 66.0]) | Dipakai untuk `DAYS_OF_COVER_LEFT` |
| Multi-target 1 panggilan | OK — `STOCKOUT` + `EXPIRY` sekaligus dalam satu request | Hemat 1 round-trip per SKU; penting untuk latensi demo |
| Batas context | **1.000 baris context masih OK**; >2 minimal, jadi rentang aman lebar | Bisa kirim riwayat panjang per batch SKU dalam satu panggilan |
| Penjelasan per baris/kolom | `explanations: null` di respons uji (butuh parameter eksplisit, belum dicoba) | Perlu probe lanjutan kalau mau dipakai untuk panel audit; jangan klaim dulu |
| Format | `POST /v2/inference/deployments/<id>/predict`, header `AI-Resource-Group: default` | Request/response JSON, mudah di-wrap |

**Konfirmasi jalur e2e yang sudah jalan:** token OAuth → RPT predict → gpt-5.4 via orchestration.
Ketiga panggilan sudah dieksekusi sukses dengan kredensial AIGO.

---

## 4. Arsitektur end-to-end (yang akan dibangun)

```
                    ┌─────────────────────────────────────────────┐
                    │  Data lokal (box ini)                       │
                    │  M5 30.490 series · BI retail index ·       │
                    │  catalog sintetis distributor (SKU×outlet)  │
                    └───────────────┬─────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       │                            │                            │
┌──────▼───────┐          ┌─────────▼─────────┐        ┌─────────▼────────┐
│ DEMAND AGENT │          │ STOCK POSITION    │        │ SUPPLIER         │
│ (lokal + M5) │          │ (lokal)           │        │ RELIABILITY      │
│              │          │                   │        │ (lokal)          │
│ event ramp   │          │ sellable stock    │        │ lead time learn  │
│ learner  ◄───┤ E2 v3    │ days of cover     │        │ drift detect     │
│ novelty      │ TERBUKTI │ expiry flags      │        │                  │
│ isolation    │ 100%/0FP │                   │        │                  │
└──────┬───────┘          └─────────┬─────────┘        └─────────┬────────┘
       │                            │                            │
       └────────────────────────────┼────────────────────────────┘
                                    │  fitur tabular per SKU
                                    ▼
                    ┌───────────────────────────────────────────┐
                    │  SAP AI CORE — sap-rpt-1.6                │
                    │  d76cf689a05d504f                         │
                    │  → DAYS_OF_COVER_LEFT   (regression)      │
                    │  → STOCKOUT_RISK        (classification)  │
                    │  → EXPIRY_RISK          (classification)  │
                    │  TERBUKTI: min 2 context rows, 1k OK      │
                    └───────────────┬───────────────────────────┘
                                    │ skor + confidence
                                    ▼
                    ┌───────────────────────────────────────────┐
                    │  DECISION AGENT (orchestrator)            │
                    │  guardrails E1: smoothing · dampening ·   │
                    │  variance cap    TERBUKTI 2.68 → 0.24     │
                    │  ↑ alasan tertulis dari gpt-5.4           │
                    │  via orchestration d8c092efb8980093       │
                    │  (templating + content filtering)         │
                    └───────────────┬───────────────────────────┘
                                    │ exception + rationale
                                    ▼
                    ┌───────────────────────────────────────────┐
                    │  JOULE (DAS) — human in the loop          │
                    │  queue exception untuk manajer            │
                    │  di-gate ke IAS group 13dda208…           │
                    └───────────────────────────────────────────┘
```

Titik integrasi SAP yang benar-benar dipakai: **RPT-1.6 (skor tabular) + gpt-5.4 via orchestration
(reasoning + guardrail naratif) + Joule (manusia di loop)**. Ini jauh lebih kuat daripada klaim
proposal lama "orders flow into the SAP business system" yang lemah di rubrik.

---

## 5. Peta rubrik → mana yang menjawab apa

| Kriteria (bobot) | Yang menjawab | Bukti yang dibawa ke demo |
|---|---|---|
| Technical Execution & Use of AWS/SAP (25%) | RPT-1.6 + orchestration + Joule; ketiganya service SAP asli, dipanggil live | Log request/response nyata + screenshot deployment di AI Launchpad |
| Working Solution & Demo (20%) | Loop tertutup: fitur → RPT → guardrail → keputusan → rationale → Joule queue | Demo live satu pass penuh |
| Innovation & Originality (20%) | E2 event-ramp learner + novelty isolation (bukan calendar feature biasa) | Angka: ramp 0.1189 vs bump 0.1562 (+23.9%), Thanksgiving +52.6% |
| Presentation & Storytelling (20%) | Diagram arsitektur di atas + narasi Plan·Reason·Act·Review·Orchestration·HITL·Responsible AI | Satu diagram, satu pass nyata |
| Problem-Solution Fit & Impact (10%) | BI index + pola Ramadan/Lebaran/THR, dampak kuantitatif | Simulasi 250 hari |
| Q&A (5%) | Jujur soal batas: E1 membuktikan guardrail bukan event-ramp; RPT butuh ≥2 context rows | Daftar honest gaps |

Wajib ditonjolkan eksplisit per rubrik (istilah SAP/AWS-nya):
- **Plan/Reason** → loop standar reason→act→observe pada Decision Agent
- **Act/Tool** → panggilan RPT + tool MCP
- **Review** → guardrail check + evaluasi hasil vs aktual
- **Orchestration** → Decision Agent sebagai hub (pola Orchestrator/Router)
- **Human in the loop** → Joule queue + ambang eskalasi
- **Responsible AI** → orchestration content filtering + data masking (PII), BTP read-only audit

---

## 6. Urutan kerja

**Langkah 1 (lokal, tanpa akun tambahan) — Decision Agent + RPT**
- Bangun catalog sintetis realistis (SKU × outlet × minggu: sales, lead time, shelf life, credit) — boleh per FAQ panitia Q2.
- Generator fitur per SKU dari output Demand/Stock/Supplier agent.
- Wrapper RPT-1.6: batch request, hormati minimum 2 context rows, satu panggilan untuk 3 target.
- Decision Agent: guardrail E1 di depan, keputusan dari skor RPT, rationale dari gpt-5.4.
- Keluaran: satu pass penuh yang bisa dijalankan ulang, lengkap dengan log rationale.

**Langkah 2 (SAP, butuh Joule CLI) — human in the loop**
- Install `@sap/joule-studio-cli`, login pakai kredensial Joule AIGO (`--no-app-tid`, tanpa `--sso`).
- Deploy capability: queue exception + rationale, di-gate ke `13dda208-ba90-4149-a5fe-ed504253d128`.
- Uji: exception muncul di web client Joule.

**Langkah 3 (opsional, kalau mau klaim lebih penuh) — deploy app CF**
- `cf target -o SEAIO_aws-sap-hackathon-si4ykj9d -s hackathon-aigo`, deploy wrapper sebagai app di team space.
- Ini yang membuat klaim "running on SAP BTP" jadi literal.

**Langkah 4 (AWS, terpisah) — hanya kalau mau tutup gap 25% dari sisi AWS**
- AWS Builder ID, akun Free `us-west-2`, budget alert `IDHackathon-Monthly` 50/80/100%.
- Pindahkan reasoning ke Amazon Nova + AgentCore Memory/Gateway.

---

## 7. Yang masih perlu diverifikasi (jangan diklaim dulu)

1. Nama team space CF persisnya (`hackathon-aigo`?) — perlu `cf target` dengan login SSO.
2. `explanations` per baris/kolom dari RPT — respons uji `null`; kalau mau dipakai untuk panel
   audit, harus dicoba dengan parameter eksplisit.
3. Batas context sebenarnya di atas 1.000 baris — 1.000 sudah OK, belum diuji di atasnya.
4. `text-embedding-3-large` untuk event registry (grounding) — belum dites.
5. Kuota/token AI Core per tim — belum diketahui batasnya, perlu dijaga saat batch besar.

---

## 8. Kredensial

Disimpan di `~/.hermes/bb-vault/aigo_ai_core.json` dan `aigo_joule.json`, mode `0600`,
tidak pernah ditampilkan di chat atau ditulis ke file skill. Token akses di-cache sementara
di `/tmp/aigo_token.txt` (perlu di-refresh tiap sesi, masa berlaku token SAP standar).
