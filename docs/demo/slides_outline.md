# Pasok — Demo Day Slides (15 min, English)

Every figure here traces to `demo/figures.md`. 12 slides, ~75 s each.

## 1 — Title
Pasok: an autonomous reorder agent that plans for the event peak without the bullwhip
Team AIGO · Track A (Intelligence Supply Chain) · Agentic AI Hackathon 2026

## 2 — The problem
General trade = ~69% of Indonesia's FMCG volume, decided on a spreadsheet.
A fixed reorder point cannot see Ramadan, Lebaran, Imlek, THR, payday.
Fast movers run dry, slow movers pile up, lead times are assumed not measured.

## 3 — The failure mode we design against
Bullwhip (Lee et al. 1997), *agent* bullwhip (Long et al. 2026).
Same forecaster, two policies, 250 days on the Bank Indonesia retail index:
- unguarded **2.68x** demand variance (fill 0.9893)
- guarded **0.24x** (fill 0.9868)      [F1–F4]

## 4 — Four agents, one loop
Demand → Stock Position → Supplier Reliability → Decision.
Perceive, forecast, decide, issue, learn.

## 5 — Demand Agent
Weekly per-SKU forecast + interval; learned per-SKU event ramp.
Held-out on 154 event windows, all 30,490 M5 series: ramp WAPE **0.0775** vs flat-bump **0.1161** (**+33.3%**) [F6–F9]

## 6 — Stock Position Agent
sellable = on-hand **5.62M** + in-transit **0.73M** + open PO **4.52M** = **10.88M u** [F19]
347 SKUs carrying an open PO, 104 in transit. Recomputed continuously, not at review.

## 7 — Supplier Reliability Agent
Learned lead time (p50/p90) from receiving records, not the promise.
Network fill **0.9126**; **9 of 12** principals below 95% → the buffer lever [F27]

## 8 — Decision Agent + guardrails (the differentiator)
cover target = lead p90 + review + buffer, buffer = z90·√(lead_var² + forecast_err²) [F21]
Erratic P02 buffer **5 d** vs reliable P03 **4 d** [F22]
Live replay: raw **1.30x** → guarded **0.35x** (**−72.8%**) [F12–F13]

## 9 — One pass, concretely
SKU0536 (biscuits, P11): cover **0.0 d**, NewYear **x2.50**, order **23,148 u**,
PO-0044 **IDR 879.6M** vs credit line IDR 5M → **escalated to the human queue**.
(source: `demo/one_pass.md`)

## 10 — SAP AI Core + Joule (human in the loop)
sap-rpt-1.6 scores days-of-cover / stockout / expiry, agreement **0.72** over 600 SKUs. [F29]
gpt-5.4 writes every rationale through the orchestration deployment (40/40). [F30]
Joule surfaces `pasok_exception_queue` — the buyer approves live.

## 11 — AWS lane (live)
Four-agent reasoning layer on AWS Lambda; brain is Amazon Bedrock (Mantle endpoint),
SAP AI Core as fallback. Live HTTPS invocation, or the recorded run / `demo/one_pass.md`
trace. AgentCore Runtime is written but quota-blocked on this account (`aws/GATES.md`).

## 11b — The order leaves the agent
Order intake posts every auto-issued order into the distributor's ordering system: the
system issues its own reference, applies its own pack size, sets the promised delivery
from the learned lead time, and posts receipts back. 130 submitted, 130 accepted
partial, 0 refused: the system shorted 1,460 units of 393,260 on its own pack rules.
Same intake talks to a file-backed desk or a real HTTP ERP: one environment variable. [F37]

## 12 — Impact and close
Pilot targets: stockouts A-class **−25%** · inventory C-class **−15%** ·
fill A-class **+3 pts** · manual review **<10%** of catalog.
Pasok plans for the peak without the bullwhip. Thank you.
