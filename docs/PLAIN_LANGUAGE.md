# Plain language contract

Elang, 18 Okt 2026: "saya gamau ada jargon jargon gitu di dalam jawabannya maupun di web
ini, saya mau responnya tuh yang dibutuhkan aja, benar benar informasi nyata".

This applies to every string a buyer reads: the six answers, the panel, the loop map, the
demo page, and anything a model writes.

## Rule 1: say what the reader needs, then stop

Every answer opens with the thing asked for. No preamble, no restating the question, no
"so", "thus", "therefore", "overall", "note that", "it is worth noting", no closing
summary of what was just said. If a line is not a number the reader acts on, a
recommendation they can act on, or the reason behind it, delete the line.

## Rule 2: no machine output

Never let a raw value reach the reader:

| never | write |
|---|---|
| `nan`, `NaN`, `None`, `-`, empty | `none` |
| `HOLD_ONE_CYCLE`, `ESCALATE_TO_HUMAN`, any `SCREAMING_SNAKE` | the sentence in the Action table below |
| `->` | a sentence, or `to` |
| `17521.3u`, `460.0u/day` | `17,521 units`, `460 units a day` |
| `x1.40` | `1.4 times normal` |
| `0.850` | `85%` where the reader is a buyer, three decimals only where it is a score |
| `**Rationale.**` | `**Why:**` |
| backticked field names, CSV column names, file paths | the plain phrase, or nothing |

## Rule 3: no unexplained shorthand

The words below are recognized in the proposal and stay, but each one gets its plain
phrasing the first time it appears in an answer body. Never in a sentence, only as the
label of a figure the reader can see.

| shorthand | plain phrasing |
|---|---|
| days of cover | days of stock left |
| sellable | available now |
| velocity, units/day | sold per day |
| lead time, lead p90, upper bound, learned | delivery time, worst case |
| fill rate | share of the order the supplier actually delivers |
| OTIF | share delivered complete and on time |
| WAPE, forecast error | forecast miss |
| guardrail | order rule |
| amplification | how much orders swing compared with demand |
| event uplift, peak multiplier | demand runs N times normal |
| exception queue | SKUs waiting for a person |
| escalated, awaiting approval | waiting for a person |
| auto-issued | placed without a person |

## Rule 4: no claim the numbers do not carry

If a count is zero, say what is true and let the reader conclude. The stockout answer
said "0 of them run out before the next delivery can arrive, so the shortfall is real",
which contradicts itself. State the count and what it means, or state nothing.

## The Action table

| stored value | buyer-facing sentence |
|---|---|
| `ISSUE_PO` | an order was placed |
| `HOLD_ONE_CYCLE` | no order this cycle, the stock on hand already covers the horizon |
| `ESCALATE_TO_HUMAN` | waiting for a person to decide |
| `REDIRECT_TO_OTHER_SKU` | the order went to another SKU instead |

## The model prompt

`src/sap/rationale.py` holds the only prompt in the project. Its system message says the
same four rules in the model's own words, and the prompt it sends uses the plain labels,
because a model echoes the labels it is given. A prompt that says "Velocity" and "lead
p90" produces an answer that says "velocity" and "p90". If the printed labels are plain,
the answer is plain, whatever the model does.

## Give the answer first, then the reason to care

An answer is a reply to a person, not a table with the labels taken off.

1. The first sentence answers the question, and it carries the date or the number the
   question asked for. Never open by describing what you are about to say.
2. Then what it means for the reader, what it is worth, what the system is already doing
   about it, and what it needs from them. Say plainly when nothing is needed. Three or four
   sentences is usually enough, and a short list is fine when the answer really is a list.
3. An event answer always carries its date and how far away it is. An event name on its own
   is not an answer, and "Lebaran" was also the wrong event: it is 156 days out with
   Christmas at 72.
4. Answer in the language the question was asked in. Keep SKU codes, supplier codes such as
   P08 and order numbers such as PO-0001 exactly as they are.
5. Never a labelled zero the reader cannot act on. "Value of the stock that runs out:
   IDR 0" says nothing: the stock does run out, and the zero only meant none of it runs out
   before the next delivery.
6. If the question names something the data does not have, say so in one sentence and then
   give the nearest thing that does exist, with its date.
