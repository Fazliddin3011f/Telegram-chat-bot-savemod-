@echo off
REM Fon rejimida ishlayotgan SaveMod main.py jarayonini to'xtatadi
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo SaveMod to'xtatildi.
timeout /t 2 >nul
