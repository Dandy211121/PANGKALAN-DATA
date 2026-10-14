"""
=================================================================
 STEP 2: ETL Process - Extract, Transform, Load
 E-Commerce Data Warehouse
=================================================================
Implementasi 7 Dimensi Data Quality:

  DQ-1  Completeness       : NULL Value Handling
  DQ-2  Accuracy           : Koreksi nilai tidak akurat
  DQ-3  Consistency        : Standardisasi format lintas tabel
  DQ-4  Uniqueness         : Deduplication + Surrogate Key
  DQ-5  Validity           : Validasi aturan logika bisnis
  DQ-6  Referential Integ. : Validasi FK -> PK/SK dimensi
  DQ-7  Timeliness (SCD-2) : Pelacakan histori perubahan data
=================================================================
"""

import sqlite3
import pandas as pd
from datetime import datetime
import os

OLTP_PATH    = "oltp_ecommerce.db"
DWH_PATH     = "dwh_ecommerce.db"
LOG_FILE     = "etl_log.txt"
ETL_RUN_TIME = datetime.now()
ETL_DATE_STR = ETL_RUN_TIME.strftime("%Y-%m-%d %H:%M:%S")
ETL_DATE_ONLY= ETL_RUN_TIME.strftime("%Y-%m-%d")

log_lines = []

def log(msg=""):
    print(msg)
    log_lines.append(str(msg))

def section(title):
    bar = "=" * 60
    log(f"\n{bar}")
    log(f"  {title}")
    log(bar)

def subsection(title):
    log(f"\n--- {title} ---")

def save_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

# =================================================================
# EXTRACT
# =================================================================
def extract(conn_oltp):
    section("EXTRACT - Membaca dari OLTP")
    tables = {}
    for t in ["customers", "products", "orders", "order_items", "payments"]:
        df = pd.read_sql(f"SELECT * FROM {t}", conn_oltp)
        tables[t] = df
        log(f"  {t:15s}: {len(df):5d} baris")
    return tables

# =================================================================
# TRANSFORM
# =================================================================

# -----------------------------------------------------------------
# DQ-1: COMPLETENESS - NULL Value Handling
# -----------------------------------------------------------------
def dq1_completeness(tables):
    section("DQ-1 | COMPLETENESS - NULL Value Handling")
    report = {"removed": 0, "filled": 0}

    # CUSTOMERS
    subsection("Customers")
    df = tables["customers"].copy()
    log(f"  Masuk: {len(df)} baris")

    # Hapus: identitas sama sekali tidak ada (nama + email kosong)
    kritis = df["full_name"].isna() & df["email"].isna()
    removed_ids = df[kritis]["customer_id"].tolist()
    df = df[~kritis]
    report["removed"] += len(removed_ids)
    log(f"  [-] DIHAPUS (nama+email NULL): {len(removed_ids)} - IDs: {removed_ids}")

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
            log(f"  [~] {col:15s} diisi '{val}': {n} baris")
    tables["customers"] = df

    # PRODUCTS
    subsection("Products")
    df = tables["products"].copy()
    n1 = df["product_name"].isna().sum()
    n2 = df["category"].isna().sum()
    n3 = df["price"].isna().sum()
    df["product_name"] = df["product_name"].fillna("Produk Tanpa Nama")
    df["category"]     = df["category"].fillna("Uncategorized")
    df["price"]        = df["price"].fillna(0.0)
    report["filled"] += n1 + n2 + n3
    log(f"  [~] product_name NULL: {n1} | category NULL: {n2} | price NULL: {n3}")
    tables["products"] = df

    # ORDERS
    subsection("Orders")
    df = tables["orders"].copy()
    n1 = df["status"].isna().sum()
    n2 = df["total_amount"].isna().sum()
    df["status"]       = df["status"].fillna("Unknown")
    df["total_amount"] = df["total_amount"].fillna(0.0)
    report["filled"] += n1 + n2
    log(f"  [~] status NULL: {n1} | total_amount NULL: {n2}")
    tables["orders"] = df

    log(f"\n  >> Ringkasan DQ-1: {report['removed']} dihapus, {report['filled']} diisi")
    return tables, report

# -----------------------------------------------------------------
# DQ-2: ACCURACY - Koreksi nilai tidak akurat
# -----------------------------------------------------------------
def dq2_accuracy(tables):
    section("DQ-2 | ACCURACY - Koreksi Nilai Tidak Akurat")
    report = {"corrected": 0}

    # ORDER ITEMS: subtotal harus = qty x unit_price
    subsection("Order Items - Rekonsiliasi Subtotal")
    df = tables["order_items"].copy()
    df["expected_subtotal"] = df["quantity"] * df["unit_price"]
    mismatch = (df["subtotal"] - df["expected_subtotal"]).abs() > 0.01
    n_mismatch = mismatch.sum()
    if n_mismatch > 0:
        log(f"  [!] {n_mismatch} baris subtotal tidak sesuai qty x price:")
        for _, r in df[mismatch].iterrows():
            log(f"      item_id={int(r.item_id)}: subtotal={r.subtotal} "
                f"expected={r.expected_subtotal}")
        df.loc[mismatch, "subtotal"] = df.loc[mismatch, "expected_subtotal"]
        log(f"  [~] Subtotal dikoreksi: {n_mismatch} baris")
        report["corrected"] += n_mismatch
    df = df.drop(columns=["expected_subtotal"])
    tables["order_items"] = df

    # ORDERS: total_amount vs sum(subtotal per order)
    subsection("Orders - Rekonsiliasi Total vs Sum Item")
    orders_df = tables["orders"].copy()
    items_df  = tables["order_items"]
    sum_per   = items_df.groupby("order_id")["subtotal"].sum().reset_index()
    sum_per.columns = ["order_id", "computed_total"]
    merged = orders_df.merge(sum_per, on="order_id", how="left")
    has_total = merged["total_amount"] > 0
    has_comp  = merged["computed_total"].notna() & (merged["computed_total"] > 0)
    pct_diff  = ((merged["total_amount"] - merged["computed_total"]).abs()
                 / merged["computed_total"].clip(lower=1))
    bad_total = has_total & has_comp & (pct_diff > 0.1)
    n_bad = bad_total.sum()
    if n_bad > 0:
        log(f"  [!] {n_bad} order total berbeda >10% dari sum(items):")
        for _, r in merged[bad_total].iterrows():
            log(f"      order_id={int(r.order_id)}: total={r.total_amount} "
                f"sum_items={r.computed_total:.0f}")
        orders_df.loc[orders_df["order_id"].isin(
            merged[bad_total]["order_id"]), "total_amount"
        ] = merged.loc[bad_total, "computed_total"].values
        report["corrected"] += n_bad
    tables["orders"] = orders_df

    log(f"\n  >> Ringkasan DQ-2: {report['corrected']} nilai dikoreksi")
    return tables, report

# -----------------------------------------------------------------
# DQ-3: CONSISTENCY - Standardisasi format lintas tabel
# -----------------------------------------------------------------
def dq3_consistency(tables):
    section("DQ-3 | CONSISTENCY - Standardisasi Format")

    def std_date(v):
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(str(v).strip(), fmt).strftime("%Y-%m-%d")
            except:
                pass
        return str(v).strip()

    # CUSTOMERS
    df = tables["customers"].copy()
    df["full_name"]  = df["full_name"].str.strip().str.title()
    df["email"]      = df["email"].str.strip().str.lower()
    df["phone"]      = df["phone"].str.strip().str.replace(r"\s+", "", regex=True)
    df["city"]       = df["city"].str.strip().str.title()
    df["province"]   = df["province"].str.strip().str.title()
    df["island"]     = df["island"].str.strip().str.title()
    df["gender"]     = df["gender"].str.strip().str.upper()
    tables["customers"] = df
    log("  [~] Customers: full_name->Title, email->lower, gender->upper")

    # PRODUCTS
    df = tables["products"].copy()
    df["product_name"] = df["product_name"].str.strip()
    df["category"]     = df["category"].str.strip().str.title()
    tables["products"] = df
    log("  [~] Products: category->Title Case")

    # ORDERS
    df = tables["orders"].copy()
    df["status"]     = df["status"].str.strip().str.title()
    df["order_date"] = df["order_date"].apply(std_date)
    tables["orders"] = df
    log("  [~] Orders: status->Title Case, order_date->YYYY-MM-DD")

    # PAYMENTS
    df = tables["payments"].copy()
    df["payment_method"] = df["payment_method"].str.strip().str.title()
    df["status"]         = df["status"].str.strip().str.title()
    tables["payments"] = df
    log("  [~] Payments: payment_method & status->Title Case")

    log(f"\n  >> Ringkasan DQ-3: Semua tabel distandarisasi formatnya")
    return tables

# -----------------------------------------------------------------
# DQ-4: UNIQUENESS - Deduplication
# -----------------------------------------------------------------
def dq4_uniqueness(tables):
    section("DQ-4 | UNIQUENESS - Deduplication")
    report = {"removed": 0}

    # CUSTOMERS: duplikat berdasarkan email
    df = tables["customers"].copy()
    before = len(df)
    df["_email_key"] = df["email"].str.lower().str.strip()
    df = (df.sort_values("customer_id")
            .drop_duplicates(subset=["_email_key"], keep="first")
            .drop(columns=["_email_key"]))
    n = before - len(df)
    report["removed"] += n
    log(f"\n  Customers: {before} -> {len(df)} ({n} duplikat dihapus, pertahankan ID terkecil)")
    tables["customers"] = df

    # ORDER ITEMS: duplikat persis
    df = tables["order_items"].copy()
    before = len(df)
    df = df.drop_duplicates(subset=["order_id","product_id","quantity","unit_price"], keep="first")
    n = before - len(df)
    report["removed"] += n
    log(f"  Order Items: {before} -> {len(df)} ({n} duplikat dihapus)")
    tables["order_items"] = df

    # PAYMENTS: satu order satu payment
    df = tables["payments"].copy()
    before = len(df)
    df = df.drop_duplicates(subset=["order_id"], keep="first")
    n = before - len(df)
    report["removed"] += n
    log(f"  Payments: {before} -> {len(df)} ({n} duplikat dihapus)")
    tables["payments"] = df

    log(f"\n  >> Ringkasan DQ-4: {report['removed']} duplikat dihapus")
    log("  Catatan: Surrogate Key (AUTOINCREMENT) dibuat otomatis saat load ke DWH")
    return tables, report

# -----------------------------------------------------------------
# DQ-5: VALIDITY - Validasi aturan logika bisnis
# -----------------------------------------------------------------
def dq5_validity(tables):
    section("DQ-5 | VALIDITY - Business Rule Validation")
    report = {"removed": 0}

    BATAS_BAWAH = datetime(2021, 1, 1)
    BATAS_ATAS  = ETL_RUN_TIME
    HARGA_MAX   = 50_000_000

    # CUSTOMERS: validasi nomor telepon & gender (L/P)
    subsection("Customers - Validasi No. Telepon & Gender (L/P)")
    df = tables["customers"].copy()
    before = len(df)

    def phone_valid(ph):
        p = str(ph).strip()
        if p in ["Tidak Tersedia", "TidakTersedia", ""]: return True
        return p.isdigit() and len(p) >= 10

    invalid_phone = ~df["phone"].apply(phone_valid)
    log(f"  [!] No. Telepon tidak valid: {invalid_phone.sum()}")
    for _, r in df[invalid_phone].iterrows():
        log(f"      ID={int(r.customer_id)} nama={r.full_name} phone='{r.phone}'")
    df = df[~invalid_phone]

    invalid_gender = ~df["gender"].isin(["L", "P"])
    log(f"  [!] Gender tidak valid (bukan L/P): {invalid_gender.sum()}")
    for _, r in df[invalid_gender].iterrows():
        log(f"      ID={int(r.customer_id)} gender='{r.gender}'")
    df = df[~invalid_gender]
    report["removed"] += (before - len(df))
    tables["customers"] = df

    # PRODUCTS: harga
    subsection("Products - Validasi Harga (0 < harga <= 50jt)")
    df = tables["products"].copy()
    before = len(df)
    invalid_price = ~((df["price"] > 0) & (df["price"] <= HARGA_MAX))
    log(f"  [!] Harga tidak valid: {invalid_price.sum()}")
    for _, r in df[invalid_price].iterrows():
        log(f"      ID={int(r.product_id)} '{r.product_name}' harga={r.price:,.0f}")
    df = df[~invalid_price]
    report["removed"] += (before - len(df))
    tables["products"] = df

    # ORDERS: tanggal dan total
    subsection("Orders - Validasi Tanggal (2021-skrg) & Total (>=0)")
    df = tables["orders"].copy()
    before = len(df)

    def tgl_valid(dt_str):
        try:
            dt = datetime.strptime(str(dt_str), "%Y-%m-%d")
            return BATAS_BAWAH <= dt <= BATAS_ATAS
        except:
            return False

    invalid_tgl   = ~df["order_date"].apply(tgl_valid)
    invalid_total = df["total_amount"] < 0
    log(f"  [!] Tanggal tidak valid: {invalid_tgl.sum()}")
    for _, r in df[invalid_tgl].iterrows():
        log(f"      order_id={int(r.order_id)} tgl={r.order_date}")
    log(f"  [!] Total negatif: {invalid_total.sum()}")
    df = df[~invalid_tgl & ~invalid_total]
    report["removed"] += (before - len(df))
    tables["orders"] = df

    # ORDER ITEMS: quantity > 0
    subsection("Order Items - Validasi Quantity (>0)")
    df = tables["order_items"].copy()
    before = len(df)
    invalid_qty = df["quantity"] <= 0
    log(f"  [!] Quantity <= 0: {invalid_qty.sum()}")
    df = df[~invalid_qty]
    report["removed"] += (before - len(df))
    tables["order_items"] = df

    # PAYMENTS: amount > 0
    subsection("Payments - Validasi Amount (>0)")
    df = tables["payments"].copy()
    before = len(df)
    invalid_pay = df["amount"] <= 0
    log(f"  [!] Amount <= 0: {invalid_pay.sum()}")
    df = df[~invalid_pay]
    report["removed"] += (before - len(df))
    tables["payments"] = df

    log(f"\n  >> Ringkasan DQ-5: {report['removed']} record tidak valid dihapus")
    return tables, report

# =================================================================
# DWH SCHEMA
# =================================================================
def create_dwh_schema(conn_dwh):
    c = conn_dwh.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS dim_date (
            date_key    INTEGER PRIMARY KEY,
            full_date   TEXT    NOT NULL,
            day         INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            month_name  TEXT    NOT NULL,
            quarter     INTEGER NOT NULL,
            year        INTEGER NOT NULL,
            weekday     TEXT    NOT NULL,
            is_weekend  INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS dim_product (
            product_key  INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL UNIQUE,
            product_name TEXT    NOT NULL,
            category     TEXT    NOT NULL,
            price        REAL    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS dim_customer (
            customer_key  INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id   INTEGER NOT NULL,
            full_name     TEXT    NOT NULL,
            email         TEXT,
            phone         TEXT,
            city          TEXT,
            province      TEXT,
            island        TEXT,
            gender        TEXT,
            registered_at TEXT,
            valid_from    TEXT    NOT NULL,
            valid_to      TEXT,
            is_current    INTEGER NOT NULL DEFAULT 1,
            dwh_version   INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS dim_order (
            order_key    INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER NOT NULL UNIQUE,
            order_status TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS fact_sales (
            sales_key    INTEGER PRIMARY KEY AUTOINCREMENT,
            order_key    INTEGER NOT NULL,
            order_id     INTEGER NOT NULL,
            customer_key INTEGER NOT NULL,
            product_key  INTEGER NOT NULL,
            date_key     INTEGER NOT NULL,
            quantity     INTEGER NOT NULL,
            unit_price   REAL    NOT NULL,
            subtotal     REAL    NOT NULL,
            order_status TEXT    NOT NULL,
            etl_loaded_at TEXT   NOT NULL,
            FOREIGN KEY (order_key)    REFERENCES dim_order(order_key),
            FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
            FOREIGN KEY (product_key)  REFERENCES dim_product(product_key),
            FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
        );
        CREATE TABLE IF NOT EXISTS fact_payments (
            payment_key     INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_id      INTEGER NOT NULL,
            order_key       INTEGER NOT NULL,
            order_id        INTEGER NOT NULL,
            customer_key    INTEGER NOT NULL,
            date_key        INTEGER NOT NULL,
            payment_method  TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            payment_status  TEXT    NOT NULL,
            etl_loaded_at   TEXT    NOT NULL,
            FOREIGN KEY (order_key)    REFERENCES dim_order(order_key),
            FOREIGN KEY (customer_key) REFERENCES dim_customer(customer_key),
            FOREIGN KEY (date_key)     REFERENCES dim_date(date_key)
        );
        CREATE TABLE IF NOT EXISTS etl_audit_log (
            log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            run_time      TEXT    NOT NULL,
            table_name    TEXT    NOT NULL,
            dq_dimension  TEXT    NOT NULL,
            action        TEXT    NOT NULL,
            records_in    INTEGER,
            records_out   INTEGER,
            records_fixed INTEGER,
            notes         TEXT
        );
    """)
    conn_dwh.commit()

BULAN = ["Januari","Februari","Maret","April","Mei","Juni",
         "Juli","Agustus","September","Oktober","November","Desember"]
HARI  = ["Senin","Selasa","Rabu","Kamis","Jumat","Sabtu","Minggu"]

def load_dim_date(conn_dwh, tables):
    c = conn_dwh.cursor()
    dates = set()
    for col, tbl in [("order_date","orders"), ("payment_date","payments")]:
        for v in tables[tbl][col].dropna():
            try: dates.add(str(v)[:10])
            except: pass
    rows = []
    for ds in sorted(dates):
        try:
            dt = datetime.strptime(ds, "%Y-%m-%d")
            rows.append((int(ds.replace("-","")), ds, dt.day, dt.month,
                         BULAN[dt.month-1], (dt.month-1)//3+1, dt.year,
                         HARI[dt.weekday()], 1 if dt.weekday()>=5 else 0))
        except: pass
    c.executemany("INSERT OR IGNORE INTO dim_date VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn_dwh.commit()
    log(f"  dim_date          : {len(rows):5d} record")
    return {r[1]: r[0] for r in rows}

def load_dim_product(conn_dwh, tables):
    c = conn_dwh.cursor()
    df = tables["products"]
    rows = [(None, int(r.product_id), r.product_name, r.category, float(r.price))
            for r in df.itertuples()]
    c.executemany("INSERT OR IGNORE INTO dim_product VALUES (?,?,?,?,?)", rows)
    conn_dwh.commit()
    res = c.execute("SELECT product_key, product_id FROM dim_product").fetchall()
    log(f"  dim_product       : {len(res):5d} record")
    return {pid: pk for pk, pid in res}

def load_dim_order(conn_dwh, tables):
    c = conn_dwh.cursor()
    df = tables["orders"]
    rows = [(None, int(r.order_id), str(r.status)) for r in df.itertuples()]
    c.executemany("INSERT OR IGNORE INTO dim_order VALUES (?,?,?)", rows)
    conn_dwh.commit()
    res = c.execute("SELECT order_key, order_id FROM dim_order").fetchall()
    log(f"  dim_order         : {len(res):5d} record")
    return {oid: ok for ok, oid in res}

# DQ-7: SCD Type 2 untuk dim_customer
def load_dim_customer_scd2(conn_dwh, tables):
    section("DQ-7 | TIMELINESS - SCD Type 2 (dim_customer)")
    log("  Melacak histori perubahan data pelanggan")
    log("  Kolom SCD-2: valid_from, valid_to, is_current, dwh_version")
    c = conn_dwh.cursor()
    df = tables["customers"]

    existing = pd.read_sql(
        "SELECT customer_id, customer_key, city, province, phone, dwh_version "
        "FROM dim_customer WHERE is_current=1", conn_dwh
    )

    inserted = 0; updated = 0
    for r in df.itertuples():
        cid  = int(r.customer_id)
        prev = existing[existing["customer_id"] == cid]

        if prev.empty:
            c.execute("""
                INSERT INTO dim_customer
                  (customer_id, full_name, email, phone, city, province, island,
                   gender, registered_at,
                   valid_from, valid_to, is_current, dwh_version)
                VALUES (?,?,?,?,?,?,?,?,?,?,NULL,1,1)
            """, (cid, r.full_name, r.email, r.phone,
                  r.city, r.province, r.island,
                  r.gender, r.registered_at, ETL_DATE_STR))
            inserted += 1
        else:
            prev_row = prev.iloc[0]
            changed  = (str(prev_row["city"])     != str(r.city) or
                        str(prev_row["province"]) != str(r.province) or
                        str(prev_row["phone"])    != str(r.phone))
            if changed:
                c.execute("""
                    UPDATE dim_customer
                    SET valid_to=?, is_current=0
                    WHERE customer_id=? AND is_current=1
                """, (ETL_DATE_STR, cid))
                new_ver = int(prev_row["dwh_version"]) + 1
                c.execute("""
                    INSERT INTO dim_customer
                      (customer_id, full_name, email, phone, city, province, island,
                       gender, registered_at,
                       valid_from, valid_to, is_current, dwh_version)
                    VALUES (?,?,?,?,?,?,?,?,?,?,NULL,1,?)
                """, (cid, r.full_name, r.email, r.phone,
                      r.city, r.province, r.island,
                      r.gender, r.registered_at,
                      ETL_DATE_STR, new_ver))
                updated += 1

    conn_dwh.commit()
    total = c.execute(
        "SELECT COUNT(*) FROM dim_customer WHERE is_current=1"
    ).fetchone()[0]
    log(f"  dim_customer aktif: {total:5d} record")
    log(f"  Insert baru: {inserted} | Update SCD-2: {updated}")

    res = c.execute(
        "SELECT customer_id, customer_key FROM dim_customer WHERE is_current=1"
    ).fetchall()
    return {cid: ck for cid, ck in res}

# -----------------------------------------------------------------
# DQ-6: REFERENTIAL INTEGRITY - Validasi FK sebelum load fact
# -----------------------------------------------------------------
def dq6_referential_integrity(tables, cust_map, prod_map, date_map, order_map):
    section("DQ-6 | REFERENTIAL INTEGRITY - Validasi FK -> Dimensi")

    items  = tables["order_items"].copy()
    orders = tables["orders"].set_index("order_id")

    orphan_order=[]; orphan_cust=[]; orphan_prod=[]; orphan_date=[]; valid_rows=[]
    for r in items.itertuples():
        try:
            if r.order_id not in orders.index:
                orphan_order.append(int(r.item_id)); continue
            order = orders.loc[r.order_id]
            cid   = int(order["customer_id"])
            pid   = int(r.product_id)
            dkey  = date_map.get(str(order["order_date"])[:10])
            ckey  = cust_map.get(cid)
            pkey  = prod_map.get(pid)
            okey  = order_map.get(int(r.order_id))
            if not okey:
                orphan_order.append(int(r.item_id)); continue
            if not ckey:
                orphan_cust.append(int(r.item_id)); continue
            if not pkey:
                orphan_prod.append(int(r.item_id)); continue
            if not dkey:
                orphan_date.append(int(r.item_id)); continue
            valid_rows.append(r)
        except: pass

    log(f"\n  fact_sales input  : {len(items)}")
    log(f"    Orphan order    : {len(orphan_order)}")
    log(f"    Orphan customer : {len(orphan_cust)}")
    log(f"    Orphan product  : {len(orphan_prod)}")
    log(f"    Orphan date     : {len(orphan_date)}")
    log(f"    Valid (lolos RI): {len(valid_rows)}")

    pays = tables["payments"]
    op_orphan_o=[]; op_orphan_c=[]; op_orphan_d=[]; valid_pay=[]
    for r in pays.itertuples():
        try:
            if r.order_id not in orders.index:
                op_orphan_o.append(int(r.payment_id)); continue
            order = orders.loc[r.order_id]
            cid   = int(order["customer_id"])
            dkey  = date_map.get(str(r.payment_date)[:10])
            ckey  = cust_map.get(cid)
            okey  = order_map.get(int(r.order_id))
            if not okey:
                op_orphan_o.append(int(r.payment_id)); continue
            if not ckey:
                op_orphan_c.append(int(r.payment_id)); continue
            if not dkey:
                op_orphan_d.append(int(r.payment_id)); continue
            valid_pay.append(r)
        except: pass

    log(f"\n  fact_payments input: {len(pays)}")
    log(f"    Orphan order     : {len(op_orphan_o)}")
    log(f"    Orphan customer  : {len(op_orphan_c)}")
    log(f"    Orphan date      : {len(op_orphan_d)}")
    log(f"    Valid (lolos RI) : {len(valid_pay)}")

    total_orphan = len(orphan_order)+len(orphan_cust)+len(orphan_prod)+len(orphan_date)+len(op_orphan_o)+len(op_orphan_c)+len(op_orphan_d)
    log(f"\n  >> Ringkasan DQ-6: {total_orphan} orphan record dikeluarkan")
    return valid_rows, valid_pay, total_orphan

def load_fact_sales(conn_dwh, valid_rows, cust_map, prod_map, date_map, order_map, tables):
    c    = conn_dwh.cursor()
    ords = tables["orders"].set_index("order_id")
    rows = []
    for r in valid_rows:
        order = ords.loc[r.order_id]
        oid   = int(r.order_id)
        rows.append((None, order_map[oid], oid,
                     cust_map[int(order["customer_id"])],
                     prod_map[int(r.product_id)],
                     date_map[str(order["order_date"])[:10]],
                     int(r.quantity), float(r.unit_price), float(r.subtotal),
                     str(order["status"]), ETL_DATE_STR))
    c.executemany("INSERT INTO fact_sales VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn_dwh.commit()
    log(f"  fact_sales        : {len(rows):5d} record")

def load_fact_payments(conn_dwh, valid_pay, cust_map, date_map, order_map, tables):
    c    = conn_dwh.cursor()
    ords = tables["orders"].set_index("order_id")
    rows = []
    for r in valid_pay:
        order = ords.loc[r.order_id]
        oid   = int(r.order_id)
        rows.append((None, int(r.payment_id), order_map[oid], oid,
                     cust_map[int(order["customer_id"])],
                     date_map[str(r.payment_date)[:10]],
                     str(r.payment_method), float(r.amount),
                     str(r.status), ETL_DATE_STR))
    c.executemany("INSERT INTO fact_payments VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    conn_dwh.commit()
    log(f"  fact_payments     : {len(rows):5d} record")

def write_audit(conn_dwh, table, dq, action, r_in, r_out, r_fix, notes=""):
    conn_dwh.execute("""
        INSERT INTO etl_audit_log
          (run_time,table_name,dq_dimension,action,
           records_in,records_out,records_fixed,notes)
        VALUES (?,?,?,?,?,?,?,?)
    """, (ETL_DATE_STR, table, dq, action, r_in, r_out, r_fix, notes))
    conn_dwh.commit()

# =================================================================
# MAIN ETL PIPELINE
# =================================================================
def main():
    section("ETL PIPELINE - E-Commerce DWH (7 Data Quality Dimensions)")
    log(f"  Waktu ETL : {ETL_DATE_STR}")
    log(f"  OLTP      : {OLTP_PATH}")
    log(f"  DWH       : {DWH_PATH}")

    # EXTRACT
    conn_oltp = sqlite3.connect(OLTP_PATH)
    tables = extract(conn_oltp)
    conn_oltp.close()
    before_counts = {t: len(tables[t]) for t in tables}

    # TRANSFORM
    section("TRANSFORM - Menerapkan 7 Dimensi Data Quality")
    tables, r1 = dq1_completeness(tables)
    tables, r2 = dq2_accuracy(tables)
    tables     = dq3_consistency(tables)
    tables, r4 = dq4_uniqueness(tables)
    tables, r5 = dq5_validity(tables)

    section("RINGKASAN TRANSFORM")
    log(f"  {'Tabel':15s} {'Sebelum':>8} {'Sesudah':>8} {'Selisih':>8}")
    log(f"  {'-'*43}")
    for t in tables:
        b = before_counts[t]; a = len(tables[t])
        log(f"  {t:15s} {b:>8} {a:>8} {b-a:>8}")

    # LOAD
    section("LOAD - Memuat ke DWH")
    if os.path.exists(DWH_PATH):
        os.remove(DWH_PATH)
    conn_dwh = sqlite3.connect(DWH_PATH)
    conn_dwh.execute("PRAGMA foreign_keys = ON")
    create_dwh_schema(conn_dwh)

    log("\n  [DIM] Tabel Dimensi:")
    date_map  = load_dim_date(conn_dwh, tables)
    prod_map  = load_dim_product(conn_dwh, tables)
    order_map = load_dim_order(conn_dwh, tables)
    cust_map  = load_dim_customer_scd2(conn_dwh, tables)  # DQ-7

    valid_rows, valid_pay, total_orphan = dq6_referential_integrity(  # DQ-6
        tables, cust_map, prod_map, date_map, order_map
    )

    log("\n  [FACT] Tabel Fakta:")
    load_fact_sales(conn_dwh, valid_rows, cust_map, prod_map, date_map, order_map, tables)
    load_fact_payments(conn_dwh, valid_pay, cust_map, date_map, order_map, tables)

    # Audit log
    for t, dq, action, r_in, r_out, r_fix, notes in [
        ("customers","DQ-1","NULL Fill",
         before_counts["customers"],len(tables["customers"]),r1["filled"],""),
        ("order_items","DQ-2","Subtotal Fix",
         before_counts["order_items"],len(tables["order_items"]),r2["corrected"],""),
        ("customers","DQ-4","Dedup",
         before_counts["customers"],len(tables["customers"]),0,"email dedup"),
        ("fact_sales","DQ-6","RI Check",
         len(tables["order_items"]),len(valid_rows),0,f"orphans={total_orphan}"),
        ("dim_customer","DQ-7","SCD-2",
         len(tables["customers"]),len(cust_map),0,"SCD Type 2 Timeliness"),
    ]:
        write_audit(conn_dwh, t, dq, action, r_in, r_out, r_fix, notes)

    # SUMMARY
    section("ETL SELESAI - Ringkasan DWH")
    log(f"  {'Tabel DWH':25s} {'Record':>8}")
    log(f"  {'-'*35}")
    for t in ["dim_customer","dim_product","dim_date","dim_order","fact_sales","fact_payments","etl_audit_log"]:
        n = conn_dwh.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        log(f"  {t:25s} {n:>8}")

    conn_dwh.close()
    save_log()
    log(f"\n  Log ETL : {LOG_FILE}")
    log(f"  DWH file: {DWH_PATH}")
    section("SELESAI")

if __name__ == "__main__":
    main()
