# Pasok — the four agents, and how they are wired

This is the integration record. Every line below is checked by
`tools/integration_audit.py`, which reads the artefacts only. Run it to reproduce:

```
.venv/bin/python tools/integration_audit.py     # 11 passed, 0 failed
```

## The four agents named in the proposal

| Proposal agent | Code | What it owns |
|---|---|---|
| Demand Agent | `src/demand/baseline.py`, `event_ramp.py`, `registry_catalog.py` | per-SKU level/class/residual (+ forecast error), event calendar, per-SKU ramp |
| Stock Position Agent | `src/agents/stock_position.py` | sellable stock, days of cover, expiry risk |
| Supplier Reliability Agent | `src/agents/supplier_reliability.py` | each principal's real lead p50/p90 and fill rate |
| Decision Agent | `src/agents/decision.py` | the orchestrator: weighs every input, picks the action, writes the rationale |

Three further agents carry the loop out of the decision: `consolidation.py` (supplier
switches), `order_executor.py` (issue/escalate), `order_intake.py` (submit to the ordering
system), `notification.py` (tell the principal), `redirect.py` (move excess to a depot),
`learn.py` (compare forecast to actual).

## The wiring, hand-off by hand-off

| # | Hand-off | Artefact (the interface) | Proof |
|---|---|---|---|
| 1 | Demand -> Decision | `data/demand/baselines.csv` | 600 rows; `decision.py` loads it for `resid_sd` |
| 2 | Demand -> Decision | `data/demand/sku_ramps.csv` | 3,000 rows; `decision.py` loads it for the event uplift |
| 3 | Demand -> Decision | `data/demand/event_registry.csv` | 5 events; `decision.py` loads it to place the window |
| 4 | Stock -> Decision | `data/stock/position_snapshot.csv` | 600 rows; carries `days_of_cover`, `expiry_risk` |
| 5 | Supplier -> Decision | `data/agents/supplier_reliability.csv` | the `lead_p90` Decision used equals the one written, on **100.0%** of 600 rows |
| 6 | Decision -> Consolidation | `data/orders/supplier_switch_proposals.csv` | proposals written; consolidation consumes reliability + catalog |
| 7 | Decision -> Order Executor | `data/agents/decisions.csv` | 600 decisions scored, one order row per SKU that needs one |
| 8 | Executor -> Notification | `data/orders/purchase_orders.csv` | one PO per ordered SKU, `{ESCALATED, AUTO_ISSUED}`; notification loads it |
| 9 | Executor -> Order Intake | `data/orders/purchase_orders.csv` -> `order_acks.csv` | 46 acks; idempotent per `po_id` |
| 10 | Intake -> Learn | `data/agents/decision_history.csv` | one row per PO; learn compares order vs receipt |
| 11 | Demand ramp -> ordered size | `data/agents/decisions.csv` | **600/600** decisions carry an event |

The key property: agents do not call each other's functions. Each writes an artefact and the
next reads it. That is why any one of them can be swapped (a different forecaster, a
different ordering system) without touching the others.

## Where the loop is deliberately open (honest gaps)

- **SAP write path.** Proposal line 11 says orders flow into the distributor's SAP business
  system. The ordering system is real and separate (`tools/distributor_api.py`, its own
  SQLite database, its own rules) and the intake writes to it. It is not SAP. SAP is used
  for scoring (RPT-1.6) and reasoning (GPT-5.4), both read-only calls. Making this literal
  needs an SAP write API (or the ordering system itself being SAP).
- **AgentCore multi-agent collaboration.** The proposal says coordination runs through
  AgentCore. In this build the coordination is the artefact chain above, which runs locally
  and deterministically. AgentCore Runtime is written and runs locally (`/ping` Healthy) but
  its deploy is account-gated; `aws/GATES.md` records that.
- **Bedrock Knowledge Base for the event registry.** The registry lives in
  `data/demand/event_registry.csv` and the per-year calendar that the agents read. It is not
  a managed Bedrock KB (that service is gated on this account), but it is a real, versioned,
  human-curatable registry: `registry_catalog.py` writes the yearly calendar without touching
  the registry file, so a curator can edit dates and the chain picks them up.

## Why this answers the proposal's claim

Proposal line 11: "Pasok is a four-agent system ... Each agent owns one narrow job, the way a
real planning team divides the work." Table above: four named agents, each owning one job,
each feeding the next through an artefact. Proposal line 22: "perceive, forecast, decide,
issue, learn" as one closed loop. Rows 1-5 are perceive+forecast, 6-7 decide, 8-9 issue, 10-11
learn. The loop is closed by `run_chain.sh`, which runs all of it in order.
