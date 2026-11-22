# Pasok — Reproducible Figures

Every number the Demo Day script quotes must appear here, next to the exact command
or file that regenerates it. **A figure absent from this sheet must not be spoken.**

Full local pipeline: `bash run_chain.sh` (deterministic, no accounts).

The table is generated, not maintained by hand: every Value below is recomputed from the
artefact in the fourth column, and `tools/figures_gate.py` fails the build when the two
disagree. After a rebuild run `.venv/bin/python tools/figures_gate.py --write` and review
the diff.

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
| F11 | Orders placed | 323 | `data/agents/decision_summary.json` → `orders_placed` | same as F10 |
| F12 | Guarded amplification, live replay | 0.32x (raw 1.25x) | `data/agents/decision_summary.json` → `amplification` | same as F10 |
| F13 | Amplification reduction | -74.1% | `data/agents/decision_summary.json` → `amplification.reduction_pct` | same as F10 |
| F14 | Auto-issued orders | 323 of 323 | `data/orders/order_summary.json` → `auto_issued` | `run_chain.sh` step 4 |
| F15 | Orders held for a person | 0, worth IDR 0 | `data/orders/order_summary.json` → `escalated`, `escalated_value_idr` | same as F14 |
| F16 | Total order value | IDR 17,411,304,275 | `data/orders/order_summary.json` → `total_value_idr` | same as F14 |
| F17 | What makes an order autonomous | the sizing policy itself: p90 lead + 7-day review + class buffer, capped by class cover (A 60 / B 60 / C 90 days). A person signs only when an order exceeds the item's own peak envelope (normal day x its best event over the days it covers); the rupiah credit line is information, not a gate | `data/orders/order_summary.json` → `policy` | `python tools/policy_gate.py` |
| F18 | Why lines wait, when they do | 0 above the item's peak envelope, 0 supplier-switch decision, 0 near-expiry hold | `data/orders/order_summary.json` → `escalation_reason_breakdown` | same as F14 |
| F19 | Sellable composition | on-hand 2,748,525 + in-transit 1,350,594.6 + open PO 2,895,274.9 = 6,994,395.5 u | `data/stock/position_summary.json` → `sellable_composition` | `run_chain.sh` step 1 |
| F20 | SKUs carrying an open PO / in-transit | 445 / 195 | same as F19 | same as F19 |
| F21 | Buffer model | z by class · sqrt(lead_var^2 + forecast_err^2), min 2 d, capped by shelf life; A 1.645, B 1.28, C 0.84 | `data/agents/decision_summary.json` → `buffer_model` | `run_chain.sh` step 2 |
| F22 | Buffer, erratic vs reliable principal | per principal, 2 to 9 days across 12 principals | `buffer_model.per_principal` | same as F21 |
| F23 | Principal notifications | 323 SENT / 0 HELD_FOR_APPROVAL | `data/orders/notification_summary.json` → `by_status` | `run_chain.sh` step 5 |
| F24 | Excess stock redirected | 502 SKUs across 5 depots | `data/orders/redirect_summary.json` → `excess_skus` | `run_chain.sh` step 6 |
| F25 | Supplier-switch proposals | 6 | `data/orders/supplier_switch_summary.json` → `proposals` | `run_chain.sh` step 3 |
| F26 | Learn step — decisions scored | 323 rows, one per PO (SUPPLY_SHORT 224, ON_PLAN 99) | `data/agents/learn_summary.json` → `score_distribution` | `run_chain.sh` step 7 |
| F27 | Observed fill rate (network) | 0.9104 | `data/agents/learn_summary.json` → `observed_fill_rate_mean` | same as F26 |
| F28 | Forecast WAPE, the SKUs this run decided | 0.1250 median on the 323 SKUs this run decided; 0.1278 across all 600 in baselines.csv | `data/agents/learn_summary.json` → `forecast_wape_best_median` | catalogue-wide figure is 0.1277 on `/loop` |
| F29 | RPT-1.6 agreement | 0.895 | `data/sap/rpt_summary.json` → `agreement_with_agent_below_reorder` | batch predict over 600 SKUs, 720 labelled context rows |
| F30 | Rationales produced by gpt-5.4 | 40 lines written by gpt-5.4-2026-03-05 via SAP orchestration, 0 template fallback (queue of 21 Oct; 0 of today's 0 held lines re-called) | `data/sap/rationales.csv` | `src/sap/rationale.py` |
| F31 | Loop cycle-over-cycle readings | 46 months in `learn_curve.csv` | `data/agents/learn_curve.csv` | `run_chain.sh` step 7 |
| F32 | Loop monthly WAPE range | 0.1003 to 0.4017, mean 0.199 | `data/agents/learn_summary.json` → `learning_curve` | same as F31 |
| F33 | Event-month concentration of worst error | 8 of top-8 | `learn_curve.csv` vs `data/catalog/events.csv` | cross-check `demo/evals.md` |
| F34 | AWS inference lane | Mantle endpoint; native Converse is account-gated | Lambda `ask` response | `aws/GATES.md` |
| F35 | Ramp classes learned per SKU x event | ramped 167 / step 425 | `data/demand/ramp_summary.json` → `ramp_class_counts` | `run_chain.sh` step 2 |
| F36 | Decision action vocabulary | SIZE / HOLD_ONE_CYCLE, then AUTO_ISSUE / DEFER / ESCALATE / REDIRECT | `decision_summary.json` + `order_summary.json` + `redirect_summary.json` | `run_chain.sh` steps 2/4/6 |
| F37 | Orders submitted to the ordering system | 323 submitted, 2 full + 321 partial, 0 refused; 1,359,792 of 1,363,622.6 units accepted (99.7%) | `data/orders/intake_summary.json` | `run_chain.sh` step 5 |
| F38 | Warehouse space | 16,098 m3 usable, 3,588.9 committed, 692.6 m3 ordered, 12,509.1 free | `order_summary.json` + `data/warehouse/capacity.json` | `python tools/build_warehouse_master.py` |
| F39 | ABC split, by consumption value | 260 A / 188 B / 152 C; A carries 80.0% of value | `data/demand/sku_classes.csv` | `run_chain.sh` step 2 |
| F40 | Replay year, agent policy on the rebuilt catalogue | 284 days, sold 52,576,986 u, lost 286,633 u (0.54%), 19,806 decided lines | `data/sim/replay2026_v18/days.csv` | `python tools/simulate.py --mode closed --name replay2026_v18 run --from 2026-01-01 --days 284` |
| F41 | The agent beside published numbers | fill A 99.9% vs 92% retail shelf availability; 22 days of inventory vs 57 at Indofood CBP; expiry 0.21% of cost vs 2.70% shrink | `data/sim/replay2026_m/days.csv` | `python tools/simulate.py --mode closed --name replay2026_m run --from 2026-01-01 --days 284` |
| F42 | Cost of the chosen policy | physical carrying IDR 1,071,910,066; financing IDR 0 at DPO 30; total IDR 1,145,710,066; lost margin IDR 36,152,344 at a 10% assumption | `data/agents/economics.json` | `python tools/economics.py --sim data/sim/replay2026_v18` |

## Notes

- **F1–F5** official baseline (Bank Indonesia retail sales index, seed 20260905).
- **F6–F9** differentiator on the public M5 dataset, **all 30,490 series aggregated** (leave-one-occurrence-out, 154 windows).
- **F10–F28, F36–F42** the live four-agent build on the synthetic distributor catalog
  (snapshot 2026-10-11), regenerated by `run_chain.sh` with the shipped defaults
  (`PASOK_CLASS_Z=A:1.645,B:1.28,C:0.84`, `PASOK_COVER_CAP=A:45,B:60,C:90`). The tighter
  pair used on 19 October (z 1.28/1.04/0.84, caps 30/45/60) produced 125 orders, 103 auto
  and 22 held; those numbers belong to that run, not to this sheet.
- **F29–F30** the SAP AI Core lane (Phase 4).
- **F31–F33** the learn step as a monthly curve over the full walk: the
  worst-error months are all event months (Ramadan / Lebaran / Chinese New Year /
  year-end), the quietest months are outside every event window.
- **F34** the AWS lane answers with Amazon Bedrock; SAP AI Core remains the fallback.
- F18 is the human queue. On this snapshot two lines wait, both held by the near-expiry
  rule: the lot would not sell before its date, so it goes to a person rather than into the
  bin. No line exceeds the item's peak envelope, carries a supplier-switch proposal, or
  trips overstock, MOQ or a demand shock. The queue was last busy on 19 October, when 22 lines waited — 21 of them past
  the class cover cap, 2 carrying a supplier switch, none on a money line. `tools/test_gates.py`
  fires the peak envelope in both directions on synthetic cases. On the current record nothing waits:
  0 of 445 wait on the snapshot; 258 of 19,806 replay orders ask for more than the item's peak can sell.
- F40/F41 are the two replays of the same 284 days on the same catalogue: the shipped agent
  policy loses 0.43 percent of demand, the manual rule it replaces loses 1.22 percent. The
  manual rule is a reconstruction (weekly review, 30 days of cover, no forecast, no event
  calendar, no shelf-life cap, no credit gate), not a recording of the distributor's
  practice, and `tools/target_measure.py` says so in `baseline_note`.
- ABC is consumption value (F39 reads 260/188/152). A holds 80.0 percent of the value in 43
  percent of the SKUs, which is why the service levels are set per class rather than per
  SKU, and why a stockout in A costs more than a markdown in C.
- Claim-to-artefact map for every proposal line: `demo/evals.md`.
- AWS gate status and reproduction commands: `aws/GATES.md`.
