# One pass, concretely — SKU0191

> Proposal line 24, turned into a trace. Every number below comes from the committed
> artefacts; regenerate with `bash run_chain.sh` and `.venv/bin/python src/agents/one_pass.py`.

**The SKU was not hand-picked.** The strict selection rule is a *biskuit* SKU whose days of cover run out before the next delivery, inside a registered event window, for which the loop issued an order, and no SKU matches it in this snapshot, so the trace falls back to tightest cover among event-covered biscuits. Winner: **SKU0191**
(P12), snapshot 2026-10-31.

## 1. Perceive — what the three agents see

| Reading | Value |
|---|---|
| On hand | 1,068 u |
| In transit | 0 u |
| Open PO | 10,142 u |
| **Sellable** | **11,210 u** |
| Velocity | 296.32 u/day |
| **Days of cover** | **37.8 d** |
| Below reorder | False |

## 2. Forecast — the event it is planning for

- Registered event: **Christmas** at **x1.01**
- Learned ramp for this SKU/event: **yes**
- Forecast: 247.0 u/day base →
  **250.0 u/day effective**

## 3. Decide — the sizing arithmetic

```
cover target = lead p90 (18) + review (7) + buffer (9)
             = 34 days
buffer       = z90 x sqrt(lead_p90 x demand_cv^2 + lead_sd^2) + p95 lateness
             = 9 d  (lead sd 3.3 d,
               demand term 1.5 d, late tail 2.0 d)
sells while  = 4,450 u over the lead time
the truck runs
stock when   = -3,381 u
the lot lands
gap to cover = 8,656 u until the lot after it lands
need         = 12,037 u, divided by supplier fill
raw order    = 12,371 u
guarded      = 12,371 u  (none)
```

Rationale recorded: *"The order is sized for what the shelf has to carry until the lot after this one lands: the stock available now covers about 1,068 units, about 4,450 units sell while the truck is on the road, and the demand between arrival and the next arrival is about 8,656 units. That leaves 12,037 units to buy, divided by a supplier that delivers about 97% of what is asked. Cover target is 34 days: 18 days worst-case delivery, 7 days until the next review, and 9 days of allowance. The SKU sells about 250 units a day in this window. Christmas does not move this SKU above a normal week in this window. The order rule did not cut this order back."*

Supplier reality: fill **0.973**, lead drift
**False**.

## 4. Issue — the purchase order and the human gate

| | |
|---|---|
| PO | **PO-0032** |
| Quantity | 12,371 u |
| Value | **IDR 185,568,000** |
| Credit line for this SKU | IDR 223,500,000 |
| Status | **AUTO_ISSUED** |
| Why | within policy limits |
| Notification | SENT (orders+p12@principal.example.id) |

The order sits inside the SKU's credit line and inside policy, so it fires automatically: the principal is notified and the order goes straight out. That is supervised autonomy working; the money gate exists and did not need to fire here.

**Ordering system:** submitted to **local-order-desk** as **SO-2026-000032**.

## 5. Learn — the loop checking itself

- Score: **ON_PLAN**
- Observed fill 0.973 → expected arrival
  12,034 u of 12,371 u
  (**short 338 u**)
- Lead time: planned p90 18 d vs observed
  18 d (drift 0.0 d)
- Held-out forecast WAPE for this SKU: **0.1654**
- Loop cycle check: snapshot month **2026-10** carried WAPE
  **0.2672** over
  18,600 forecast/actual readings. The loop
  tracks 46 months; its worst month
  (2023-06, 0.4029)
  is an event month, its best (2025-06,
  0.0994) a quiet one. Full curve:
  `data/agents/learn_curve.csv`.

**Next cycle's lever:** this principal's fill rate (0.973)
is the binding constraint, so the buffer for P12 rises and the shortfall shrinks on
the following pass. That is the "starts smarter" step.
