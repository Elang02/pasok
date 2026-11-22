# Pasok

Autonomous reorder agent for Indonesian FMCG distributors. Four agents run one loop:
perceive, forecast, decide, issue, learn. Orders go out under guardrails that keep order
variance close to demand variance, so the agent can plan for an event peak without
triggering the bullwhip effect.

Agentic AI Hackathon 2026, Track A (Intelligence Supply Chain), SOKRATES / BINUS Alam
Sutera. Team Pasok, Sistem Informasi, Universitas Katolik Atma Jaya.

**Status:** finalist top-40. Demo Day 31 October 2026, 15 minutes, English.

[![The Pasok console answering "what runs out this week?"](media/demo-poster.jpg)](media/demo-day-2026.mp4)

Click the poster for the Demo Day recording (3 minutes 52 seconds, 28 MB).

## The four agents

| Agent | Job |
|---|---|
| Demand | weekly per-SKU forecast with interval, learned per-SKU event ramp, candidate events for human curation, explicit per-supplier buffer capped by shelf life |
| Stock Position | one true sellable figure (on-hand + in-transit + open PO), days of cover against forecast, coverage-floor and expiry-risk flags |
| Supplier Reliability | real lead time (p50/p90) and fill rate learned from receiving records, drift detection |
| Decision | orchestrator; auto-issue, hold one cycle, redirect to branch depot, or escalate, with a plain-language rationale on every decision |

Guardrails: forecasts smoothed before sizing, quantities dampened against the previous
order, per-order cap. Event uplifts sit outside the damping but inside the shelf-life cap.

## The Indonesian calendar

The Demand Agent plans against a real calendar instead of an arithmetic guess. Ramadan,
Lebaran and Nyepi come from the national holiday decrees (SKB 3 Menteri); Imlek from
the published lunar new year dates; THR is anchored to Lebaran because Permenaker 6/2016
requires the bonus to be paid at least 7 days before it.

The first version derived Ramadan from "11 days earlier per year" and Imlek from a
`year % 3` rule. Every Imlek date it produced was wrong by a week or more (2024-02-13
against the real 2024-02-10), and Ramadan missed 2025 by a day. A registry whose dates
are wrong cannot claim the "dates drift yearly" property the proposal sells, so the drift
is now a lookup against the official calendar.

Valentine's Day and St Patrick's Day are left out on purpose. They do not move Indonesian
general-trade volume, so modelling them would add registry rows that predict nothing.
`src/demand/registry_catalog.py` records that exclusion next to the inclusions.

Checked against the generated data rather than the registry source:

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

`src/catalog/generate.py` writes `data/catalog/sales.csv` (about 240 MB), so that file is
not in the repo; everything else the chain reads ships with it. The chain is deterministic
and needs no accounts. Each agent prints `VERIFICATION PASS` when its own arithmetic
reconciles, and the run ends `CHAIN OK`. Measured here: generation 1m29s, chain 49s.

Audit the build:

```bash
.venv/bin/python tools/integration_audit.py      # 11 hand-offs proven from artefacts
.venv/bin/python tools/test_cases.py             # TC-1 stockout within a week, TC-2 spike within a month
.venv/bin/python tools/proposal_conformance.py   # build vs the proposal, live read from disk
.venv/bin/pip install python-pptx                # only for the deck check
.venv/bin/python demo/deck/check_deck_numbers.py  # every figure the deck quotes, read back from the PPTX
```

Two checks need artefacts this repo does not ship: `tools/figures_gate.py` reads the SAP
scoring output (`data/sap/rpt_summary.json`) and `tools/target_measure.py` reads a replay
set (`data/sim/replay2026_m/world/stock_daily.csv`). The hand-off audit, the test cases and
the deck check run on what is here.

`check_deck_numbers.py` reports nine drifted claims. The deck was built for the 21 October
Demo Day and quotes that snapshot (137 orders, IDR 7.71 bn), while `data/` here is the
31 October snapshot that `bash run_chain.sh` produced. Re-running the chain will not
reproduce the demo numbers, because `src/catalog/generate.py` seeds history up to the day
it runs.

## Numbers

The artefacts under `data/` are the 31 October 2026 snapshot, produced by the two commands
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

The demo documents quote earlier snapshots from 11 to 21 October 2026. `docs/MODUL_PASOK.md`
carries the 21 October run: 139 order lines, IDR 13.42 bn auto-issued.

## Run the console locally

```bash
.venv/bin/pip install -r requirements-web.txt
PASOK_WEB_PORT=8080 .venv/bin/python web/app.py
```

Then open http://localhost:8080. The console reads `data/` as `run_chain.sh` left it, so
the pages show the snapshot that was just produced. Checked here on Python 3.8 with fastapi
and uvicorn installed: `/`, `/orders`, `/loop`, `/health`, `/suppliers`, `/transfers`,
`/catalog` and `/panel` all return 200.

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
web/             public read-only console, ten pages
data/            artefacts the loop reads and writes (generated, mostly committed)
demo/            demo package: script, slides, figures, evals, architecture
aws/             AWS gate status and reproduction commands
simulation/      guardrail simulation on the Bank Indonesia retail index
experiments/     M5 event-ramp evaluation
proposal_pasok_v2_canonical.txt   the submitted proposal, the source of truth
```

## What is not in this repo

`.planning/` (the build diary), `sources/panitia_pdfs/` (organiser briefing PDFs), the raw
video footage under `demo/video/` (the 3m52s demo edit ships as
`media/demo-day-2026.mp4`), `data/catalog/sales.csv` and `data/stock/stock_daily.csv`
(both regenerated by the two commands above).

## What is real and what is a stand-in

Read `demo/evals.md` before quoting any number.

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

`demo/deck/Pasok_DemoDay_2026.pptx` is the 13-slide deck. The ppt-master project under
`~/work/ppt-master/` built it, and `demo/deck/check_deck_numbers.py` checks every figure
against its artefact. `demo/script_en.md` is the timed 15-minute script, with every figure
traced to `demo/figures.md`, which `tools/figures_gate.py` rebuilds and checks row by row.
`demo/slides_outline.md` follows the deck slide for slide. `demo/one_pass.md` is the
five-step trace for one rule-selected SKU, regenerated by `bash run_chain.sh`.

## Documents

| File | What it is |
|---|---|
| `docs/MODUL_PASOK.md` | the 22-section module, written in Indonesian for the Indonesian panel |
| `docs/MODUL_PASOK.pdf` | the same module as a print-ready PDF |
| `docs/AUDIT_MODUL.md` | every figure in the module checked against the artefacts |
| `demo/script_en.md` | the timed 15-minute Demo Day script |
| `demo/evals.md` | what is proven and what is not |
| `proposal_pasok_v2_canonical.txt` | the proposal as submitted |

## Credits

Built by Vicentius Elang Krisnanto for Agentic AI (SAP) 2026. MIT licence, see `LICENSE`.
Contact: elangk111@gmail.com · [github.com/Elang02](https://github.com/Elang02)
