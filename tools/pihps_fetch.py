"""Fetch daily food prices from PIHPS (Bank Indonesia) public endpoint.

Endpoint (verified 200 OK, JSON):
  https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetChartKomoditas
  params: price_type_id, comcat_id, province_id, regency_id, showKota,
          showPasar, tipe_laporan=6, start_date, end_date

Returns rows: {"price": 17050.0, "name": "DKI Jakarta", "date": "19 Oct 26"}
An empty province_id returns every province (33 rows per trading day).
"""
import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://www.bi.go.id/hargapangan/WebSite/TabelHarga/GetChartKomoditas"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
OUT = "/home/ubuntu/pasok/data/external/raw"

# commodity id -> display name (ids from GetRefCommodityAndCategory)
COMMODITIES = {
    "com_3": "Beras Kualitas Medium I",
    "com_10": "Telur Ayam Ras Segar",
    "com_17": "Minyak Goreng Curah",
    "com_18": "Minyak Goreng Kemasan Bermerk 1",
    "com_20": "Gula Pasir Kualitas Premium",
}

YEARS = [2022, 2023, 2024, 2025, 2026]


def fetch(comcat, start, end, attempts=4):
    q = urllib.parse.urlencode({
        "price_type_id": 1,
        "comcat_id": comcat,
        "province_id": "",
        "regency_id": "",
        "showKota": "false",
        "showPasar": "false",
        "tipe_laporan": 6,
        "start_date": start,
        "end_date": end,
    })
    req = urllib.request.Request(
        BASE + "?" + q,
        headers={"User-Agent": UA, "Accept": "application/json",
                 "X-Requested-With": "XMLHttpRequest",
                 "Referer": "https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas"},
    )
    last = None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                code = r.status
                payload = r.read()
            data = json.loads(payload)
            if code == 200 and isinstance(data.get("data"), list):
                return data["data"]
            last = f"HTTP {code}"
        except Exception as exc:  # noqa: BLE001 - network retry
            last = repr(exc)
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"fetch failed {comcat} {start}..{end}: {last}")


def main():
    os.makedirs(OUT, exist_ok=True)
    for comcat in COMMODITIES:
        for year in YEARS:
            dest = os.path.join(OUT, f"{comcat}_{year}.json")
            if os.path.exists(dest) and os.path.getsize(dest) > 100:
                print("skip", dest)
                continue
            rows = fetch(comcat, f"{year}-01-01", f"{year}-12-31")
            with open(dest, "w", encoding="utf-8") as fh:
                json.dump(rows, fh)
            print(dest, len(rows), os.path.getsize(dest))


if __name__ == "__main__":
    main()
