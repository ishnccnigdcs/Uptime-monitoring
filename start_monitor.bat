@echo off
echo Запуск мониторинга сайтов...
cd /d "%~dp0"
set TELEGRAM_BOT_TOKEN=%TELEGRAM_BOT_TOKEN%
set TELEGRAM_CHAT_ID=%TELEGRAM_CHAT_ID%
set CHECK_INTERVAL=60
python run_monitor.py
pause
