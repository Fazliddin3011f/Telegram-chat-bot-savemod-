@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Chat Bot ishga tushirilmoqda...
start /min "ChatBot" pythonw chatbot.py > logs\chatbot.log 2>&1
echo Chat Bot ishga tushdi.
timeout /t 2 >nul
