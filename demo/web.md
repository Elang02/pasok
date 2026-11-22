# Pasok — the web console

## Open it

```
http://43.134.92.128:8090/
```

That is the box's current public address, port 8090, the console for the four-agent loop. It runs
as a systemd unit (`pasok-web.service`) bound to `0.0.0.0`, so it comes back after a restart.

**The old address in this file was `http://172.104.187.19/`, port 80, on the previous host.** That
host is gone: on 2026-10-18 the URL answered `503` from an external vantage point while the
console's real address answered `200` from the same vantage point. Anything still quoting the old
address is stale, including `.planning/STATE.md`, `.planning/ROADMAP.md` and the phase 9 and 10
verification reports, which recorded truthfully what was live on 10 October.

## What it does

A search box and six one-click questions. Type or click, and the answer comes back rendered
(the same answers the A2A server serves to SAP Joule).

| Intent | Example question |
|---|---|
| stockout | What is going to run out of stock within a week? |
| spike | What goods need more stock because a spike is coming within a month? |
| exceptions | Which SKUs are in the exception queue? |
| summary | How did the network perform overall? |
| sku | Why was SKU0286 reordered? |
| order | Where did PO-0314 end up? |

Questions work in Indonesian too ("stok apa yang habis minggu ini?", "barang apa yang perlu
distok lebih karena lonjakan bulan depan").

## Endpoints

```
GET  /                 the console
GET  /api/ask?q=...    route a question and return the answer as markdown
GET  /api/health       status, the six skills, snapshot, order count
GET  /api/data         the raw artefact summaries behind the answers
```

## Why it is safe to put on port 80

- Read-only. Nothing here writes; it reads the artefacts the pipeline already produced.
- No credentials on this path. It does not touch AWS, SAP, or the distributError API.
- Loopback services stay loopback: the agent runtime (8081), the ordering API (8099) and the
  A2A server (8085) are not exposed.

## Files

| File | Role |
|---|---|
| `web/app.py` | the FastAPI app (routes questions to `pasok_answers`) |
| `web/index.html` | the console UI |
| `web/pasok-web.service` | the systemd unit |

## Refresh the numbers

The console reads whatever the pipeline last wrote. After a pipeline run, nothing needs
restarting (the app reads the files per request); after editing `web/`:

```bash
sudo systemctl restart pasok-web.service
```
