# Pasok — Demo Day Script (English, 15:00)

**Event:** Agentic AI Hackathon 2026, Track A (Intelligence Supply Chain)
**Team:** Pasok — Vicentius Elang Krisnanto, Joshua Sahusilawane, Bintang Neera
**Venue:** BINUS Alam Sutera · **31 October 2026** · 15 minutes · English

Every figure spoken below has a row in `demo/figures.md`. Numbers are quoted from the
committed artefacts, never from memory.

---

## 0:00–1:30 — The problem

**Say:**
> "A distributor's buyer places orders by hand, and when a holiday approaches they
> order more. Sounds harmless. But when every buyer in the chain does that at the same
> time, small demand changes become huge order swings. That is the bullwhip effect, and
> it is the known failure mode of automated reordering.
>
> We built Pasok: an autonomous reorder agent that plans for the event peak without
> triggering the bullwhip. And we can prove the difference. On the official Bank
> Indonesia retail sales index, an unguarded reorder policy amplifies demand variance
> to **2.68 times**. Ours brings it down to **0.24 times** — with fill rate intact at
> **0.9868**."

**Show:** slide with the two amplification bars (F1, F2) and both fill rates (F3, F4).

---

## 1:30–5:00 — Demand Agent + Stock Position Agent

**Say:**
> "Four agents run the loop. The Demand Agent turns outlet history into a weekly
> forecast per SKU with a confidence interval. The hard part is events: Lebaran and
> Imlek move every year, and each SKU ramps differently. Instead of a flat bump, we
> learn a build-peak-decay ramp per SKU. On 154 held-out event windows that beats a
> flat bump by **33.3%** WAPE, over all 30,490 M5 series.
>
> The Stock Position Agent computes one true sellable figure — on-hand plus in-transit
> plus open purchase orders — and days of cover against the forecast, with two flags:
> coverage floor and expiry risk."

**Show:** forecast plot for one SKU with the ramp (F6, F7, F8, F9); the position table
for the same SKU.

---

## 5:00–8:00 — Decision Agent + guardrails (the differentiator)

**Say:**
> "The Decision Agent orchestrates. It weighs holding cost, service level, supplier
> risk, credit headroom, shelf life, and the event ramp. Then three fixed guardrails
> run: smooth the forecast before sizing, dampen against the previous order, and cap
> the per-order variance.
>
> In the live build across **600 SKUs**, the loop issued **137 orders** — **130
> auto-issued (94.9%)**, **7 escalated** for a human. That is **1.2% of the catalog**
> needing a person, against the proposal's under-10% target. Unguarded ordering
> would have moved **680,072 units**; the guarded loop moved **437,960** — the cap
> alone cut 242,112 units. And every decision carries a plain-language rationale."

**Show:** the guardrail diagram (G1/G2/G3) and the live decision summary (F10–F18).
Click one escalated order and read its reason aloud.

---

## 8:00–11:00 — SAP AI Core + Joule (human in the loop)

**Say:**
> "Scoring and reasoning run on SAP AI Core. **sap-rpt-1.6** scores the catalog on
> three targets — days of cover, stockout, expiry — and agrees with our agent at
> **0.72** across all 600 SKUs. The rationale you are reading was written by
> **gpt-5.4** through the orchestration deployment, one per exception SKU.
>
> And this is where the human stays in the loop. Joule surfaces the exception queue.
> The buyer sees exactly why an order was escalated — say, value above the auto limit,
> or over the SKU credit line — and approves it."

**Show:** the Joule queue (`pasok_exception_queue`) and approve one escalated order
live (F19, F20, F21). **This is the SAP moment — let it breathe.**

---

## 11:00–13:00 — AWS lane (live)

**Say:**
> "The agent runs on AWS. The four-agent reasoning layer is a Lambda function, and the
> brain is Amazon Bedrock — a live model through the Bedrock Mantle endpoint. SAP AI
> Core is the scoring and reasoning layer, and it is the fallback brain. Watch —
> I will ask it a live question over HTTPS."

**Do:** POST to the Function URL:
`https://vyfesxclb5gwzqqkg5csbkgxeq0jdnpf.lambda-url.us-west-2.on.aws/`
with `{"action":"ask","prompt":"..."}` or `{"action":"exceptions"}`. The response must
quote a real SKU and a real number.

**Fallback ladder, in order:**
1. Play the recording made the day before.
2. If the live call fails, walk `demo/one_pass.md`: the same five-step loop with the
   rule-selected SKU (SKU0536), every number from the committed artefacts
   (`bash run_chain.sh` regenerates it). Say plainly that the endpoint is unreachable
   from the venue and the trace shows exactly what it returns.

Never fake a live call.

**Note for the judges (if asked about AgentCore):** the AgentCore variant is written
(`agentcore/app/pasok_agent/`), but this account's Bedrock inference is behind an
account-authorization gate and its AgentCore runtime quota is 0 pending AWS review.
The working path is the Mantle endpoint, and the Lambda lane is the same agent, same
tools, same data, running on AWS today. Full detail and reproduction commands:
`aws/GATES.md`.

**Note for the judges (if asked about planning or M5):** the build was planned in GSD
(`.planning/`, 10 phases, 40 plans with execution summaries), not Kiro, and
the ramp evaluation aggregates all **30,490** M5 series over 154 held-out event windows
(ramp WAPE 0.0775 vs flat-bump 0.1161). Claims map:
`demo/evals.md`.

---

## 11:45–13:00 — The order leaves the agent (distributor ordering system)

**Say:**
> "A decision is only worth something if the order actually reaches the distributor's
> ordering system. Our intake posts every auto-issued order into that system and takes
> its answer: the system issues its own reference, rounds to its own pack size, sets the
> promised delivery date from the lead time we learned, and posts the goods receipt back.
>
> We submitted **130 orders**. All 130 were accepted, 130 of them **partial** — the
> system rounded to its own pack size and shorted us 1,460 units on 393,260 ordered.
> Seven orders never left: five sat above the Rp 200 million signing line and two fell
> under the supplier's minimum order value. Those seven go to the human queue with the
> reason attached. We do not lose them and we do not override the distributor.
>
> Nothing here is hard-wired to one vendor: the same intake talks to a file-backed desk
> for the demo and to an HTTP endpoint for a real ERP. Switching it is one environment
> variable."

**Show:** `data/orders/intake_summary.json` (submitted / partial / shortfall counts), two rows of
`order_acks.csv` (reference issued by the system, pack size, promised delivery). Then
`demo/one_pass.md` §4, which states where the traced PO went.

**If asked whether this writes to SAP:** no. SAP is the scoring and reasoning layer here
(RPT-1.6 + gpt-5.4); the ordering system is a pluggable intake proven against a stand-in
ERP. A distributor's OData endpoint plugs in without a rewrite. Detail: `demo/evals.md`.

---

## 13:00–15:00 — Results and close

**Say:**
> "On the pilot metrics we are targeting a 25% cut in stockout incidents on A-class
> SKUs, a 15% cut in average inventory value on C-class, and fewer than 10% of the
> catalog reviewed manually. The guardrailed loop is the reason it is safe to let the
> agent order at all.
>
> Pasok plans for the event peak without triggering the bullwhip. Thank you."

**Show:** the pilot metrics table (from PROJECT.md §Success Metrics). Stop talking
before the timer.

---

## Timing budget

| Section | Minutes | Cumulative |
|---|---|---|
| Problem | 1.5 | 1:30 |
| Demand + Stock Position | 3.5 | 5:00 |
| Decision + guardrails | 3.0 | 8:00 |
| SAP AI Core + Joule | 3.0 | 11:00 |
| AWS lane + order intake live | 2.0 | 13:00 |
| Results + close | 2.0 | 15:00 |
| **Total** | **15.0** | |

## Backup recording

- Capture 1920x1080, 30 fps, MP4, with system audio and microphone.
- Record the full 15 minutes the day before Demo Day, once the runtime is live.
- Store as `demo/backup/pasok_demo_<date>.mp4` on the presenter laptop and a USB
  stick. Test playback on the venue laptop before the session.
