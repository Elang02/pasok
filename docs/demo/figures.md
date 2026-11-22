# Pasok — Reproducible Figures

Every number the Demo Day script quotes must appear here, next to the exact command
or file that regenerates it. **A figure absent from this sheet must not be spoken.**

Full local pipeline: `bash run_chain.sh` (7 steps, deterministic, no accounts).

| # | Figure (as spoken) | Value | Source artefact | Regenerate with |
|---|---|---|---|---|
| F1 | Unguarded bullwhip amplification | 2.68x demand variance | `simulation/results.json` → `unguarded.amplification` | `cd simulation && <venv>/bin/python replenish_sim.py` (seed 20260905) |
| F2 | Guarded bullwhip amplification | 0.24x demand variance | `simulation/results.json` → `guarded.amplification` | same as F1 |
| F3 | Fill rate, unguarded | 0.9893 | `simulation/results.json` → `unguarded.fill_rate` | same as F1 |
| F4 | Fill rate, guarded | 0.9868 | `simulation/results.json` → `guarded.fill_rate` | same as F1 |
| F5 | Simulation horizon | 250 days (30 warmup) | `simulation/results.json` → `days`, `warmup` | same as F1 |
| F6 | Event-ramp WAPE (all 30,490 M5 series) | 0.0775 | `experiments/e2_results.json` → `E2a_event_ramp.overall_wape.ramp` | `python experiments/e2_event_ramp.py` (seed 20261008) |
| F7 | Flat-bump baseline WAPE | 0.1161 | `experiments/e2_results.json` → `E2a_event_ramp.overall_wape.flat_bump` | same as F6 |
| F8 | Event-ramp improvement vs flat-bump | +33.25% | `experiments/e2_results.json` → `improvement_pct.ramp_vs_flat_bump_pct` | same as F6 |
| F9 | Event windows tested | 154 | `experiments/e2_results.json` → `E2a_event_ramp.windows_tested` | same as F6 |
| F10 | Catalog size | 600 SKUs | `data/agents/decision_summary.json` → `n_skus` | `run_chain.sh` step 2 |
| F11 | Orders placed | 137 | `data/agents/decision_summary.json` → `orders_placed` | same as F10 |
| F12 | Guarded amplification, live replay | 0.35x (raw 1.30x) | `data/agents/decision_summary.json` → `amplification` | same as F10 |
| F13 | Amplification reduction | −72.8% | `data/agents/decision_summary.json` → `amplification.reduction_pct` | same as F10 |
| F14 | Auto-issued orders | 130 | `data/orders/order_summary.json` → `auto_issued` | `run_chain.sh` step 4 |
| F15 | Escalated orders | 7 | `data/orders/order_summary.json` → `escalated` | same as F14 |
| F16 | Total order value | IDR 7,707,789,750 | `data/orders/order_summary.json` → `total_value_idr` | same as F14 |
| F17 | Auto-issue limit | IDR 200,000,000 | `data/orders/order_summary.json` → `auto_limit_idr` | same as F14 |
| F18 | Escalation triggers | 5 above limit · 0 over credit · 0 supplier switch · 2 MOQ · 0 candidate event · 0 demand shock | `data/orders/order_summary.json` → `escalation_reason_breakdown` | same as F14 |
| F19 | Sellable composition | on-hand 5,624,563 + in-transit 731,231 + open PO 4,524,559 = 10,880,353 u | `data/stock/position_summary.json` → `sellable_composition` | `run_chain.sh` step 1 |
| F20 | SKUs carrying an open PO / in-transit | 347 / 104 | `data/stock/position_summary.json` → `sellable_composition` | same as F19 |
| F21 | Buffer model | z90·√(lead_var² + forecast_err²), min 2 d, capped by shelf life; 0 SKUs capped | `data/agents/decision_summary.json` → `buffer_model` | `run_chain.sh` step 2 |
| F22 | Buffer, erratic vs reliable principal | P02 (fill 0.84) 5 d vs P03 (fill 0.98) 4 d | `data/agents/decision_summary.json` → `buffer_model.per_principal` | same as F21 |
| F23 | Principal notifications | 130 SENT / 7 HELD | `data/orders/notification_summary.json` → `by_status` | `run_chain.sh` step 5 |
| F24 | Excess stock redirected | 412 SKUs, IDR 19,085,275,501 protected of IDR 34,607,884,420 at risk | `data/orders/redirect_summary.json` | `run_chain.sh` step 6 |
| F25 | Supplier-switch proposals | 5 (P02/P05/P06/P07→P01, P08→P03) | `data/orders/supplier_switch_summary.json` | `run_chain.sh` step 3 |
| F26 | Learn step — decisions scored | one row per PO | | `data/agents/learn_summary.json` → `score_distribution` | `run_chain.sh` step 7 |
| F27 | Observed fill rate (network) | 0.9126 | `data/agents/learn_summary.json` → `observed_fill_rate_mean` | same as F26 |
| F28 | Held-out forecast WAPE (live catalog) | 0.0852 median | `data/agents/learn_summary.json` → `forecast_wape_best_median` | same as F26 |
| F29 | RPT-1.6 agreement | 0.72 | Phase 4 run log | batch predict over 600 SKUs, 2 batches |
| F30 | Rationales produced by gpt-5.4 | 40 / 40 | `data/sap/rationales.csv` → `source=orchestration` | `src/sap/rationale.py` |
| F31 | Loop cycle-over-cycle readings | 823,200 | `data/agents/learn_curve.csv` | `run_chain.sh` step 7 |
| F32 | Loop monthly WAPE range (46 months) | 0.1237 .. 0.7494 | `data/agents/learn_summary.json` → `learning_curve` | same as F31 |
| F33 | Event-month concentration of worst error | 8 of top-8 | `learn_curve.csv` vs `data/catalog/events.csv` | cross-check `demo/evals.md` |
| F34 | AWS brain served by Bedrock | `bedrock-mantle/moonshotai.kimi-k2.5` | Lambda `ask` response | `aws/GATES.md` |
| F35 | Ramp classes learned per SKU x event | ramped 1,328 / step 1,672 | `data/demand/ramp_summary.json` → `ramp_class_counts` | `run_chain.sh` step 2 |
| F37 | Orders submitted to the ordering system | 130 submitted, 130 accepted partial, 0 refused | `data/orders/intake_summary.json` | `run_chain.sh` step 5 (`order_intake.py`) |
| F36 | Decision action vocabulary | SIZE / HOLD_ONE_CYCLE, then AUTO_ISSUE / ESCALATE / REDIRECT | `data/agents/decision_summary.json` → `action_counts` + `order_summary.json` + `redirect_summary.json` | `run_chain.sh` steps 2/4/6 |

## Notes

- **F1–F5** official baseline (Bank Indonesia retail sales index, seed 20260905).
- **F6–F9** differentiator on the public M5 dataset, **all 30,490 series aggregated** (leave-one-occurrence-out, 154 windows).
- **F10–F28** the live four-agent build on the synthetic distributor catalog
  (snapshot 2025-12-28), regenerated by `run_chain.sh`.
- **F29–F30** the SAP AI Core lane (Phase 4).
- **F31–F33** the learn step as a monthly curve over the full 36-month walk: the
  worst-error months are all event months (Ramadan / Lebaran / Chinese New Year /
  year-end), the quietest months are outside every event window.
- **F34** the AWS lane answers with Amazon Bedrock; SAP AI Core remains the fallback.
- F18's `candidate_event` and `demand_shock` are **0 in this snapshot** because every
  SKU's uplift matches a registered event; the trigger logic is wired and fires on
  novel uplift (documented in `06-06-SUMMARY.md`).
- Claim-to-artefact map for every proposal line: `demo/evals.md`.
- AWS gate status and reproduction commands: `aws/GATES.md`.
