-- =================================================================
-- SKEMA BASIS DATA DATA WAREHOUSE (DWH) - E-COMMERCE
-- Pemodelan: Star Schema (Constellation)
-- =================================================================

-- 1. Dimensi Waktu (SCD Type 0)
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

-- 2. Dimensi Produk (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_product (
    product_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INTEGER NOT NULL UNIQUE,
    product_name TEXT    NOT NULL,
    category     TEXT    NOT NULL,
    price        REAL    NOT NULL
);

-- 3. Dimensi Pelanggan (SCD Type 2)
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

-- 4. Dimensi Pesanan (SCD Type 1)
CREATE TABLE IF NOT EXISTS dim_order (
    order_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL UNIQUE,
    order_status TEXT    NOT NULL
);

-- 5. Tabel Fakta Penjualan (Transaksional per Item)
CREATE TABLE IF NOT EXISTS fact_sales (
    sales_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    order_key    INTEGER NOT NULL,
    order_id     INTEGER NOT NULL,
    customer_key INTEGER NOT NULL,
    product_key  INTEGER NOT NULL,
    date_key     INTEGER NOT NULL,
    branch_name  TEXT    NOT NULL,
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

-- 6. Tabel Fakta Pembayaran (Transaksional Arus Kas)
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

-- 7. Tabel Log Audit Kualitas Data ETL
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
