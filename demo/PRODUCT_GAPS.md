# Pasok: what is still missing, as of 19 October 2026

This is an internal audit, not a pitch document. Each line names the evidence and whether
it is fixed, in flight, or open.

## Fixed today

**P1. The architecture overclaimed AgentCore.**
`demo/architecture.md` and the deck said the four agents run inside Bedrock AgentCore
Runtime. On this account `Total Agents per Account` quota is 0 and the increase was
refused (`aws/GATES.md`, Gate 2), so the loop runs as one Lambda service and Bedrock
inference goes through the Mantle endpoint. Both documents now say that, before a judge
finds it in the repo.

**P2. FIXED. ABC was ranked by units, not by value.**
`src/demand/baseline.py` ranked SKUs by cumulative units (80/95). FMCG practice, and
APICS, rank by consumption value. Ranked by value the split becomes 260 A / 188 B / 152 C
instead of 278 / 178 / 144: the cheap sachets leave class A. A holds **80.0% of value** in
43% of the SKUs, which is why the unit-based split looked plausible for so long. The classifier now uses
units x unit cost and writes `total_value_idr` next to `total_units`. Three replays followed. v3 (value ABC, same service levels) was **rejected**: 0.759% lost
at Rp 316.3bn average inventory, about Rp 50bn more stock than v2 for 0.18 points of
service. v4 (value ABC, shipped service levels and caps) is **promoted**: 0.717% lost at
Rp 284.0bn, the best service of the three.

**P3. FIXED. There was no money layer at all.**
The console reports service, never cost. `tools/economics.py` now computes, over the
replay window: average inventory value, inventory turns, carrying cost split into the part that is
physical (storage, handling, damage, obsolescence at 8% per year) and the part that is
financing, which depends on supplier terms through the cash conversion cycle
(CCC = DIO + DSO - DPO). On the v18 replay at DPO 30: average inventory Rp 23.8bn, 20.9
turns a year, DIO 13.6 days. The distributor funds none of it, because 13.6 days of stock
is paid for inside 30-day supplier terms, so the annual bill is Rp 0.9bn physical and Rp 0
financing. At DPO 45 the cash cycle turns negative by 1.4 days: the terms cover the stock
and a little of the receivables too. **This is why a "holding cost" number without payment
terms is fiction**; the earlier 25%-of-value figure assumed the distributor funds
everything, which is the worst case, not the normal one. The slice sitting above its class
cover cap is real but small on this snapshot: 15 SKUs, 4.8% of sellable value (Rp 8.2bn),
and it is a storage and expiry problem before it is a financing one.

## Open, in priority order

**P4. FIXED. The human queue is a real exit, and every gate is now forced by a test.**
The gate logic moved out of `main()` into `gate_reasons()`, a pure function.
`tools/test_gates.py` forces eleven cases: clean, space, credit, MOQ deferred, MOQ
blocked, supplier switch, event overreach, overstock, near expiry, candidate event and
demand shock. The chain reproduces the same snapshot byte for byte on whatever catalogue it
is pointed at: 458 orders and 74 held lines after the rebuild, 166 and 2 on the older
catalogue, so the refactor changed structure rather than behaviour.

**P5. ABC is computed once, at the start of the record.**
`classify()` runs at `src/demand/baseline.py:129` and the class is never recomputed in the
daily loop. APICS guidance is quarterly reclassification; the claim that quarterly review
cuts stockouts by about 15% is a vendor/industry claim, not something we have measured.
Next: reclassify on a rolling 12-week window each quarter and count migrations.

**P6. There is no live data feed.**
Demand comes from the recorded history and the replay. A real deployment needs outlet
sell-through (POS) and goods-receipt events. The console's snapshot is dated 11 October
2026; on Demo Day it will be three weeks old unless the loop is fed. This is an integration
requirement, not a code gap, and the Q&A answer says so.

**P7. The XYZ half of the matrix is inert.**
Coefficient of variation across the catalogue spans 0.34 to 0.46, so no SKU reaches the
High band and the volatility axis never changes a decision. It is displayed honestly on
`/health`, but it does not yet earn its place.

**P8. Supplier-switch proposals are written, not executed.**
`data/orders/supplier_switch_summary.json` carries five proposals and a median network
fill of 0.901. Nothing routes volume away from a weak principal automatically; the buffer
rises instead. That is a deliberate authority boundary, but it means the reliability agent
influences safety stock, not sourcing.

**P9. Price, promotion and credit are boundaries, not decisions.**
The agent checks a credit limit and refuses to exceed it. It does not plan promotions,
negotiate price, or extend terms. Promo allocation is the top cause of dead stock in FMCG
distribution, so this is the largest missing commercial capability.

**P10. The console has no authentication.**
It binds to localhost today. Any deployment needs a login, an audit log per user, and a
CSRF story before a distributor's buyer touches it.

## What this means for the pitch

Do not claim a money saving. Claim the mechanism and the measured service: 0.70% of demand
lost, 0.9030 network fill, 10.8 inventory turns, and a carrying cost that shows where the
next gain is. If a judge asks "how much does it save", the honest answer is that the
economic layer now exists and the first read says the next win is inventory, not service.
