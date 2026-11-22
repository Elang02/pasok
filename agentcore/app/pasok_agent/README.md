# Pasok Agent — AgentCore Runtime

Four-agent replenishment system for an Indonesian consumer-goods distributor, exposed
on Amazon Bedrock AgentCore Runtime.

- **Demand Agent** — weekly forecast per SKU with event ramp (Imlek, Lebaran, Nyepi,
  Christmas, THR, payday)
- **Stock Position Agent** — live sellable stock, days of cover, reorder/expiry flags
- **Supplier Reliability Agent** — learned lead times (p50/p90) and fill rate, not the
  catalog promise
- **Decision Agent** — orchestrator: auto-issue, hold, redirect, or escalate, always
  with a plain-language rationale

The runtime answers questions about the replenishment state by querying the four
agents' artifacts in `./data/`. All figures are grounded in those files.

## Run locally

```bash
uv sync
uv run python main.py     # serves POST /invocations and GET /ping on :8080
```
