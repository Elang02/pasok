<!-- GSD PHASE 2 PLAN — 02-01 -->
# Plan 02-01: Stock Position Agent

## Objective

Compute the single true sellable figure per SKU and days of cover, from a simulated
inventory position consistent with the sales history. This is the input the Decision
Agent reasons over and what SAP RPT-1.6 scores in Phase 4.

## Tasks

1. Write `src/stock/position.py`:
   - Reconstruct opening stock per SKU consistent with `data/catalog/sales.csv`:
     arrivals follow the receiving.csv lead-time profile, depletion follows sales.
   - The agent reads ONLY the ledger exports (catalog.csv, receiving.csv, sales
     weekly parquet) — never the generator's intent. Same discipline as a real
     agent reading a distributor ERP export.
   - Per SKU compute: on_hand_units, in_transit_units (open POs not yet received),
     sellable_units, days_of_cover = sellable / avg daily velocity (28-day window),
     below_reorder flag (cover < lead time + safety), expiry flag (shelf life vs
     cover).
2. Emit `data/stock/position_snapshot.csv` (one row per SKU at the snapshot date)
   and `data/stock/stock_daily.csv` (daily per SKU for the Decision Agent replay).

## Verification

- Script exits 0; 600 SKUs in output; no negative stock anywhere.
- Walk invariant: opening + arrivals − sales − writeoffs = closing (tolerance 0).
- Days-of-cover distribution median within 15-90 (sane for FMCG distribution).
- Deterministic (seeded, no RNG drift between runs).

## Out of scope

Order decisions (02-02/02-03); lead-time learning belongs to 02-02.
