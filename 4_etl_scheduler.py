"""
=================================================================
 STEP 4: ETL Scheduler (Automated Pipeline Execution)
 E-Commerce Data Warehouse
=================================================================
Script ini mengotomatiskan eksekusi pipeline ETL secara berkala.
Fitur:
  1. Mode Interval (misal: tiap 60 detik / demo di depan dosen)
  2. Mode Harian (misal: tiap jam 00:00 / produksi malam hari)
  3. Pencatatan log eksekusi otomatis ke 'scheduler_log.txt'
  4. Penghentian rapi (Graceful Shutdown) dengan Ctrl+C
=================================================================
"""

import sys
import os
import time
import subprocess
from datetime import datetime
import argparse

import shutil

# Cari launcher python yang memiliki environment paket lengkap di Windows
if shutil.which("py"):
    PYTHON_CMD = ["py", "-3"]
else:
    PYTHON_CMD = [sys.executable]

SCRIPT_ETL  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2_etl_process.py")
LOG_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduler_log.txt")

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def execute_etl(run_count):
    log_event(f"[>] [RUN #{run_count}] Memulai eksekusi ETL otomatis ({SCRIPT_ETL})...")
    start_time = time.time()
    
    try:
        # Jalankan 2_etl_process.py sebagai subprocess
        result = subprocess.run(
            PYTHON_CMD + [SCRIPT_ETL],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            log_event(f"[OK] [RUN #{run_count}] ETL Berhasil diselesaikan dalam {elapsed:.2f} detik.")
        else:
            log_event(f"[ERROR] [RUN #{run_count}] ETL Gagal (Exit Code {result.returncode}) dalam {elapsed:.2f} detik.")
            if result.stderr:
                log_event(f"  Error details: {result.stderr.strip()[:300]}")
    except Exception as e:
        log_event(f"[ERROR] [RUN #{run_count}] Eksepsi saat menjalankan ETL: {e}")

def run_interval_mode(seconds):
    print("=" * 65)
    print(f"  ETL SCHEDULER: MODE INTERVAL")
    print(f"  Interval Eksekusi : Setiap {seconds} detik")
    print(f"  Target Script     : {os.path.basename(SCRIPT_ETL)}")
    print(f"  Log File          : {os.path.basename(LOG_FILE)}")
    print(f"  Tekan Ctrl + C untuk menghentikan scheduler.")
    print("=" * 65)
    
    run_count = 1
    # Eksekusi pertama langsung saat scheduler dinyalakan
    execute_etl(run_count)
    
    while True:
        next_run = datetime.fromtimestamp(time.time() + seconds).strftime("%H:%M:%S")
        print(f"[*] Menunggu eksekusi berikutnya pada pukul {next_run} (interval {seconds} detik)...")
        time.sleep(seconds)
        run_count += 1
        execute_etl(run_count)

def run_daily_mode(target_time_str):
    print("=" * 65)
    print(f"  ETL SCHEDULER: MODE HARIAN (DAILY SCHEDULE)")
    print(f"  Waktu Eksekusi   : Pukul {target_time_str} setiap hari")
    print(f"  Target Script    : {os.path.basename(SCRIPT_ETL)}")
    print(f"  Log File         : {os.path.basename(LOG_FILE)}")
    print(f"  Tekan Ctrl + C untuk menghentikan scheduler.")
    print("=" * 65)
    
    run_count = 0
    executed_today = False
    
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        
        if current_time_str == target_time_str:
            if not executed_today:
                run_count += 1
                execute_etl(run_count)
                executed_today = True
        else:
            executed_today = False
            
        time.sleep(20)  # Polling setiap 20 detik untuk mencocokkan menit

def main():
    parser = argparse.ArgumentParser(description="Automated ETL Pipeline Scheduler for E-Commerce DWH")
    parser.add_argument("--interval", type=int, default=60, help="Interval eksekusi dalam detik (default: 60 detik)")
    parser.add_argument("--daily", type=str, default=None, help="Jadwal harian format HH:MM (contoh: 02:00)")
    parser.add_argument("--once", action="store_true", help="Jalankan ETL satu kali saja lewat scheduler lalu keluar")
    
    args = parser.parse_args()
    
    if args.once:
        print("[*] Menjalankan ETL satu kali (Mode --once)...")
        execute_etl(1)
        return
        
    try:
        if args.daily:
            run_daily_mode(args.daily)
        else:
            run_interval_mode(args.interval)
    except KeyboardInterrupt:
        print("\n")
        log_event("[STOP] Scheduler dihentikan dengan aman oleh pengguna (KeyboardInterrupt).")
        print("Scheduler berhasil dinonaktifkan.")

if __name__ == "__main__":
    main()
