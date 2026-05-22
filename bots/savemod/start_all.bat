@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ====================================
echo   BARCHA BOTLANI ISHGA TUSHIRISH
echo ====================================
echo.

:: Logs papkasini yaratish
if not exist logs mkdir logs

echo [1/4] SaveMod Userbot ishga tushirilmoqda...
start /min "SaveMod" pythonw main.py > logs\savemod.log 2>&1

echo [2/4] Chat Bot ishga tushirilmoqda...
start /min "ChatBot" pythonw chatbot.py > logs\chatbot.log 2>&1

echo [3/4] Payment Monitor ishga tushirilmoqda...
start /min "PaymentMonitor" pythonw payment_monitor.py > logs\payment_monitor.log 2>&1

echo [4/4] Asosiy Bot (agar alohida ishga tushirilsa)...
echo.
echo ------------------------------------
echo Barcha botlar ishga tushdi!
echo Logs: logs\ papkasida
echo.
echo Tekshirish uchun:
echo   - SaveMod: type logs\savemod.log
echo   - ChatBot: type logs\chatbot.log
echo   - Payment: type logs\payment_monitor.log
echo ------------------------------------
timeout /t 3 >nul
