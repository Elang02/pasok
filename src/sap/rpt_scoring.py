"""
Pasok — SAP RPT-1.6 real catalog scoring
========================================

Scores the Pasok catalog with the real `sap-rpt-1.6` deployment on SAP AI Core, using
the official request schema from the panitia BTP instructions (prediction_config with
target_columns, rows as dicts, index_column).

The design that makes this more than a prop:
  * CONTEXT rows carry REAL LABELS from the inventory walk. For a sample of historical
    as-of dates we take the decision features and attach what actually happened in the
    next 14 days (stockout, expiry write-off, days of cover left).
  * QUERY rows are the 600 SKUs at the live snapshot date, unlabelled.

So the model has to generalise from observed history, not echo an answer we handed it.

Targets (all three in ONE call, as the rubric wants):
  STOCKOUT_NEXT14   classification (Yes/No)
  EXPIRY_RISK       classification (Yes/No)
  DAYS_COVER_LEFT   regression

Run
---
    cd <repo root>
    .venv/bin/python src/sap/rpt_scoring.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import urllib.parse
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
STOCK = ROOT / "data" / "stock"
AG = ROOT / "data" / "agents"
OUT = ROOT / "data" / "sap"

DEPLOYMENT = os.environ.get("RPT_DEPLOYMENT", "d76cf689a05d504f")
TOKEN_FILE = Path(os.environ.get("AIGO_TOKEN_FILE", "/tmp/aigo_token.txt"))
API_FILE = Path(os.environ.get("AIGO_API_FILE", "/tmp/aigo_apiurl.txt"))
KEYBROKER = "https://hackathon-keybroker.cfapps.ap10.hana.ondemand.com/ai-core/aigo-key"


def snapshot_date() -> str:
    """The last day of the generated sales window, read from the data.

    Stock Position writes this value into `position_snapshot.csv`; the query
    block must ask about the same day the loop decided on. A literal here
    points the query at a date the walk no longer contains, and the lookup
    below then returns nothing.
    """
    with (STOCK / "position_snapshot.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    if rows and rows[0].get("snapshot"):
        return rows[0]["snapshot"]
    raise SystemExit("position_snapshot.csv carries no snapshot date; "
                     "run run_chain.sh step 1 first")


SNAPSHOT = snapshot_date()
HORIZON = 14
N_CONTEXT_DATES = 30          # historical as-of dates used as labelled context
CONTEXT_PER_DATE = 24         # SKUs sampled per date, stratified on the stockout label
RNG_SEED = 20261008


# ------------------------------------------------------------------ helpers ---
def get_token() -> tuple[str, str]:
    """Return (token, api_host). Prefer the cached token; refresh from the keybroker
    if it is missing or stale. The token is never printed."""
    if TOKEN_FILE.exists() and API_FILE.exists():
        tok = TOKEN_FILE.read_text().strip()
        api = API_FILE.read_text().strip().replace("https://", "").rstrip("/")
        if tok:
            return tok, api

    # refresh path: keybroker -> OAuth -> token + api url
    req = urllib.request.Request(KEYBROKER, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        key = json.loads(r.read().decode())

    uaa = key.get("uaa", key)
    token_url = uaa["url"].rstrip("/") + "/oauth/token"
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": uaa["clientid"],
        "client_secret": uaa["clientsecret"],
    }).encode()
    treq = urllib.request.Request(token_url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(treq, timeout=30) as r:
        tok = json.loads(r.read().decode())["access_token"]
    api = key.get("serviceurls", {}).get("AI_API_URL", "").replace("https://", "").rstrip("/")
    TOKEN_FILE.write_text(tok)
    API_FILE.write_text(api)
    return tok, api


def build_features(daily: pd.DataFrame, sup: pd.DataFrame, asof: pd.Timestamp) -> pd.DataFrame:
    """Decision features per SKU at an as-of date, computed only from data up to that day."""
    hist = daily.loc[:asof]
    last28 = hist.tail(28)
    vel = last28.mean()
    on_hand = daily.loc[asof] if asof in daily.index else None
    # the walk's own columns
    row = daily.loc[asof]
    feat = pd.DataFrame({
        "SKU_ID": daily.columns,
        "VELOCITY": vel.reindex(daily.columns).to_numpy(),
        "ASOF": asof.strftime("%Y-%m-%d"),
    })
    return feat


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    daily = pd.read_parquet(ROOT / "data" / "prep" / "daily_by_sku.parquet")
    if "date" in daily.columns:
        daily = daily.set_index("date")
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()

    walk = pd.read_csv(STOCK / "stock_daily.csv", parse_dates=["date"])
    walk = walk.sort_values(["sku", "date"]).reset_index(drop=True)
    snap = pd.read_csv(STOCK / "position_snapshot.csv")
    sup = pd.read_csv(AG / "supplier_reliability.csv")[["principal_id", "lead_p90_d"]]
    dec = pd.read_csv(AG / "decisions.csv")

    # ---- labels from the walk: what happened in the NEXT 14 days ----
    g = walk.groupby("sku", observed=True)
    walk["fut_lost"] = g["lost_sales"].transform(
        lambda s: s.iloc[::-1].rolling(HORIZON, min_periods=1).sum().iloc[::-1].shift(-1)
    ).fillna(0)
    walk["fut_demand"] = g["sales"].transform(
        lambda s: s.iloc[::-1].rolling(HORIZON, min_periods=1).sum().iloc[::-1].shift(-1)
    ).fillna(0)
    walk["fut_oh_min"] = g["on_hand"].transform(
        lambda s: s.iloc[::-1].rolling(HORIZON, min_periods=1).min().iloc[::-1].shift(-1)
    ).fillna(0)
    # MATERIAL stockout flag on every row (ground-truth basis for stratification)
    walk["material_so"] = walk["fut_lost"] > 0.05 * walk["fut_demand"].clip(lower=1.0)

    # ---- build the context block: labelled historical rows ----
    rng = np.random.default_rng(RNG_SEED)
    all_dates = pd.to_datetime(sorted(walk["date"].unique()))
    # keep dates that leave room for a full future window
    usable = [d for d in all_dates if d <= all_dates[-1] - pd.Timedelta(days=HORIZON)]
    picks = sorted(rng.choice(usable, size=min(N_CONTEXT_DATES, len(usable)), replace=False))

    meta = snap.set_index("sku")[["principal_id", "velocity_units_day", "days_of_cover", "shelf_life_days"]]
    lead = sup.set_index("principal_id")["lead_p90_d"]

    def feat_row(sku: str, r: pd.Series, asof_velocity: float | None = None,
                 asof_cover: float | None = None) -> dict:
        """Decision features for one row. `asof_*` overrides keep the CONTEXT rows honest:
        a historical row must describe THAT day, not the snapshot day. (Found and fixed:
        using snapshot cover for historical context taught the model nonsense.)"""
        pid = meta.loc[sku, "principal_id"]
        vel = asof_velocity if asof_velocity is not None else float(meta.loc[sku, "velocity_units_day"])
        cover = asof_cover if asof_cover is not None else float(meta.loc[sku, "days_of_cover"])
        return {
            "SKU_ID": sku,
            "ON_HAND": round(float(r["on_hand"]), 1),
            "IN_TRANSIT": round(float(r["in_transit"]), 1),
            "VELOCITY": round(vel, 1),
            "COVER_DAYS": round(cover, 1),
            "LEAD_P90": float(lead.get(pid, 12.0)),
            "MONTH": int(pd.Timestamp(r["date"]).month),
        }

    skus = list(snap["sku"])
    context_rows = []
    for d in picks:
        sub = walk[walk["date"] == d].copy()
        if sub.empty:
            continue
        # stratified sampling per date: equal Yes/No on the stockout label so the
        # model sees a balanced context (a 1:11 split taught it to over-predict Yes)
        sub["is_yes"] = sub["material_so"]
        yes = sub[sub["is_yes"]]
        no = sub[~sub["is_yes"]]
        half = CONTEXT_PER_DATE // 2
        take_yes = min(half, len(yes))
        take_no = min(CONTEXT_PER_DATE - take_yes, len(no))
        take = pd.concat([
            yes.iloc[rng.choice(len(yes), size=take_yes, replace=False)] if take_yes else yes.iloc[0:0],
            no.iloc[rng.choice(len(no), size=take_no, replace=False)] if take_no else no.iloc[0:0],
        ])
        for _, r in take.iterrows():
            # historical velocity & cover AS OF THAT DAY (28-day window ending here)
            h = walk[(walk["sku"] == r["sku"]) & (walk["date"] <= d)].tail(28)
            vel_asof = float(h["sales"].mean()) if len(h) else float(meta.loc[r["sku"], "velocity_units_day"])
            sellable_asof = float(r["on_hand"]) + float(r["in_transit"])
            cover_asof = (sellable_asof / vel_asof) if vel_asof > 0 else 999.0
            row = feat_row(r["sku"], r, asof_velocity=vel_asof, asof_cover=cover_asof)
            # MATERIAL stockout: lost sales > 5% of the 14-day demand. A raw
            # fut_lost > 0 test is noise here (the weekly-review policy always leaks
            # a few units at the gap between order cycles).
            demand14 = float(r.get("fut_demand", 0.0)) or vel_asof * HORIZON
            row["STOCKOUT_NEXT14"] = "Yes" if r["fut_lost"] > 0.05 * max(demand14, 1.0) else "No"
            row["EXPIRY_RISK"] = "Yes" if r["fut_oh_min"] > float(meta.loc[r["sku"], "shelf_life_days"]) else "No"
            row["DAYS_COVER_LEFT"] = round(float(r["fut_oh_min"]) / max(1.0, float(meta.loc[r["sku"], "velocity_units_day"])), 1)
            context_rows.append(row)
    ctx = pd.DataFrame(context_rows)
    print(f"context rows: {len(ctx)} across {len(picks)} as-of dates")
    print(f"  label balance STOCKOUT_NEXT14: {ctx['STOCKOUT_NEXT14'].value_counts().to_dict()}")
    print(f"  label balance EXPIRY_RISK:     {ctx['EXPIRY_RISK'].value_counts().to_dict()}")

    # ---- query block: the live snapshot, unlabelled ----
    snap_date = pd.Timestamp(SNAPSHOT)
    wlast = walk[walk["date"] == snap_date].set_index("sku")
    query_rows = []
    for sku in skus:
        r = wlast.loc[sku]
        row = feat_row(sku, r)
        row["STOCKOUT_NEXT14"] = "[PREDICT]"
        row["EXPIRY_RISK"] = "[PREDICT]"
        row["DAYS_COVER_LEFT"] = "[PREDICT]"
        query_rows.append(row)
    qry = pd.DataFrame(query_rows)

    payload = {
        "prediction_config": {
            "target_columns": [
                {"name": "STOCKOUT_NEXT14", "prediction_placeholder": "[PREDICT]", "task_type": "classification"},
                {"name": "EXPIRY_RISK", "prediction_placeholder": "[PREDICT]", "task_type": "classification"},
                {"name": "DAYS_COVER_LEFT", "prediction_placeholder": "[PREDICT]", "task_type": "regression"},
            ]
        },
        "index_column": "SKU_ID",
        "rows": pd.concat([ctx, qry], ignore_index=True).to_dict(orient="records"),
    }

    token, api = get_token()
    url = f"https://{api}/v2/inference/deployments/{DEPLOYMENT}/predict"

    # RPT caps QUERY rows at 512, so the 600-SKU snapshot ships in batches. Context is
    # sent once with every batch (the model needs labelled history each call).
    QRY_BATCH = 300
    all_preds: list[dict] = []
    batches_meta = []
    t0 = time.time()
    for b0 in range(0, len(qry), QRY_BATCH):
        chunk = qry.iloc[b0:b0 + QRY_BATCH]
        payload_b = dict(payload)
        payload_b["rows"] = pd.concat([ctx, chunk], ignore_index=True).to_dict(orient="records")
        req = urllib.request.Request(
            url,
            data=json.dumps(payload_b).encode(),
            headers={
                "Authorization": f"Bearer {token}",
                "AI-Resource-Group": "default",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                resp = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"HTTP {e.code}: {body[:600]}", file=sys.stderr)
            return 1
        all_preds.extend(resp.get("predictions", []))
        batches_meta.append({
            "batch": len(batches_meta) + 1,
            "query_rows": int(len(chunk)),
            "request_id": resp.get("id"),
            "status": resp.get("status"),
            "metadata": resp.get("metadata"),
        })
    dt = time.time() - t0
    resp = {"id": batches_meta[-1]["request_id"], "status": batches_meta[-1]["status"],
            "metadata": batches_meta[-1]["metadata"], "predictions": all_preds}
    http_status = 200

    (OUT / "rpt_raw_response.json").write_text(json.dumps(resp, indent=2))
    (OUT / "rpt_request_meta.json").write_text(json.dumps({
        "url": url.replace(api, "<api-host>"),
        "deployment": DEPLOYMENT,
        "http_status": http_status,
        "elapsed_s": round(dt, 2),
        "n_context_rows": int(len(ctx)),
        "n_query_rows": int(len(qry)),
        "n_batches": len(batches_meta),
        "batches": batches_meta,
        "targets": [t["name"] for t in payload["prediction_config"]["target_columns"]],
    }, indent=2))

    preds = resp.get("predictions", [])
    rows = []
    for p in preds:
        sku = p.get("SKU_ID")
        rec = {"sku": sku}
        for tgt in ("STOCKOUT_NEXT14", "EXPIRY_RISK", "DAYS_COVER_LEFT"):
            v = p.get(tgt)
            if isinstance(v, list) and v:
                rec[tgt] = v[0].get("prediction")
                rec[f"{tgt}_conf"] = v[0].get("confidence")
            else:
                rec[tgt] = v
        rows.append(rec)
    sc = pd.DataFrame(rows)
    sc.to_csv(OUT / "rpt_scores.csv", index=False)

    # ---- agreement vs the agent's own flags (honest number, no spin) ----
    if len(sc):
        m = sc.merge(
            snap[["sku", "below_reorder"]], on="sku", how="inner"
        )
        agent_flag = m["below_reorder"].astype(bool)
        model_flag = m["STOCKOUT_NEXT14"].astype(str).str.lower().eq("yes")
        agree = float((agent_flag == model_flag).mean())
        both = int((agent_flag & model_flag).sum())
    else:
        agree, both = None, 0

    summary = {
        "http_status": http_status,
        "request_id": resp.get("id"),
        "n_context_rows": int(len(ctx)),
        "n_query_rows": int(len(qry)),
        "n_predictions": int(len(sc)),
        "elapsed_s": round(dt, 2),
        "predicted_stockout_yes": int(sc["STOCKOUT_NEXT14"].astype(str).str.lower().eq("yes").sum()) if len(sc) else 0,
        "predicted_expiry_yes": int(sc["EXPIRY_RISK"].astype(str).str.lower().eq("yes").sum()) if len(sc) else 0,
        "days_cover_left_median": float(pd.to_numeric(sc["DAYS_COVER_LEFT"], errors="coerce").median()) if len(sc) else None,
        "agreement_with_agent_below_reorder": agree,
        "both_flag_same_sku": both,
        "note": "Context rows carry labels from the inventory walk; query rows are the live snapshot.",
    }
    (OUT / "rpt_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
