# Pasok: the talk, word for word

Fifteen minutes, thirteen pages, English. The deck is the evidence; this file is what you say over
it. Timings come from the words themselves at 135 a minute, rounded up to the next five seconds, so
nobody has to talk faster than a normal pace for a room this size.

| Time | Page | Seconds | Words |
| --- | --- | --- | --- |
| 0:00 | 1 cover | 35 | 74 |
| 0:35 | 2 the moving calendar | 60 | 132 |
| 1:35 | 3 orders swing harder than demand | 80 | 170 |
| 2:55 | 4 four agents, one loop | 55 | 122 |
| 3:50 | 5 the nearest event, in words | 65 | 143 |
| 4:55 | 6 one SKU, one order | 65 | 146 |
| 6:00 | 7 why this order | 60 | 132 |
| 7:00 | 8 forecast and lead time | 80 | 172 |
| 8:20 | 9 three rules | 55 | 123 |
| 9:15 | 10 SAP and AWS | 80 | 170 |
| 10:35 | 11 the live demo | 70 | 156 |
| 11:45 | 12 where the numbers come from | 50 | 110 |
| 12:35 | 13 five results beside published numbers | 100 | 221 |
| 14:15 | buffer | 45 | |

---

## 0:00 — Page 1, cover (35 s, about 74 words)

Good morning. I am presenting for Team AIGO, from BINUS Alam Sutera.

Pasok answers one question every morning: what should we reorder today, and why. Six hundred SKUs,
twelve principals, 1,396 days of history behind it.

One loop decides. Every decision carries the numbers that produced it, so a buyer can check the
work instead of trusting it.

First the problem, then the loop, then the money, and then where each number comes from.

---

## 0:35 — Page 2, the moving calendar (60 s, about 132 words)

A reorder point is usually set once and left alone. Here is why that fails.

Lebaran moves thirty-three days across four years. Imlek moves twenty-six. Nyepi moves seventeen.
Christmas and New Year stay where they are. One row for each event, one dot for each year: the dots
that drift are the ones that cost money.

A buyer who sets the point in January buys for the wrong week by March, and the same mistake
returns every year. With six hundred SKUs, nobody re-checks six hundred dates by hand.

So the calendar is an input to the ordering rule. Every order in this deck is sized against the date
that will actually happen, not the date that happened last year. That single change is what the rest
of this deck builds on.

---

## 1:35 — Page 3, orders swing harder than demand (80 s, about 170 words)

Left alone, ordering makes demand worse. We replayed two hundred fifty days of demand, a series calibrated to the Bank Indonesia retail
index, with the guardrail switched off, and orders swung 2.68 times as hard as the demand they were trying to serve.
That is the bullwhip, measured on one aggregate series we can switch rules on and off in.

Switch three rules on and the swing falls to 0.24 times.

The cost is real and small: fill rate goes from 98.93 to 98.68 percent, a quarter of a point.
Average stock falls from 2,187 units to 274: the same fill on about a tenth of the shelf.

The rules do not buy better service with more stock. They remove the overshoot, and the shelf gets
shorter as a side effect.

Hold on to that pair of numbers. It is the whole argument for a guardrail. One caution while you read
it: this is one aggregate series, not the six hundred SKUs, so take the direction, not the exact size.

---

## 2:55 — Page 4, four agents, one loop (55 s, about 122 words)

The loop has four agents, and each one answers a single question.

When does each SKU's ramp start? That part is learned. What is sellable, on order, and in transit?
That part is measured. What lead time and fill rate does each principal actually deliver? That comes
from 1,975 receipts. And what should we send, hold, and why? The system writes that down.

Each agent hands the next a number it can check. The rules set the quantity. The model writes the
reason, and only the reason.

An order above the SKU's peak-day rate times its cover window, plus five percent, goes to a manager;
nothing this morning did. The loop runs once a morning at six, before the buying desk opens.

---

## 3:50 — Page 5, the nearest event, in words (65 s, about 143 words)

This is the console, asked in plain words: which event is nearest, and which products does it move?

The answer comes back with the date, the distance to it, and the products. Christmas, 25 December
2026, fifty-eight days out. Thirteen of six hundred SKUs move. The other five hundred eighty-seven stay
within ten percent of a normal day.

Three products climb. Kakao Sari Cokelat Batang, from 58 to 79 a day, 1.35 times. Manis Raya
Cokelat Koin, 48 to 74, 1.53 times. Kakao Sari Bubuk, 50 to 71, 1.42 times.

The point is not that a model can talk. The point is that every sentence carries a number a buyer
can open the catalogue and check.

Ask for the arithmetic and the same screen prints the rows it used: which ramps, which dates, which
multipliers, each traceable to a file in the repository.

---

## 4:55 — Page 6, one SKU, one order (65 s, about 146 words)

One SKU, end to end. SKU0436, biscuits, principal P12.

The loop ordered 417 units, against an eighteen-day lead, a seven-day review, and a six-day buffer.
Cover target is thirty-one days. On the shelf tonight, 1,743 units, five and a half days; with what is on the road and on order, 44.8,
which is why this is not a full restock. Stock when the lot lands is 2,930, demand until the next
arrival 3,340: a gap of 407, and at 97.6 percent fill, 417 goes out.

The reorder point is eighteen days. Fill on this item is 97.6 percent, with ten units short.

Why only 417: the rule escalates above 10,763 units over this window. This order sat below that, so
it went out on its own.

Every one of those numbers is read from the same trace the system used. Nothing here is a later
reconstruction.

---

## 6:00 — Page 7, why this order (60 s, about 132 words)

This is the receipt. The screen reads top to bottom: stock on hand, what sells while the truck runs,
what has to land, the gap, the order, and the reason beside it.

The escalation rule says inside policy limits. Notification went to P12. The ordering system
reference is SO-2026-000284.

That paragraph at the bottom is the rule's own template, the same numbers in sentences. The stock
available now has to carry about 7,500 units until the lot after this one lands. About 4,572 sell
while the truck runs. Demand between arrivals
is about 3,340. What is left is 407 units, spread across the supplier's lead time.

That covers 98 percent of what was asked, on a 31-day target: 18 days of lead, 7 of review, and 6
of allowance.

---

## 7:00 — Page 8, forecast and lead time (80 s, about 172 words)

Two forecasts, tested over 154 event windows on the public M5 retail dataset. The learned shape
misses 7.8 percent of demand. A flat
bump on the holiday date misses 11.6 percent. The learned shape misses about a third less.

It also catches 120 of 120 spikes that never made it into the event calendar, at a false-alarm rate
under one day in a hundred.

Lead time is measured, not assumed. Fill on arrival is 90.60 percent across 1,975 receipts. The
worst principal, P06, sits at 82.9 percent, and the console strip on the page is that same record
with its own rounding.

Nine of the twelve principals deliver below 95 percent of what we ask, so each one carries its own
buffer instead of a house average, sized from that principal's lead-time spread, our forecast error
and the tail of its late deliveries.

I will say the uncomfortable part myself: 90.6 percent is not a good number. It is what our receipts
produce, and a pilot should start from what is true.

---

## 8:20 — Page 9, three rules (55 s, about 123 words)

Three rules keep one order honest.

Smooth the forecast, so the last week alone does not decide. Hold back a jump, from 1.25 to 0.32
times over the replay. Cap one delivery at what the shelf can actually sell before it expires.

Seven SKUs were trimmed this morning, ten thousand twenty-eight units, all by the shelf-life cap; the
other two cut nothing. It is on the page because a guardrail still sets the ceiling every order passes
under, whether or not it fires today.

The evidence is the replay, not this page. Over 250 days the rules cut the swing to 0.24 times and
cost a quarter point of fill. That is what a controlled system looks like when you show it honestly.

---

## 9:15 — Page 10, SAP and AWS (80 s, about 170 words)

SAP scores six hundred SKUs in 10.73 seconds. On 89.5 percent of them SAP's flag and ours agree, but
that is a base rate: the two never flag the same SKU. Forty of forty rationales came back written
rather than templated.

The chain is short: SAP scores, AWS runs the loop, Bedrock on Mantle writes the reason. The same
chain is packaged as a Lambda in the AWS lane, and on this laptop it runs on a six o'clock timer,
so a bad morning in either cloud cannot stop the orders. The AgentCore runtime is written and
blocked by a quota of zero, and we say that rather than pretend it is live.

SAP calls 577 SKUs near expiry and not one stockout. Our loop watches the calendar and the shelf;
SAP watches the shelf. Where they disagree, the buyer sees both flags and decides.

That split is deliberate: the scoring is deterministic, the writing is cheap to redo. If the model
misbehaves, the numbers it describes do not move.

---

## 10:35 — Page 11, the live demo (70 s, about 156 words)

Page eleven is the money page, and I am going to skip it, because the loop is running and you can see the money yourself. [open http://43.134.92.128:8090]

This is the screen the buyer opens. I type the question the way a buyer asks it: which is the nearest
event. [type it] The answer names Christmas, fifty-five days from today, thirteen of six hundred SKUs,
and the biggest mover, Kakao Sari, fifty-eight to seventy-nine a day. None of that sentence was typed
by hand. Every number was read from what the morning loop wrote.

Now the morning itself. [open /orders] The loop runs at six every morning; today we re-ran it at 11:55
after extending the data, which is why the top row says 11:55. That pass placed 470 orders, 470 without a
person, zero waiting, 30.12 billion rupiah, and nothing worth IDR 0 waiting. The table under it is
the buying record, a replay that stops on 22 October, which is why it looks quieter than this morning.

[back to the deck, page 12]

---

## 11:45 — Page 12, where the numbers come from (50 s, about 110 words)

I want to be exact about what is real here.

The sales, the stock, the lead times and the fill rates are generated. Seed 20261008, six hundred
SKUs, a hundred twenty outlets, 1,396 days.

Everything outside that is real. Prices from PIHPS, October 2026. Event dates from the civil, lunar
and Saka calendars. Uplift and shape from GAPMMI, Antara, NielsenIQ, and search interest for the days
around each event.

So this is a simulated catalogue, and these results are a ceiling rather than a forecast. A pilot
replaces every generated row with a year of your own order lines and receipts, and then the same
loop reports on your numbers.

---

## 12:35 — Page 13, five results beside published numbers (100 s, about 221 words)

Last page, and this one has a rule: every outside number on it comes from outside this project.

Fill rate on A-class, 99.89 percent. A shopper visiting a store finds about 92 percent of items on
the shelf; that is the Corsten and Gruen figure, and the GMA study puts out-of-stock at 8.3.

Demand we lost, 0.54 percent, against that 8.3.

Days of inventory, 22. Indofood CBP reports 56.7 in its 2025 accounts, from a published paper that
we cite on the slide.

Expiry, 0.21 percent of cost of goods. Supermarket shrink in the shrink survey runs about 2.70
percent of sales.

Lines needing a person, 1.3 percent of the catalogue, against our own ceiling of ten.

Four of five sit beside a published number; the fifth is our own ceiling. The promise we missed is one we made to
ourselves: write-off rose while A-class cover went to 99.9 percent. That is a trade we chose, and the
pilot is where we tune it.

Here is the ask. Ninety days on your own records. No change to how buyers work: the loop drafts, a
person approves, every line carries its reason. Four numbers come back monthly, and at day ninety you
decide whether it stays.

One loop, six hundred SKUs, a reason beside every line. Thank you. I will take questions.

---

## If the clock runs long

Cut page 10 first, then page 3. Page 3's two numbers, 2.68 and 0.24, can move into the answer to a
question, and page 10's SAP split can be one sentence. Never cut page 13: the ask lives there.

## If the projector fails

Talk from page 6 and page 13 only. SKU0436 at 417 units, then the five benchmark rows. Both sets are
short enough to hold in your head, and the pilot ask needs no screen.

## Four questions to rehearse out loud

| Question | Answer, in one breath |
| --- | --- |
| Is the data real? | Sales and stock are generated from seed 20261008; prices, calendars and uplift are real sources. Page 12 lists which is which. |
| Why is fill only 90.6 percent? | Because we measure fill on arrival from 1,975 receipts, not fill on the order. Nine of twelve principals underfill, and each carries its own buffer. |
| What if the model writes a wrong reason? | The reason quotes the numbers the rule used, one by one, and a buyer can check each. The trace sits in `data/agents/one_pass.json`, not in the prose. |
| Why should we trust 22 days of inventory? | It comes from the replay, not from a target: the unguarded run sits at 2,187 units of average stock, the guarded run at 274, with fill down a quarter of a point. |

## Where each number in this script comes from

| Number | File |
| --- | --- |
| 2.68 and 0.24 times, fill 98.93 and 98.68, stock 2,187 to 274 | `simulation/results.json` |
| 1.25 to 0.32 times over 104 days | `data/agents/decision_summary.json` |
| 7.8 and 11.6 percent, 120 of 120 spikes, 154 M5 event windows | `experiments/e2_results.json` |
| 90.60 percent fill, P06 at 82.9 | `data/agents/supplier_reliability.csv` |
| 470 orders, 30.12 bn, 0 escalated | `data/orders/last_run.json` |
| 477 surplus SKUs, 10.22 bn | `data/orders/redirect_summary.json` |
| 1,743 on hand, 44.8 days, 4,572 sold in lead, 2,932 at arrival, 3,340 window, 407 gap, 417 units, 10,763 ceiling, 97.6 percent | `data/agents/one_pass.json` |
| 13 of 600, 58 to 79, 48 to 74, 50 to 71 | `data/demand/sku_ramps.csv` |
| 10.73 seconds, 89.5 percent, 577 near expiry, 0 stockouts | `data/sap/rpt_summary.json` |
| 40 of 40 written reasons, 0 templated | `data/sap/rationale_summary.json` |
| 0.54 (lost over sold plus lost), 22 days, 0.21, 1.3 percent | `data/agents/outcomes.json`, `data/sim/replay2026_v29/days.csv` |
| 600 SKUs, 120 outlets, 1,396 days, seed | `data/catalog/meta.json` |
