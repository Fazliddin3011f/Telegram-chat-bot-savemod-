@echo off
chcp 65001 >nul
echo Payment Monitor to'xtatilmoqda...
taskkill /FI "WINDOWTITLE eq PaymentMonitor" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq savemod/payment_monitor.py" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq payment_monitor.py" /F >nul 2>&1
echo Payment Monitor to'xtatildi.
timeout /t 2 >nul
