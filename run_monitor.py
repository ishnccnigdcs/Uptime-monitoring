"""
Скрипт для запуска мониторинга в отдельном процессе
"""
import os
import sys
from monitor import SiteMonitor
from notifier import TelegramNotifier
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Главная функция для запуска мониторинга"""
    # Получить настройки из переменных окружения
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))
    
    # Инициализация Telegram бота
    telegram_bot = None
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        telegram_bot = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        logger.info("Telegram бот инициализирован")
    else:
        logger.warning("Telegram бот не настроен. Установите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")
    
    # Инициализация монитора
    monitor = SiteMonitor(telegram_bot=telegram_bot)
    
    # Отправить сообщение о запуске
    if telegram_bot:
        telegram_bot.send_message("🚀 Система мониторинга сайтов запущена!")
    
    # Запустить мониторинг
    try:
        monitor.start_monitoring(interval=CHECK_INTERVAL)
    except KeyboardInterrupt:
        logger.info("Остановка мониторинга...")
        if telegram_bot:
            telegram_bot.send_message("⏹ Система мониторинга остановлена")
        sys.exit(0)


if __name__ == '__main__':
    main()
