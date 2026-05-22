@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0backup.ps1"
if errorlevel 1 (
    echo Backup olishda xatolik bo'ldi.
    pause
    exit /b 1
)
timeout /t 2 >nul
