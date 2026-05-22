@echo off
REM SaveMod userbotni fon rejimida ishga tushiradi (terminal oynasi chiqmaydi)
cd /d "%~dp0"
if not exist ..\logs mkdir ..\logs
start "savemod" /MIN cmd /c "py main.py >> ..\logs\savemod.log 2>&1"
echo SaveMod fon rejimida ishga tushdi.
echo To'xtatish uchun stop.bat ni ishlatng.
timeout /t 3 >nul
