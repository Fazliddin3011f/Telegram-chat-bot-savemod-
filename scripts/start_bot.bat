@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
start "scan-bot" /MIN cmd /c "py bot.py >> logs\bot.log 2>&1"
echo Scan bot ishga tushdi.
timeout /t 2 >nul
