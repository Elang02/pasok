# Audit modul Pasok, 21 Oktober 2026

Gate: setiap butir dicek dengan perintah, bukan ingatan. Verdict hanya satu dari COVERED, WRONG, PARTIAL, MISSING, UNVERIFIABLE.

| # | Butir | Sumber | Verdict | Tindakan |
|---|---|---|---|---|
| 1 | 600 SKU | position_summary.json n_skus | COVERED | - |
| 2 | 139 baris order | decision_summary.json orders_placed | COVERED | - |
| 3 | 121 otomatis, 18 menunggu | order_summary.json | COVERED | - |
| 4 | Nilai order otomatis Rp13.399.348.800 | order_summary auto_value_idr 13.421.740.570 | WRONG | diganti |
| 5 | Nilai eskalasi Rp3.437.202.355 | order_summary escalated_value_idr | COVERED | - |
| 6 | 251 SKU dialihkan, Rp7.652.757.323 | redirect_summary.json | COVERED | diperbaiki sebelumnya |
| 7 | SKU0361: 4.707,6 unit, 703,18 per hari, cover 6,7 | decisions.csv + snapshot | COVERED | - |
| 8 | SKU0361 order 8.554,6 unit | decisions.csv raw_order | COVERED | - |
| 9 | P06: OTIF 72,1 persen, fill 83,2 persen, lead p90 11 hari | supplier_reliability.csv | COVERED | - |
| 10 | Label learn 81/29/29 | learn_summary.json | COVERED | - |
| 11 | Fill diamati 91,25 persen | learn_summary observed_fill_rate_mean | COVERED | - |
| 12 | WAPE median 9,15 persen | learn_summary forecast_wape_best_median | COVERED | - |
| 13 | Bulan terburuk April 2024, WAPE 78,05 | learn_curve.csv | COVERED | - |
| 14 | Bulan terbaik Juni 2025, WAPE 13,12 | learn_curve.csv | COVERED | - |
| 15 | "Sepuluh langkah" | run_chain.sh punya 11 invokasi (0, 0b, 1-9) | WRONG | ditulis sebelas program |
| 16 | "Tujuh baris pemeriksaan lulus" | tidak ada artefak yang mencetak 7 baris | UNVERIFIABLE | dihapus, diganti CHAIN OK |
| 17 | Tiga guardrail dipakai | variance_cap_binding 0, guardrail_flags none 600/600 | PARTIAL | ditambah paragraf batas |
| 18 | Amplification 1,31 ke 0,36 | decision_summary amplification, replay 104 hari | PARTIAL | disebut sebagai replay |
| 19 | Amplification 2,68 ke 0,24 | simulasi 250 hari indeks BI | COVERED | disebut sebagai simulasi |
| 20 | Delapan SKU cover 7 hari atau kurang, semuanya dipesan | snapshot + decisions | COVERED | - |
| 21 | Nilai delapan SKU Rp698.433.520 | konsol membacanya dari `test_cases.json` 19 Oktober, bukan keputusan 21 Oktober | WRONG (sumber basi) | `tools/test_cases.py` dijalankan ulang, sekarang Rp806.890.340 dan cocok dengan decisions.csv |
| 22 | Halaman konsol | 11 templat di web/ | MISSING 5 halaman | bagian 13.1 ditambah |
| 23 | Lambda AWS | URL hidup, HTTP 200, snapshot 125 keputusan | MISSING | bagian 19 ditambah |
| 24 | Joule | tidak ada kode integrasi | MISSING | ditulis belum disambung |
| 25 | AgentCore terkunci | architecture.md + kuota | COVERED | - |
| 26 | SAP AI Core RPT-1.6 | rpt_summary 200, 600 prediksi, 10,73 detik | COVERED | ditambahkan sebelumnya |
| 27 | RPT 577 kedaluwarsa vs agen 0 | rpt_summary + snapshot | COVERED | dicatat sebagai beda definisi |
| 28 | Kelas ABC 262/178/160, potong 80/95 | sku_classes.csv | COVERED | ditambahkan sebelumnya |
| 29 | XYZ semua Med | sku_classes.csv | COVERED | dicatat belum membedakan |
| 30 | Cap shelf tidak memotong baris | cap_from need times headroom, 600/600 | COVERED | - |
| 31 | below_reorder 65, expiry_risk 0 | position_summary.json | COVERED | - |
| 32 | Angka rapor turns 6,41, DIO 44,3, hilang 0,717 persen | compare_replays v4 | MISSING | bagian 15 ditambah |

Dicek 32 butir. Berubah 9: satu angka salah, satu hitungan program salah, satu klaim tanpa artefak, satu aturan yang tidak menyala, dua bagian baru (halaman konsol, AWS), tiga cacat baru masuk daftar.

## Perintah yang dipakai

```
python3 ~/.hermes/skills/deliverable-coverage-gate/scripts/surface_inventory.py /home/ubuntu/pasok
python3 -c "import json;print(json.load(open('data/orders/order_summary.json'))['auto_value_idr'])"
grep -c "\.py" run_chain.sh
python3 -c "import json;d=json.load(open('data/agents/decision_summary.json'));print(d['variance_cap_binding'])"
curl -s -X POST <lambda-url> -d '{"question":"how many skus"}'
.venv/bin/python tools/compare_replays.py data/sim/replay2026_v4 data/sim/nopayday
```
