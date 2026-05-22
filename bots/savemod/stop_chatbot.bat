@echo off
chcp 65001 >nul
echo Chat Bot to'xtatilmoqda...
taskkill /FI "WINDOWTITLE eq ChatBot" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq savemod/chatbot.py" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq chatbot.py" /F >nul 2>&1
echo Chat Bot to'xtatildi.
timeout /t 2 >nul
