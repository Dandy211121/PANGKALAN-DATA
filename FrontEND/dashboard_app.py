"""
Dashboard Analitik DWH E-Commerce (backend API + web server)
Hanya memakai library standar Python (tanpa pip install).
Jalankan: py -3 dashboard_app.py  ->  http://localhost:8080
"""
import http.server, socketserver, sqlite3, json, os, webbrowser, threading
from collections import defaultdict
from datetime import date, timedelta
from urllib.parse import urlparse, parse_qs

PORT = 8080
BASE = os.path.dirname(os.path.abspath(__file__))
DWH = os.path.join(os.path.dirname(BASE), "4_dwh", "dwh_ecommerce.db")
VALID = ("Completed", "Shipped", "Processing")
SQL = """SELECT f.sales_key, f.order_id, d.full_date, d.weekday, c.customer_id, c.full_name, c.city,
 c.gender, p.product_name, p.category, f.branch_name, f.quantity, f.subtotal, f.order_status
 FROM fact_sales f JOIN dim_date d ON f.date_key=d.date_key
 JOIN dim_customer c ON f.customer_key=c.customer_key
 JOIN dim_product p ON f.product_key=p.product_key"""
COLS = ["id", "order", "date", "weekday", "cust_id", "customer", "city", "gender",
        "product", "category", "branch", "qty", "subtotal", "status"]

def db():
    return sqlite3.connect(DWH)

def load(conn, start, end):
    rows = conn.execute(SQL + " WHERE d.full_date BETWEEN ? AND ?", (start, end)).fetchall()
    return [dict(zip(COLS, r)) for r in rows]

def keep(rows, q):
    st, br, ca = q.get("status", "valid"), q.get("branch", ""), q.get("category", "")
    out = []
    for r in rows:
        if st == "valid" and r["status"] not in VALID: continue
        if st not in ("valid", "all") and r["status"] != st: continue
        if br and r["branch"] != br: continue
        if ca and r["category"] != ca: continue
        out.append(r)
    return out

def summary(rows, margins):
    rev = sum(r["subtotal"] for r in rows)
    profit = sum(r["subtotal"] * margins.get(r["category"], 0) / 100 for r in rows)
    orders = len({r["order"] for r in rows})
    return {"revenue": rev, "profit": profit, "orders": orders, "qty": sum(r["qty"] for r in rows),
            "aov": rev / orders if orders else 0, "customers": len({r["cust_id"] for r in rows})}

def group(rows, keyfn, margins):
    g = defaultdict(lambda: {"revenue": 0, "profit": 0, "qty": 0, "orders": set()})
    for r in rows:
        k = keyfn(r); x = g[k]
        x["revenue"] += r["subtotal"]; x["qty"] += r["qty"]; x["orders"].add(r["order"])
        x["profit"] += r["subtotal"] * margins.get(r["category"], 0) / 100
    return [{"key": k, "revenue": v["revenue"], "profit": v["profit"], "qty": v["qty"],
             "orders": len(v["orders"])} for k, v in sorted(g.items(), key=lambda i: str(i[0]))]

def period_key(gran):
    if gran == "day": return lambda r: r["date"]
    if gran == "week":
        def wk(r):
            d = date.fromisoformat(r["date"]); return (d - timedelta(days=d.weekday())).isoformat()
        return wk
    return lambda r: r["date"][:7]

def analytics(q):
    conn = db()
    lo, hi = conn.execute("SELECT MIN(full_date), MAX(full_date) FROM dim_date d JOIN fact_sales f ON f.date_key=d.date_key").fetchone()
    start, end = q.get("start") or lo, q.get("end") or hi
    try: margins = json.loads(q.get("margins", "{}"))
    except ValueError: margins = {}
    margins = {k: float(v) for k, v in margins.items()}
    raw = load(conn, start, end)
    rows = keep(raw, q)
    # periode pembanding (rentang sama persis sebelum 'start')
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    span = (e - s).days + 1
    prev = keep(load(conn, (s - timedelta(days=span)).isoformat(), (s - timedelta(days=1)).isoformat()), q)
    top = lambda lst, n: sorted(lst, key=lambda x: -x["revenue"])[:n]
    allst = keep(raw, {**q, "status": "all"})
    status = group(allst, lambda r: r["status"], margins)
    cust = group(rows, lambda r: (r["cust_id"], r["customer"], r["city"]), margins)
    pay = defaultdict(lambda: {"Success": 0, "Failed": 0, "n_ok": 0, "n_fail": 0})
    for m, st, amt in conn.execute("""SELECT payment_method, payment_status, amount FROM fact_payments p
        JOIN dim_date d ON p.date_key=d.date_key WHERE d.full_date BETWEEN ? AND ?""", (start, end)):
        x = pay[m]; x[st] += amt; x["n_ok" if st == "Success" else "n_fail"] += 1
    audit = [dict(zip(("time", "table", "dq", "action", "in", "out", "fixed", "notes"), r)) for r in
             conn.execute("SELECT run_time, table_name, dq_dimension, action, records_in, records_out, records_fixed, notes FROM etl_audit_log ORDER BY log_id DESC LIMIT 50")]
    cnt = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
           ("fact_sales", "fact_payments", "dim_customer", "dim_product", "dim_order", "dim_date")}
    conn.close()
    return {
        "range": {"min": lo, "max": hi, "start": start, "end": end},
        "kpi": summary(rows, margins), "kpi_prev": summary(prev, margins),
        "cancel_rate": (sum(x["orders"] for x in status if x["key"] in ("Cancelled", "Returned")) /
                        max(1, sum(x["orders"] for x in status))),
        "series": group(rows, period_key(q.get("gran", "month")), margins),
        "daily": group(rows, lambda r: r["date"], margins),
        "branch": top(group(rows, lambda r: r["branch"], margins), 20),
        "category": top(group(rows, lambda r: r["category"], margins), 20),
        "product": top(group(rows, lambda r: (r["product"], r["category"]), margins), 10),
        "weekday": group(rows, lambda r: r["weekday"], margins),
        "city": top(group(rows, lambda r: r["city"], margins), 10),
        "gender": group(rows, lambda r: r["gender"] or "-", margins),
        "customers": top(cust, 10), "status": status,
        "payments": [{"method": m, **v} for m, v in sorted(pay.items())],
        "rows": sorted(rows, key=lambda r: (r["date"], r["id"]), reverse=True),
        "audit": audit, "counts": cnt,
    }

def meta():
    conn = db()
    m = {"branches": [r[0] for r in conn.execute("SELECT DISTINCT branch_name FROM fact_sales ORDER BY 1")],
         "categories": [r[0] for r in conn.execute("SELECT DISTINCT category FROM dim_product ORDER BY 1")],
         "statuses": [r[0] for r in conn.execute("SELECT DISTINCT order_status FROM fact_sales ORDER BY 1")]}
    conn.close(); return m

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=os.path.join(BASE, "static"), **k)
    def log_message(self, *a): pass
    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/api/"):
            try:
                if not os.path.exists(DWH): raise FileNotFoundError("DWH belum ada. Jalankan ETL dulu (2_etl/etl_pipeline.py).")
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                data = meta() if u.path == "/api/meta" else analytics(q)
                body, code = json.dumps(data, default=str).encode(), 200
            except Exception as ex:
                body, code = json.dumps({"error": str(ex)}).encode(), 500
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            super().do_GET()

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("", PORT), Handler) as srv:
        print(f"Dashboard DWH berjalan di http://localhost:{PORT}  (Ctrl+C untuk berhenti)")
        threading.Timer(1, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
        try: srv.serve_forever()
        except KeyboardInterrupt: print("\nDihentikan.")
