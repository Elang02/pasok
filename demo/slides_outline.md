# Pasok — Demo Day slides (15 minutes, English)

Companion to `demo/deck/Pasok_DemoDay_2026.pptx`, built by `demo/deck/build_deck.py` on the
committee's own template (`assets/bg1.png` cover, `assets/bg2.png` content). Twelve pages,
about 70 seconds each, timed in `demo/REHEARSAL.md`. `demo/deck/check_deck_numbers.py` matches
20 claims against the artefacts, and every figure has a row in `demo/figures.md`.

There is no live demo: pages 5 and 6 are screenshots of the running console, captured on
28 October from the build that shipped, not mock-ups.

## 1. Pasok (cover)
600 SKUs, 12 principals, 445 orders on the last pass. One sentence: the desk decides what to
reorder, in tranches the shelf can carry.

## 2. One buyer, 600 SKUs, a calendar that moves
Eight Lebaran dates in eight years, from 5 June 2019 to 20 March 2026. The buyer plans against
a calendar that moves under them: Lebaran walks 32 days earlier in four years, Christmas stays on
25 December. Source: `data/demand/event_calendar.csv`.

## 3. Left alone, orders swing harder than demand
2.68 times demand with no rules, 0.24 with them; fill 98.93% against 98.68%. Source:
`simulation/results.json`.

## 4. Four agents, one desk, a reason for every line
Demand, stock position, supplier reliability, decision. "The model writes the reason, never
the quantity."

## 5. The nearest event, and what it moves
Payday, 25 October 2026, 14 days out, moves nothing above noise; Christmas, 20 December 2026,
70 days out, moves 13 of 600 SKUs at 1.35 to 1.63 times. Screenshot
plus the same answer typeset. Sources: `data/demand/sku_ramps.csv`, `catalog.csv`.

## 6. One SKU, one order, every line explained
SKU0041, biskuit, P03: cover 8.7 days, trigger 7, target 18 (lead 7 + review 7 + buffer 4),
3,375 units, IDR 53.0M against a 212M peak envelope, fill 97.7%, short 78. Source:
`data/agents/one_pass.json`.

## 7. Why this order, in the desk's own words
The rationale the desk wrote for SKU0041: the stock on hand, the units that sell while the
truck runs, the demand until the next arrival, the gap, then the order divided by the
principal's fill. The gate that could have stopped it is named, and the notification that
followed. The page is a capture of the running build at `/order`, one order with its arithmetic: stock on
hand, what sells while the truck runs, the gap, the supplier's fill, the order placed, the gate
that could have stopped it, and the notification that followed. Source: `data/agents/one_pass.json`
through `web/app.py` `/order`; the deck itself lives in Google Slides, one file the team edits.

## 8. The forecast learns the shape, the lead time is measured
Error 7.8% against 11.6% for a flat bump, over 154 holidays and 30,490 series; 120 of 120
surprise spikes caught. Source: `experiments/e2_results.json`.

Best and worst of twelve principals, 1,956 receipts, network fill 90.34%. Source:
`data/agents/supplier_reliability.csv`.

## 9. Three rules keep one order honest
Smooth the forecast, hold back a jump, cap one delivery at what the shelf can sell: 1.33 to
0.36 times, cap cuts 0 of 445 orders.

## 10. SAP scores, AWS runs, and the desk writes the reason
600 SKUs scored in 10.73 seconds, 40 of 40 reasons written, 577 calls of near expiry and none
of a stockout. Source: `data/sap/`.

Lambda for the chain, Bedrock through the Mantle endpoint, SAP AI Core for scores. AgentCore
runtime is written and blocked by an account quota of zero; the deck states it.

## 11. One snapshot, in money
445 orders, 446 out without a person, IDR 31.50 bn placed, 443 surplus SKUs redirected with
IDR 8.95 bn protected. Source: `data/orders/order_summary.json`, `redirect_summary.json`.

## 12. What it does beside outside numbers, and what a pilot needs
Fill 99.9% against 92% retail shelf availability; 22 days of inventory against 57 at Indofood
CBP; expiry 0.21% of cost against 2.70% supermarket shrink; 0 of 445 orders a person had to
see. Sources with URLs in `data/agents/outcomes.json`.

From the client: a year of order lines and lead times as they arrive. From us: four numbers a
month and every order with its reason on file. Repo: `github.com/Elangk1` (private, access on
request).
