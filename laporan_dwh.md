# Laporan Proyek ETL & Data Warehouse
## E-Commerce Online Shop

---

## 2. 7 Dimensi Data Quality yang Diimplementasikan

| Kode | Dimensi DQ | Definisi | Implementasi dalam Proyek |
|------|------------|----------|---------------------------|
| DQ-1 | **Completeness** | Tidak ada atribut penting yang kosong tanpa alasan | Imputasi nilai default / hapus jika non-identifiable |
| DQ-2 | **Accuracy** | Nilai mencerminkan fakta riil bisnis | Rekonsiliasi subtotal (qty × price) & total order |
| DQ-3 | **Consistency** | Format seragam di semua tabel | Standardisasi nama, email, gender, nomor telepon, tanggal |
| DQ-4 | **Uniqueness** | Tidak ada rekaman ganda / redundan | Deduplikasi pelanggan & item, pembentukan Surrogate Key |
| DQ-5 | **Validity** | Validasi aturan logika bisnis | Validasi no. telepon (digit ≥10), harga (>0, ≤50jt), tanggal order, quantity |
| DQ-6 | **Referential Integrity** | Foreign Key merujuk ke Primary/Surrogate Key yang valid | Cek orphan record sebelum dimuat ke tabel fakta |
| DQ-7 | **Timeliness** | Histori perubahan data tercatat secara kronologis | Implementasi SCD Type 2 pada `dim_customer` |

---

## 3. Arsitektur Basis Data Sumber (OLTP)

Tabel OLTP yang digunakan sebagai sumber data transaksi:

| Tabel | Keterangan | Jumlah Record (kotor) |
|-------|-----------|----------------------|
| `customers` | Data profil pelanggan | 214 |
| `products` | Data katalog produk & harga | 25 |
| `orders` | Header transaksi pesanan | 507 |
| `order_items` | Rincian barang per pesanan | 1.587 |
| `payments` | Transaksi pembayaran | 502 |

### Relasi OLTP

```
customers (1) ──── (N) orders (1) ──── (N) order_items (N) ──── (1) products
                         │
                        (1)
                         │
                    payments (N)
```

---

## 4. Simulasi Data Kotor pada Sumber OLTP

Untuk mensimulasikan data riil dari sistem operasional, data kotor disisipkan dengan skenario:

### Teknik 1 — NULL Values
| Record | Tabel | Field yang NULL |
|--------|-------|----------------|
| 5 customer | `customers` | `full_name`, `email`, `phone`, `city`, `gender` |
| 3 order | `orders` | `status`, `total_amount` |
| 2 product | `products` | `category`, `price` |

### Teknik 2 — Duplikasi
| Record | Tabel | Jenis Duplikat |
|--------|-------|----------------|
| 3 customer | `customers` | Email sama persis / nama dengan huruf besar |
| 23 order item | `order_items` | `item_id` berbeda, isi barang dan pesanan sama |

### Teknik 3 — Bad Business Logic
| Record | Tabel | Masalah Logika Bisnis |
|--------|-------|-----------------------|
| 4 product | `products` | Harga negatif, nol, atau ekstrem (999 juta) |
| 2 order item | `order_items` | Quantity <= 0, subtotal tidak sesuai |
| 4 order | `orders` | Total negatif, tanggal masa depan (2099) atau terlalu lampau (2015) |
| 2 payment | `payments` | Amount negatif atau nol |
| 4 customer | `customers` | No. telepon tidak valid (huruf / <10 digit), gender di luar 'L'/'P' |


## 6. Detail Implementasi ETL per 7 Dimensi DQ

### DQ-1: Completeness — NULL Value Handling
| Field | Aksi | Alasan |
|-------|------|--------|
| `full_name` + `email` keduanya NULL | **Dihapus** | Tidak bisa diidentifikasi sama sekali |
| `full_name` NULL saja | Diisi `"Unknown Customer"` | Nama opsional jika email ada |
| `email` NULL saja | Diisi `"unknown@placeholder.com"` | Placeholder email |
| `phone` NULL | Diisi `"Tidak Tersedia"` | Field opsional |
| `city/province/island` NULL | Diisi `"Tidak Diketahui"` | Diperlukan analisis geografis |
| `gender` NULL | Diisi `"Tidak Diketahui"` | Nilai default |
| `price` NULL | Diisi `0.0` | Nilai default, ditolak di DQ-5 |
| `status` order NULL | Diisi `"Unknown"` | Menjamin kelengkapan status |
| `total_amount` NULL | Diisi `0.0` | Menghindari nilai NULL numerik |

**Hasil: 1 record dihapus, 19 field diisi**

---

### DQ-2: Accuracy — Rekonsiliasi Nilai
| Validasi | Aturan | Tindakan |
|----------|--------|----------|
| `subtotal` item | Harus = `quantity × unit_price` | Dikoreksi otomatis |
| `total_amount` order | Selisih > 10% dari sum(items) | Dikoreksi ke nilai item |

**Hasil: 3 nilai dikoreksi**

---

### DQ-3: Consistency — Standardisasi Format
| Field | Transformasi |
|-------|-------------|
| `full_name` | → Title Case ("BUDI" → "Budi") |
| `email` | → Lowercase + trim spasi |
| `phone` | → Hapus spasi dan karakter non-digit |
| `gender` | → Uppercase ("l" → "L") |
| `city`, `province` | → Title Case |
| `category`, `status` | → Title Case |
| Semua tanggal | → Format seragam ISO YYYY-MM-DD |
| `payment_method` | → Title Case |

---

### DQ-4: Uniqueness — Deduplication + Surrogate Key
| Tabel | Kriteria | Aksi | Jumlah |
|-------|----------|------|--------|
| `customers` | Email sama (case-insensitive) | Pertahankan customer_id terkecil | 4 dihapus |
| `order_items` | order_id + product_id + qty + price sama | Pertahankan item_id terkecil | 23 dihapus |
| DWH Dimensi | - | **Surrogate Key** AUTOINCREMENT di semua dimensi | - |

**Hasil: 27 duplikat dihapus**

---

### DQ-5: Validity — Business Rule Validation
| Validasi | Aturan Bisnis | Aksi | Jumlah |
|----------|--------------|------|--------|
| Nomor telepon pelanggan | Digit numerik ≥ 10 digit | Dihapus | 2 |
| Gender pelanggan | Hanya `"L"` atau `"P"` | Dihapus | 3 |
| Harga produk | `0 < harga ≤ Rp50.000.000` | Dihapus | 4 |
| Tanggal order | 2021-01-01 s/d sekarang | Dihapus | 2 |
| Total order | Harus `≥ 0` | Dihapus | 1 |
| Quantity item | Harus `> 0` | Dihapus | 1 |
| Payment amount | Harus `> 0` | Dihapus | 2 |

**Hasil: 15 record tidak valid dihapus**

---

### DQ-6: Referential Integrity — Validasi FK → SK Dimensi
Sebelum memuat ke tabel fakta, setiap baris transaksi divalidasi ke 4 tabel dimensi induk:
- `customer_key` harus ada di `dim_customer`
- `product_key` harus ada di `dim_product`
- `date_key` harus ada di `dim_date`
- `order_key` harus ada di `dim_order`

Baris yang referensinya tidak ditemukan (**orphan records**) dikeluarkan dan dicatat dalam audit log.

**Hasil: 13 orphan record (akibat deduplikasi akun pelanggan) disaring dan tidak dimuat ke tabel fakta**

---

### DQ-7: Timeliness — SCD Type 2 pada `dim_customer`
Karena DWH bersifat *time-variant*, perubahan data master pelanggan (misal: perpindahan domisili kota/provinsi atau nomor telepon) dilacak menggunakan **Slowly Changing Dimension Type 2**:

| Kolom | Fungsi |
|-------|--------|
| `valid_from` | Tanggal versi record mulai berlaku |
| `valid_to` | Tanggal versi record berakhir (NULL = masih aktif) |
| `is_current` | `1` = versi aktif, `0` = versi lama (historis) |
| `dwh_version` | Nomor urut versi (1, 2, dst.) |

---

## 7. Ringkasan Hasil Transformasi ETL

Tabel berikut menunjukkan perbandingan data sebelum dan sesudah tahap pembersihan data (Data Cleansing):

| Tabel OLTP | Sebelum ETL | Setelah ETL | Selisih (Dibersihkan) |
|------------|-------------|-------------|-----------------------|
| `customers` | 214 | 204 | -10 |
| `products` | 25 | 21 | -4 |
| `orders` | 507 | 504 | -3 |
| `order_items` | 1.587 | 1.563 | -24 |
| `payments` | 502 | 500 | -2 |

---

## 8. Hasil Pemuatan ke Data Warehouse (DWH)

Berikut adalah jumlah record aktual yang berhasil dimuat ke dalam skema DWH:

| Tabel DWH | Kategori | Jumlah Record | Keterangan / Peran |
|-----------|----------|---------------|-------------------|
| `dim_customer` | Dimensi | 204 | Master profil pelanggan (SCD Type 2) |
| `dim_product` | Dimensi | 21 | Master produk & kategori (SCD Type 1) |
| `dim_date` | Dimensi | 595 | Master kalender waktu transaksi (SCD Type 0) |
| `dim_order` | Dimensi | 504 | Master pesanan & status order (SCD Type 1) |
| `fact_sales` | Fakta | 1.553 | Transaksi penjualan per item barang |
| `fact_payments` | Fakta | 497 | Transaksi arus kas & status pembayaran |
| `etl_audit_log` | Audit | 5 | Log riwayat audit kualitas data ETL |

---

## 9. Hasil Analisis Bisnis (OLAP) dari DWH

Berikut adalah ringkasan hasil eksekusi query analitis dari file `3_dwh_analysis.py`:

### A. Penjualan per Kategori Produk
| Kategori | Jumlah Transaksi | Total Qty | Total Pendapatan |
|----------|------------------|-----------|------------------|
| Electronics | 380 | 938 | Rp 3.014.850.000 |
| Furniture | 149 | 382 | Rp 664.500.000 |
| Fashion | 386 | 951 | Rp 286.425.000 |
| Appliances | 179 | 429 | Rp 173.950.000 |
| Books | 235 | 604 | Rp 56.600.000 |
| Health | 224 | 537 | Rp 25.329.000 |

### B. Top 5 Produk Terlaris
| Produk | Kategori | Total Qty | Total Pendapatan |
|--------|----------|-----------|------------------|
| Blender Philips 2L | Appliances | 238 | Rp 107.100.000 |
| Kaos Polos Cotton | Fashion | 230 | Rp 17.250.000 |
| Kursi Gaming RGB | Furniture | 220 | Rp 462.000.000 |
| Buku Data Science | Books | 210 | Rp 25.200.000 |
| Jaket Hoodie Distro | Fashion | 207 | Rp 38.295.000 |

### C. Tren Penjualan per Kuartal
| Tahun | Q1 | Q2 | Q3 | Q4 |
|-------|----|----|----|----|
| 2022 | Rp 340,6 jt | Rp 289,3 jt | Rp 368,4 jt | Rp 339,5 jt |
| 2023 | Rp 316,5 jt | Rp 399,3 jt | Rp 362,0 jt | Rp 337,5 jt |
| 2024 | Rp 300,6 jt | Rp 376,7 jt | Rp 266,7 jt | Rp 524,6 jt |

### D. Distribusi Status Pesanan (via `dim_order`)
| Status Pesanan | Jumlah Order | Total Nilai Transaksi |
|----------------|--------------|-----------------------|
| Completed | 104 | Rp 822.396.000 |
| Shipped | 103 | Rp 936.740.000 |
| Processing | 103 | Rp 940.199.000 |
| Cancelled | 98 | Rp 954.643.000 |
| Returned | 89 | Rp 567.676.000 |

---

## 10. Struktur File Proyek & Instruksi Eksekusi

Struktur folder proyek diorganisasikan secara modular merepresentasikan arsitektur sistem:
**3 Sumber OLTP ➔ ETL Pipeline (Scheduler) ➔ Data Warehouse ➔ Dashboard / Viewing**

```
DWH/
├── 📂 1_oltp/                # Sumber data operasional (3 Cabang OLTP)
│   ├── generate_oltp.py     # Generator data kotor multi-cabang
│   ├── oltp_cabang_1.db     # Sumber 1: Cabang Jakarta (Head Office & Online)
│   ├── oltp_cabang_2.db     # Sumber 2: Cabang Surabaya (Retail Hub Timur)
│   └── oltp_cabang_3.db     # Sumber 3: Cabang Bandung (Regional Store)
│
├── 📂 2_etl/                 # Pipeline ETL & 7 Dimensi DQ
│   └── etl_pipeline.py      # Ekstraksi multi-sumber, cleansing, SCD-2, & load
│
├── 📂 3_scheduler/           # Otomatisasi Penjadwalan
│   ├── etl_scheduler.py     # Program scheduler (interval & daily)
│   ├── run_scheduler.bat    # Batch launcher 1-klik di Windows
│   └── scheduler_log.txt    # Log riwayat jadwal eksekusi
│
├── 📂 4_dwh/                 # Data Warehouse Storage
│   ├── schema_dwh.sql       # Skema DDL tabel dimensi & fakta
│   ├── dwh_ecommerce.db     # Basis data Star Schema DWH (SQLite)
│   └── etl_audit_log.txt    # Log audit kualitas data
│
├── 📂 5_dashboard/           # Lapisan Presentasi & Viewing
│   ├── dashboard_app.py     # Web Dashboard Interaktif (Port 8080)
│   ├── olap_analysis.py     # Script analisis bisnis OLAP
│   ├── run_dashboard.bat    # Batch launcher 1-klik web dashboard
│   └── 📂 charts/           # Grafik visualisasi bisnis (PNG)
│
├── 📄 main.py                # Runner terpusat menu interaktif
├── 📄 README.md              # Dokumentasi arsitektur repositori
└── 📄 laporan_dwh.md         # Laporan komprehensif proyek
```

### Instruksi Eksekusi Terpusat:
Jalankan file `main.py` di terminal untuk mengakses menu terintegrasi:
```bash
py -3 main.py
```

Atau jalankan per modul secara langsung:
1. **Generate 3 Sumber OLTP:** `py -3 1_oltp/generate_oltp.py`
2. **Jalankan Pipeline ETL:** `py -3 2_etl/etl_pipeline.py`
3. **Buka Web Dashboard:** `py -3 5_dashboard/dashboard_app.py` *(akses di `http://localhost:8080`)*
4. **Analisis Bisnis OLAP & Grafik:** `py -3 5_dashboard/olap_analysis.py`
5. **Jalankan Scheduler:** `py -3 3_scheduler/etl_scheduler.py --interval 60`
