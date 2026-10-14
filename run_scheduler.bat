@echo off
title Automated ETL Scheduler - E-Commerce DWH
echo ========================================================
echo  Automated ETL Scheduler - E-Commerce Data Warehouse
echo ========================================================
echo.
py -3 4_etl_scheduler.py --interval 60
pause
