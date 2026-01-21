#!/bin/bash
echo "Запуск мониторинга сайтов..."
cd "$(dirname "$0")"
export TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-""}
export TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-""}
export CHECK_INTERVAL=${CHECK_INTERVAL:-60}
python3 run_monitor.py
