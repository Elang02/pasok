# Potongan kode

Repo ini menyimpan sebagian kode Pasok, bukan semuanya. Yang ada di sini bisa dibaca dan dijelaskan,
tapi tidak bisa langsung dijalankan.

| File | Asal | Isi |
| --- | --- | --- |
| `registry_catalog.py` | `src/demand/registry_catalog.py` | Membangun registry katalog 600 SKU: kategori, principal, umur simpan, permintaan dasar, biaya satuan, volatilitas, credit limit |
| `handler.py` | `aws/lambda/pasok_agent/handler.py` | Handler Lambda: meminta token SAP AI Core dari client credentials, token Bedrock dari peran fungsi, lalu memanggil model untuk menulis alasan dan menjawab konsol |
| `run_chain.sh` | `run_chain.sh` | Rantai sebelas program: registry, build_prep, stock_position, decision, consolidation, order_executor, order_intake, notification, redirect, learn, one_pass |

`run_chain.sh` memanggil `tools/build_prep.py` dan sembilan file `src/agents/*.py` yang tidak ikut di
repo ini. Skrip disertakan karena ia menunjukkan urutan dan ketergantungan rantai, bukan karena bisa
dijalankan.

## Menjalankan ulang artefak

Tidak bisa. Artefak di `data/` adalah keluaran jadi, bukan hasil yang bisa dibangun ulang dari repo
ini. Kalau butuh menjalankan rantai, diperlukan kode lengkap plus katalog dan kalender event yang
sudah ada di `data/catalog/` dan `data/demand/`.
