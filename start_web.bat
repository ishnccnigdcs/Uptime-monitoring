@echo off
echo Запуск веб-интерфейса мониторинга сайтов...
cd /d "%~dp0"
set TELEGRAM_BOT_TOKEN=%TELEGRAM_BOT_TOKEN%
set TELEGRAM_CHAT_ID=%TELEGRAM_CHAT_ID%
python app.py
pause
