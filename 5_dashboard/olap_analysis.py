"""
=============================================================
 5. DASHBOARD / VIEWING: Analisis Bisnis OLAP & Generator Chart
=============================================================
Menjalankan query analitis OLAP pada DWH dan mengekspor grafik
ke folder '5_dashboard/charts/'.
=============================================================
"""

import sqlite3
import pandas as pd
import os
import matplotlib.pyplot as plt

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)
DWH_PATH   = os.path.join(ROOT_DIR, "4_dwh", "dwh_ecommerce.db")
CHARTS_DIR = os.path.join(BASE_DIR, "charts")

os.makedirs(CHARTS_DIR, exist_ok=True)

def run_analysis():
    print("=" * 65)
    print("  HASIL ANALISIS BISNIS OLAP (DATA WAREHOUSE)")
    print("=" * 65)

    conn = sqlite3.connect(DWH_PATH)

    # 1. Penjualan per Kategori
    query_cat = """
        SELECT 
            p.category as Kategori,
            COUNT(DISTINCT f.order_id) as Transaksi,
            SUM(f.quantity) as Qty,
            CAST(SUM(f.subtotal) AS INT) as Total_Penjualan
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY Total_Penjualan DESC
    """
    df_cat = pd.read_sql(query_cat, conn)
    print("\n--- 1. Penjualan Berdasarkan Kategori Produk ---")
    print(df_cat.to_string(index=False))

    # Export Chart 1
    plt.figure(figsize=(8, 4.5))
    plt.bar(df_cat["Kategori"], df_cat["Total_Penjualan"] / 1e6, color="#3b82f6")
    plt.title("Total Penjualan per Kategori Produk (Juta Rp)")
    plt.xlabel("Kategori")
    plt.ylabel("Penjualan (Juta Rp)")
    plt.xticks(rotation=20)
    plt.tight_layout()
    chart1_path = os.path.join(CHARTS_DIR, "penjualan_per_kategori.png")
    plt.savefig(chart1_path, dpi=150)
    plt.close()
    print(f"   [Chart tersimpan: {os.path.basename(chart1_path)}]")

    # 2. Penjualan per Cabang (Multi-Source OLTP)
    query_branch = """
        SELECT 
            f.branch_name as Cabang,
            COUNT(DISTINCT f.order_id) as Transaksi,
            CAST(SUM(f.subtotal) AS INT) as Total_Penjualan,
            CAST(AVG(f.subtotal) AS INT) as Rata_rata_Penjualan
        FROM fact_sales f
        GROUP BY f.branch_name
        ORDER BY Total_Penjualan DESC
    """
    df_branch = pd.read_sql(query_branch, conn)
    print("\n--- 2. Kontribusi Penjualan per Cabang (Multi-OLTP) ---")
    print(df_branch.to_string(index=False))

    # Export Chart 2
    plt.figure(figsize=(7, 4.5))
    plt.pie(df_branch["Total_Penjualan"], labels=df_branch["Cabang"], autopct="%1.1f%%", colors=["#10b981", "#6366f1", "#f59e0b"])
    plt.title("Pangsa Omzet per Sumber Cabang OLTP")
    plt.tight_layout()
    chart2_path = os.path.join(CHARTS_DIR, "penjualan_per_cabang.png")
    plt.savefig(chart2_path, dpi=150)
    plt.close()
    print(f"   [Chart tersimpan: {os.path.basename(chart2_path)}]")

    # 3. Top 5 Produk Terlaris
    query_top = """
        SELECT 
            p.product_name as Produk,
            p.category as Kategori,
            SUM(f.quantity) as Total_Qty,
            CAST(SUM(f.subtotal) AS INT) as Total_Pendapatan
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_name, p.category
        ORDER BY Total_Pendapatan DESC
        LIMIT 5
    """
    df_top = pd.read_sql(query_top, conn)
    print("\n--- 3. Top 5 Produk Berdasarkan Pendapatan ---")
    print(df_top.to_string(index=False))

    conn.close()
    print("\n" + "=" * 65)
    print("  Semua analisis OLAP selesai dan chart grafik berhasil dibuat.")
    print("=" * 65)

if __name__ == "__main__":
    run_analysis()
