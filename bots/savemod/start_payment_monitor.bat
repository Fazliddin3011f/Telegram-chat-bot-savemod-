@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Payment Monitor ishga tushirilmoqda...
if not exist logs mkdir logs
start /min "PaymentMonitor" pythonw payment_monitor.py > logs\payment_monitor.log 2>&1
echo Payment Monitor ishga tushdi.
timeout /t 2 >nul
