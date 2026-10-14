# E-Commerce Data Warehouse (DWH) & ETL Pipeline

Proyek perancangan **Data Warehouse (DWH)** dan pipeline **ETL (Extract, Transform, Load)** untuk platform E-Commerce berbasis **7 Dimensi Data Quality**, pemodelan *Star Schema*, implementasi *Slowly Changing Dimension Type 2 (SCD Type 2)*, otomatisasi *Scheduler*, dan *Web Dashboard / Viewing*.

---

## 🏗️ Arsitektur Sistem

Arsitektur pipeline data dirancang modular sesuai alur berikut:

```
┌──────────────┐
│ OLTP Cabang 1│──┐
└──────────────┘  │
┌──────────────┐  │       ┌──────────────┐       ┌──────────────┐       ┌────────────────────┐
│ OLTP Cabang 2│──┼──────>│ ETL Pipeline │──────>│     DWH      │──────>│ Dashboard / Viewing│
└──────────────┘  │       └──────┬───────┘       └──────────────┘       └────────────────────┘
┌──────────────┐  │              │
│ OLTP Cabang 3│──┘              ▼
└──────────────┘          ┌──────────────┐
                          │  Scheduler   │
                          └──────────────┘
```

1. **3 Sumber OLTP (`1_oltp/`)**: 3 basis data transaksi cabang independen (Jakarta, Surabaya, Bandung) dengan simulasi data kotor.
2. **ETL Pipeline (`2_etl/`)**: Ekstraksi multi-sumber, pembersihan berbasis 7 Dimensi Data Quality, dan pembentukan Star Schema.
3. **Scheduler (`3_scheduler/`)**: Program otomatisasi yang memicu eksekusi pipeline ETL secara berkala (interval / harian).
4. **Data Warehouse (`4_dwh/`)**: Basis data analitik Star Schema dengan 4 tabel dimensi dan 2 tabel fakta.
5. **Dashboard / Viewing (`5_dashboard/`)**: Lapisan visualisasi interaktif web modern dan ekspor grafik OLAP.

---

## 📁 Struktur Direktori Proyek

```
PROYEK_DWH/
├── 📂 1_oltp/                        # Sumber data operasional OLTP (3 Cabang)
│   ├── generate_oltp.py             # Script pembuat data kotor 3 cabang
│   ├── oltp_cabang_1.db             # Cabang Jakarta (Head Office & Online)
│   ├── oltp_cabang_2.db             # Cabang Surabaya (Retail Hub Timur)
│   └── oltp_cabang_3.db             # Cabang Bandung (Regional Store)
│
├── 📂 2_etl/                         # Pipeline ETL & 7 Dimensi Data Quality
│   └── etl_pipeline.py              # Ekstraksi multi-cabang, 7 DQ, SCD-2, & Load
│
├── 📂 3_scheduler/                   # Pengatur Jadwal Otomatis
│   ├── etl_scheduler.py             # Program scheduler (interval & daily)
│   ├── run_scheduler.bat            # Launcher batch 1-klik di Windows
│   └── scheduler_log.txt            # Log riwayat jadwal eksekusi
│
├── 📂 4_dwh/                         # Penyimpanan Data Warehouse
│   ├── schema_dwh.sql               # Skema DDL tabel dimensi & fakta
│   ├── dwh_ecommerce.db             # Basis data Star Schema SQLite
│   └── etl_audit_log.txt            # Log audit integritas & data quality
│
├── 📂 5_dashboard/                   # Lapisan Dashboard & Viewing
│   ├── dashboard_app.py             # Web dashboard interaktif (Port 8080)
│   ├── olap_analysis.py             # Script analisis bisnis OLAP
│   ├── run_dashboard.bat            # Launcher 1-klik web dashboard
│   └── 📂 charts/                   # Grafik visual bisnis (PNG)
│
├── 📄 main.py                        # Runner terpusat menu interaktif
├── 📄 laporan_dwh.md                 # Laporan akademik lengkap proyek
├── 📄 README.md                      # Dokumentasi arsitektur repositori
└── 📄 .gitignore                     # Filter file cache & lingkungan lokal
```

---

## 🚀 Panduan Eksekusi

### Opsi A: Menggunakan Menu Utama (`main.py`)
Jalankan file runner utama di terminal:
```bash
py -3 main.py
```
Pilih opsi menu:
* `1` : Generate 3 Basis Data OLTP
* `2` : Jalankan Pipeline ETL (7 DQ)
* `3` : Jalankan Analisis OLAP & Generate Chart
* `4` : Buka Web Dashboard (http://localhost:8080)
* `5` : Jalankan Scheduler
* `6` : Eksekusi End-to-End Pipeline

---

### Opsi B: Eksekusi Langsung per Modul

#### 1. Generate Multi-Sumber OLTP
```bash
py -3 1_oltp/generate_oltp.py
```

#### 2. Jalankan Pipeline ETL (Extract, 7 DQ, Load)
```bash
py -3 2_etl/etl_pipeline.py
```

#### 3. Jalankan Web Dashboard / Viewing
```bash
py -3 5_dashboard/dashboard_app.py
```
*(Atau double-click `5_dashboard/run_dashboard.bat` untuk membuka dashboard di browser http://localhost:8080)*

#### 4. Jalankan Analisis Bisnis & Grafik
```bash
py -3 5_dashboard/olap_analysis.py
```

#### 5. Jalankan Scheduler Otomatis
```bash
py -3 3_scheduler/etl_scheduler.py --interval 60
```

---

## 🛡️ 7 Dimensi Data Quality yang Diimplementasikan
* **DQ-1 Completeness**: Menghapus baris non-identifikasi & imputasi nilai default pada atribut parsial.
* **DQ-2 Accuracy**: Rekonsiliasi perkalian subtotal item (`qty x price`) dan total pesanan.
* **DQ-3 Consistency**: Standardisasi teks ke Title Case, email lowercase, dan format tanggal ISO `YYYY-MM-DD`.
* **DQ-4 Uniqueness**: Deduplikasi akun pelanggan, rincian item, dan pembayaran.
* **DQ-5 Validity**: Validasi batas logika bisnis (nomor HP ≥ 10 digit, gender L/P, harga produk > 0 dan ≤ 50jt, qty > 0).
* **DQ-6 Referential Integrity**: Eliminasi orphan records sebelum memuat data ke tabel fakta.
* **DQ-7 Timeliness**: Pelacakan histori perubahan master profil pelanggan menggunakan **SCD Type 2**.

---

## 👥 Pengembang
* **Nama Akun:** Dandy211121
* **Mata Kuliah:** Pangkalan Data / Data Warehouse (Semester 3)
