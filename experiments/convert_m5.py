"""One-shot: convert M5 sales CSV to parquet + npy cache for fast repeated loads."""
import time
from pathlib import Path
import numpy as np
import pandas as pd

R = Path(__file__).resolve().parents[1]
DATA = R / "data/m5"
csv = DATA / "sales_train_validation.csv"
pq = DATA / "sales_train.parquet"
npy = DATA / "sales_train.npy"
meta_csv = DATA / "sales_train_meta.csv"

if not pq.exists():
    t0 = time.time()
    sales = pd.read_csv(csv, engine="pyarrow")
    print(f"read csv: {time.time()-t0:.1f}s", flush=True)
    sales.to_parquet(pq, compression="zstd")
    print("parquet written", flush=True)
    day_cols = [c for c in sales.columns if c.startswith("d_")]
    arr = sales[day_cols].to_numpy(dtype=np.float32)
    np.save(npy, arr)
    keep = arr.sum(axis=1) > 200
    sales[keep].to_csv(meta_csv, index=False)
    np.save(DATA / "sales_train_filtered.npy", arr[keep])
    print(f"done: arr {arr.shape}, filtered {(keep).sum()} rows", flush=True)
else:
    print("parquet already exists", flush=True)
