# What if the range carried goods with three weeks of life?

A labelled what-if, not a claim about the distributor's actual range. The catalogue's shortest
shelf life is 180 days, so nothing in the real data can spoil. To find out what the expiry work
actually does, sixty beverage SKUs were given 21 days of life instead of seven months, and the
same ninety days were run three times from the same starting position.

| run, 19 Oct 2026, both from one opening state | demand not served | units expired | units the agent decided |
|---|---|---|---|
| no spoilage ceiling (`PASOK_NO_STAGING=1`) | 2,737,797 u = 5.46% | 1,910,282 u = 3.81% | 72,045,226 |
| ceiling live (`shelf life minus one review`) | 2,857,452 u = 5.70% | 1,341,324 u = 2.68% | 69,409,908 |

**The ceiling pays for itself, and it took two defects to see it.** Earlier tables in this file
(both the three-row version and a two-row version, 6.28% to 6.97% with spoilage 1,308,653 down to
1,236,604) were produced while the guard was effectively absent. Two defects, and the second one is narrower
than it first looked: the ceiling was skipped on the lot-aware code path, so it never fired; and
the snapshot's lot-age filter and `expiry_risk` flag were built from the catalogue's shelf life
while the world expired goods on the override, so the filter treated three-week goods as
seven-month goods and never excluded an ageing lot. The ceiling itself already read the override;
what was blind was the snapshot. Both are fixed: `tools/simulate.py` now builds the snapshot from
the same life the world uses. Every arm had come out identical because the guard was never
consulted.

Measured with the agent finally informed: **spoilage down 568,958 units (29.8%), demand not served
up 119,655 units (0.24 points, 4.4%), units decided down 2,635,318 (3.7%)**. That is **0.21 units of
service given up per unit saved from the bin**, so on this product the ceiling is worth having, and
the earlier "the guard does not pay for itself" line is withdrawn.

The percentages are over the **recorded demand for the same ninety days, 50,112,358 units**
(`data/catalog/sales.csv`, 1 Jan to 31 Mar 2026, identical for all three runs because the demand
series is the record). An earlier version of this table divided by `sold_units + lost_units` from
`days.csv`, which overstates the base: on a non-review day that file writes the day's
**demand** into `sold_units` and the unmet part into `lost_units`, so the unmet part was counted
twice and the base moved with the run's own stockouts (52.7M / 54.9M / 53.9M). The direction of
the finding is unchanged, the honest cost is about 2.7 points of demand rather than 2.4.

The first version of the guard subtracted the review period as well. For a 21-day product with
a 15-day lead time that left a ceiling of two days of demand per review, which starved the
shelf: it saved the most stock from spoiling and destroyed the most sales. The corrected
version takes the window as what it really is, the days between arrival and expiry, six days
for this product, and lands between the two.

## What actually binds, traced on one SKU

The staged rule limits the size of one order to `shelf life minus one review window`, floored at two
days, and goods already in transit do not consume it. For SKU0108 (P04, lead p90 **19.4 days**,
life **21 days**, demand **1,172 units a day**) that is **14 days of demand per order**, 16,406
units. With the ceiling live and the snapshot finally carrying the right shelf life, this SKU
spoils **52,690 units instead of 100,194** and shows **no empty days in either arm**. An earlier
build showed it sitting at zero for nineteen days with nothing in transit, and that was a defect in
the code, not a property of the product: the ceiling never fired, and the snapshot was built from
the catalogue's shelf life instead of the override.

### Correction: the life clock starts when the goods land

The first version of this ceiling subtracted the delivery time from the shelf life
(`shelf life minus lead p90`). That counted the journey twice: a lot in this world expires
`shelf` days **after it arrives** (`tools/simulate.py`, `age = day minus arrive`), so goods land
with their full life and transit does not eat into it. The ceiling is now
`life minus one review window`, the buffer cap is `life minus one review window`, and the only
line the agent refuses to order is one where delivery takes longer than the goods last at all,
which no ordering policy can fix. On the live catalogue nothing changes: the shortest life is 180
days, the run reproduces its numbers exactly, and no SKU is refused.

**The table below needs a re-baseline before it is quoted.** Its three runs were made with the old
double-counting ceiling and, more importantly, with an older opening state: the distributor's
world seeds from the current artefacts, which have advanced since. Re-running the same commands
today gives different absolute numbers, so the sizes in the table are historical, not
reproducible. Re-measure both arms from one pinned opening state before putting a number in front
of a judge.

### The rule now says so out loud

An earlier version of this scenario exposed a rule that was not running: the ceiling floored at
two days of demand and quietly placed those two-day orders every review, so the agent looked busy
while every delivery arrived with almost no usable life left. That is the failure mode this
project calls a rule that never fires.

The rule is now explicit. Below a **two-day life margin** (shelf life minus lead p90) the agent
places **no order**, sets `unservable_shelf_life`, hands the line to a person with the two numbers
that make it true, and the summary counts it (`unservable_skus`). In the thirty-day window, nine of
the sixty short-life SKUs (the ones on the 19.4-day supplier) were flagged at every review.

Measured on the same thirty days, same override, only the rule differing:

| run | demand served | demand not served | units expired | units the agent decided |
|---|---|---|---|---|
| two-day dribble (rule off) | 9,801,263 | 419,050 | 291,001 | 14,582,997 |
| no order, flagged (rule on) | 9,801,263 | 419,050 | 293,039 | 14,332,729 |

Service and lost demand are identical, the pointless order stream is gone (250,268 fewer units
decided), and the bin is 2,038 units fuller, which is the dribble arriving dead. On the catalogue
this experiment ran against, no SKU had a life margin under two days, so the live run was
unaffected (600 SKUs, 121 orders, 509,374 units, amplification 1.31x to 0.36x).

That catalogue has since been rebuilt: it now carries short shelf lives (1 month on 16 bread SKUs,
median 10 months) and per-category event amplitudes, so the run reports 458 orders and the bin
question is live rather than hypothetical. The numbers above stay as the record of the experiment
on the record-day catalogue; the rule it tests is now exercised by real SKUs, which is why
`data/agents/targets.json` measures expiry instead of assuming it.

So the binding constraint is the rule's own ceiling, not the review cadence: calling the agent
every day cannot help when the ceiling is two days of demand and the goods count against it while
they are still on the road. A 21-day product delivered in 19.4 days has no workable policy at any
cadence; the real answers are a nearer source or dropping the line, which is exactly why the
distributor's own catalogue carries nothing shorter than 180 days.

## What this measures, and what it says

The guard takes 29.8% off spoilage, 1,910,282 units down to 1,341,324, and adds 0.24 points to
demand not served, 5.46% up to 5.70%, over a recorded demand of 50,112,358 units. It pays for
itself: 0.21 units of service given up per unit saved from the bin.

The measured cost is small but real, and it comes from the policy underneath, not from the ceiling.
A 21-day product on a 19.4-day lead, reviewed once a week, has no slack: the coverage target wants 26
days of stock, the life allows 21, and the ceiling therefore holds less than the target wants. The
real answer for goods like these is a shorter review cycle, ordering small and often, which is what
the per-order ceiling was meant to express.

So the honest demo line is the measured one: the agent's own policy limit is visible, and it is
that fresh goods need a shorter review than the calendar currently gives them.

## How to reproduce

The override file is `demo/scenario_short_shelf_life.csv` (sixty SKUs, 21 days). The catalogue
is untouched.

```
PASOK_SHELF_OVERRIDE=demo/scenario_short_shelf_life.csv \
  .venv/bin/python tools/simulate.py --mode closed --name scen_stage2 run --from 2026-01-01 --days 90
PASOK_SHELF_OVERRIDE=demo/scenario_short_shelf_life.csv PASOK_NO_STAGING=1 \
  .venv/bin/python tools/simulate.py --mode closed --name scen_nostage run --from 2026-01-01 --days 90
```

Note stated plainly in the code as well: the stock already on hand when a world is seeded has no
lot date in the record, so its lots carry the seed day, and expiry is measured only on goods
that arrive during a run.
