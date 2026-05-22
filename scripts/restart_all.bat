@echo off
cd /d "%~dp0"
call stop_bot.bat
call savemod\stop.bat
call update_vps.bat
call start_bot.bat
call savemod\start.bat
echo Hamma botlar yangilandi va qayta ishga tushdi.
timeout /t 3 >nul
