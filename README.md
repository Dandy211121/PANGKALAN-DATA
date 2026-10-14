# E-Commerce Data Warehouse (DWH) & ETL Pipeline

Proyek perancangan **Data Warehouse (DWH)** dan pipeline **ETL (Extract, Transform, Load)** untuk platform E-Commerce berbasis **7 Dimensi Data Quality**, pemodelan *Star Schema*, implementasi *Slowly Changing Dimension Type 2 (SCD Type 2)*, serta otomasi *Scheduler Pipeline*.

---

## 📌 Fitur Utama

1. **Simulasi Data Kotor OLTP (`1_generate_oltp.py`)**:
   - Mensimulasikan kondisi riil data operasional: missing values (NULL), data duplikat, dan pelanggaran logika bisnis (*bad business logic*).
2. **Pipeline ETL Komprehensif (`2_etl_process.py`)**:
   - **DQ-1 Completeness**: Penanganan NULL (imputasi / penyaringan).
   - **DQ-2 Accuracy**: Rekonsiliasi perhitungan matematis subtotal & total order.
   - **DQ-3 Consistency**: Standardisasi format nama, email, telepon, dan tanggal ISO.
   - **DQ-4 Uniqueness**: Deduplikasi pelanggan & item, pembentukan Surrogate Key.
   - **DQ-5 Validity**: Validasi batas bisnis (harga wajar, qty > 0, telepon valid, dsb).
   - **DQ-6 Referential Integrity**: Eliminasi orphan record sebelum memuat tabel fakta.
   - **DQ-7 Timeliness (SCD-2)**: Pelacakan histori perubahan data master pelanggan (`valid_from`, `valid_to`, `is_current`, `dwh_version`).
3. **Analisis Bisnis OLAP (`3_dwh_analysis.py`)**:
   - Query analitis multi-dimensi: performa penjualan per kategori, top produk, tren kuartalan, dan status pesanan.
4. **Otomatisasi Scheduler (`4_etl_scheduler.py` & `run_scheduler.bat`)**:
   - Mendukung eksekusi berkala berbasis interval detik/menit atau jadwal harian otomatis.
   - Pencatatan log eksekusi ke `scheduler_log.txt`.

---

## 📁 Struktur Direktori

```
DWH/
├── 1_generate_oltp.py    # Generator database operasional OLTP + simulasi data kotor
├── 2_etl_process.py      # Pipeline ETL: 7 Dimensi DQ, SCD-2, pembentukan DWH
├── 3_dwh_analysis.py     # Query analitis OLAP pada DWH
├── 4_etl_scheduler.py    # Otomatisasi Scheduler pipeline ETL (Interval / Harian)
├── run_scheduler.bat     # Batch launcher 1-klik untuk scheduler di Windows
├── oltp_ecommerce.db     # Basis data sumber OLTP (SQLite)
├── dwh_ecommerce.db      # Basis data Data Warehouse (SQLite)
├── etl_log.txt           # Log audit data quality ETL
├── scheduler_log.txt     # Log riwayat eksekusi scheduler
├── laporan_dwh.md        # Laporan lengkap proyek
└── README.md             # Dokumentasi utama repositori
```

---

## 🚀 Panduan Eksekusi

### 1. Eksekusi Manual (Urutan Tahapan)
Pastikan Python 3 sudah terpasang, lalu jalankan perintah berikut secara berurutan di terminal:
```bash
py -3 1_generate_oltp.py
py -3 2_etl_process.py
py -3 3_dwh_analysis.py
```

### 2. Menjalankan Scheduler Otomatis
* **Mode Interval (Tiap 60 Detik / Demo):**
  ```bash
  py -3 4_etl_scheduler.py --interval 60
  ```
  *(Atau double-click file `run_scheduler.bat`)*

* **Mode Harian (Tiap Tengah Malam):**
  ```bash
  py -3 4_etl_scheduler.py --daily 00:00
  ```

---

## 👥 Pengembang
* **Nama Akun:** Dandy211121
* **Mata Kuliah:** Pangkalan Data / Data Warehouse (Semester 3)
