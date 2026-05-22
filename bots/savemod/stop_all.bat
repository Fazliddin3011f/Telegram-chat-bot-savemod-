@echo off
chcp 65001 >nul
echo ====================================
echo   BARCHA BOTLANI TO'XTATISH
echo ====================================
echo.

echo [1/2] SaveMod to'xtatilmoqda...
taskkill /FI "WINDOWTITLE eq SaveMod" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq savemod/main.py" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq main.py" /F >nul 2>&1
echo SaveMod to'xtatildi.

echo [2/3] Chat Bot to'xtatilmoqda...
taskkill /FI "WINDOWTITLE eq ChatBot" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq savemod/chatbot.py" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq chatbot.py" /F >nul 2>&1
echo Chat Bot to'xtatildi.

echo [3/3] Payment Monitor to'xtatilmoqda...
taskkill /FI "WINDOWTITLE eq PaymentMonitor" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq savemod/payment_monitor.py" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq payment_monitor.py" /F >nul 2>&1
echo Payment Monitor to'xtatildi.

echo.
echo ------------------------------------
echo Barcha botlar to'xtatildi!
echo ------------------------------------
timeout /t 2 >nul
