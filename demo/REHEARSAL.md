# Fifteen minutes, no live demo

Word-for-word script: `demo/TALK_SCRIPT.md` (1,792 words, 135 a minute). The clock below is read from that file, so the two cannot drift apart.

The room gets a deck, not a browser. Every screen the talk refers to is a capture from the
build that shipped, taken on 28 October from the console at `127.0.0.1:8090`.

| Clock | Page | What is said | What is on screen |
|---|---|---|---|
| 0:00 | 1 | Who we are, one sentence: Pasok decides what to reorder. | Title, 600 SKUs, 12 principals, 323 orders |
| 0:35 | 2 | The buyer's year: one person, 600 SKUs, a calendar that moves. Lebaran drifts 33 days; Christmas never moves. | Seven events, one dot per year, 2023 to 2026 |
| 1:35 | 3 | Orders swing harder than demand; three rules bring 2.68 to 0.24. | Bars, fill row, average stock |
| 2:55 | 4 | Four agents, one loop: each hands the next a number it can check. | Agent list and the supervised-autonomy line |
| 3:45 | 5 | This is the console, captured, not a mock-up: the nearest event and the products it moves. | The answer, large |
| 4:55 | 6 | One SKU, one order: stock, sales while the truck runs, what must land. | Ledger read from the trace |
| 5:45 | 7 | Why this order: Pasok's own arithmetic, one row at a time. | The order page, captured |
| 6:45 | 8 | The forecast learns the shape; the lead time is measured: 7.8% against 11.6%, fill 90.6% network. | Six rows, worst principal named |
| 8:00 | 9 | The three rules, and the replay that proves them: 1.25 to 0.32, shelf cap trims 7 of 600. | Three rules and the replay |
| 8:55 | 10 | SAP scores 600 in 10.73 seconds; AWS runs the chain; AgentCore is quota-blocked and we say so. | SAP and the lane |
| 10:00 | 11 | One snapshot in money: 323 orders, none waiting, because the rule is tested both ways. | Ledger of orders and rupiah |
| 10:50 | 12 | Where the numbers come from: the sales are generated, the calendar, prices and outside numbers are not. | Six rows, one line each |
| 11:45 | 13 | The five proposal targets: two met, three missed with their causes named. Then the ask: ninety days, four numbers a month. | Targets against results, then the pilot |

Buffer: 40 seconds. If the clock runs long, cut page 4 to one sentence and give page 13 its two minutes.

The video is a backup for the projector, not the talk: 53 seconds, one continuous screen capture of five console questions, narrated in English, captioned in English. Script: `demo/video/narasi/script_en.md`. File: `demo/video/Pasok_demo_en.mp4`. No cuts, no page reloads.

# Demo Day rehearsal: 15 minutes, English

Everything on screen comes from a file. Nothing in this script is a claim the pages do not
already show, and every number below is the number the page will show.

## The artefacts to submit

- `demo/deck/Pasok_DemoDay_2026.pptx` (13 slides). Authored as SVG in the ppt-master
  project and exported to native PowerPoint; every page passed the ppt-master quality
  gate. `demo/deck/check_deck_numbers.py` reads the PPTX and compares each figure against
  the artefacts, and `tools/figures_gate.py` guards the figures sheet it quotes.
- `demo/QA_BANK.md` (16 answers, each named to an artefact).
- `shots/` (the offline fallback, re-taken against the v4 artefacts).

## Timing

12 minutes talking, 3 minutes questions. Slides 1, 2 and 13 are short on purpose; the demo
screens carry the middle. If the clock runs long, cut slide 4 (the four agents) and say the
names over the architecture slide instead.

## Before Demo Day, deploy status (closed 2026-10-19)

The AWS endpoint was answering from the 11 October snapshot while the pipeline regenerated
its artefacts. Closed on 2026-10-19: the bundle was refreshed, the drift gate went green,
and the code was pushed with `PASOK_LAMBDA_FN=pasok-agent AWS_PROFILE=elang01
./tools/deploy_lambda.sh`. The endpoint answered HTTP 200 with the current artefacts
(fill 0.9110, WAPE 0.0871, 125 decisions, 22 held at that moment; the artefacts have since
moved to 0.9030, WAPE 0.1276, 323 orders, none held). If a redeploy is needed, the one command above is all
it takes; do not open the URL live until it has answered 200 that day carrying the numbers
in `demo/figures.md`.

## The one sentence to open with

Pasok is a replenishment agent that runs a real FMCG distributor's buying loop every day at
06:00, decides what to order and why, sends the orders, and learns from what actually
arrived. The console on screen is not a mockup: every figure on it is read from the file the
loop wrote, and a gate fails the build if a page disagrees with its own data.

## Order to show, and why

| # | Screen | What it proves | Time |
|---|---|---|---|
| 1 | `/` console, ask one question | It answers in plain language and shows its reasoning | 3 min |
| 2 | `/orders` | The loop runs daily and logs every run, with the reason per order | 2 min |
| 3 | `/receiving` | The honest half: 1,749 of 1,911 deliveries arrived short | 2 min |
| 4 | `/health` | What the network holds, by ABC-XYZ class | 2 min |
| 5 | `/transfers` | IDR 8.95bn of stock moved instead of bought | 2 min |
| 6 | `/cities` + `/suppliers` | Where it sells, and who delivers worst | 2 min |
| 7 | `/loop` + `/panel` | The schedule, the four checks, and the agent panel | 2 min |

Close on `/demo`, which is built for the judges, then stop talking and take questions.

## The questions to ask, verbatim

Ask these, do not type them live unless the connection is good. On `/` the console answers in
about four seconds and the reasoning line stays open.

1. `which SKUs run out this week, and is anything waiting for me?`
   Answer on screen: 11 of 600 SKUs run out inside a week, none of them dies before the next
   delivery can arrive, and all 11 already have an order — every one auto-issued, IDR
   193,071,250 of orders. Those eleven wait for nobody; the queue elsewhere is
   different question, so do not say "the queue is empty".
2. `what is the nearest event, and what product that spike`
   Payday on 25 October 2026, 14 days away, which moves nothing above noise; the next one that
   does is Christmas on 25 December 2026, 58 days away. **13 of 600 SKUs** move with it, all chocolate,
   1.35 to 1.69 times a normal day (Kakao Sari Cokelat Batang 100 g, 58 to 79 pcs a day), and no
   order has been stretched for it yet because the loop only sizes for the 30-day horizon.
3. `why did we order so much for SKU0012?` (an auto-issued order: the reasoning panel shows
   the sizing and the credit headroom it stayed inside)

Each answer shows **Thought for about 4 seconds** and four steps. Point at the last step: it
re-checks every number in the answer against the record and prints how many matched, a count
computed at read time rather than typed into the page. That is the difference between an agent
and a text generator.

## The four numbers to say out loud

- **1,911 deliveries** recorded, **1,749 came in short**, 706 took longer than promised.
  The buying is not the weak link, the delivery is.
- **5,735,261 units** of sellable stock held, and **4 SKUs** at risk of expiring, which
  the expiry check states with its own threshold.
- **IDR 8.95 billion** of stock moved between depots instead of bought again.
- **72.7%** less swinging in the orders because of the order rule. This is the bullwhip
  claim in the proposal, and it is on the Loop page in plain words.

## If a judge asks why suppliers ship short

One line, then move on. The suppliers fill 83 to 98 percent of what is ordered, so the agent
orders for that: it divides the order by the supplier's own fill rate, so what ARRIVES covers
the need. Every SKU has exactly one supplier here, so replacing them is not on the table. What
the agent does instead is order for the shortfall and put the drifting supplier in front of a
person. The delivered quantity is recorded per order, so a judge who wants to check can see
the ordered and the arriving count on the same row.

## What NOT to say

- Do not quote a percentage for the BI series: no artefact carries one. The measured claim is
  narrower and stronger: a fitted ramp beats a flat bump on M5 event windows, WAPE 0.0775
  against 0.1161 over 154 windows and 30,490 series (`experiments/e2_results.json`).
- Do not say all three guardrail rules produce the drop. Smoothing does the work; the
  damping sign is inverted and the variance cap does not bind in that simulation. Writeups
  are in DEFECTS.md.
- Do not claim the receiving figures are for the orders placed on 11 October. They are the
  full history up to that date, which is why the page says "up to the snapshot".

## If a judge asks about expiry, or about goods that die on the shelf

This one is a side experiment recorded in `demo/evals.md`, not reproducible from `data/` today:
the catalogue gives SKU0108 seven months of life, so the 21 days below is the what-if's own
override. Say that before the numbers if a judge asks where the scenario lives.

One line, then the numbers, then the limit: "The shortest life in this catalogue is one month and
7 SKUs sit at expiry risk, so the ceiling can bind here. We also tested it out of case: sixty
drinks given 21 days of life, ninety days, both arms from one opening state. The ceiling takes
29.8 percent off spoilage,
1,910,282 units down to 1,341,324, and costs 0.24 points of the period's demand, 2,737,797 unserved
units up to 2,857,452 out of
50,112,358. On a 21-day product on a 19.4-day lead, reviewed weekly, there is no slack: the target
wants 26 days of cover, the life allows 21. That is the policy limit the agent exposes, and the fix
is a shorter review cycle for fresh goods, with the ceiling already in the room."

If they want one SKU: SKU0108, a drink with 21 days of life, delivered in 19.4 days. The staged
ceiling limits one order to `shelf life minus one review window`, 14 days of demand or 16,406 units,
and goods already on the road do not consume it. Measured with the ceiling live and the snapshot
carrying the same shelf life the world uses, this SKU spoils 52,690 units instead of 100,194 and
never runs dry in either arm. The nineteen empty days it showed in earlier builds came from two
defects in the code, not from the product: the ceiling never fired, and the snapshot was built from
the catalogue's 180-day life instead of the 21-day override.

If they ask about shelf life: the clock starts when the goods land, so transit does not eat into
the 21 days, and an earlier ceiling that subtracted delivery time was counting the journey twice
and has been corrected. The line is refused only when delivery takes longer than the goods last,
and with a 19.4-day lead against 21 days of life nothing in this scenario is refused on that ground.

The guard does pay for itself, measured: 29.8 percent less spoilage for 0.24 points of demand, and
the table that shows it is in `demo/evals.md`. The earlier line that said no setting pays for itself
was written while two defects were hiding the guard, and it is withdrawn.

## Screenshots

Prepared in `shots/demo-*.png`, 11 pages plus two clipped versions of the tall ones
(`02-orders-top`, `05-transfers-top`) for slides. Regenerate any time with:

    .venv/bin/python tools/demo_shots.py

The script drives a real headless Chrome over CDP, waits for each page to finish reading its
endpoint, opens the reasoning panel on the chat, and prints the measured page height and the
row count it found, so a blank page cannot pass as a screenshot.

## What winners do (research, from people who judge)

Sources: JetBrains "How to Win a Hackathon: Notes From the Judging Table" (June 2026, quotes
from judges at stateshift, Scarf, OpenAI, JetBrains, Nebius), Masai "How to win an AI
Hackathon in 2026", lablab "Winning AI Hackathons". Their answers line up with our rubric.

The rules, in the words of the people who score:

1. **Make the judges feel the problem before showing anything.** "Get your audience of
   judges sharing your frustration with the problem." Our opening must be the distributor's
   pain in numbers, not our stack.
2. **Something working within about 90 seconds.** Take the problem, show the solution, fast.
   Our answer: the year timelapse (one minute) plus one chat question, both in the first
   three minutes.
3. **One "oh, this is possible now" moment beats a feature tour.** Ours: "the loop has run
   every day since the handover, here is the month replaying" with stockouts coming down.
4. **Put the judges in the user's shoes.** Walk them through the buyer's morning on the
   console, not through our architecture diagram.
5. **Be direct about what works and what does not.** "Honesty reads as confidence."
   Say the March limit plainly: a two-week lead time cannot beat a same-week peak.
6. **Mock every stall.** Pre-fill, no slow calls, no login. Our console is deterministic
   from artefacts and the chat answers in about four seconds.
7. **Cut features; the demo is the scope.** Eleven screens is already the ceiling. Adding
   more makes every pitch longer.
8. **Practice out loud, timed.** Teams that practiced look like they practiced.

## Mapped to the SOKRATES rubric

- **Tech exec, AWS/SAP, 25%** (the single heaviest line): the SAP AI Core call is real and
  shown in the answer trace, but it is one line today..Name the AWS/SAP pieces per screen and
  consider a slide of the architecture with the same numbers on it.
- **Demo, 20%**: strong (eleven screens, one flow, deterministic). Demo the buyer's day, not the
  system.
- **Innovation, 20%**: the differentiators are the guardrails story, the honest scorecard,
  and a year of operating history nobody else will have. Say them in that order.
- **Presentation, 20%**: rehearse with a timer; 15 minutes means about 2 minutes per screen
  and we have seven screens plus questions. Script the opening and the close.
- **Fit, 10%**: the FMCG distributor specificity is the fit evidence: 600 SKUs, 12 suppliers,
  120 outlets, traditional trade share. Say the numbers, they are all on screen.
- **QA, 5%**: the gates are the story: 42 figures checked against artefacts, 16 answers read
  as plain language, 11 integration checks. One sentence, then move on.

## The one-sentence test

If a judge can repeat our pitch to the next judge, we win the demo section. Draft: "This
distributor used to buy by hand and half its deliveries came late. Since January an agent has
placed every order, without a person, and we replay its whole year."
