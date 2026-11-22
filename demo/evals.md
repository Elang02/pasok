# Claims vs artefacts

Every quantified or specific claim in `proposal_pasok_v2_canonical.txt`, matched to the
artefact that proves it, or to an honest correction. The submitted proposal is frozen
(FAQ Q6 allows changes with justification); parity is closed by documenting the delta,
never by rewriting the proposal.

## Proven

| Proposal claim | Line | Artefact | Value |
|---|---|---|---|
| 250-day simulation, unguarded bullwhip | 27, 28 | `simulation/results.json` | 2.68x variance, fill 0.9893, 5 stockout days |
| guarded orders swing 0.24x | 27, 28 | `simulation/results.json` | 0.24x, fill 0.9868, avg inventory 274.4 |
| M5 validation of the ramp learner | 29 | `experiments/e2_results.json` | ramp WAPE 0.0775 vs flat-bump 0.1161 (+33.25%), 154 windows, **all 30,490 M5 series** |
| four-agent loop: perceive, forecast, decide, issue, learn | 21, 22 | `run_chain.sh`, `demo/one_pass.md` | full chain, `CHAIN OK`, one-pass trace on SKU0286 |
| one pass on a biscuit SKU before an event | 24 | `demo/one_pass.md`, `data/agents/one_pass.json` | SKU0286, cover 8.2d, event Payday x1.06, PO-0314 AUTO_ISSUED IDR 15,901,480 |
| real catalog scored by sap-rpt-1.6, three targets, one call | 11 (implied) | `data/sap/rpt_summary.json` | HTTP 200, 600 predictions, stockout-Yes 0, expiry-Yes 577, agreement 0.895 |
| every rationale produced by gpt-5.4 orchestration | 20 | `data/sap/rationale_summary.json` | 40/40, model gpt-5.4-2026-03-05, 0 template fallback |
| supervised autonomy: auto within limits, escalate high-stakes | 31 | `data/orders/order_summary.json` | 445 auto / 0 held of 445 decided, 120 SKUs skipped; a person sees only an order bigger than that item's own peak can absorb (normal day x its best event), never a rupiah ceiling |
| principal notification per issued PO | 22 | `data/orders/notification_summary.json` | 384 SENT / 74 HELD_FOR_APPROVAL; IDR 18.85bn notified, IDR 14.41bn held |
| redirect excess to a branch depot | 20 | `data/orders/redirect_summary.json` | 443 excess SKUs, TRANSFER and MARKDOWN lines across 5 depots, IDR 12.77bn at risk, IDR 8.95bn protected |
| guardrails: smoothing, damping, variance cap | 26 | `data/agents/decision_summary.json` | amplification 1.33x raw -> 0.36x guarded (-72.7%) |
| sellable = on-hand + in-transit + open PO | 18 | `data/stock/position_summary.json` | 3,058,578.0 + 453,747.5 + 2,716,465.3 = 6,228,789.9 u |
| buffer from forecast errors + lead-time variability, shelf-capped | 15 | `src/agents/decision.py` | `ceil(z90*sqrt(lead_var^2+forecast_err^2))`, min 2d |
| escalation on supplier switch / candidate event / demand shock | 31 | `data/orders/supplier_switch_summary.json`, `order_summary.json.escalation_reason_breakdown` | 5 switch proposals (5 pairs); on this snapshot over_credit 0, supplier_switch 0, candidate_event 0, demand_shock 0 |

## Corrected or qualified

| Proposal claim | Line | Correction |
|---|---|---|
| "planned in Kiro before any code" | 29 | No `.kiro/specs/`, no Kiro artefact exists. The planning artefact is GSD: `.planning/` in this repo, 22 phases, 67 plans with SUMMARY files. Say "planned in GSD" in the demo. |
| "validated further on the public M5 dataset (30,490 series)" | 29 | **Now literal:** the evaluation aggregates **all 30,490 series** (`n_series_aggregated: 30490`) over 154 event windows, ramp WAPE 0.0775 vs flat-bump 0.1161 (+33.25%). The earlier 500-series run was a sample; the stored artefact is the full run. |
| registry holds "Imlek, Lebaran, Nyepi, Christmas, THR weeks, payday cycles, principal promos" | 13 | The registry carries 8 rows: Ramadan, Lebaran, Imlek, Christmas, NewYear, Nyepi, THR and Payday. Six of them are holidays; THR is not one — it is the payday window that Lebaran drags with it, kept as its own row so the bonus spending lands in the weeks before the holiday rather than on it, and its dates are computed from Lebaran's, never typed. Learned ramps exist for the same 8 events (`sku_ramps.csv`, 4,800 rows, 600 per event). Principal promos **are modelled in the generator** but are not a registry row; Valentine's Day and St Patrick's Day are excluded on purpose. Full table: `data/demand/registry_catalog.csv`. | Dates for the Islamic holidays come from the tabular calendar used by the generator and can sit a day either side of the government's announcement (Lebaran 2023 is 22 April officially, 21 April here); the drift, which is what the deck shows, is unaffected.
| "a ramp it learns per SKU" | 13 | Learned and used for sizing (peak_mult read by `decision.py`). The ramped/step classification is uneven: Imlek 99.8% and Ramadan 97.0% of SKUs classify as ramped, NewYear only 17.7% and Lebaran 61.0%, because the generator gives each event its own shape rather than one shared ramp. The sizing still uses the learned peak. |
| "Bedrock Knowledge Base owns an event registry" | 13 | The registry is a file (`data/demand/event_registry.csv`); no Knowledge Base exists (Gate 3). Documented in `aws/GATES.md`. |
| "on Amazon Bedrock AgentCore" | 11 | AgentCore Runtime quota is 0 (Gate 2). The AWS lane runs on **Lambda** with the Bedrock **Mantle** endpoint as the brain, SAP AI Core as fallback. Same agent, same tools, same data. |
| "the loop finds a biscuit SKU ... eleven days before Lebaran" | 24 | The trace runs on the real snapshot (2026-10-11) and the rule selects **SKU0286**, but its registered event is **Payday** (x1.111), not Lebaran. No Lebaran window is open on the snapshot date, so the "eleven days before Lebaran" framing is illustrative; the mechanism (cover < lead, inside an event, order sized from the learned ramp) is what the trace proves. Say "a biscuit SKU whose cover runs out before the next delivery, inside a live event window". |
| "an action: auto-issue, hold one cycle, redirect to a branch depot, or escalate" | 20 | **3 of 4 actions are live, 1 fires zero times.** auto-issue 384 / hold 74 is real (`order_summary.json`), redirect fires on 443 SKUs (`redirect_summary.json`), and `hold one cycle` is emitted by `decision.py` as an explicit `action=HOLD_ONE_CYCLE` label (120 SKUs) instead of being an implicit zero order. |
| "the buffer ... reliable principals run lean, erratic ones fatter" | 15 | **Qualified.** The per-order buffer (`decision.py`, `ceil(1.28*sqrt(lead_var^2+forecast_err^2))`, min 2) is a *forecast/lead-time* buffer, not a service-level buffer, and it does not rank monotonically with supplier reliability: P06 (fill 0.833, the worst, lead sd 2.2 d) gets 4 days while P09 (fill 0.860, lead sd 0.7 d) gets 2, because the buffer follows lead-time variance, not fill rank. `supplier_reliability.csv` also carries a separate `recommended_buffer_days` (2-7) learned from fill rate, which is *not* what the orders use. Say "the buffer tracks lead-time variability and forecast error per supplier; the fill-rate-derived buffer is a separate recommendation". |
| "the next cycle starts smarter" | 22 | The learn artefacts report one 4-week window (`learn_summary.json`, recent_window 2026-10-11, `demand_surprises_outside_2sd: 0`, one principal with lead drift above a day). One snapshot cannot show cycle-over-cycle improvement. Phase 7 plan 07-03 closed this: `learn_curve.csv` tracks 46 months, 2023-01 to 2026-10 (823,200 forecast/actual readings, WAPE 0.1051..0.4699, mean 0.2152) and the one-pass trace now carries the LEARN step's cycle reading. Say "the loop tracks forecast-vs-actuals month on month; the worst-error months are the event months". |
| "orders and stock movements flow into the distributor's SAP business system" | 11 | **Built as a pluggable order intake (Phase 8), not as a live SAP write.** `src/agents/order_intake.py` submits every auto-issued order to an `OrderDesk`; the file-backed desk is the demo default and the HTTP desk posts to any real endpoint via `PASOK_ORDER_ENDPOINT`. Proven on the shipped run: all 384 auto-issued orders posted to the file-backed desk, 2 accepted in full and 443 in part against the pack rules and 0 refused, 2,561,400 of 2,565,950 units accepted (99.8%, 5,453 short) (`data/orders/intake_summary.json`); the HTTP desk was exercised separately against a stand-in ERP (`tools/fake_distributor_api.py`, which returns its own `ERP00001..` references and refuses lines that break its pack rules). SAP itself remains scoring + reasoning (RPT-1.6 predict, gpt-5.4 orchestration). A distributor's OData endpoint plugs in by setting one environment variable. Say "orders flow into the distributor's ordering system through a pluggable intake, proven against a stand-in ERP; SAP is the scoring and reasoning layer". |
| "coordinate through AgentCore's multi-agent collaboration; Memory keeps a per-SKU decision history; Gateway secures every tool call" | 23 | **AgentCore Memory and Gateway are empty on this account.** `list-memories` -> `{"memories": []}`, `list-gateways` -> `{"items": []}`. The per-SKU decision history exists as a file (`data/agents/decision_history.csv`, one row per PO); multi-agent coordination runs in-process in the Lambda; tool calls are secured by IAM plus the Lambda's own auth. AgentCore Runtime quota is 0 (`aws/GATES.md`, Gate 2). Say "the decision history is a durable artefact and coordination is in-process; AgentCore Memory/Gateway are pending the account gate". |
| registry holds event "dates drift yearly" and plans "against this year's verified date" | 13 | The registry (`data/demand/event_registry.csv`) carries 8 event types with `first_seen`, `last_seen`, `occurrences`, `mean_factor`, `median_factor`. It does **not** carry per-year calendar tables, and the dates are not "verified" from an official source: they are observed in the generator's own event table (`data/catalog/events.csv`). |
| "a controlled study confirms hybrid designs lose nothing in accuracy (Tan et al., NeurIPS 2024)" | 17 | Citation carried from the proposal; the build uses classical per-SKU baselines. `baseline.py` picks per SKU among ma4 / snaive / ses and writes the winner; ma4 wins 390 SKUs and snaive 210. Citation is context, not a measured result of this build. |
| "Retail research reports similar reductions (Syed et al., 2026)" | 35 | Citation carried from the proposal; no external study was run or reproduced here. |
| "agent bullwhip effect ... (Long et al., 2026)" / "bullwhip effect (Lee et al., 1997)" | 26 | Citations carried from the proposal to name the failure mode. The mitigation is measured in this build (`simulation/results.json`), the literature is context. |
| "success metrics" table (stockout -25%, C-class inventory -15%, expiry trend, A-class fill +3 points, manual review) | 45-59 | **Reported as absolute outcomes beside published benchmarks, with no invented baseline.** The repo holds no record of this distributor's current practice, so a comparison against a replay we generated would measure the generator: the same "manual" A-class fill has read 96.3%, 97.9%, 98.8% and 99.9% across four catalogue rebuilds, and "manual" stockouts 4, 20, 30 and 67 incidents a month. `tools/outcome_measure.py` writes `data/agents/outcomes.json`, each line beside an outside number with its URL: A-class fill 99.9% vs 92% retail shelf availability (Corsten & Gruen; GMA 8.3%); 22 days of inventory vs 57 at Indofood CBP in 2025; expiry 0.21% of cost of goods vs 2.70% supermarket shrink. Two proposal targets stay unmet in kind: a +3 point fill target is arithmetically out of reach from a 97.9-99.9% start (ceiling +2.12 at 97.9%), and the percentage targets need the client's own baseline before they can be scored. Say "these are the levels we hold; the pilot measures the change against the distributor's records". |
| "risk scored over holding cost, service level, shelf life, credit" | 20 | **Qualified: three of the four size an order, the fourth only reports.** Service level enters as the per-class z (`src/agents/decision.py:52`, `A:1.645,B:1.28,C:0.84`, read at `:297` as `z_used` and echoed at `:418` as `service_z`). Shelf life caps the order and the buffer; the peak envelope is the gate a person signs. Holding cost is **not** read by `decision.py`: `data/agents/economics.json` is produced by `tools/economics.py` and consumed only by `tools/figures_gate.py`. Say "the buffer follows the service level of the class, shelf life caps it, and an order past the item's own peak decides who signs" — not "cost-optimised". |

## Not claimed, but worth knowing

- **AgentCore Gateway is not live, and the proposal is not being edited to say otherwise.**
  Elang's decision (2026-10-10): the canonical proposal stays exactly as submitted, including its
  line 23 wording about Gateway. The account cannot host it: `CreateAgentRuntime` against
  `us-west-2` returns `ServiceQuotaExceededException: maxAgents limit exceeded for account
  865152853021`, so the AgentCore quota is zero. No increase is being requested. What the build
  actually proves, from artefacts, is that tool calls are secured by **IAM on the Lambda lane**
  and by **loopback binding locally**, with model and orchestration governance in **SAP AI Core**
  (orchestration `d8c092efb8980093`, Claude 4.6 Sonnet and gpt-5.4). The demo should present that
  substitution with the error message in hand, not claim AgentCore Gateway is running. A judge
  who asks "where is your gateway" gets the quota evidence and the substitute, in that order.
- **SAP's own MCP Gateway was checked and is NOT what the hackathon provides.** SAP Integration
  Suite ships an MCP Gateway ("customer-managed, governed MCP exposure for SAP and non-SAP
  APIs"), which is the direct functional equivalent of the proposal's Gateway line. The panitia
  entitlements are **Joule, AI Core and AI Launchpad** on a shared BTP sub-account (1000
  credits/month for BINUS students), and Integration Suite is not among them. So the security
  claim rests on IAM, loopback and AI Core governance, all of which are live and demonstrable.
- **Do not claim the M5 public-dataset result is reproducible by re-running the pipeline.**
  `experiments/e2_results.json` holds 30,490 series and 154 windows, but the check that produced
  it (`E2_learner`) is not in `run_chain.sh`. The number is quoted as a one-off measured result
  and nothing more.

- **The guardrails were not running on the pipeline, and now they are.** `decision.py` sized
  each order from `forecast x horizon - sellable` and then capped it with a single
  network-wide number (median guarded order level x 1.2). A fast mover's order runs to 25x
  the network median, so that ceiling never touched it: all 600 orders came out with
  `guarded_order == raw_order` and `guardrail_flags == 'none'`. A rule that never fires is not
  running, and the proposal (line 26) promises three rules that run while the agent works.
  The cap is now **per SKU and cover-based**: an order may buy at most `CAP_HEADROOM` (1.5x) the
  SKU's own target cover, and it is computed against the BASE forecast while the order itself uses
  the **event-uplifted** forecast. It therefore binds only while a SKU sits inside an event window.
  **Measured today on the 2026-10-11 snapshot: it binds on 0 of 600 orders** (`guarded_order ==
  raw_order` for all 600 rows in `data/agents/decisions.csv`, `variance_cap_binding: 0` in
  `decision_summary.json`), because no SKU is inside an event window on that date. An earlier run
  measured **384 of 600 bound, 2,237,347 units removed (42.1% of raw volume)** during event
  windows; quote that number only together with the window it came from. The replay's 1.33x to
  0.36x comes from the smoothing and the damping, which is what `demo/REHEARSAL.md` already tells
  the presenter to say.
- **Honest reading of that fix, both halves.** The cap demonstrably bounds volume, and it
  makes the guardrail claim in the proposal true. It does **not** demonstrably reduce
  variability: measured on the realised order stream, the per-SKU coefficient of variation of
  order cover is **0.59 with the cap and 0.58 without it** (`tools/bullwhip_effect.py`,
  counterfactual on the same weeks and the same demand, measured on the record-day catalogue of
  18 October; the metric describes the cadence, so it moves by hundredths when the mix changes). So the correct sentence for a judge
  is "the cap now runs and bounds each order against that SKU's own ordering rhythm", and the
  incorrect one is "it cut the bullwhip effect by X%". The Figure 1 claim (2.68x unguarded to
  0.24x guarded) is the standalone Bank Indonesia simulation and is a different experiment; it
  is unchanged by this fix and must not be quoted as a result on the live loop.
- **Why the variance ratio is the wrong metric on this loop, stated once so nobody quotes
  301x or 955x.** `tools/bullwhip_real.py` reports Var(order)/Var(demand) per SKU as a median
  of **300.98x** on the rebuilt catalogue (p25 176.10, p75 523.25, p90 835.11), and **955.04x**
  on the day-to-day change a manager actually sees. Both are artefacts of the cadence. This
  pipeline orders on a weekly review, so the median SKU carries an order on **7.3% of days** and
  a replenishment on the rest of the review calendar. A variance ratio on such a stream measures the
  sparsity of the cadence, not amplification; any periodic restock policy, including a perfect
  one, scores enormous on it. Amplification here is reported as order-cover variability
  (median CV 0.59) and as the share of orders that chase the previous week's noise (**median
  correlation -0.15, 0.0% of SKUs positively correlated**), both from the same 18 October
  counterfactual, which are the defensible forms.
- **Two cap forms were tried and rejected, with the reason, so the choice is auditable.**
  (a) `forecast_daily + CAP_K x sigma_daily` resolves to 2-3 days of demand and cut a
  legitimate 26-day horizon order by 83%, i.e. it truncated the plan instead of bounding the
  noise. (b) `cover_days_target x (forecast + CAP_K x sigma)` can never bind, because the raw
  order is already `target - sellable` and so sits under the horizon by construction (median
  raw/target 0.30). Form (c), used, is the one that both binds and leaves a sane order: on this
  catalogue the median cover after delivery is 32.7 days and the worst line sits at 47.3 days,
  against class caps of 45/60/90.

- **The reorder trigger was using the average delivery time instead of the cautious one.**
  This was a real defect and it is now fixed. The walk placed orders when cover fell below
  `lead mean + safety`, so a delivery in the slow tail arrived after the shelf was empty.
  `principal_lead_times()` now returns the learned p90 alongside the mean: the MEAN drives the
  simulated arrival (a truck arrives when it arrives) and the P90 drives the trigger, so an
  order is placed early enough that a slow delivery still lands in time. `simulate_sku()` takes
  `lead_trigger_days`, and the snapshot carries both `lead_time_days` and `lead_trigger_days` so
  the choice is auditable.

  Measured effect on the same run (the 18 October catalogue, before the rebuild): SKUs at
  `sellable = 0` fell from **11 to 1**, total lost
  sales from **11,894,466 to 7,300,366** units, median days of cover rose from **21.7 to 23.9**,
  and p10 cover from **3.29 to 6.39**. Ten of the eleven previous zero-cover SKUs now hold stock.
  The regret test (`tools/order_point_backtest.py`): firing on the p90 trigger, 0 of 12 suppliers
  leave the weekly review gap uncovered, against 12 of 12 before.

  Note the ordering direction matters: the trigger has to be the p90, not the mean, because the
  question is "will the order land before the shelf empties", and that is a tail question. The
  earlier version answered a different question ("when does it usually arrive").
- **Credit limits are now sized to the goods, per the rule that a line must cover the event
  peak.** This was a defect and it is fixed. The first version picked `credit_limit_idr` at
  random from four round numbers (Rp5M/10M/25M/50M): correlation with units sold per day
  **+0.017**, median limit covering **0.22x** of one replenishment cycle, **485 of 600 SKUs**
  unable to buy one cycle inside their own line. The generator now sets
  `line = normal monthly value (event days removed) x the multiple the GUARDRAILS allow`.
  Of the three guardrails in `decision.py`, only `CAP_K` (order <= forecast + 2.5 sigma) caps
  order size, and measured on the orders they produced the realised multiple of a normal month
  peaks at 1.63x (p99 1.45x, median 0.57x), so `GUARDRAIL_MULT` is 2.0. Derivation and the
  per-rule breakdown: `tools/guardrail_multiple.py`.
  On the rebuilt catalogue the line correlates **0.998** with each SKU's monthly value, because it
  is sized from that value, and only **0.11** with units per day, because a cheap fast mover and an
  expensive slow one can carry the same line; the median line is **Rp97.2M**. Note the line is a **commercial policy, not a forecast**: a principal extends
  credit knowing the buyer stocks up for peak season, so it may exceed expected demand. That is
  why it was not rewritten to feed back into the Decision Agent's sizing, which must stay
  unbiased.
- **The supplier-switch flag was marking every line of a weak principal.** Five proposals exist
  (`supplier_switch_proposals.csv`): P02, P05, P06, P07, P08, all weak on observed fill rate
  (0.832 to 0.895 against a network median of 0.901). The flag used to hit all **244** orders
  from those principals, because the candidate principal (P01) carries all five categories so
  the "shares a category" test always passed. Fixed: the flag now fires only where the switch
  would actually move money (`value_idr >= Rp500M` on that principal), which is **16 lines**
  instead of 244. A switch proposal is about a principal's reliability, not about every order
  line routed through it.
- **The approval split with the shipped policy.** The loop issues **384 of 458 orders
  itself** (92.7%); **35 are held**, worth **Rp 10.40bn**: 15 over a principal's credit
  line, 15 because the lot would not clear before its expiry date, 6 during a supplier
  switch, and 1 past the class cover cap (A 60, B 60, C 90 days). In the year-long replay
  the money gate never fires: **258 of 19,806** orders cross the peak envelope. The old split was
  two mistakes, a flat Rp200M ceiling that
  measured money instead of cover and MOQ judged per SKU line, both now fixed; the queue is
  empty on this snapshot, and the replay is where the human review rate is measured.
- **The event uplift now splits by category, with the per-SKU ramp on top.** The catalogue
  carries per-category amplitudes read by `generate.py` from
  `data/demand/category_event_amplitude.csv` (18 sourced rows: syrup and biscuits 1.3x over
  Ramadan-Lebaran, dried cake 1.5x, chocolate 1.35x at Lebaran, snack 1.1x), so the event term
  is no longer one flat array for all 600 SKUs. The machinery still learns per-SKU ramps
  (`sku_ramps.csv`, 600 rows per event, 8 events) and sizes from them. Say "the category split
  comes from industry and press evidence, the per-SKU shape is learned from our own sales".
- `data/demand/event_registry.csv` carries eight drivers, Nyepi among them. Widening the
  registry changes the Decision Agent's event windows and therefore the orders, so it is a
  scope statement, not something to add silently.
- The learn summary's flat signals (0 demand surprises, and lead drift on one principal
  only, above a day) are real readings on this data, not missing code.

## Short-lived goods: tested out of case, because the live record does not spoil

The catalogue's shelf life now runs **1 to 35 months, median 10**, so on the live record the
spoilage ceiling still binds on **0 of 600** SKUs and expiry risk is **7 SKUs**. That is a property of
the data, not a dead rule, and the demo says it in that order.

To find out what the expiry work does, sixty beverage SKUs were given **21 days** of life instead
of their catalogue life, and the same ninety days were run three times from the same starting position
(`demo/SCENARIO_SHORT_SHELF_LIFE.md`, override file `demo/scenario_short_shelf_life.csv`):

| run | demand lost | units expired |
|---|---|---|
| no spoilage ceiling | 2,737,797 u = 5.46% | 1,910,282 u = 3.81% |
| ceiling live, `shelf life minus one review` | 2,857,452 u = 5.70% | 1,341,324 u = 2.68% |

Both arms were run on 19 October 2026 from one opening state, after two defects were fixed: the
ceiling was skipped on the lot-aware path, and the agent was reading shelf life from the catalogue
while the world expired goods on the override. Measured with both fixed: spoilage down 568,958
units (29.8%), demand not served up 119,655 units (0.24 points), units decided down 2,635,318
(3.7%). **0.21 units of service given up per unit saved from the bin.**

Worked example, one SKU, same ninety days, same demand: **SKU0108**, a drink given 21 days of life
instead of its catalogue life.

| SKU0108 over the window | no guard | ceiling live |
|---|---|---|
| demand not served | 0 u | 0 u |
| units expired | 100,194 u | 52,690 u |
| empty-stock days | 0 | 0 |

Both arms serve this SKU's demand in full once the two defects below are fixed, and the ceiling
halves what goes in the bin: **100,194 units down to 52,690**. Earlier tables in this file showed a
20,000-unit shortfall and a nineteen-day empty spell; those builds had the ceiling skipped and the
snapshot reading the wrong shelf life, so they describe the defects, not the product.

**Correction first: the life clock starts at arrival.** The ceiling used to subtract the delivery
time from the shelf life, which counts the journey twice: a lot expires `shelf` days **after it
lands**. The ceiling and the buffer cap are now `life minus one review window`, and the only
refused line is one where delivery takes longer than the goods last at all. The live run is
unaffected (shortest life one month, numbers reproduced exactly, no SKU refused).

**The variance cap, measured after it was rebuilt (19 Oct 2026).** It used to cap `target x headroom`,
a quantity the raw order can never exceed, so it could not fire: `0 of 600` SKUs, even at `1.0x` the
target. It now caps the *need* (`cap = need x 1.25`, `PASOK_CAP_HEADROOM`), which fires exactly when
the fill-rate divisor pushes an order more than a quarter above what the agent computed it needs.

Two 90-day runs from one opening state, short-shelf-life override:

| run, ceiling live in both | demand not served | units expired | units the agent decided |
|---|---|---|---|
| cap off (`PASOK_CAP_HEADROOM=9`) | 3,399,903 u = 6.78% | 1,271,373 u = 2.54% | 68,726,437 |
| cap live (`1.25`, the shipped policy) | 3,469,143 u = 6.92% | 1,255,336 u = 2.51% | 68,628,611 |

**The event window, rebuilt and measured (19 Oct 2026).** The sizing carried the multiplier of the
day the order was placed, averaged over the buying horizon, so 19 days of goods in transit diluted
the peak: orders placed for 5 Mar carried 2.26 while the days they actually sold on ran 3.19 (-30%).
Three defects, all fixed in one pass: the uplift is now averaged over the **selling window**
(arrival through arrival plus one review, not order plus lead), overlapping events now **multiply**
(Ramadan x Imlek) instead of the first one winning, and **Payday** (1.22 on the 25th through the 5th,
per `src/catalog/generate.py`) now reaches the size at all. One run, `ramp_fix`, same opening state:

| run, 90 days, short-life override | demand not served | units expired | units the agent decided |
|---|---|---|---|
| before (`shelf_stage`) | 2,857,452 u = 5.70% | 1,341,324 u = 2.68% | 69,409,908 |
| event window fixed (`ramp_fix`) | 1,616,259 u = 3.23% | 1,436,400 u = 2.87% | 83,209,947 |

**Unserved demand down 1,241,193 units (43.4%), served up 123,540, spoilage up 95,076 units (7.1%).**
Thirteen units of service recovered per unit of extra spoilage, and the ordering that was too small
for Ramadan is the whole story: the multiplier on 5 Mar went 2.26 to 2.458. Residual: the agent
applies a learned ramp shape, the world's actual shape differs, so the gap at that review is now
+0.73 instead of +0.94, and closing the rest means re-fitting ramp shapes more finely than weekly.

**The frontier, in money (19 Oct 2026).** Three policies, one run shape:

| policy, 90 days | demand not served | units expired |
|---|---|---|
| `ramp_fix` (event windows fixed, ceiling in baseline units, weekly review) | 1,616,259 u = 3.23% | 1,436,400 u |
| `cad3` (same, review every 3 days) | 841,901 u = 1.68% | 1,905,171 u |
| `ceiling_ev` (same, ceiling in selling-window rate) | 1,294,650 u = 2.58% | 1,861,227 u |

Each step buys service with spoilage at a worsening rate: `cad3` recovers 774,358 units of demand
for 468,771 more spoiled units (1.65:1 in units), `ceiling_ev` recovers 321,609 for 424,827
(0.76:1). A unit served earns the gross margin, a unit spoiled loses its full cost
(`unit_cost_idr`, median Rp 14,000), so a step pays for itself only when the markup exceeds the
ratio itself: `cad3` needs a markup above 61 percent of cost, `ceiling_ev` above 132 percent.
FMCG distribution runs nowhere near that, so **`ramp_fix` is the money-optimal point on this
frontier** and the shipped policy. The remaining 1.6M unserved is the price of a 19.4-day lead
against 21-day goods under a weekly review; the lever that moves it is a nearer source, not a
larger order book.

The cap takes **1.3 percent off spoilage and costs 69,240 units of demand**, about 4.3 units of
service given up per unit saved from the bin: on fresh goods the cap is a small net negative, and it
is kept because it bounds a different failure, a supplier whose fill rate collapses mid-quarter.
`data/agents/decision_summary.json` reports `variance_cap_binding: 0` on the live October snapshot,
because the lowest fill rate there is 0.832 and the cap only bites below 0.80. Say both halves of
that sentence to a judge.

**The rule that was not running, and now is.** The staged ceiling applies to the size of one order on
every code path, and a line is refused only when delivery takes longer than its shelf life, which
sets `unservable_shelf_life`, escalates it with the reason in plain words, and counts it in
`decision_summary.json`. Same thirty days, only the rule differing: served and unserved demand
identical (9,801,263 and 419,050), decided units down 250,268, expired units 2,038 higher because
the dribble was landing dead. The live catalogue is unaffected: no SKU has a life margin under two
days and the October run reproduces its numbers exactly, with no line refused.

**What binds, measured rather than assumed.** The ceiling limits the size of one order, not the
level the shelf may reach: `shelf life minus one review window`, and goods already in transit do not
consume it. For SKU0108 (life 21 days, review 7) that is 14 days of demand per order, 16,406 units.
The life clock starts when the goods land, so a 19.4-day delivery does not eat into the 21 days.
With the ceiling live this SKU spoils **52,690 units instead of 100,194** and never runs dry in
either arm; the nineteen empty days it showed in earlier builds came from the two defects, not from
the product. What remains is a cadence problem, not a ceiling problem: 21 days of life, a 19.4-day
lead and a weekly review leave the policy on a knife edge, which is why the real catalogue's
shortest life is one month and its median ten.

The base is the recorded demand for the same ninety days, **50,112,358 units**, identical for all
three runs. Divide `lost_units` by `sold_units + lost_units` and you get 5.65 / 9.85 / 8.04
instead, because on non-review days `days.csv` writes the day's demand into `sold_units`; the
unmet part is then counted twice and the base moves with the run's own stockouts. The guard
takes 29.8 percent off spoilage (1,910,282 down to 1,341,324 units) and costs 0.24 points of demand,
5.46 up to 5.70, so on this product the ceiling pays for itself. The ceiling limits one order's size,
and goods in transit do not consume it. An earlier version capped the level the shelf could reach
after landing and counted in-transit goods toward that level, which starved the shelf by
construction: for a 21-day product on a 15-day lead the whole two-day level was already in transit.
Stated limit: stock on hand when a world is seeded
carries no lot date, so expiry is measured only on goods that arrive during a run.

## Late deliveries: read the shelf, not the clock (computed 2026-10-26)

"Late" is measured against a paper promise (the learned p90 lead time set by
`order_intake.py`), and the slip is a network property: on the matured record
(20,300 replay decisions across 284 days) about half of agent arrivals land after the
paper promise, every miss 1-2 days, none more. What the buffer buys is that lateness stays
cheap: the shelf went empty on **0.28% of agent SKU-days against 0.12% in the manual replay**
(`replay2026_v25` against `replay2026_m`), and the median cover across the replay is 28 days.
The young-record pair phase 15 quoted (49.9% vs 27.4%) is superseded by the replay record;
the claim to make to a judge is the shelf claim, not the clock claim.

## The replay year, and what it costs

The record a judge sees is now one code version run day by day from 1 January to
11 October 2026, in a closed world of the same 600 SKUs, the same 12 principals and
the same lead times (`data/sim/replay2026_v7/`; the manual baseline in `replay2026_m/`). It is a simulation, not the live desk,
and it is labelled that way on the orders page.

Across 284 days and 41 review days the loop placed 20,300 orders for 59.7 million
units, Rp 566.4bn at cost. Three numbers describe the outcome, and one of them is bad:

- **Demand lost to an empty shelf: 70,047 units, 0.13% of demand** (manual replay
  60,647, 0.11%). For scale, the cross-country retail out-of-stock average is 8.3%
  (Gruen and Corsten, 71,000 shoppers, 29 countries), so this is inside the normal band.
- **Expired stock: 244,967 units, 0.41% of the 59.7 million ordered** (manual replay
  7,218, 0.01%). Almost all of it is one-month bread bought ahead of an event. This is
  the number the build still loses on, and it is named as a miss in `targets.json`.
- **Median days of cover: 28.2.** That is the price of the first number: a month of stock
  in the network, shown on every console page rather than hidden behind the fill rate.

Fill on the 11 October live snapshot is 0.9030 (landed units over ordered units); the
replay grades each decision the same way and reports 382 partial acceptances, none refused. The two differ because they are different worlds, and
the deck must say which one a number comes from.

The last ten days of the replay show cover falling from 21.0 to 10.1 days by 8
October, 115 SKUs empty at the close on 11 October, and the next deliveries pulling
median cover back to 22.8. That dip is the delivery cycle, not a failure of the rule:
orders placed on 8 October cannot arrive before the supplier's lead time, which runs
5 to 25 days at the p90 across the twelve principals. It is worth
showing to a judge precisely because it is the kind of week a real distributor has.

## External check: do Indonesian prices really ramp before Lebaran?

The event uplift in this build is learned from the shop's own sales, so a judge may
fairly ask whether the pattern is real or invented. The Indonesian food price panel
(PIHPS, Bank Indonesia) answers that with an independent series: 212,952 daily
observations, 34 provinces, January 2022 to October 2026, five commodities
(`data/external/pihps_harga.csv`). Rise means 2% above the median of the 60 days
before the window; the window is 60 days before to 30 days after each Eid.

- Minyak goreng kemasan: rise starts 38.7 days before Eid, peak 18 days after, +7.8%
- Gula pasir: rise starts 39.0 days before, peak 13 days after, +4.3%
- Telur ayam: rise starts 29.0 days before, peak 2.6 days after, +7.0%
- Minyak goreng curah: rise starts 29.5 days before, peak 10.6 days before, +6.1%
- Beras medium: already 2% above baseline at day 60, so the onset is censored and
  the honest statement is that rice rises earlier than the window we measured

Two things follow. First, the 29 to 39 day lead time the panel measures is the same
order of magnitude as the ramp the loop learns, which is why the agent starts
lifting orders a month out rather than a week. Second, the packaged-oil and sugar
peaks land after Eid, which is a reminder not to describe every price peak as
pre-holiday. The chart is `demo/pihps_event_risers.png`.

The limitations are part of the evidence: this is a national median across
provinces, not a Jakarta distributor's invoice; rice's onset cannot be measured with
this window; and three of five commodities rise in only two to four of the five
years. It confirms the direction and the timing, not the exact multiplier the shop
sees on any single SKU.
