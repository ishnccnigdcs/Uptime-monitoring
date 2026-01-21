"""
Уведомления в Telegram через aiogram.

Важно: это НЕ бот с обработкой команд. Здесь только отправка сообщений
из мониторинга (при падении/восстановлении сайта).
"""

import asyncio
import logging
from typing import Any, Dict, Optional

try:
    # aiogram v2
    from aiogram import Bot  # type: ignore
except Exception:  # pragma: no cover
    Bot = None  # type: ignore

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

        if Bot is None:
            logger.warning(
                "Пакет aiogram не установлен. Установите его, чтобы работали Telegram-уведомления."
            )
            self._bot: Optional[Any] = None
        else:
            self._bot = Bot(token=bot_token)

    async def _send_async(self, message: str) -> bool:
        if not self._bot or not self.chat_id:
            logger.warning("Telegram уведомления не настроены, сообщение не отправлено")
            return False
        try:
            # aiogram v2: параметры позиционные тоже поддерживаются, оставим именованные
            await self._bot.send_message(chat_id=self.chat_id, text=message)
            return True
        except Exception as e:  # pragma: no cover
            logger.error(f"Ошибка отправки в Telegram (aiogram): {e}")
            return False

    def send_message(self, message: str) -> bool:
        """Синхронная обёртка, чтобы вызывать из обычного кода."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram уведомления не настроены, сообщение не отправлено")
            return False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self._send_async(message))
            return True

        return asyncio.run(self._send_async(message))

    def send_notification(self, site_url: str, is_up: bool, details: Optional[Dict[str, Any]] = None) -> bool:
        if is_up:
            emoji = "✅"
            status_text = "восстановлен"
        else:
            emoji = "❌"
            status_text = "недоступен"

        message = f"{emoji} Сайт {status_text}\nURL: {site_url}"

        if details:
            if "response_time" in details and details["response_time"] is not None:
                message += f"\nВремя ответа: {details['response_time']:.2f}с"
            if "status_code" in details and details["status_code"] is not None:
                message += f"\nHTTP статус: {details['status_code']}"
            if "error_message" in details and details["error_message"]:
                message += f"\nОшибка: {details['error_message']}"

        return self.send_message(message)

