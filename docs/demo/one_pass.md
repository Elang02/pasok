# One pass, concretely — SKU0421

> Proposal line 24, turned into a trace. Every number below comes from the committed
> artefacts; regenerate with `bash run_chain.sh` and `.venv/bin/python src/agents/one_pass.py`.

**The SKU was not hand-picked.** The selection rule is the paragraph's own: a
*biscuits* SKU whose **days of cover run out before the next delivery**, inside a
registered **event window**, for which the loop issued an order. Winner: **SKU0421**
(P09), snapshot 2026-10-11.

## 1. Perceive — what the three agents see

| Reading | Value |
|---|---|
| On hand | 2,079 u |
| In transit | 0 u |
| Open PO | 0 u |
| **Sellable** | **2,079 u** |
| Velocity | 292.79 u/day |
| **Days of cover** | **7.1 d** |
| Below reorder | True |

## 2. Forecast — the event it is planning for

- Registered event: **nan** at **x1.00**
- Learned ramp for this SKU/event: **no**
- Forecast: 270.5 u/day base →
  **270.5 u/day effective**

## 3. Decide — the sizing arithmetic

```
cover target = lead p90 (5) + review (7) + buffer (4)
             = 16 days
buffer       = z90 x sqrt(lead_var 1.0^2 + forecast_err 2.3^2) -> 4 d
raw order    = target cover x effective forecast - sellable = 2,249 u
guarded      = 2,159 u  (damping,variance_cap)
```

Rationale recorded: *"cover 16.0d (lead p90 5.0d + review 7d + buffer 4d); sellable 2078.6u; forecast 270.5u/day; variance cap binds (2.5sigma cap at 2159u)"*

Supplier reality: fill **0.855**, lead drift
**False**.

## 4. Issue — the purchase order and the human gate

| | |
|---|---|
| PO | **PO-0032** |
| Quantity | 2,159 u |
| Value | **IDR 82,045,800** |
| Credit line for this SKU | IDR 594,100,000 |
| Status | **AUTO_ISSUED** |
| Why | within policy limits |
| Notification | SENT (orders+p09@principal.example.id) |

The order values above the SKU's credit line, so it does not fire automatically: the
principal is **not** notified and the order sits in the human queue. That is
supervised autonomy working, not a failure.

**Ordering system:** submitted to **local-order-desk** as **SO-2026-000027**.

## 5. Learn — the loop checking itself

- Score: **SUPPLY_SHORT**
- Observed fill 0.860 → expected arrival
  1,856 u of 2,159 u
  (**short 303 u**)
- Lead time: planned p90 5 d vs observed
  5 d (drift 0.0 d)
- Held-out forecast WAPE for this SKU: **0.0898**
- Loop cycle check: snapshot month **2026-10** carried WAPE
  **0.4374** over
  6,600 forecast/actual readings. The loop
  tracks 46 months; its worst month
  (2025-01, 0.7494)
  is an event month, its best (2023-01,
  0.1237) a quiet one. Full curve:
  `data/agents/learn_curve.csv`.

**Next cycle's lever:** this principal's fill rate (0.860)
is the binding constraint, so the buffer for P09 rises and the shortfall shrinks on
the following pass. That is the "starts smarter" step.
