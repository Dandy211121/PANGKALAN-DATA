"""
=============================================================
 STEP 1: Generate Dirty OLTP Data (E-Commerce)
=============================================================
Script ini membuat database OLTP dengan data kotor:
- Data NULL (missing values)
- Data duplikat
- Bad business logic
=============================================================
"""

import sqlite3
import random
import os
from datetime import datetime, timedelta

DB_PATH = "oltp_ecommerce.db"
random.seed(42)

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

CITIES = [
    ("Jakarta", "DKI Jakarta", "Jawa"),
    ("Surabaya", "Jawa Timur", "Jawa"),
    ("Bandung", "Jawa Barat", "Jawa"),
    ("Medan", "Sumatera Utara", "Sumatera"),
    ("Semarang", "Jawa Tengah", "Jawa"),
    ("Makassar", "Sulawesi Selatan", "Sulawesi"),
    ("Palembang", "Sumatera Selatan", "Sumatera"),
    ("Depok", "Jawa Barat", "Jawa"),
    ("Tangerang", "Banten", "Jawa"),
    ("Bekasi", "Jawa Barat", "Jawa"),
]

PAYMENT_METHODS = ["Transfer Bank", "Credit Card", "GoPay", "OVO", "Dana", "Indomaret", "Alfamart"]
ORDER_STATUSES  = ["Completed", "Shipped", "Processing", "Cancelled", "Returned"]
FIRST_NAMES     = ["Budi","Siti","Dewi","Andi","Rudi","Ani","Joko","Sri","Agus","Rina",
                   "Hendra","Maya","Fajar","Nita","Doni","Lisa","Hadi","Wati","Tono","Dina"]
LAST_NAMES      = ["Santoso","Wijaya","Kusuma","Rahayu","Susanto","Purnomo","Hidayat",
                   "Setiawan","Wahyudi","Pratama","Sari","Utami","Wibowo","Nugroho","Hartono"]

def random_date(start_year=2022, end_year=2024):
    start = datetime(start_year, 1, 1)
    end   = datetime(end_year, 12, 31)
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))

def make_email(fname, lname):
    domains = ["gmail.com", "yahoo.com", "hotmail.com"]
    return f"{fname.lower()}.{lname.lower()}{random.randint(1,99)}@{random.choice(domains)}"

def make_phone():
    return f"08{random.randint(10,99)}{random.randint(10000000,99999999)}"

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
            order_id INTEGER, payment_method TEXT,
            payment_date TEXT, amount REAL, status TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
    """)
    conn.commit()

def insert_clean_customers(conn, n=200):
    c = conn.cursor()
    rows = []
    for i in range(1, n + 1):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        cd = random.choice(CITIES)
        rows.append((i, f"{fn} {ln}", make_email(fn,ln), make_phone(),
                      cd[0], cd[1], cd[2], random.choice(["L","P"]),
                      random_date(2021,2023).strftime("%Y-%m-%d %H:%M:%S")))
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    return n

def insert_clean_products(conn):
    c = conn.cursor()
    rows = [(i, n, cat, p, random.randint(10,500), random_date(2021,2022).strftime("%Y-%m-%d"))
            for i,(n,cat,p) in enumerate(PRODUCT_CATALOG, 1)]
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", rows)
    conn.commit()

def insert_clean_orders(conn, n_cust, n_orders=500):
    c = conn.cursor()
    order_rows=[]; item_rows=[]; payment_rows=[]
    item_id = 1
    for oid in range(1, n_orders+1):
        cid  = random.randint(1, n_cust)
        odt  = random_date(2022, 2024)
        stat = random.choice(ORDER_STATUSES)
        n_it = random.randint(1,5)
        total= 0.0
        for _ in range(n_it):
            pid   = random.randint(1, len(PRODUCT_CATALOG))
            price = PRODUCT_CATALOG[pid-1][2]
            qty   = random.randint(1,4)
            sub   = price*qty
            total+= sub
            item_rows.append((item_id, oid, pid, qty, price, sub))
            item_id += 1
        order_rows.append((oid, cid, odt.strftime("%Y-%m-%d"), stat, round(total,2)))
        pdt = odt + timedelta(days=random.randint(0,2))
        payment_rows.append((oid, oid, random.choice(PAYMENT_METHODS),
                              pdt.strftime("%Y-%m-%d %H:%M:%S"), round(total,2),
                              "Success" if stat!="Cancelled" else "Failed"))
    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", order_rows)
    c.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", item_rows)
    c.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", payment_rows)
    conn.commit()
    return n_orders

def inject_dirty_data(conn):
    c = conn.cursor()
    print("  [DIRTY] NULL values...")
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", [
        (201, None, "siti.null@gmail.com", None, "Jakarta","DKI Jakarta","Jawa","P","2022-03-01 10:00:00"),
        (202, "Agus Tanpa HP", None, None, "Bandung","Jawa Barat","Jawa","L","2022-04-15 09:00:00"),
        (203, "Unknown User", "unknown@mail.com", "081234567890", None, None, None, None, "2022-06-01 11:00:00"),
        (204, None, None, None, "Surabaya","Jawa Timur","Jawa","L",None),
        (205, "Sri Tanpa Kota","sri@gmail.com","082233445566",None,None,None,"P","2023-01-01 08:00:00"),
    ])
    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", [
        (501, 1, "2023-05-01", None, None),
        (502, 2, "2023-06-15", None, 500000),
        (503, 3, "2023-07-20", "Shipped", None),
    ])
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", [
        (21, "Produk Misterius", None, None, 50, "2022-01-01"),
        (22, None, "Books", 75000, 30, "2022-02-01"),
    ])
    print("  [DIRTY] Duplicate data...")
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", [
        (206,"Budi Santoso","budi.santoso1@gmail.com","081122334455","Jakarta","DKI Jakarta","Jawa","L","2022-05-01 09:00:00"),
        (207,"Budi Santoso","budi.santoso1@gmail.com","081122334455","Jakarta","DKI Jakarta","Jawa","L","2022-05-01 09:00:00"),
        (208,"BUDI SANTOSO","budi.santoso1@gmail.com","081122334455","Jakarta","DKI Jakarta","Jawa","L","2022-05-05 14:00:00"),
        (209,"Dewi Rahayu","dewi.rahayu33@gmail.com","085566778899","Bandung","Jawa Barat","Jawa","P","2022-07-10 10:00:00"),
        (210,"Dewi Rahayu","dewi.rahayu33@gmail.com","085566778899","Bandung","Jawa Barat","Jawa","P","2022-07-10 10:00:00"),
    ])
    c.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", [
        (9001, 1, 1, 2, 7500000, 15000000),
        (9002, 1, 1, 2, 7500000, 15000000),
    ])
    print("  [DIRTY] Bad business logic...")
    c.executemany("INSERT INTO products VALUES (?,?,?,?,?,?)", [
        (23,"Produk Harga Negatif","Electronics",-500000,10,"2022-01-01"),
        (24,"Produk Gratis","Fashion",0,20,"2022-01-01"),
        (25,"Produk Harga Gila","Health",999999999,5,"2022-01-01"),
    ])
    c.executemany("INSERT INTO order_items VALUES (?,?,?,?,?,?)", [
        (9003, 5, 2, -3, 4200000, -12600000),
        (9004, 6, 3,  2, 3500000,  1000000),
    ])
    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?)", [
        (504, 10, "2024-01-15", "Completed", -250000),
        (505, 11, "2024-02-20", "Completed",  0),
        (506, 12, "2099-12-31", "Completed",  500000),
        (507, 13, "2015-01-01", "Completed",  300000),
    ])
    c.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?)", [
        (9001, 504, "GoPay",  "2024-01-16 10:00:00", -250000, "Success"),
        (9002, 505, "OVO",    "2024-02-21 08:00:00",       0, "Success"),
    ])
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?,?,?)", [
        (211,"User HP Pendek","pendek@gmail.com","123","Jakarta","DKI Jakarta","Jawa","L","2023-01-01 00:00:00"),
        (212,"User HP Huruf","huruf@gmail.com","BUKAN_TELEPON","Medan","Sumatera Utara","Sumatera","P","2022-03-01 00:00:00"),
        (213,"Orang Aneh","aneh@gmail.com","083333333333","Surabaya","Jawa Timur","Jawa","X","2022-01-01 00:00:00"),
        (214,"Orang Lain","lain@gmail.com","084444444444","Bandung","Jawa Barat","Jawa","TIDAK DIKETAHUI","2022-02-01 00:00:00"),
    ])
    conn.commit()

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    print("\n" + "="*60)
    print("  GENERATE OLTP DATABASE (E-Commerce) + DIRTY DATA")
    print("="*60)
    conn = sqlite3.connect(DB_PATH)
    print("\n[1] Membuat skema OLTP...")
    create_oltp_schema(conn)
    print("    OK Skema berhasil dibuat")
    print("\n[2] Mengisi data bersih...")
    n_cust = insert_clean_customers(conn, 200)
    insert_clean_products(conn)
    n_ord  = insert_clean_orders(conn, n_cust, 500)
    print(f"    OK {n_cust} customers, {len(PRODUCT_CATALOG)} products, {n_ord} orders")
    print("\n[3] Menyisipkan DATA KOTOR...")
    inject_dirty_data(conn)
    print("\n[4] Ringkasan:")
    for t in ["customers","products","orders","order_items","payments"]:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"    {t:15s}: {cnt:5d} record")
    conn.close()
    print(f"\nSUKSES: Database '{DB_PATH}' berhasil dibuat!")
    print("="*60)

if __name__ == "__main__":
    main()
