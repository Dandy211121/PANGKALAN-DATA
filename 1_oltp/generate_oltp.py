"""
=============================================================
 1. OLTP: Generator Data Operasional Multi-Sumber
=============================================================
Menghasilkan 3 Basis Data OLTP Independen sesuai Arsitektur:
  1. oltp_cabang_1.db (Cabang Jakarta / Head Office & Web)
  2. oltp_cabang_2.db (Cabang Surabaya / Jawa Timur)
  3. oltp_cabang_3.db (Cabang Bandung / Jawa Barat)

Masing-masing sumber diinjeksi dengan simulasi data kotor:
  - Missing Values (NULL)
  - Data Duplikat
  - Bad Business Logic (Harga minus, total salah, dll)
=============================================================
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BRANCHES = [
    {"id": 1, "name": "Cabang Jakarta (Head Office & Online)", "db": "oltp_cabang_1.db", "city": "Jakarta", "prov": "DKI Jakarta"},
    {"id": 2, "name": "Cabang Surabaya (Retail Hub Timur)",   "db": "oltp_cabang_2.db", "city": "Surabaya", "prov": "Jawa Timur"},
    {"id": 3, "name": "Cabang Bandung (Regional Store)",      "db": "oltp_cabang_3.db", "city": "Bandung", "prov": "Jawa Barat"}
]

PRODUCT_CATALOG = [
    ("Laptop ASUS VivoBook",      "Electronics",  7500000),
    ("Samsung Galaxy A54",        "Electronics",  4200000),
    ("Headphone Sony WH-1000XM4", "Electronics",  3500000),
    ("Keyboard Mechanical Rexus", "Electronics",   850000),
    ("Mouse Logitech MX Master",  "Electronics",   950000),
    ("Kaos Polos Cotton",         "Fashion",        75000),
    ("Celana Jeans Slim Fit",     "Fashion",       250000),
    ("Sepatu Nike Air Max",       "Fashion",       850000),
    ("Tas Ransel Laptop",         "Fashion",       320000),
    ("Jaket Hoodie Distro",       "Fashion",       185000),
    ("Buku Python Programming",   "Books",          95000),
    ("Buku Data Science",         "Books",         120000),
    ("Novel Laskar Pelangi",      "Books",          65000),
    ("Meja Belajar Minimalis",    "Furniture",    1250000),
    ("Kursi Gaming RGB",          "Furniture",    2100000),
    ("Blender Philips 2L",        "Appliances",    450000),
    ("Rice Cooker Sharp 1.8L",    "Appliances",    350000),
    ("Sabun Mandi Dove",          "Health",         22000),
    ("Vitamin C 1000mg",          "Health",         85000),
    ("Masker KN95",               "Health",         35000),
]

PAYMENT_METHODS = ["Transfer Bank", "Credit Card", "GoPay", "OVO", "Dana", "Indomaret", "Alfamart"]
ORDER_STATUSES  = ["Completed", "Shipped", "Processing", "Cancelled", "Returned"]
FIRST_NAMES     = ["Budi","Siti","Dewi","Andi","Rudi","Ani","Joko","Sri","Agus","Rina",
                   "Hendra","Maya","Fajar","Nita","Doni","Lisa","Hadi","Wati","Tono","Dina"]
LAST_NAMES      = ["Santoso","Wijaya","Kusuma","Rahayu","Susanto","Purnomo","Hidayat",
                   "Setiawan","Wahyudi","Pratama","Sari","Utami","Wibowo","Nugroho","Hartono"]

def create_oltp_schema(conn):
    c = conn.cursor()
    c.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS payments;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;
        
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            full_name TEXT, email TEXT, phone TEXT,
            city TEXT, province TEXT, island TEXT,
            gender TEXT, registered_at TEXT
        );
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT, category TEXT, price REAL,
            stock INTEGER, created_at TEXT
        );
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER, order_date TEXT,
            status TEXT, total_amount REAL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER, product_id INTEGER,
            quantity INTEGER, unit_price REAL, subtotal REAL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        CREATE TABLE payments (
            payment_id INTEGER PRIMARY KEY,
            order_id INTEGER, payment_date TEXT,
            payment_method TEXT, amount REAL, status TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
    """)
    conn.commit()

def generate_branch_data(branch_info, seed_val=42):
    random.seed(seed_val)
    db_path = os.path.join(BASE_DIR, branch_info["db"])
    conn = sqlite3.connect(db_path)
    create_oltp_schema(conn)
    c = conn.cursor()

    # 1. Customers
    cust_data = []
    base_id = (branch_info["id"] - 1) * 1000
    for i in range(1, 75):
        cid = base_id + i
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        name = f"{fn} {ln}"
        email = f"{fn.lower()}.{ln.lower()}{random.randint(1,99)}@gmail.com"
        phone = f"08{random.randint(10,99)}{random.randint(10000000,99999999)}"
        gender = random.choice(["L", "P"])
        reg = (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 900))).strftime("%Y-%m-%d")
        cust_data.append((cid, name, email, phone, branch_info["city"], branch_info["prov"], "Jawa", gender, reg))

    # Dirty Customers
    cust_data.append((base_id + 75, None, None, None, None, None, None, None, None)) # NULL kritis
    cust_data.append((base_id + 76, "Rudi Duplikat", "rudi.duplikat@gmail.com", "081234567890", branch_info["city"], branch_info["prov"], "Jawa", "L", "2023-01-01"))
    cust_data.append((base_id + 77, "RUDI DUPLIKAT", "rudi.duplikat@gmail.com", "081234567890", branch_info["city"], branch_info["prov"], "Jawa", "L", "2023-01-01")) # Duplikat
    cust_data.append((base_id + 78, "Andi Salah HP", "andi.salah@gmail.com", "12345", branch_info["city"], branch_info["prov"], "Jawa", "L", "2023-01-01")) # HP < 10 digit
    cust_data.append((base_id + 79, "Dewi Salah Gender", "dewi.gender@gmail.com", "081298765432", branch_info["city"], branch_info["prov"], "Jawa", "X", "2023-01-01")) # Gender 'X'

    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", cust_data)

    # 2. Products
    prod_data = []
    for pid, (pname, cat, prc) in enumerate(PRODUCT_CATALOG, start=1):
        prod_data.append((pid, pname, cat, prc, 100, "2022-01-01"))
    # Dirty Products
    prod_data.append((21, "Produk Minus", "Electronics", -50000, 10, "2022-01-01"))
    prod_data.append((22, "Produk 999 Juta", "Furniture", 999000000, 5, "2022-01-01"))
    prod_data.append((23, None, None, 0, 0, "2022-01-01"))
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", prod_data)

    # 3. Orders, Items, Payments
    order_data = []
    item_data = []
    pay_data = []
    item_counter = (branch_info["id"] - 1) * 10000 + 1
    pay_counter = (branch_info["id"] - 1) * 5000 + 1

    for o_num in range(1, 160):
        oid = (branch_info["id"] - 1) * 5000 + o_num
        cid = random.choice([cd[0] for cd in cust_data[:70]]) # valid customer
        odate = (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 1000))).strftime("%Y-%m-%d")
        ostatus = random.choice(ORDER_STATUSES)
        
        # generate items
        num_items = random.randint(1, 4)
        total_order = 0.0
        for _ in range(num_items):
            prod = random.choice(prod_data[:20])
            pid = prod[0]
            prc = prod[3]
            qty = random.randint(1, 3)
            sub = qty * prc
            total_order += sub
            item_data.append((item_counter, oid, pid, qty, prc, sub))
            item_counter += 1

        order_data.append((oid, cid, odate, ostatus, total_order))
        
        # payment
        pay_method = random.choice(PAYMENT_METHODS)
        p_status = "Success" if ostatus != "Cancelled" else "Failed"
        pay_data.append((pay_counter, oid, odate, pay_method, total_order, p_status))
        pay_counter += 1

    # Injeksi Dirty Orders & Items
    # Bad date 2099
    order_data.append((base_id + 991, cust_data[0][0], "2099-12-31", "Completed", 100000))
    # Negative total
    order_data.append((base_id + 992, cust_data[0][0], "2023-05-01", "Completed", -50000))
    # Bad quantity <= 0
    item_data.append((item_counter, base_id + 991, 1, -2, 75000, -150000))
    # Bad subtotal calculation
    item_data.append((item_counter + 1, order_data[0][0], 1, 2, 100000, 5000)) # harusnya 200rb
    # Duplicate item
    dup_item = item_data[0]
    item_data.append((item_counter + 2, dup_item[1], dup_item[2], dup_item[3], dup_item[4], dup_item[5]))

    # Bad payment amount <= 0
    pay_data.append((pay_counter, base_id + 992, "2023-05-01", "GoPay", -50000, "Failed"))

    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_data)
    c.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", item_data)
    c.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", pay_data)
    conn.commit()
    conn.close()

    print(f"[OK] Berhasil membuat: {branch_info['db']} ({branch_info['name']})")
    print(f"   -> {len(cust_data)} customers, {len(prod_data)} products, {len(order_data)} orders, {len(item_data)} items")

def main():
    print("=" * 65)
    print("  MEMBUAT 3 BASIS DATA OLTP INDEPENDEN (MULTI-SUMBER)")
    print("=" * 65)
    for idx, b in enumerate(BRANCHES, start=1):
        generate_branch_data(b, seed_val=40 + idx)
    print("=" * 65)
    print("  Semua sumber data OLTP siap diekstraksi oleh ETL Pipeline.")
    print("=" * 65)

if __name__ == "__main__":
    main()
