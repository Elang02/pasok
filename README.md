# Pasok

Autonomous reorder agent for Indonesian FMCG distributors. Four agents run one loop:
perceive, forecast, decide, issue, learn. Orders are issued under guardrails that keep
order variance close to demand variance, so the agent can plan for an event peak without
triggering the bullwhip effect.

Agentic AI Hackathon 2026, Track A (Intelligence Supply Chain), SOKRATES / BINUS Alam
Sutera. Team Pasok, Sistem Informasi, Universitas Katolik Atma Jaya.

**Status:** finalist top-40. Demo Day 31 October 2026, 15 minutes, English.

[![Demo Pasok: konsol menjawab "what runs out this week?"](media/demo-poster.jpg)](media/demo-day-2026.mp4)

Klik gambar untuk rekaman demo Demo Day (3 menit 52 detik, 28 MB). Versi bahasa Indonesia dari
halaman ini ada di [README.id.md](README.id.md).

## The four agents

| Agent | Job |
|---|---|
| Demand | weekly per-SKU forecast with interval, learned per-SKU event ramp, candidate events for human curation, explicit per-supplier buffer capped by shelf life |
| Stock Position | one true sellable figure (on-hand + in-transit + open PO), days of cover against forecast, coverage-floor and expiry-risk flags |
| Supplier Reliability | real lead time (p50/p90) and fill rate learned from receiving records, drift detection |
| Decision | orchestrator; auto-issue, hold one cycle, redirect to branch depot, or escalate, with a plain-language rationale on every decision |

Guardrails: forecasts smoothed before sizing, quantities dampened against the previous
order, per-order cap. Event uplifts sit outside the damping but inside the shelf-life cap.

## The Indonesian calendar, and what is deliberately not in it

The Demand Agent plans against a real calendar, not an arithmetic guess. Ramadan,
Lebaran and Nyepi come from the national holiday decrees (SKB 3 Menteri); Imlek from
the published lunar new year dates; THR is anchored to Lebaran because Permenaker 6/2016
requires the bonus to be paid at least 7 days before it.

The first version derived Ramadan from "11 days earlier per year" and Imlek from a
`year % 3` rule. Every Imlek date it produced was wrong by a week or more (2024-02-13
against the real 2024-02-10), and Ramadan missed 2025 by a day. A registry whose dates
are wrong cannot claim the "dates drift yearly" property the proposal sells, so the drift
is now a lookup against the official calendar.

Western observances are excluded on purpose. Valentine's Day and St Patrick's Day do not
move Indonesian general-trade volume, so modelling them would add registry rows that
predict nothing. `src/demand/registry_catalog.py` records that exclusion next to the
inclusions, so it reads as a decision rather than an oversight.

Verified from the generated data, not from the source:

```
Ramadan  2023-03-23  2024-03-11  2025-03-01  2026-02-18
Lebaran  2023-04-21  2024-04-09  2025-03-30  2026-03-20
Nyepi    2023-03-22  2024-03-11  2025-03-29  2026-03-19
Imlek    2023-01-22  2024-02-10  2025-01-29  2026-02-17
THR      2023-04-04  2024-03-23  2025-03-13  2026-03-03
```

## Run it

```bash
python -m venv .venv
.venv/bin/pip install pandas numpy pyarrow matplotlib
.venv/bin/python src/catalog/generate.py   # (re)build the synthetic catalog and its sales history
bash run_chain.sh                          # eleven programs, ends CHAIN OK
```

`src/catalog/generate.py` writes `data/catalog/sales.csv` (~240 MB), which is why it is not in the
repo; everything else the chain reads ships with it. The chain is deterministic and needs no accounts.
It ends `CHAIN OK`, after the `VERIFICATION PASS` line each agent prints when its own arithmetic
reconciles. Measured here: generation 1m29s, chain 49s.

Audit the build:

```bash
.venv/bin/python tools/integration_audit.py      # 11 hand-offs proven from artefacts
.venv/bin/python tools/test_cases.py             # TC-1 stockout within a week, TC-2 spike within a month
.venv/bin/python tools/proposal_conformance.py   # build vs REQUIREMENTS.md, live read from disk
.venv/bin/python tools/figures_gate.py           # the 42 figures the demo quotes, vs the artefacts
.venv/bin/python tools/target_measure.py         # the five proposal targets, measured per ABC class
.venv/bin/python demo/deck/check_deck_numbers.py  # every figure the deck quotes, read back from the PPTX
```

## Numbers

The artefacts committed under `data/` are the 31 October 2026 snapshot, reproduced by the two commands
above. Every figure below is read from the file named beside it.

| Measure | Value | File |
|---|---|---|
| Catalogue | 600 SKU, 120 outlets, 1,399 days, 10,034,120 sales rows | `data/catalog/meta.json` |
| SKU ordered / skipped | 470 / 130 | `data/agents/decision_summary.json` |
| Units after guardrails vs raw | 3,169,930 vs 3,194,155 | `data/agents/decision_summary.json` |
| Variance cap binding | 8 SKUs, cutting 24,225.4 units | `data/agents/decision_summary.json` |
| Orders issued | 470 auto (100%), IDR 30,123,910,900 | `data/orders/order_summary.json` |
| Warehouse occupancy | 3,195.1 of 12,500 m3 | `data/orders/order_summary.json` |
| Inter-branch transfers | 467 transfers, 5 depots, IDR 10,216,545,412 protected of IDR 15,512,068,197 at risk | `data/orders/redirect_summary.json` |
| Observed fill rate | 90.47% | `data/agents/learn_summary.json` |
| Median best held-out WAPE | 12.91% | `data/agents/learn_summary.json` |
| Below reorder / expiry risk | 38 / 6 | `data/stock/position_summary.json` |
| Lost sales over the replay | 880,472 units | `data/stock/position_summary.json` |

The demo documents quote an earlier snapshot (11–21 October 2026); `docs/MODUL_PASOK.md` carries the
21 October run, 139 order lines, IDR 13.42 bn auto-issued. Numbers move when the snapshot moves.

## Services

| Service | Unit | Port |
|---|---|---|
| Web console | `web/pasok-web.service` | 80 |
| MCP server (tools for SAP and AWS) | `tools/pasok-mcp.service` | 8086 |
| A2A server (agent card + MCP transport for Joule) | `tools/pasok-a2a.service` | 8085 |

Install:

```bash
sudo cp web/pasok-web.service /etc/systemd/system/
sudo cp tools/pasok-mcp.service tools/pasok-a2a.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pasok-web pasok-mcp pasok-a2a
```

## Layout

```
src/agents/      the four agents and the loop (perceive forecast decide issue learn)
src/catalog/     synthetic distributor catalog generator (SKU x outlet x week)
src/demand/      baselines, event registry, per-SKU ramp learner
src/sap/         sap-rpt-1.6 batch scoring, gpt-5.4 rationale
tools/           audits, backtests, benchmarks, the stand-in distributor ERP
web/             public read-only console, four pages
data/            artefacts the loop reads and writes (generated, mostly committed)
demo/            demo package: script, slides, figures, evals, architecture
aws/             AWS gate status and reproduction commands
simulation/      guardrail simulation on the Bank Indonesia retail index
experiments/     M5 event-ramp evaluation
sources/         panitia briefing PDFs
proposal_pasok_v2_canonical.txt   the submitted proposal, the source of truth
```

## What is not in this repo

`.planning/` (the build diary), `sources/panitia_pdfs/` (organiser briefing PDFs), the raw video
footage under `demo/video/` (the 3m52s demo edit ships as `media/demo-day-2026.mp4`),
`data/catalog/sales.csv` and `data/stock/stock_daily.csv` (both regenerated by the two commands above).

## What is real and what is a stand-in

Read `demo/evals.md` before quoting any number. In short:

- Scoring and reasoning run on SAP AI Core: sap-rpt-1.6 batch predict for
  days-of-cover / stockout / expiry, gpt-5.4 for the rationales.
- The human in the loop is Joule: `pasok_exception_queue` is live in the tenant.
- The AWS lane runs on Lambda with Bedrock through the Mantle endpoint. AgentCore
  Runtime is quota-0 on this account and Bedrock native `Converse` is account-gated;
  both are recorded with reproduction commands in `aws/GATES.md`.
- Orders leave the agent through a pluggable intake. The distributor ordering system is
  a stand-in ERP with its own rules, reference sequence and SQLite database, so the swap
  to a real ERP is one environment variable (`PASOK_ORDER_ENDPOINT`).
- Data is synthetic and realistic, which the organiser FAQ Q2 explicitly allows.

## Demo Day

`demo/deck/Pasok_DemoDay_2026.pptx` is the 13-slide deck, built by
the ppt-master project under `~/work/ppt-master/` and checked by
`demo/deck/check_deck_numbers.py` (every figure against its artefact). `demo/script_en.md` is the timed
15-minute script, every figure traced to `demo/figures.md`, which is rebuilt and checked
row by row by `tools/figures_gate.py`. `demo/slides_outline.md` follows the deck slide for
slide. `demo/one_pass.md` is the five-step trace for one rule-selected SKU, regenerated by
`bash run_chain.sh`.
