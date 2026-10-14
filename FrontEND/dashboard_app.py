"""
=============================================================
 5. DASHBOARD / VIEWING: Web Dashboard Interaktif DWH
=============================================================
Menyajikan antarmuka visualisasi web modern untuk DWH:
  - KPI Cards (Total Omzet, Transaksi, Volume, AOV)
  - Grafik Interaktif (Chart.js)
  - Tabel Data Fakta Penjualan Terkini (Viewing)
  - Visualisasi Diagram Arsitektur DWH
Port Default: http://localhost:8080
=============================================================
"""

import http.server
import socketserver
import sqlite3
import json
import os
import webbrowser
import threading

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DWH_PATH = os.path.join(ROOT_DIR, "4_dwh", "dwh_ecommerce.db")

def get_dashboard_data():
    if not os.path.exists(DWH_PATH):
        return {"error": "Database DWH belum dibuat. Silakan jalankan ETL pipeline terlebih dahulu."}
    
    conn = sqlite3.connect(DWH_PATH)
    c = conn.cursor()

    # KPI Summary
    kpi_query = """
        SELECT 
            COUNT(DISTINCT order_id) as total_transaksi,
            SUM(quantity) as total_qty,
            CAST(SUM(subtotal) AS INT) as total_omzet,
            CAST(AVG(subtotal) AS INT) as aov
        FROM fact_sales
    """
    c.execute(kpi_query)
    kpi = c.fetchone()

    # Penjualan per Kategori
    cat_query = """
        SELECT p.category, CAST(SUM(f.subtotal) AS INT) as total
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.category
        ORDER BY total DESC
    """
    c.execute(cat_query)
    categories = [{"name": r[0], "total": r[1]} for r in c.fetchall()]

    # Penjualan per Cabang (Multi-OLTP)
    branch_query = """
        SELECT branch_name, CAST(SUM(subtotal) AS INT) as total, COUNT(DISTINCT order_id) as orders
        FROM fact_sales
        GROUP BY branch_name
        ORDER BY total DESC
    """
    c.execute(branch_query)
    branches = [{"branch": r[0], "total": r[1], "orders": r[2]} for r in c.fetchall()]

    # Tren per Kuartal
    trend_query = """
        SELECT d.year || ' Q' || d.quarter as periode, CAST(SUM(f.subtotal) AS INT) as total
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        GROUP BY periode
        ORDER BY periode ASC
    """
    c.execute(trend_query)
    trends = [{"period": r[0], "total": r[1]} for r in c.fetchall()]

    # Top 5 Produk
    top_query = """
        SELECT p.product_name, p.category, SUM(f.quantity) as qty, CAST(SUM(f.subtotal) AS INT) as total
        FROM fact_sales f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_name, p.category
        ORDER BY total DESC
        LIMIT 5
    """
    c.execute(top_query)
    top_products = [{"name": r[0], "category": r[1], "qty": r[2], "total": r[3]} for r in c.fetchall()]

    # Recent Transactions (Viewing layer)
    recent_query = """
        SELECT f.sales_key, f.order_id, d.full_date, c.full_name, c.city, p.product_name, f.branch_name, f.quantity, CAST(f.subtotal AS INT), f.order_status
        FROM fact_sales f
        JOIN dim_date d ON f.date_key = d.date_key
        JOIN dim_customer c ON f.customer_key = c.customer_key
        JOIN dim_product p ON f.product_key = p.product_key
        ORDER BY f.sales_key DESC
        LIMIT 25
    """
    c.execute(recent_query)
    recent = [{
        "key": r[0], "order_id": r[1], "date": r[2], "customer": r[3],
        "city": r[4], "product": r[5], "branch": r[6], "qty": r[7], "subtotal": r[8], "status": r[9]
    } for r in c.fetchall()]

    conn.close()

    return {
        "kpi": {
            "total_transaksi": kpi[0] or 0,
            "total_qty": kpi[1] or 0,
            "total_omzet": kpi[2] or 0,
            "aov": kpi[3] or 0
        },
        "categories": categories,
        "branches": branches,
        "trends": trends,
        "top_products": top_products,
        "recent_sales": recent
    }

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E-Commerce Data Warehouse Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg: #0f172a;
            --surface: #1e293b;
            --surface-hover: #334155;
            --primary: #38bdf8;
            --primary-accent: #0284c7;
            --secondary: #818cf8;
            --success: #34d399;
            --warning: #fbbf24;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: #334155;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg); color: var(--text-main); padding: 24px; }
        .container { max-width: 1400px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--border); }
        .badge { background: rgba(56,189,248,0.15); color: var(--primary); padding: 6px 14px; border-radius: 99px; font-size: 0.85rem; font-weight: 600; }
        
        /* Architecture Flow Banner */
        .arch-banner { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 18px 24px; margin-bottom: 24px; }
        .arch-title { font-size: 0.95rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }
        .arch-flow { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .flow-node { background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; font-size: 0.88rem; font-weight: 600; }
        .flow-node.highlight { border-color: var(--primary); background: rgba(56,189,248,0.1); color: var(--primary); }
        .flow-arrow { color: var(--text-muted); font-size: 1.2rem; }

        /* KPI Cards */
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; transition: transform 0.2s; }
        .kpi-card:hover { transform: translateY(-2px); border-color: var(--primary); }
        .kpi-label { font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 8px; }
        .kpi-val { font-size: 1.8rem; font-weight: 700; color: var(--text-main); }
        .kpi-sub { font-size: 0.8rem; color: var(--success); margin-top: 6px; }

        /* Charts Grid */
        .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(480px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .chart-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        .chart-title { font-size: 1.05rem; font-weight: 600; margin-bottom: 16px; color: var(--text-main); display: flex; justify-content: space-between; align-items: center; }

        /* Table */
        .table-box { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 20px; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 0.88rem; text-align: left; }
        th { background: rgba(255,255,255,0.03); color: var(--text-muted); padding: 12px; border-bottom: 1px solid var(--border); font-weight: 600; }
        td { padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-main); }
        tr:hover td { background: var(--surface-hover); }
        .tag-status { padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; }
        .status-completed { background: rgba(52,211,153,0.15); color: var(--success); }
        .status-shipped { background: rgba(56,189,248,0.15); color: var(--primary); }
        .status-processing { background: rgba(251,191,36,0.15); color: var(--warning); }
        .status-cancelled, .status-returned { background: rgba(239,68,68,0.15); color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1 style="font-size: 1.6rem; font-weight: 700; margin-bottom: 4px;">E-Commerce Data Warehouse Dashboard</h1>
                <p style="color: var(--text-muted); font-size: 0.9rem;">Visualisasi Analitis & Lapisan Viewing DWH (Star Schema + 7 Dimensi DQ)</p>
            </div>
            <div class="badge">Pipeline Status: Active ✔</div>
        </header>

        <!-- Diagram Arsitektur Alur Sistem -->
        <div class="arch-banner">
            <div class="arch-title">Arsitektur Pipeline Sistem DWH</div>
            <div class="arch-flow">
                <div class="flow-node">1. OLTP (Jakarta)</div>
                <div class="flow-node">2. OLTP (Surabaya)</div>
                <div class="flow-node">3. OLTP (Bandung)</div>
                <div class="flow-arrow">➔</div>
                <div class="flow-node highlight">ETL Pipeline (7 DQ)</div>
                <div class="flow-arrow">➔</div>
                <div class="flow-node highlight">Data Warehouse (Star Schema)</div>
                <div class="flow-arrow">➔</div>
                <div class="flow-node highlight">Dashboard / Viewing (Live)</div>
            </div>
        </div>

        <!-- KPI Summary Cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Omzet Penjualan</div>
                <div class="kpi-val" id="kpi-omzet">Rp 0</div>
                <div class="kpi-sub">Dari 3 Sumber Cabang OLTP</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Total Transaksi</div>
                <div class="kpi-val" id="kpi-orders">0</div>
                <div class="kpi-sub">Pesanan Lolos Validasi DQ</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Volume Barang Terjual</div>
                <div class="kpi-val" id="kpi-qty">0</div>
                <div class="kpi-sub">Total Item Terdistribusi</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Rata-rata Order (AOV)</div>
                <div class="kpi-val" id="kpi-aov">Rp 0</div>
                <div class="kpi-sub">Nilai Transaksi Rata-rata</div>
            </div>
        </div>

        <!-- Charts Grid -->
        <div class="charts-grid">
            <div class="chart-box">
                <div class="chart-title">Penjualan per Kategori Produk</div>
                <canvas id="catChart" height="220"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Distribusi Omzet per Cabang OLTP</div>
                <canvas id="branchChart" height="220"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Tren Penjualan per Kuartal</div>
                <canvas id="trendChart" height="220"></canvas>
            </div>
            <div class="chart-box">
                <div class="chart-title">Top 5 Produk Terlaris</div>
                <canvas id="topChart" height="220"></canvas>
            </div>
        </div>

        <!-- Viewing Table: Transaksi Terbaru -->
        <div class="table-box">
            <div class="chart-title" style="margin-bottom: 12px;">Lapisan Viewing: Transaksi Fakta Penjualan Terkini (fact_sales)</div>
            <table>
                <thead>
                    <tr>
                        <th>ID Fakta</th>
                        <th>Order ID</th>
                        <th>Tanggal</th>
                        <th>Pelanggan</th>
                        <th>Kota</th>
                        <th>Produk</th>
                        <th>Cabang Sumber</th>
                        <th>Qty</th>
                        <th>Subtotal</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="sales-tbody">
                    <tr><td colspan="10" style="text-align:center;">Memuat data...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function rupiah(num) {
            return 'Rp ' + Number(num).toLocaleString('id-ID');
        }

        fetch('/api/data')
            .then(res => res.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                    return;
                }

                // Fill KPI
                document.getElementById('kpi-omzet').textContent = rupiah(data.kpi.total_omzet);
                document.getElementById('kpi-orders').textContent = Number(data.kpi.total_transaksi).toLocaleString('id-ID');
                document.getElementById('kpi-qty').textContent = Number(data.kpi.total_qty).toLocaleString('id-ID') + ' unit';
                document.getElementById('kpi-aov').textContent = rupiah(data.kpi.aov);

                // Chart 1: Categories
                new Chart(document.getElementById('catChart'), {
                    type: 'bar',
                    data: {
                        labels: data.categories.map(c => c.name),
                        datasets: [{
                            label: 'Total Penjualan (Rp)',
                            data: data.categories.map(c => c.total),
                            backgroundColor: '#38bdf8',
                            borderRadius: 6
                        }]
                    },
                    options: { responsive: true, plugins: { legend: { display: false } } }
                });

                // Chart 2: Branches
                new Chart(document.getElementById('branchChart'), {
                    type: 'doughnut',
                    data: {
                        labels: data.branches.map(b => b.branch),
                        datasets: [{
                            data: data.branches.map(b => b.total),
                            backgroundColor: ['#38bdf8', '#818cf8', '#34d399']
                        }]
                    },
                    options: { responsive: true }
                });

                // Chart 3: Trends
                new Chart(document.getElementById('trendChart'), {
                    type: 'line',
                    data: {
                        labels: data.trends.map(t => t.period),
                        datasets: [{
                            label: 'Omzet',
                            data: data.trends.map(t => t.total),
                            borderColor: '#34d399',
                            backgroundColor: 'rgba(52,211,153,0.1)',
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: { responsive: true }
                });

                // Chart 4: Top Products
                new Chart(document.getElementById('topChart'), {
                    type: 'bar',
                    data: {
                        labels: data.top_products.map(p => p.name),
                        datasets: [{
                            label: 'Pendapatan',
                            data: data.top_products.map(p => p.total),
                            backgroundColor: '#818cf8',
                            borderRadius: 6
                        }]
                    },
                    options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
                });

                // Table
                const tbody = document.getElementById('sales-tbody');
                tbody.innerHTML = '';
                data.recent_sales.forEach(row => {
                    const tr = document.createElement('tr');
                    const statusClass = 'status-' + row.status.toLowerCase();
                    tr.innerHTML = `
                        <td>#${row.key}</td>
                        <td>${row.order_id}</td>
                        <td>${row.date}</td>
                        <td><strong>${row.customer}</strong></td>
                        <td>${row.city}</td>
                        <td>${row.product}</td>
                        <td>${row.branch}</td>
                        <td>${row.qty}</td>
                        <td><strong>${rupiah(row.subtotal)}</strong></td>
                        <td><span class="tag-status ${statusClass}">${row.status}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            });
    </script>
</body>
</html>
"""

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = get_dashboard_data()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        else:
            super().do_GET()

def start_server():
    server_address = ("", PORT)
    with socketserver.TCPServer(server_address, DashboardHandler) as httpd:
        print("=" * 65)
        print(f"  WEB DASHBOARD / VIEWING BERJALAN")
        print(f"  Akses di browser : http://localhost:{PORT}")
        print(f"  Tekan Ctrl + C untuk mematikan server dashboard.")
        print("=" * 65)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer dashboard dihentikan.")

if __name__ == "__main__":
    start_server()
