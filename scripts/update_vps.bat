@echo off
cd /d "%~dp0"
call backup_vps.bat
"C:\Program Files\Git\cmd\git.exe" pull
if errorlevel 1 (
    echo Git pull xato berdi.
    pause
    exit /b 1
)
echo Kod yangilandi.
timeout /t 2 >nul
