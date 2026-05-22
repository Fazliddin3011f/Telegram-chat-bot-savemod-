@echo off
chcp 65001 >nul
cd /d "%~dp0\..\public-repo"

echo ====================================
echo   PUBLIC REPO GA PUSH
 echo ====================================
echo.
echo Target: https://github.com/Fazliddin3011f/Telegram-chat-bot-savemod-
echo.

if not exist .git (
  echo [XATO] Avval "sync_to_public.bat" ishlating!
  pause
  exit /b 1
)

echo [1/3] O'zgarishlar tekshirilmoqda...
git status --short

echo.
echo [2/3] Commit qilish...
set /p msg="Commit xabari: "
if "%msg%"=="" set msg="Update from dev"

git add .
git commit -m "%msg%"

echo.
echo [3/3] GitHub ga yuborilmoqda...
git push -f origin main

echo.
echo ====================================
echo   SUCCESS! Public repo yangilandi
echo ====================================
echo.
echo URL: https://github.com/Fazliddin3011f/Telegram-chat-bot-savemod-
echo.
pause
