"""
=============================================================
 STEP 3: DWH Analysis & Reporting
=============================================================
Query analitik pada Data Warehouse (Star Schema)
=============================================================
"""

import sqlite3
import pandas as pd

DWH_PATH = "dwh_ecommerce.db"

def run_query(conn, title, sql):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print("="*55)
    df = pd.read_sql(sql, conn)
    print(df.to_string(index=False))
    return df

def main():
    conn = sqlite3.connect(DWH_PATH)

    # 1. Total penjualan per kategori produk
    run_query(conn, "Total Penjualan per Kategori Produk", """
        SELECT
            p.category                          AS Kategori,
            COUNT(f.sales_key)                  AS Jumlah_Transaksi,
            SUM(f.quantity)                     AS Total_Qty,
            printf('%.0f', SUM(f.subtotal))     AS Total_Pendapatan
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY SUM(f.subtotal) DESC
    """)

    # 2. Top 5 Produk Terlaris
    run_query(conn, "Top 5 Produk Terlaris", """
        SELECT
            p.product_name                      AS Produk,
            p.category                          AS Kategori,
            SUM(f.quantity)                     AS Total_Qty,
            printf('%.0f', SUM(f.subtotal))     AS Total_Pendapatan
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_key
        ORDER BY SUM(f.quantity) DESC
        LIMIT 5
    """)

    # 3. Penjualan per Kuartal
    run_query(conn, "Penjualan per Kuartal (Trend)", """
        SELECT
            d.year                              AS Tahun,
            'Q' || d.quarter                    AS Kuartal,
            COUNT(DISTINCT f.order_id)          AS Jumlah_Order,
            printf('%.0f', SUM(f.subtotal))     AS Total_Penjualan
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY d.year, d.quarter
        ORDER BY d.year, d.quarter
    """)

    # 4. Metode Pembayaran Terpopuler
    run_query(conn, "Metode Pembayaran Terpopuler", """
        SELECT
            fp.payment_method                   AS Metode,
            COUNT(*)                            AS Jumlah,
            printf('%.0f', SUM(fp.amount))      AS Total_Amount,
            fp.payment_status                   AS Status
        FROM fact_payments fp
        GROUP BY fp.payment_method, fp.payment_status
        ORDER BY COUNT(*) DESC
    """)

    # 5. Pelanggan Terbaik (Top 5)
    run_query(conn, "Top 5 Pelanggan Terbaik", """
        SELECT
            c.full_name                         AS Nama,
            c.city                              AS Kota,
            COUNT(DISTINCT f.order_id)          AS Jumlah_Order,
            printf('%.0f', SUM(f.subtotal))     AS Total_Belanja
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        GROUP BY c.customer_key
        ORDER BY SUM(f.subtotal) DESC
        LIMIT 5
    """)

    # 6. Penjualan per Pulau
    run_query(conn, "Penjualan per Pulau (Geografis)", """
        SELECT
            c.island                            AS Pulau,
            COUNT(DISTINCT f.order_id)          AS Jumlah_Order,
            printf('%.0f', SUM(f.subtotal))     AS Total_Penjualan
        FROM fact_sales f
        JOIN dim_customer c ON f.customer_key = c.customer_key
        WHERE c.island != 'Tidak Diketahui'
        GROUP BY c.island
        ORDER BY SUM(f.subtotal) DESC
    """)

    # 7. Status Order via dim_order
    run_query(conn, "Distribusi Status Order (via dim_order)", """
        SELECT
            o.order_status                      AS Status,
            COUNT(DISTINCT f.order_key)         AS Jumlah_Order,
            printf('%.0f', SUM(f.subtotal))     AS Total_Nilai
        FROM fact_sales f
        JOIN dim_order o ON f.order_key = o.order_key
        GROUP BY o.order_status
        ORDER BY COUNT(DISTINCT f.order_key) DESC
    """)

    conn.close()
    print("\n" + "="*55)
    print("  Analisis DWH selesai!")
    print("="*55)

if __name__ == "__main__":
    main()
