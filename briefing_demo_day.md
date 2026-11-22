# Pasok - Demo Day Briefing (reconstructed 2026-10-08)

> REKONSTRUKSI: file asli hasil distilasi deck 11 Sep 2026 hilang saat migrasi.
> Isi di bawah diambil dari distilasi tersimpan di skill reference (sokrates-agentic-ai-hackathon-2026.md).

## Demo Day rubric + rules — dari Participant Briefing deck (11 Sep 2026)

Briefing deck disimpan di `/home/ubuntu/pasok/briefing_demo_day.md`. Yang menentukan strategi build:

**Rubrik Demo Day (total 100%):**
1. Technical Execution & Use of AWS/SAP — **25%**
2. Working Solution & Demo (live functional prototype) — **20%**
3. Innovation & Originality — **20%**
4. Presentation & Storytelling (butuh architecture diagram) — **20%**
5. Problem-Solution Fit & Impact (pain point + quantified value) — **10%**
6. Q&A / Ability to Defend — **5%**

Final rank = rata-rata skor juri, tiap juri bobot sama. **45% bergantung pada live demo + pemakaian
AWS/SAP yang benar**, jadi prototipe yang jalan mengalahkan slide. Wajib tampilkan eksplisit:
Plan · Reason · Act/Tool · Review · Orchestration/Workflow · Human in the loop · Responsible AI.

**Format final:** 15 menit per tim termasuk Q&A · **bahasa INGGRIS** (juri internasional) ·
Track A Supply Chain 20 tim, Track B Manufacturing 20 tim · offline di BINUS Alam Sutera 31 Okt.

**FAQ yang mengubah asumsi (verbatim, dari deck):**
- Stack sendiri (mis. LangChain) BOLEH, integrasi via A2A/MCP/REST. Demo boleh lewat Joule atau agen lain.
- **Data sintetis BOLEH**, asal realistis dan relevan dengan use-case. Ini melegalkan pendekatan BI-index + M5.
- MVP minimal: agent yang bisa planning, reasoning, tool execution. **Agent orchestrator = poin tambahan.**
- **Di Demo Day semua finalist WAJIB mengumpulkan demo + presentasi sebagai artefak event.**
- Build window: 21 Sep – 31 Okt 2026 (setelah finalist diumumkan).
- Use-case BOLEH berubah dari proposal "asal ada justifikasi dan penjelasan yang jelas" → ini yang
  melegalkan framing jujur "event-ramp = Road to Glory build".

**Mentoring (1–30 Okt):** 100% voluntary, "ZERO influence on judging or final score" → jangan
over-invest. Submit pertanyaan via Smartsheet Senin 5/12/19/26 Okt sebelum 16:00 GMT+7. Hanya 10 tim
 dapat slot Zoom, 4 × 30 menit, Rabu sore, first-come-first-served.

**Resource yang harus diklaim:** AWS Skill Builder · AWS Free Tier accounts · **Kiro Free** ·
**AWS Workshops** (Agentic AI via Kiro / Quick / **Strands Agent**, **Bedrock AgentCore**, **MCP Servers**
— paling relevan dengan arsitektur Pasok). **AWS Student Rewards** ($579 value, $0): Verified + 7 + 14 + 21
badges → 12 bulan Skill Builder Premium ($449) → $10 credits → $20 credits → $100 exam voucher; badge dari
artikel/komentar/daily streak/vote di AWS Builder Center; reward pertama ~2 minggu, voucher ujian ~90 hari;
ujian: CLF-C02 atau AWS Certified AI Practitioner.
SAP Learning Hub Student Edition (2 ujian sertifikasi gratis/tahun, verify via SheerID).
SAP learning assets yang punya PRACTICE SYSTEM cuma dua: **Joule Studio Resource Hub** dan Learning Journey
"Solving your business problems using prompts and LLMs in SAP's Generative AI Hub" — sisanya self-paced tanpa
environment, jadi kurang berguna untuk build. Course Joule yang tersedia: Introducing Joule · Joule Studio in
SAP Build · Joule for Consultants · Discovering High-Value Opportunities for Agentic AI · Joule for Business
Users · Implementing Joule across Your Organizational System Landscape · **Designing Agentic Systems with a
Human-Centered Approach** (ini yang menyuplai elemen "Human in the loop" yang wajib ditonjolkan di rubrik).
Ada juga Faculty/Classroom Guides (Joule Studio, SAP-RPT Playground) + **Mentoring and Office Hours**.
**SAP BAIP sub-account: REQUEST** — tanpa itu Joule Studio Agent Builder tidak tersedia (Pro-Code CLI +
AI Core tetap ada). Kontak: Ferry Mulyadi ([kontak panitia], Hackathon Lead), Whye Loong Wong
([kontak panitia], Co-Lead).

**Kiro student benefit (1.000 credits/bulan) = TIDAK berlaku untuk tim ini** (verified 2026-09-25 di
`kiro.dev/students`). Syaratnya DUA, bukan satu: (1) 18+ mahasiswa di accredited college/university,
(2) kampus terdaftar di **daftar resmi eligible-schools** (133 kampus, 16+ negara). **Binus University
satu-satunya kampus Indonesia di daftar itu**; Unika Atma Jaya tidak ada. Dua catatan lama di file ini
saling bertentangan dan yang menyatakan "Unika eligible" itu SALAH: kalimat umum di setup guide
("accredited college/university") hanya syarat perlu, daftar kampus yang mengikat. Yang realistis:
**Kiro Free = 50 credits/bulan**, plus **bonus credits hackathon** dari registrasi Smartsheet
(`tinyurl.com/id-attend`) yang terbuka untuk semua tim. Minta kampus ditambahkan lewat form
"Don't see your school listed?" pakai email kampus.

**Form registrasi/attendance yang masih hidup:** `https://tinyurl.com/id-attend` (dari deck hands-on lab,
jalur **bonus Kiro credits**) dan `https://tinyurl.com/59u9af3f` (dari briefing deck, jalur Q&A) — keduanya
resolve ke **form Smartsheet yang SAMA**: `app.smartsheet.com/b/form/01a06a11ffac723489120abc9f2c3f89`
("Attendance Sheet 3 for AI Agentic Hackathon"). Satu registrasi menutup dua-duanya.

## Akun/akses yang benar-benar dibutuhkan (verified 2026-09-25)
