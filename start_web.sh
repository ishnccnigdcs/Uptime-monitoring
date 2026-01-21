#!/bin/bash
echo "Запуск веб-интерфейса мониторинга сайтов..."
cd "$(dirname "$0")"
export TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
export TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
python3 app.py
