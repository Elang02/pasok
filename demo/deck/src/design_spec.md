<!-- ppt-master-schema: design-spec/v1 -->
# Pasok Demo Day - Design Spec

## I. Project Information

| Item | Value |
| --- | --- |
| Project Name | Pasok Demo Day |
| Canvas Format | PPT 16:9 (1280x720) |
| Page Count | 13 |
| Primary Language | en |
| Target Audience | Hackathon judges and a mixed room of technical and business reviewers at BINUS Alam Sutera |
| Communication Intent | Prove that a reorder agent can size orders honestly at 600-SKU scale, then state exactly where it still fails |
| Desired Audience Outcome | Each judge can name one mechanism (measured lead times, buffer arithmetic, money gate) and one open gap without asking |
| Core Message / Ask / Action | Pasok sizes the order and writes the reason; on our snapshot 445 of 480 orders left without a person, and the targets it misses are stated on the same slide |
| Delivery Context | Live 13-slide pitch, 8 minutes, projected, then left as a file |
| Artifact Afterlife | Read on a laptop without the speaker; every page must stand alone |
| Reading Mode | presentation |
| Content Strategy | Balanced: claim, number, and the artefact that produced it on the same page |
| Design Style | Editorial light — ivory paper, ink text, one amber accent, serif headlines over sans body, hairlines instead of boxes |
| AI Image Acquisition Path | none |
| Generation Mode | continuous |
| Spec Refinement | disabled |
| Speaker Notes | disabled — presenter speaks from memory and the rehearsal sheet, no notes were requested |
| Custom Animations | disabled — workflow default |
| Narration Audio | disabled — workflow default |
| Created Date | 2026-10-27 |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| Format | PPT 16:9 |
| Dimensions | 1280 × 720 |
| viewBox | `0 0 1280 720` |
| Margins | 72 px on all sides |
| Content Area | 1136 × 576 within x 72–1208, y 72–648 |

## III. Visual Theme

### Theme Style

- **Mode**: narrative
- **Visual style**: editorial
- **Theme**: a printed analyst's report read aloud — paper, ink, one warm accent, numbers set large and quiet labels around them
- **Tone**: sober, evidentiary, no salesmanship

### Color Scheme

| Role | HEX | Purpose |
| --- | --- | --- |
| Background | #F7F3EA | page paper |
| Secondary background | #EDE6D8 | banded rows, quiet panels |
| Primary | #1F1B16 | headlines and body ink |
| Accent | #B4551F | the one number that matters on a page, rules, active marker |
| Secondary accent | #2F4858 | data series and chart bars where accent would shout |
| Body text | #2A2622 | running text |
| Secondary text | #6B6257 | captions, sources, footnotes |
| Divider | #D8CDBB | hairlines, table rules |

## IV. Typography System

### Font Plan

| Role | Character (Reference) | Primary | English if non-English | Fallback tail |
| --- | --- | --- | --- | --- |
| Title | editorial serif, high contrast | Georgia | Georgia | 'Times New Roman', serif |
| Body | humanist sans, screen-safe | Segoe UI | Segoe UI | Calibri, Arial, sans-serif |

- **Title stack**: Georgia, 'Times New Roman', serif
- **Body stack**: 'Segoe UI', Calibri, Arial, sans-serif

### Font Size Hierarchy

| Purpose | Anchor Size (px) |
| --- | ---: |
| Display | 96 |
| Title | 44 |
| Lead | 32 |
| Subtitle | 28 |
| Body | 24 |
| Annotation | 16 |

## V. Layout Principles

### Deck-wide Direction

- **Hierarchy direction**: title top-left, one hero number or chart occupying the optical centre, evidence line at the foot
- **Composition tendency**: asymmetric two-column splits and full-width bands; never centred blocks of equal weight
- **Cross-page continuity**: the same hairline rule under every title, the same accent used once per page, page number set small at the lower right
- **Spacing posture**: open, with generous top air on anchor pages and tighter leading on dense pages
- **Spacing anchors**: page margin 72, block gap 32, column gutter 48, corner radius 0, body leading 1.5

## VI. Icon Usage Specification

- **Primary bundled library**: none — the deck carries no icons; hierarchy comes from type, rules and numbers alone.

## VII. Visualization Reference List

| Page | Family | Template | Usage |
| --- | --- | --- | --- |
| 3 | line/multi-series | line-multi-series | order variance over 250 days, guarded against unguarded |
| 7 | bar/grouped | bar-grouped | ramp WAPE against flat-bump WAPE on the same windows |
| 8 | bar/horizontal | bar-horizontal | principal fill rates, P02 lowest |
| 12 | bar/stacked | bar-stacked | auto-issued against held value in one snapshot |

## VIII. Image Resource List

| Filename | Dimensions | Ratio | Purpose | Type | Image pattern | Crop Policy | Acquire Via | Status | Reference | text_policy | page_role |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

## IX. Content Outline

### Part 1: The problem and the machine

#### Slide 01 - Title

- **Audience move**: walking in, unsure what Pasok is → knows it is a reorder agent that also refuses to order
- **Relationships**: team line and date sit below the title as one block; no contrast between units
- **Composition**: Reference — title left, subtitle in a narrower measure under it, footer rule carrying team and venue
- **Title**: Pasok
- **Core message**: a reorder agent that sizes the order and writes the reason, and holds the order when the numbers look wrong
- **Content**: kicker DEMO DAY · TRACK A · INTELLIGENCE SUPPLY CHAIN · subtitle one sentence · team names · Sistem Informasi, Unika Atma Jaya · 31 October 2026 · BINUS Alam Sutera

#### Slide 02 - One buyer reorders 600 SKUs against a calendar that moves

- **Audience move**: thinks reordering is arithmetic → sees that the calendar, not the arithmetic, is what moves
- **Relationships**: two facts (69% general trade, fixed reorder points) contrast with the moving event calendar drawn beneath them
- **Composition**: Reference — facts in the left column, event-date dot field across the lower half, two hero figures at the right
- **Title**: One buyer reorders 600 SKUs against a calendar that moves
- **Core message**: the events that lift demand drift every year, so last year's plan lands in the wrong week
- **Content**: 69% of FMCG volume moves through general trade / most stores still run a fixed reorder point / every event drifts, so last year's plan lands in the wrong week · hero: 600 SKUs on one desk, 9 of 12 suppliers below 95% fill · caption: each dot is a real event date from the registry; Lebaran keeps arriving earlier
- **Visualization**: event-drift-dots — five years of event start dates per event, one dot per occurrence

#### Slide 03 - An unguarded agent over-orders, and the chart shows it

- **Audience move**: expects an agent to help → sees that an unguarded agent is worse than a rule
- **Relationships**: two runs of the same model contrast; the guarded line sits close to demand while the unguarded line spikes
- **Composition**: Reference — chart dominant, two variance figures stacked at the right, one-line method note at the foot
- **Title**: An unguarded agent over-orders, and the chart shows it
- **Core message**: same forecaster, same 250 days; only the three rules differ, and they move order variance from 2.68x to 0.24x
- **Content**: method note: same forecaster, 250 trading days, Bank Indonesia retail index · hero: order variance 2.68x without rules, 0.24x with them · legend: amber unguarded, slate guarded, grey demand
- **Visualization**: variance-lines — seven-day averages of order and demand index

#### Slide 04 - Four agents run one pass, and the model never picks the quantity

- **Audience move**: assumes the language model chooses the order → sees the model writes only the reason
- **Relationships**: four agents in sequence, each feeding the next, then the order system as the sink
- **Composition**: Reference — four numbered bands stacked, arrows implied by alignment, the closing line set as a pull quote
- **Title**: Four agents run one pass, and the model never picks the quantity
- **Core message**: quantity comes from arithmetic over measured inputs; the model writes the sentence a buyer reads
- **Content**: Demand Agent — forecast, event ramp, anomaly flag · Stock Position Agent — sellable units, days of cover, two flags · Supplier Reliability Agent — lead p50/p90, fill rate, drift · Decision Agent — action, quantity, reason · Order system — auto-issue or human queue · pull quote: the model writes the reason, never the quantity

### Part 2: What the machine measured

#### Slide 05 - The console names the next event and the goods that spike

- **Audience move**: doubts the agent knows the calendar → sees a live answer with a date, a factor and a ranked list
- **Relationships**: the question and the answer contrast; the ranked SKU list is the evidence under the answer
- **Composition**: Reference — question set as a quote, answer panel beside it, three ranked SKUs below, caption at the foot
- **Title**: The console names the next event and the goods that spike
- **Core message**: ask which event is next and it answers with a date, a multiplier and the goods that move
- **Content**: question: what needs more stock for a spike next month? · answer: nothing inside a month, Christmas sits at 79 days, median SKU 1.60x, one passes 2.5, strongest 2.63 · ranked SKUs · caption: live on 26 October, four steps, 6.1 seconds, every number checked against the records
- **Visualization**: ranked-sku-list — three SKUs with multiplier and extra units

#### Slide 06 - One SKU, from eight days of cover to a scored order

- **Audience move**: has seen numbers, not a decision → can retell one decision end to end
- **Relationships**: the cover ladder (8.2 → trigger 14 → target 17) is the spine; the order and its outcome hang off it
- **Composition**: Reference — ladder across the upper half as three stations on a rule, order facts in a column below, outcome strip at the base
- **Title**: One SKU, from eight days of cover to a scored order
- **Core message**: the loop found SKU0286 under its trigger, sized 2,092 units itself, and graded its own fill afterwards
- **Content**: SKU0286, biscuits, principal P03 · 8.2 days of cover, under the 14-day trigger (lead 7 + review 7) · 17-day cover target (lead 7 + review 7 + buffer 3) · 2,092 units, IDR 15.9M inside an IDR 95.1M credit line · delivery at p90 of 7 days · scored 97.70% fill, 48 units short, fed back in · nobody approved it

#### Slide 07 - The forecast learns what each SKU does around an event

- **Audience move**: assumes event uplift is one number → sees a learned ramp per SKU beat a flat bump
- **Relationships**: two WAPE bars contrast on the same windows; the novelty figures sit apart as a second claim
- **Composition**: Reference — paired bars at the left with large numerals, three supporting figures in a row beneath, method note at the foot
- **Title**: The forecast learns what each SKU does around an event
- **Core message**: 30,490 series, 154 windows, leave-one-occurrence-out: the ramp wins, and an unnamed spike still gets flagged
- **Content**: ramp WAPE 0.0775 against flat bump 0.1161 · novel spikes caught 120 of 120 · false alarms 0.65 per 100 days · method: scored leave-one-occurrence-out on M5
- **Visualization**: wape-bars — two bars on one axis

#### Slide 08 - Lead time comes from goods receipts, not from a promise

- **Audience move**: assumes supplier lead time is a contract number → sees p90 learned from 1,956 receipts
- **Relationships**: principal bars are ordered by fill, P02 last and highlighted; the two headline figures sit above them
- **Composition**: Reference — hero numerals top right, horizontal bars occupying the centre, note at the foot
- **Title**: Lead time comes from goods receipts, not from a promise
- **Core message**: every receipt updates p50 and p90, and a slow supplier earns a longer cover target instead of a complaint
- **Content**: network fill 90.32% · P02 on time 81.1% · measured from 1,956 goods receipts · P02 is the slowest principal in the catalogue
- **Visualization**: fill-bars — twelve principals, fill rate, P02 highlighted

### Part 3: The rules, the lane, and the ledger

#### Slide 09 - Three rules guard the order stream

- **Audience move**: has seen one good decision → understands the three rules that make it repeatable
- **Relationships**: three rules in parallel, then the two formulas they implement, then the replay evidence
- **Composition**: Reference — three numbered rules across the top, formulas set as a quiet band, evidence figures at the base
- **Title**: Three rules guard the order stream
- **Core message**: smooth, damp, cap; on this snapshot none cut a unit, so the replay carries the proof
- **Content**: 1 smooth the forecast before it drives sizing · 2 damp against the last order · 3 cap the order so variance out stays near variance in · cover = lead p90 + review + buffer · buffer = z · sqrt(lead variance squared + forecast error squared) · replay 1.33x to 0.36x · cap touched 0 of 600 · all three are coded; on this snapshot none cut a unit, so the replay is the evidence
- **Visualization**: rule-formula-stack — three rules with their two formulas

#### Slide 10 - SAP scores the catalogue and writes the reason

- **Audience move**: wonders whether this is a demo-only stack → sees SAP and Bedrock doing paid work
- **Relationships**: three claims in parallel, each with its number beneath; the disagreement note is set apart as a caveat
- **Composition**: Reference — three columns of claim and figure, caveat band at the foot in secondary ink
- **Title**: SAP scores the catalogue and writes the reason
- **Core message**: sap-rpt-1.6 scores 600 SKUs in 10.73 seconds, gpt-5.4 writes all 40 rationales, Joule shows the queue
- **Content**: agreement with the agent 0.895 · rationales written 40 of 40, none from a template · Joule shows the queue so the buyer approves where they already work · caveat: RPT flags 577 SKUs as expiry risk where we flag none; the definitions differ

#### Slide 11 - The AWS lane answers live

- **Audience move**: suspects a slide-ware architecture → sees what actually runs and what is blocked
- **Relationships**: a three-row stack (Lambda, Bedrock, SAP AI Core) with the blocked AgentCore stated as a footnote, not hidden
- **Composition**: Reference — three bands stacked with labels at the left and roles at the right, footnote rule beneath
- **Title**: The AWS lane answers live
- **Core message**: four agents in one Lambda behind a public URL, Bedrock through Mantle, SAP AI Core as fallback
- **Content**: Lambda function URL — four agents, one bundle · Bedrock, Mantle endpoint — the answering model · SAP AI Core — fallback and scoring · footnote: AgentCore is written and blocked by a quota on this account, so Lambda hosts the lane today

#### Slide 12 - What one snapshot moved

- **Audience move**: has heard claims → sees a ledger with both columns, including the money that waited
- **Relationships**: ordered and held contrast in one stacked bar; the redirect figure is a third, separate saving
- **Composition**: Reference — stacked bar at the top, three figures in a row beneath, run-log caption at the foot
- **Title**: What one snapshot moved
- **Core message**: 480 orders, 445 without a person, 35 held; IDR 30.27 bn ordered and IDR 7.78 bn redirected instead of bought
- **Content**: 480 orders, 445 auto-issued, 35 held (15 over a credit line, 15 near expiry, 6 mid switch) · 414 surplus SKUs moved to another depot, IDR 7.78 bn protected · in the year-long replay the money gate never fired, 0 of 18,824 orders; this pass, rebuilding a thin shelf, 15 did · caption: run log as it stood on the evening of 26 October
- **Visualization**: ledger-bar — auto-issued against held value

#### Slide 13 - A pilot on one distributor, for one month

- **Audience move**: has judged the build → knows the next step and what would prove or break it
- **Relationships**: four commitments in parallel, closing rule carrying the team and the repository
- **Composition**: Reference — four numbered commitments in one column, closing rule and team line at the foot
- **Title**: A pilot on one distributor, for one month
- **Core message**: run it on their receipts, connect their ERP, measure fill and stock value at the end of the month
- **Content**: run it on their receipts, not our synthetic file · connect their ERP in place of our order desk · measure fill rate and stock value at the end of the month · ask us about any SKU and we will show the trace · footer: Team Pasok · github.com/Elangk1 (private; access on request)

## X. Speaker Notes Requirements

- **Generation**: disabled
