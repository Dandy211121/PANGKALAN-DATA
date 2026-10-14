@echo off
title Web Dashboard / Viewing - E-Commerce DWH
echo ========================================================
echo   MEMBUKA DASHBOARD / VIEWING DATA WAREHOUSE
echo ========================================================
echo.
echo Membuka browser di http://localhost:8080 ...
start http://localhost:8080
py -3 dashboard_app.py
pause
