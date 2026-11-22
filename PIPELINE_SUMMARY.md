# PIPELINE SUMMARY - ReplenishAgent
**Problem**: Distributor FMCG Jakarta 2.500 SKU reorder pakai spreadsheet flat -> stockout + overstock; data ada tapi tak ada layer yang mengeksekusi keputusan per SKU.
**Final Method Thesis**: Empat agen LLM di Bedrock AgentCore mengeksekusi reorder rutin dengan antrean pengecualian, ditahan guardrail stabilitas order berbasis dampened feedback yang menjaga amplifikasi variansi <= 2x.
**Final Verdict**: **READY** (dengan 2 catatan dari REVIEW_SUMMARY)
**Date**: 5 Sep 2026

## Final Deliverables
- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Refinement report: (terintegrasi di REVIEW_SUMMARY - landscape + verdict)
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Experiment tracker: `refine-logs/EXPERIMENT_TRACKER.md`

## Contribution Snapshot
- Dominant contribution: order-stability guardrails (smoothing + damping + cap) untuk agen reorder otonom - jawaban inference-time terhadap "decision bullwhip" (Long et al. 2026) tanpa RL post-training.
- Optional supporting contribution: eksekusi PO end-to-end dengan audit rationale per keputusan (beda dari framework decision-support ACM APIT 2026).
- Explicitly rejected complexity: GRPO post-training, multi-echelon, LLM-as-forecaster, negosiasi antar agen.

## Must-Prove Claims
- C1: guardrail memegang amplifikasi <= 2x tanpa turun service level (E1)
- C2: keunggulan dari guardrail + eksekusi, bukan sekadar ada LLM (E2)
- C3: 4 agen > 1 monolitik pada auditability/consistency (E3)
- C4: tetap benar pada demand publik M5 + pola Indonesia (E4)

## First Runs to Launch
1. E1a: baseline tanpa guardrail, demand sintetis stabil (harness lokal, CPU)
2. E1d: full guardrail pada demand yang sama
3. E2: (s,S) policy vs LLM+guardrail, metrik gabungan service-cost

## Main Risks
- Angka anchor dari simulator sendiri -> mitigasi E4 (M5 public data)
- AgentCore belum aktif -> E1/E2/E4 jalan lokal policy-identik; E3 menunggu credits

## Next Action
- `/run-experiment` E1 (Road to Glory, 1-30 Okt)
