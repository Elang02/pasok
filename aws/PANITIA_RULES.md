# Apa yang panitia suruh (dari PDF panitia)

Sumber: `sources/panitia_pdfs/participant_briefing.pdf` (Participant Briefing, 11 Sep 2026)
dan `sources/panitia_pdfs/student_account_setup.pdf` (ID Hackathon 2026 Student Account Setup Guide).

## Yang panitia SURUH pakai: **Free plan**, bukan Paid

Setup Guide, Step 2 langkah 6:

> "Choose the **Free plan** and basic support. Read the plan details shown during
> signup. Free Tier does not make every AWS service free. New accounts receive
> USD $100 in AWS credits on signup, plus up to USD $100 more by completing
> getting-started activities (up to USD $200 total) — use these to stay within
> your budget."

Dan peringatan eksplisit:

> "**Do not create AWS Organizations for the hackathon.**"

Alasannya (dari AWS docs): Free plan **otomatis naik ke Paid** kalau kamu bikin
AWS Organizations, Control Tower, join APN, atau bikin kontrak Professional
Services / Enterprise Agreement.

Jadi aturan panitia = **tetap Free plan**. Dan akun ini sekarang PAID — itu yang
harus dibereskan.

## Step 2 AWS budget alerts (persis yang panitia minta)

1. Buka **Billing and Cost Management → Budgets**
2. Create budget → monthly cost budget template
3. Nama: **`IDHackathon-Monthly`**, isi jumlah yang disetujui panitia
4. Isi email yang kamu cek tiap hari
5. Alerts di **50%, 80%, 100%** + tambahan **forecasted alert**
6. Create budget

Panitia bilang keras:

> "Budget alerts are warnings, **not hard stops**. Billing data can be delayed and
> AWS resources continue running after an alert. Check spending every day and
> delete resources when you finish using them."

## Step 2 Secure the AWS account

- Root MFA **wajib**
- Bikin IAM user **`StudentAdmin`** (AdministratorAccess + MFA), pakai itu untuk
  kerja harian, root hanya untuk billing/recovery
- Satu region saja (yang diumumkan waktu training)
- **IAM Identity Center tidak diperlukan**, jangan bikin AWS Organizations

## Cara kontrol biaya (verbatim dari panitia)

- Pakai satu AWS Region
- Bikin resource seperlunya saja
- Pilih ukuran terkecil yang cukup
- Stop/delete compute, database, notebook, endpoint begitu selesai
- Cek Billing tiap akhir hari

## Rubrik Demo Day (31 Okt, BINUS Alam Sutera, 15 menit per tim termasuk Q&A)

- Working Solution & Demo — 20%
- **Technical Execution & Use of AWS/SAP — 25%**
- Innovation & Originality — 20%
- Problem-Solution Fit & Impact — 20%
- Presentation & Storytelling — 10%
- Q&A — 5%

Agentic aspects yang harus ditonjolkan: Plan, Reason, Act/Tool, Review,
Orchestration/Workflow, Human in the loop, Responsible AI.

Stack yang panitia sebut: AWS (Kiro, AgentCore, Bedrock), SAP (Joule, AI Core,
AI Launchpad). Tapi FAQ Q1: **stack sendiri (mis. LangChain) BOLEH**, demo boleh
via Joule atau agent lain (Strands, Quick). Integrasi A2A/MCP/REST boleh.

## Kontak

- Ferry Mulyadi — [kontak panitia] (AWS Hackathon Lead)
- Whye Loong Wong — [kontak panitia] (AWS Hackathon Co-Lead)
