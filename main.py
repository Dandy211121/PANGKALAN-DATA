"""
=================================================================
 MAIN RUNNER: E-Commerce Data Warehouse & ETL Pipeline
 Sesuai Arsitektur: 3 OLTP -> ETL -> DWH -> Dashboard
=================================================================
"""

import sys
import os
import subprocess
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if shutil.which("py"):
    PYTHON_CMD = ["py", "-3"]
else:
    PYTHON_CMD = [sys.executable]

def run_script(rel_path, description):
    script_full = os.path.join(BASE_DIR, rel_path)
    print("\n" + "=" * 65)
    print(f"▶ {description} ({rel_path})")
    print("=" * 65)
    subprocess.run(PYTHON_CMD + [script_full])

def main():
    while True:
        print("\n" + "=" * 65)
        print("  SISTEM DATA WAREHOUSE (DWH) E-COMMERCE")
        print("  Arsitektur: Multi-OLTP -> ETL (Scheduler) -> DWH -> Dashboard")
        print("=" * 65)
        print("  1. [OLTP]      Generate 3 Basis Data Cabang OLTP")
        print("  2. [ETL]       Jalankan Pipeline ETL (7 Dimensi DQ & SCD-2)")
        print("  3. [Analytics] Jalankan Analisis OLAP & Export Chart")
        print("  4. [Dashboard] Buka Web Dashboard Interaktif (Port 8080)")
        print("  5. [Scheduler] Jalankan Scheduler Otomatis (Demo 60s)")
        print("  6. [Full Run]  Jalankan End-to-End Pipeline (1 -> 2 -> 3)")
        print("  0. Keluar")
        print("=" * 65)
        
        try:
            choice = input("Pilih menu (0-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nKeluar dari program.")
            break

        if choice == "1":
            run_script(os.path.join("1_oltp", "generate_oltp.py"), "Membuat 3 Basis Data OLTP")
        elif choice == "2":
            run_script(os.path.join("2_etl", "etl_pipeline.py"), "Menjalankan Pipeline ETL")
        elif choice == "3":
            run_script(os.path.join("5_dashboard", "olap_analysis.py"), "Menjalankan Analisis OLAP")
        elif choice == "4":
            run_script(os.path.join("5_dashboard", "dashboard_app.py"), "Menjalankan Web Dashboard")
        elif choice == "5":
            run_script(os.path.join("3_scheduler", "etl_scheduler.py"), "Menjalankan ETL Scheduler")
        elif choice == "6":
            run_script(os.path.join("1_oltp", "generate_oltp.py"), "Langkah 1/3: Generate OLTP")
            run_script(os.path.join("2_etl", "etl_pipeline.py"), "Langkah 2/3: Eksekusi ETL")
            run_script(os.path.join("5_dashboard", "olap_analysis.py"), "Langkah 3/3: Analisis OLAP & Chart")
            print("\n[OK] Pipeline End-to-End berhasil diselesaikan!")
        elif choice == "0":
            print("Terima kasih. Program selesai.")
            break
        else:
            print("[!] Pilihan tidak valid. Silakan masukkan angka 0-6.")

if __name__ == "__main__":
    main()
