"""
=================================================================
 3. SCHEDULER: Otomatisasi Penjadwalan Pipeline ETL
=================================================================
Script ini memicu eksekusi pipeline ETL (2_etl/etl_pipeline.py)
secara terjadwal dan berkala.
=================================================================
"""

import sys
import os
import time
import subprocess
from datetime import datetime
import argparse
import shutil

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)
SCRIPT_ETL = os.path.join(ROOT_DIR, "2_etl", "etl_pipeline.py")
LOG_FILE   = os.path.join(BASE_DIR, "scheduler_log.txt")

if shutil.which("py"):
    PYTHON_CMD = ["py", "-3"]
else:
    PYTHON_CMD = [sys.executable]

def log_event(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def execute_etl(run_count):
    log_event(f"[>] [RUN #{run_count}] Memicu eksekusi ETL otomatis: {os.path.basename(SCRIPT_ETL)}...")
    start_time = time.time()
    
    try:
        result = subprocess.run(
            PYTHON_CMD + [SCRIPT_ETL],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        elapsed = time.time() - start_time
        
        if result.returncode == 0:
            log_event(f"[OK] [RUN #{run_count}] Pipeline ETL Berhasil selesai dalam {elapsed:.2f} detik.")
        else:
            log_event(f"[ERROR] [RUN #{run_count}] Pipeline Gagal (Exit Code {result.returncode}) dalam {elapsed:.2f} detik.")
            if result.stderr:
                log_event(f"   Error: {result.stderr.strip()[:200]}")
    except Exception as e:
        log_event(f"[ERROR] [RUN #{run_count}] Terjadi eksepsi: {e}")

def run_interval_mode(seconds):
    print("=" * 65)
    print("  ETL SCHEDULER: MODE INTERVAL")
    print(f"  Target Pipeline   : {os.path.basename(SCRIPT_ETL)}")
    print(f"  Interval Eksekusi : Setiap {seconds} detik")
    print(f"  Log Penyimpanan   : {os.path.basename(LOG_FILE)}")
    print("  Tekan Ctrl + C untuk menghentikan scheduler.")
    print("=" * 65)
    
    run_count = 1
    execute_etl(run_count)
    
    while True:
        next_run = datetime.fromtimestamp(time.time() + seconds).strftime("%H:%M:%S")
        print(f"[*] Menunggu eksekusi berikutnya pukul {next_run} ({seconds} detik)...")
        time.sleep(seconds)
        run_count += 1
        execute_etl(run_count)

def run_daily_mode(target_time_str):
    print("=" * 65)
    print("  ETL SCHEDULER: MODE HARIAN")
    print(f"  Target Pipeline   : {os.path.basename(SCRIPT_ETL)}")
    print(f"  Jadwal Harian     : Pukul {target_time_str} WIB")
    print(f"  Log Penyimpanan   : {os.path.basename(LOG_FILE)}")
    print("  Tekan Ctrl + C untuk menghentikan scheduler.")
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
            
        time.sleep(20)

def main():
    parser = argparse.ArgumentParser(description="ETL Scheduler Runner")
    parser.add_argument("--interval", type=int, default=60, help="Interval eksekusi dalam detik (default: 60)")
    parser.add_argument("--daily", type=str, default=None, help="Jadwal harian format HH:MM (contoh: 00:00)")
    parser.add_argument("--once", action="store_true", help="Jalankan ETL satu kali lalu selesai")
    
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
        log_event("[STOP] Scheduler dihentikan oleh pengguna (KeyboardInterrupt).")
        print("Scheduler berhasil dihentikan.")

if __name__ == "__main__":
    main()
