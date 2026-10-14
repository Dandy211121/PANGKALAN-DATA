@echo off
title ETL Scheduler - E-Commerce Data Warehouse
echo ========================================================
echo   ETL SCHEDULER: Otomatisasi Eksekusi Pipeline DWH
echo ========================================================
echo.
py -3 etl_scheduler.py --interval 60
pause
