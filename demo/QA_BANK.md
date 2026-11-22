# Q&A bank for Demo Day

Answers are short on purpose. Each one names the artefact behind it so a judge can check
rather than believe.

**1. Is this just a forecast with a nicer chart?**
No. The forecast is one input. The loop issues purchase orders, gets acknowledgements,
receives goods, and scores its own decisions against what arrived. The replay runs 284
days and 20,300 order lines; the console reads that record, it does not illustrate it.

**2. Why an LLM at all? Why not a classical optimiser?**
The arithmetic is classical: cover, safety stock, MOQ, space, and a demand envelope. The language model
writes the explanation a buyer reads and cross-checks the call. Sizing never comes from
the model, so a bad generation cannot change an order.

**3. What stops it from ordering something stupid?**
Three layers. The sizing policy bounds the quantity by cover. Shared constraints bound the
order by space and the principal's minimum order, plus one demand gate: an order bigger than the
item's own peak can absorb. The downside gates
send anything resting on an unproven assumption to a person: a supplier-switch proposal, an
event uplift beyond the SKU's own peak, overstock past the class cap, near-expiry inside the
30-day markdown window, or an uplift with no registered event. On this snapshot three of them
fire: 0 lines waited: none over a money line, none near expiry, none mid switch.

**4. No orders are waiting. Is that supervision or a stuck system?**
Supervision, and this pass did not need it: nothing waited, worth IDR 0. The 27 October pass did carry 35 lines worth IDR 10.40bn, which is what the log row shows. The queue is not
decorative either — **22 lines waited on 19 October**, 21 of them because the order would have
run past the class cover cap, 2 carrying a supplier switch (one line both). What has never
happened is a line waiting on its own peak envelope: **258 of 19,806** replay order lines crossed it,
and `tools/test_gates.py` fires that gate on eleven synthetic cases. On this pass nothing trips
it because cover after delivery tops out at 47.3 days against caps of 45/60/90 and the building
has 12,862.5 m3 free.
The queue is a real exit with the reason attached to each line (`data/orders/approval_queue.csv`),
and on this snapshot it is 0 of 600 decisions: no order exceeded its item's peak envelope, no lot would sit inside its markdown window, and no principal is in drift, so no switch fires. The gates are armed; they simply had nothing to hold.

**5. How do you know the agent is better than the buyer?**
It is better on the class that matters and worse on one number, and both are on the record.
Same catalogue, same window, same starting stock. On A-class SKUs the agent loses 0.8
stockout incidents a month against the manual rule's 4.0, a fall of 80%, and fills 100.00%
against 99.91%. Across the whole catalogue it is not ahead: 0.13% of demand lost (70,047
units) against 0.11% (60,647), because it holds more C-class stock (+5.8%) and lets 244,967
units expire against 7,218 — almost all one-month bread bought ahead of an event. That is
the miss in `targets.json`, and the next build prices shelf life into the ramp instead of
trusting the class cap. The manual baseline is a reconstruction of the rule, not a recording:
weekly review, 30 days of cover, no forecast, no calendar, no shelf-life cap, no demand envelope.

**6. Is the data real?**
Three sources, labelled honestly. The demand shape comes from Bank Indonesia's retail
index; the event-ramp experiment uses the public M5 dataset; the distributor catalogue is
synthetic and allowed by the briefing. We never present synthetic figures as a client
result, and the repo marks which is which.

**7. Is AWS actually used, or is it a logo?**
Partly, and say which part. The four-agent loop runs on Lambda with the Bedrock Mantle
endpoint; the last deploy answered HTTP 200 with the artefacts current at that moment (fill
0.9030 today). Bedrock AgentCore is written and deployed as CDK, but this account's
AgentCore quota is zero, so the runtime never starts (`aws/GATES.md`). SAP AI Core runs
gpt-5.4 for the reasoning text, and RPT-1.6 cross-checks below-reorder calls at 0.895
agreement with the agent.

**8. What does SAP do that a spreadsheet cannot?**
It is the system of record. A purchase order has to exist there for the business to trust
it: reference, pack multiple, promise date, receipt. The agent speaks the ordering
system's interface, file-backed today and HTTP ERP by environment variable.

**9. What breaks first at 2,500 SKUs?**
Compute, not logic: the loop is per-SKU. What does break is space: at 2,500 SKUs the
warehouse master needs carton dimensions and pallet positions from the WMS, not a
pack-derived estimate. That is the first integration we would ask a distributor for.

**10. What about expiry?**
The catalogue's shortest life is one month now and 7 SKUs carry an expiry flag, so the real
data can spoil. We still measure the ceiling in a labelled what-if with 21-day goods,
recorded in `demo/evals.md` rather than reproducible from `data/` today: the shelf-life
ceiling cut spoilage from 3.81% to 2.68% and cost 0.24 points of service. That trade is a
business decision, so it is shown, not hidden.

**11. Bullwhip: did you just tune it until the number looked good?**
No. The replay reports the raw and guarded amplification together. One of the three
guardrail rules, the variance cap, binds zero times on this snapshot; we say that on the
slide and prove it fires on a low-fill run instead of claiming a save.

**12. What did you deliberately not solve?**
Supplier selection, price negotiation, credit extension, promotions and store-level POS.
The agent reports those; a person decides them. A demo that claims all of it is a demo
nobody can deploy.

**13. If the network dies during this pitch, what happens?**
We switch to the offline bundle in `shots/` and this deck. The console pages are
screenshots of the same artefacts, and the numbers are in `demo/figures.md` with the
command that regenerates each one.

**14. What does it cost to run, and what does it save?**
It depends on the supplier's terms, which is the honest answer. The distributor owns the
stock but does not fund it: with DIO 13.6 days, DSO 30 and DPO 30 the cash cycle is 13.6 days,
so a Rp 23.8bn average inventory needs no working capital at 30-day terms and costs Rp 0.9bn
a year in physical carrying. At DPO 45 the cycle turns negative by 1.4 days. What survives
every term sheet is physical carrying, the order cost of Rp 74M, and the share of inventory
value sitting above the class cover cap.

**15. Your ABC classes: by units or by value?**
By value now. The first build ranked by units, which called cheap sachets strategic.
Ranked by consumption value, the split is 260 A / 188 B / 152 C, and A carries 80.0% of the
value in 43% of the SKUs. That is why the replay had to be re-run: class sets the service
level, and service level sets every order.

**16. What would you do with another month?**
Wire a real WMS space master, add carton-level receiving, and run a shadow mode beside a
live buyer so the comparison is against a person, not against a previous policy.
