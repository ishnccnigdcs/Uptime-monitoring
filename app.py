"""
FastAPI веб-приложение для управления мониторингом
"""
import logging
import os
import sqlite3
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

from monitor import SiteMonitor
from notifier import TelegramNotifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Site Monitor", version="1.0.0")

# Статика и шаблоны
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    templates = None

# Инициализация монитора
monitor = SiteMonitor()

# Инициализация Telegram бота (если настроен)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

telegram_bot = None
if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
    try:
        telegram_bot = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
        monitor.telegram_bot = telegram_bot
        logger.info("Telegram бот (aiogram) инициализирован")
    except Exception as e:
        logger.warning(f"Не удалось инициализировать Telegram бот: {e}. Продолжаем без уведомлений.")
else:
    logger.warning(
        "Telegram бот не настроен (установите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID)"
    )


# Pydantic модели для валидации данных
class SiteCreate(BaseModel):
    url: str
    name: str = ""


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Any:
    """Главная страница"""
    try:
        if templates is None:
            raise HTTPException(status_code=500, detail="Шаблоны не найдены")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Ошибка при загрузке главной страницы: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


@app.get("/api/sites")
def get_sites() -> List[Dict[str, Any]]:
    """Получить список всех сайтов"""
    try:
        sites = monitor.get_all_sites()

        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()

        for site in sites:
            cursor.execute(
                """
                SELECT is_up, last_check, consecutive_failures 
                FROM site_status WHERE site_id = ?
            """,
                (site["id"],),
            )
            status = cursor.fetchone()

            if status:
                site["is_up"] = bool(status[0])
                site["last_check"] = status[1]
                site["consecutive_failures"] = status[2]
            else:
                site["is_up"] = None
                site["last_check"] = None
                site["consecutive_failures"] = 0

        conn.close()
        return sites
    except Exception as e:
        logger.error(f"Ошибка при получении списка сайтов: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


@app.post("/api/sites")
def add_site(data: SiteCreate) -> Dict[str, Any]:
    """Добавить новый сайт"""
    url = data.url.strip()
    name = data.name.strip() if data.name else ""

    if not url:
        raise HTTPException(status_code=400, detail="URL обязателен")

    try:
        site_id = monitor.add_site(url, name)
        if site_id:
            return {"success": True, "site_id": site_id}
        raise HTTPException(status_code=400, detail="Сайт уже существует")
    except Exception as e:
        logger.error(f"Ошибка при добавлении сайта: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


@app.delete("/api/sites/{site_id}")
def delete_site(site_id: int) -> Dict[str, Any]:
    """Удалить сайт"""
    monitor.remove_site(site_id)
    return {"success": True}


@app.post("/api/sites/{site_id}/check")
def check_site_now(site_id: int) -> Dict[str, Any]:
    """Проверить сайт немедленно"""
    site_info = monitor.get_site_info(site_id)
    if not site_info:
        raise HTTPException(status_code=404, detail="Сайт не найден")

    result = monitor.check_site(site_id, site_info["url"])
    return result


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    """Получить статистику"""
    try:
        conn = sqlite3.connect(monitor.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM sites")
        total_sites = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM site_status WHERE is_up = 1")
        up_sites = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM site_status WHERE is_up = 0")
        down_sites = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT s.url, c.is_up, c.checked_at, c.response_time, c.error_message
            FROM checks c
            JOIN sites s ON c.site_id = s.id
            ORDER BY c.checked_at DESC
            LIMIT 10
        """
        )
        recent_checks = cursor.fetchall()

        conn.close()

        return {
            "total_sites": total_sites,
            "up_sites": up_sites,
            "down_sites": down_sites,
            "recent_checks": [
                {
                    "url": r[0],
                    "is_up": bool(r[1]),
                    "checked_at": r[2],
                    "response_time": r[3],
                    "error_message": r[4],
                }
                for r in recent_checks
            ],
        }
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=False)
