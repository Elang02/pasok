# Pasok web console: English pass and trim brief

Read this whole file before editing anything. It is the contract for this pass.

## Why

The hackathon is judged in English, on 31 October, at BINUS. The console currently
reads in Indonesian. It must read in English. The operator also rejected the amount of
prose on the pages: "saya mau webnya ini yang clean gitu UInya, gausah terlalu banyak
penjelasan yang ga perlu, kan itu nanti ada di presentasinya, ini web agentnya loh,
bukan presentasi". So this pass does two things, and only these two:

1. Every visible string becomes **English**.
2. Explainer prose is **deleted**. The console shows the agent working, not the pitch.

## The two rules of the trim

Keep:

- page title, nav labels, control labels (buttons, tabs, placeholders)
- column headers, table cells, numbers, units, status words
- empty, loading and error states, each naming the cause and the next action
- a single short line only when it tells the reader what to *do* next ("Pick a
  question, or type your own.")

Delete:

- any sentence that explains what the system is, why it exists, or that its numbers
  come from files. That belongs in the slide deck, not in the tool.
- asides, hedges, reassurance, "so that you do not have to guess", "this is real, not
  a simulation", "in other words"
- repeated statements of the same fact on one page
- the marketing footer line ("empat agen · satu loop · semua angka dari file"). The
  footer keeps at most the figures that are facts (SKU count, principal count).

When a title and its caption say the same thing, keep the title and delete the caption.

## Fixed vocabulary

Do not invent synonyms. Use exactly these. Agent names are English in the proposal, so
they are English here.

| Indonesian on screen now | English |
|---|---|
| rekaman <date> | snapshot <date> |
| sisa (hari) / cover | days of cover |
| lama kirim / tunggu kirim | lead time |
| terpenuhi | fill rate |
| salah ramal | forecast error |
| otomatis | auto-issued |
| nunggu manusia / naik ke manusia | awaiting approval |
| antrian persetujuan | approval queue |
| tahan satu siklus | held one cycle |
| pembatas (varians) | guardrail (variance cap) |
| kenaikan event / rampa | event uplift |
| lonjakan | spike |
| sisa stok yang bisa dijual | sellable stock |
| antrian pengecualian | exception queue |
| jalankan loop | Run the loop |
| jejak satu SKU | Trace one SKU |
| panel agen | Agent panel |
| peta loop | Loop map |
| tanya agen | Ask the agents |
| konsol | Console |
| para agen | the agents |
| Permintaan | Demand |
| Posisi stok | Stock Position |
| Keandalan supplier | Supplier Reliability |
| Keputusan | Decision |
| Pengirim order | Order Executor |
| Penerima order | Order Intake |
| Notifikasi | Notification |
| Belajar | Learn |
| kedaluwarsa | expiry |
| barang | category |

Numbers and dates: English month names, day first ("11 October 2026"). Thousands
separator comma, decimal point. Currency "IDR 7.56M".

Never use an em dash or a semicolon. Use comma, colon, period, or parentheses.

## Numbers on screen must not be typed

The page may not carry a figure in its own markup. It carries a placeholder and the
server fills it from the artefact. Three forms exist, defined in `web/figures.py`:

- `<!--SNAPSHOT-->` — the masthead line, already on every console page
- `<span data-fig="key">fallback</span>` — one figure, replaced at request time
- `<!--LEARN_BARS-->` — the demo page's monthly error bars

Available `data-fig` keys, exactly these:

```
n_skus  principal_count  orders_placed  orders_skipped  variance_cap_binding
total_guarded_units  amplification_reduction  skus_with_order  auto_issued
escalated  auto_rate  order_value  fill_rate  wape_best_median  sku0421_wape
learn_months  curve_readings  curve_wape_last
```

`loop.html` still carries typed order counts from two generations ago: "384 dari 562
dibatasi", "507 terkirim · 55 nunggu manusia", "562 dipesan · 38 tahan satu siklus".
Those are wrong twice over (wrong language, wrong run). Bind them with `data-fig`.

## Do not change

- any file outside the one assigned to you
- `web/pasok.css` (the palette, container and heading scale are settled)
- any pipeline number or artefact
- Indonesian field names, CSV column names, API keys, or file paths. Those are the real
  names. Only the text a person reads changes.

## Check before you report

Run these from the repo root and paste the real output in your summary:

```
.venv/bin/python tools/ui_system_gate.py
.venv/bin/python tools/ui_truth_gate.py
.venv/bin/python -m py_compile web/*.py
```

`ui_text_gate.py` is being replaced by an English gate in another workstream. Do not
edit it, and do not try to make it pass.

Do not git commit. Do not touch `.planning/`. Do not run a browser.
