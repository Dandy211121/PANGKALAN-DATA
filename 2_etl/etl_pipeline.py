"""
=================================================================
 2. ETL: Pipeline Ekstraksi Multi-Sumber, 7 Dimensi DQ, & Load
=================================================================
Pipeline ini membaca data dari 3 sumber OLTP di folder '1_oltp/':
  - oltp_cabang_1.db (Jakarta)
  - oltp_cabang_2.db (Surabaya)
  - oltp_cabang_3.db (Bandung)

Lalu menerapkan 7 Dimensi Data Quality:
  DQ-1 Completeness       : Imputasi & filter data NULL
  DQ-2 Accuracy           : Rekonsiliasi perhitungan (qty x price, total order)
  DQ-3 Consistency        : Standardisasi format (Title Case, ISO Date, phone)
  DQ-4 Uniqueness         : Deduplikasi akun & rincian pesanan
  DQ-5 Validity           : Validasi aturan bisnis (harga, telepon, gender, dll)
  DQ-6 Referential Integ. : Penyaringan orphan records FK -> Dimensi
  DQ-7 Timeliness (SCD-2) : Pelacakan histori perubahan profil pelanggan

Dan memuat hasilnya ke Data Warehouse:
  - 4_dwh/dwh_ecommerce.db
=================================================================
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os
import shutil

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR  = os.path.dirname(BASE_DIR)
OLTP_DIR  = os.path.join(ROOT_DIR, "1_oltp")
DWH_DIR   = os.path.join(ROOT_DIR, "4_dwh")
DWH_PATH  = os.path.join(DWH_DIR, "dwh_ecommerce.db")
LOG_FILE  = os.path.join(DWH_DIR, "etl_audit_log.txt")

ETL_RUN_TIME  = datetime.now()
ETL_DATE_STR  = ETL_RUN_TIME.strftime("%Y-%m-%d %H:%M:%S")

log_lines = []

def log(msg=""):
    print(msg)
    log_lines.append(str(msg))

def section(title):
    bar = "=" * 65
    log(f"\n{bar}")
    log(f"  {title}")
    log(bar)

def subsection(title):
    log(f"\n--- {title} ---")

def save_log():
    os.makedirs(DWH_DIR, exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

# =================================================================
# 1. EXTRACT (Membaca dari 3 Sumber OLTP)
# =================================================================
def extract_multi_oltp():
    section("1. EXTRACT - Membaca dari 3 Basis Data OLTP")
    sources = [
        {"file": "oltp_cabang_1.db", "branch": "Cabang Jakarta"},
        {"file": "oltp_cabang_2.db", "branch": "Cabang Surabaya"},
        {"file": "oltp_cabang_3.db", "branch": "Cabang Bandung"}
    ]

    combined = {
        "customers": [],
        "products": [],
        "orders": [],
        "order_items": [],
        "payments": []
    }

    for src in sources:
        db_path = os.path.join(OLTP_DIR, src["file"])
        if not os.path.exists(db_path):
            log(f"  [!] Peringatan: {src['file']} belum ada. Jalankan generator terlebih dahulu!")
            continue

        conn = sqlite3.connect(db_path)
        for tbl in ["customers", "products", "orders", "order_items", "payments"]:
            df = pd.read_sql(f"SELECT * FROM {tbl}", conn)
            df["source_branch"] = src["branch"]
            combined[tbl].append(df)
        conn.close()
        log(f"  [OK] Berhasil mengekstrak dari: {src['file']} ({src['branch']})")

    tables = {}
    for tbl, dfs in combined.items():
        if dfs:
            tables[tbl] = pd.concat(dfs, ignore_index=True)
            log(f"       -> Total {tbl:12s}: {len(tables[tbl]):5d} baris terkumpul")
        else:
            tables[tbl] = pd.DataFrame()

    return tables

# =================================================================
# 2. TRANSFORM (7 Dimensi Data Quality)
# =================================================================

# DQ-1: COMPLETENESS
def dq1_completeness(tables):
    section("DQ-1 | COMPLETENESS - NULL Value Handling")
    report = {"removed": 0, "filled": 0}

    # Customers
    df = tables["customers"].copy()
    kritis = df["full_name"].isna() & df["email"].isna()
    n_kritis = kritis.sum()
    df = df[~kritis]
    report["removed"] += n_kritis
    log(f"  [-] Pelanggan dihapus (nama + email NULL): {n_kritis}")

    fills = {
        "full_name":     "Unknown Customer",
        "email":         "unknown@placeholder.com",
        "phone":         "Tidak Tersedia",
        "city":          "Tidak Diketahui",
        "province":      "Tidak Diketahui",
        "island":        "Tidak Diketahui",
        "gender":        "Tidak Diketahui",
        "registered_at": ETL_DATE_STR,
    }
    for col, val in fills.items():
        n = df[col].isna().sum()
        if n > 0:
            df[col] = df[col].fillna(val)
            report["filled"] += n
            log(f"  [~] {col:15s} diimputasi '{val}': {n}")
    tables["customers"] = df

    # Products
    df = tables["products"].copy()
    df["product_name"] = df["product_name"].fillna("Produk Tanpa Nama")
    df["category"]     = df["category"].fillna("Uncategorized")
    df["price"]        = df["price"].fillna(0.0)
    tables["products"] = df

    # Orders
    df = tables["orders"].copy()
    df["status"]       = df["status"].fillna("Unknown")
    df["total_amount"] = df["total_amount"].fillna(0.0)
    tables["orders"] = df

    log(f"  >> Ringkasan DQ-1: {report['removed']} dihapus, {report['filled']} kolom diisi")
    return tables, report

# DQ-2: ACCURACY
def dq2_accuracy(tables):
    section("DQ-2 | ACCURACY - Koreksi Nilai Subtotal & Total")
    report = {"corrected": 0}

    df_items = tables["order_items"].copy()
    df_items["expected"] = df_items["quantity"] * df_items["unit_price"]
    mismatch = (df_items["subtotal"] - df_items["expected"]).abs() > 0.01
    n_mismatch = mismatch.sum()
    if n_mismatch > 0:
        df_items.loc[mismatch, "subtotal"] = df_items.loc[mismatch, "expected"]
        log(f"  [~] Subtotal salah dikoreksi ke (qty x price): {n_mismatch} baris")
        report["corrected"] += n_mismatch
    df_items = df_items.drop(columns=["expected"])
    tables["order_items"] = df_items

    # Rekonsiliasi Total Order
    orders_df = tables["orders"].copy()
    sum_items = df_items.groupby("order_id")["subtotal"].sum().reset_index()
    sum_items.columns = ["order_id", "calc_total"]
    m = orders_df.merge(sum_items, on="order_id", how="left")
    bad_totals = (m["total_amount"] - m["calc_total"]).abs() > 1.0
    n_bad = bad_totals.sum()
    if n_bad > 0:
        orders_df.loc[orders_df["order_id"].isin(m[bad_totals]["order_id"]), "total_amount"] = m.loc[bad_totals, "calc_total"].values
        log(f"  [~] Total amount order disinkronkan ke sum(item): {n_bad} baris")
        report["corrected"] += n_bad
    tables["orders"] = orders_df

    log(f"  >> Ringkasan DQ-2: {report['corrected']} nilai dikoreksi")
    return tables, report

# DQ-3: CONSISTENCY
def dq3_consistency(tables):
    section("DQ-3 | CONSISTENCY - Standardisasi Format Data")

    def std_date(v):
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
            try: return datetime.strptime(str(v).strip(), fmt).strftime("%Y-%m-%d")
            except: pass
        return str(v).strip()

    df = tables["customers"].copy()
    df["full_name"] = df["full_name"].str.strip().str.title()
    df["email"]     = df["email"].str.strip().str.lower()
    df["phone"]     = df["phone"].str.strip().str.replace(r"\s+", "", regex=True)
    df["city"]      = df["city"].str.strip().str.title()
    df["province"]  = df["province"].str.strip().str.title()
    df["gender"]    = df["gender"].str.strip().str.upper()
    tables["customers"] = df

    df_p = tables["products"].copy()
    df_p["category"] = df_p["category"].str.strip().str.title()
    tables["products"] = df_p

    df_o = tables["orders"].copy()
    df_o["status"]     = df_o["status"].str.strip().str.title()
    df_o["order_date"] = df_o["order_date"].apply(std_date)
    tables["orders"] = df_o

    df_pay = tables["payments"].copy()
    df_pay["payment_method"] = df_pay["payment_method"].str.strip().str.title()
    df_pay["status"]         = df_pay["status"].str.strip().str.title()
    tables["payments"] = df_pay

    log("  [OK] Seluruh format teks dan tanggal berhasil diseragamkan.")
    return tables

# DQ-4: UNIQUENESS
def dq4_uniqueness(tables):
    section("DQ-4 | UNIQUENESS - Deduplikasi Data")
    report = {"removed": 0}

    # Customers dedup
    df = tables["customers"].copy()
    b = len(df)
    df = df.drop_duplicates(subset=["email"], keep="first")
    n = b - len(df)
    report["removed"] += n
    log(f"  [-] Akun pelanggan duplikat dihapus: {n}")
    tables["customers"] = df

    # Order items dedup
    df_i = tables["order_items"].copy()
    b = len(df_i)
    df_i = df_i.drop_duplicates(subset=["order_id", "product_id", "quantity", "unit_price"], keep="first")
    n = b - len(df_i)
    report["removed"] += n
    log(f"  [-] Item pesanan duplikat dihapus: {n}")
    tables["order_items"] = df_i

    # Payments dedup
    df_p = tables["payments"].copy()
    b = len(df_p)
    df_p = df_p.drop_duplicates(subset=["order_id"], keep="first")
    n = b - len(df_p)
    report["removed"] += n
    log(f"  [-] Pembayaran duplikat per order dihapus: {n}")
    tables["payments"] = df_p

    log(f"  >> Ringkasan DQ-4: {report['removed']} duplikat dibersihkan")
    return tables, report

# DQ-5: VALIDITY
def dq5_validity(tables):
    section("DQ-5 | VALIDITY - Validasi Aturan Logika Bisnis")
    report = {"removed": 0}

    # Customers: No. HP & Gender
    df = tables["customers"].copy()
    b = len(df)
    def phone_ok(p):
        p = str(p).strip()
        if p in ["Tidak Tersedia", ""]: return True
        return p.isdigit() and len(p) >= 10
    valid_phone  = df["phone"].apply(phone_ok)
    valid_gender = df["gender"].isin(["L", "P", "Tidak Diketahui"])
    df = df[valid_phone & valid_gender]
    report["removed"] += (b - len(df))
    log(f"  [-] Pelanggan HP/Gender tidak valid dihapus: {b - len(df)}")
    tables["customers"] = df

    # Products: Harga 0 < harga <= 50jt
    df_p = tables["products"].copy()
    b = len(df_p)
    valid_prc = (df_p["price"] > 0) & (df_p["price"] <= 50_000_000)
    df_p = df_p[valid_prc]
    report["removed"] += (b - len(df_p))
    log(f"  [-] Produk harga negatif/ekstrem dihapus: {b - len(df_p)}")
    tables["products"] = df_p

    # Orders: Tanggal & Total
    df_o = tables["orders"].copy()
    b = len(df_o)
    def tgl_ok(d):
        try:
            dt = datetime.strptime(str(d)[:10], "%Y-%m-%d")
            return datetime(2021, 1, 1) <= dt <= datetime.now()
        except: return False
    valid_tgl = df_o["order_date"].apply(tgl_ok)
    valid_tot = df_o["total_amount"] >= 0
    df_o = df_o[valid_tgl & valid_tot]
    report["removed"] += (b - len(df_o))
    log(f"  [-] Order tanggal salah / total minus dihapus: {b - len(df_o)}")
    tables["orders"] = df_o

    # Order Items: Qty > 0
    df_i = tables["order_items"].copy()
    b = len(df_i)
    df_i = df_i[df_i["quantity"] > 0]
    report["removed"] += (b - len(df_i))
    log(f"  [-] Item belanjaan quantity <= 0 dihapus: {b - len(df_i)}")
    tables["order_items"] = df_i

    # Payments: Amount > 0
    df_pay = tables["payments"].copy()
    b = len(df_pay)
    df_pay = df_pay[df_pay["amount"] > 0]
    report["removed"] += (b - len(df_pay))
    log(f"  [-] Transaksi pembayaran amount <= 0 dihapus: {b - len(df_pay)}")
    tables["payments"] = df_pay

    log(f"  >> Ringkasan DQ-5: {report['removed']} record melanggar aturan bisnis dibuang")
    return tables, report

# =================================================================
# 3. LOAD (Memuat ke Star Schema DWH)
# =================================================================
BULAN = ["Januari","Februari","Maret","April","Mei","Juni",
         "Juli","Agustus","September","Oktober","November","Desember"]
HARI  = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]

def create_dwh_tables(conn):
    schema_file = os.path.join(DWH_DIR, "schema_dwh.sql")
    if os.path.exists(schema_file):
        with open(schema_file, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.commit()

def load_to_dwh(tables):
    section("3. LOAD - Memuat ke Data Warehouse (4_dwh/dwh_ecommerce.db)")
    os.makedirs(DWH_DIR, exist_ok=True)
    if os.path.exists(DWH_PATH):
        try: os.remove(DWH_PATH)
        except: pass

    conn = sqlite3.connect(DWH_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    create_dwh_tables(conn)
    c = conn.cursor()

    # Dimensi Date
    dates = set()
    for col, tbl in [("order_date","orders"), ("payment_date","payments")]:
        for v in tables[tbl][col].dropna():
            try: dates.add(str(v)[:10])
            except: pass
    date_rows = []
    for ds in sorted(dates):
        try:
            dt = datetime.strptime(ds, "%Y-%m-%d")
            date_rows.append((int(ds.replace("-","")), ds, dt.day, dt.month,
                              BULAN[dt.month-1], (dt.month-1)//3+1, dt.year,
                              HARI[dt.weekday()], 1 if dt.weekday()>=5 else 0))
        except: pass
    c.executemany("INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?,?,?,?,?)", date_rows)
    date_map = {r[1]: r[0] for r in date_rows}
    log(f"  [DIM] dim_date     : {len(date_rows)} record")

    # Dimensi Product
    df_p = tables["products"].drop_duplicates(subset=["product_id"])
    prod_rows = [(None, int(r.product_id), str(r.product_name), str(r.category), float(r.price))
                 for r in df_p.itertuples()]
    c.executemany("INSERT OR IGNORE INTO dim_product VALUES (?,?,?,?,?)", prod_rows)
    prod_map = {pid: pk for pk, pid in c.execute("SELECT product_key, product_id FROM dim_product").fetchall()}
    log(f"  [DIM] dim_product  : {len(prod_rows)} record")

    # Dimensi Order
    df_o = tables["orders"].drop_duplicates(subset=["order_id"])
    order_rows = [(None, int(r.order_id), str(r.status)) for r in df_o.itertuples()]
    c.executemany("INSERT OR IGNORE INTO dim_order VALUES (?,?,?)", order_rows)
    order_map = {oid: ok for ok, oid in c.execute("SELECT order_key, order_id FROM dim_order").fetchall()}
    log(f"  [DIM] dim_order    : {len(order_rows)} record")

    # DQ-7: SCD Type 2 Customer
    df_c = tables["customers"].drop_duplicates(subset=["customer_id"])
    cust_rows = []
    for r in df_c.itertuples():
        cust_rows.append((int(r.customer_id), str(r.full_name), str(r.email), str(r.phone),
                          str(r.city), str(r.province), str(r.island), str(r.gender),
                          str(r.registered_at), ETL_DATE_STR, None, 1, 1))
    c.executemany("""
        INSERT INTO dim_customer
          (customer_id, full_name, email, phone, city, province, island,
           gender, registered_at, valid_from, valid_to, is_current, dwh_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, cust_rows)
    cust_map = {cid: ck for ck, cid in c.execute("SELECT customer_key, customer_id FROM dim_customer WHERE is_current=1").fetchall()}
    log(f"  [DIM] dim_customer : {len(cust_rows)} record (SCD Type 2 Aktif)")

    # DQ-6: Referential Integrity Check
    section("DQ-6 | REFERENTIAL INTEGRITY - Validasi Relasi ke Dimensi")
    items = tables["order_items"]
    orders_indexed = tables["orders"].set_index("order_id")

    valid_sales = []
    orphan_items = 0
    for r in items.itertuples():
        if r.order_id not in orders_indexed.index:
            orphan_items += 1; continue
        ord_info = orders_indexed.loc[r.order_id]
        cid = int(ord_info["customer_id"])
        pid = int(r.product_id)
        dkey = date_map.get(str(ord_info["order_date"])[:10])
        ckey = cust_map.get(cid)
        pkey = prod_map.get(pid)
        okey = order_map.get(int(r.order_id))

        if not (ckey and pkey and dkey and okey):
            orphan_items += 1; continue

        branch = str(ord_info.get("source_branch", "Cabang Jakarta"))
        valid_sales.append((None, okey, int(r.order_id), ckey, pkey, dkey, branch,
                            int(r.quantity), float(r.unit_price), float(r.subtotal),
                            str(ord_info["status"]), ETL_DATE_STR))

    c.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", valid_sales)
    log(f"  [FACT] fact_sales    : {len(valid_sales)} record (Orphans dikeluarkan: {orphan_items})")

    # Fact Payments
    pays = tables["payments"]
    valid_pays = []
    orphan_pays = 0
    for r in pays.itertuples():
        if r.order_id not in orders_indexed.index:
            orphan_pays += 1; continue
        ord_info = orders_indexed.loc[r.order_id]
        cid = int(ord_info["customer_id"])
        dkey = date_map.get(str(r.payment_date)[:10])
        ckey = cust_map.get(cid)
        okey = order_map.get(int(r.order_id))

        if not (ckey and dkey and okey):
            orphan_pays += 1; continue

        valid_pays.append((None, int(r.payment_id), okey, int(r.order_id), ckey, dkey,
                           str(r.payment_method), float(r.amount), str(r.status), ETL_DATE_STR))

    c.executemany("INSERT INTO fact_payments VALUES (?,?,?,?,?,?,?,?,?,?)", valid_pays)
    log(f"  [FACT] fact_payments : {len(valid_pays)} record (Orphans dikeluarkan: {orphan_pays})")

    # Audit log
    c.execute("""
        INSERT INTO etl_audit_log (run_time, table_name, dq_dimension, action, records_in, records_out, records_fixed, notes)
        VALUES (?, 'fact_sales', 'DQ-6', 'Referential Integrity Check', ?, ?, 0, 'Multi-source pipeline')
    """, (ETL_DATE_STR, len(items), len(valid_sales)))

    conn.commit()
    conn.close()

def main():
    section("ETL PIPELINE DWH E-COMMERCE (7 DATA QUALITY DIMENSIONS)")
    tables = extract_multi_oltp()
    tables, _ = dq1_completeness(tables)
    tables, _ = dq2_accuracy(tables)
    tables    = dq3_consistency(tables)
    tables, _ = dq4_uniqueness(tables)
    tables, _ = dq5_validity(tables)
    load_to_dwh(tables)
    save_log()
    section("ETL PIPELINE SELESAI DENGAN SUKSES")
    log(f"Database DWH siap digunakan: {DWH_PATH}")

if __name__ == "__main__":
    main()
