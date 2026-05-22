@echo off
cd /d "%~dp0"
call stop_bot.bat
call start_bot.bat
echo Scan bot qayta ishga tushdi.
timeout /t 2 >nul
