"""
Модуль мониторинга сайтов
Проверяет доступность сайтов каждую минуту
"""
import requests
import time
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SiteMonitor:
    def __init__(self, db_path='monitoring.db', telegram_bot=None):
        self.db_path = db_path
        self.telegram_bot = telegram_bot
        self.init_database()
        
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для хранения сайтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для истории проверок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id INTEGER,
                status_code INTEGER,
                response_time REAL,
                is_up INTEGER,
                error_message TEXT,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')
        
        # Таблица для статусов (последний известный статус)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS site_status (
                site_id INTEGER PRIMARY KEY,
                is_up INTEGER,
                last_check TIMESTAMP,
                consecutive_failures INTEGER DEFAULT 0,
                FOREIGN KEY (site_id) REFERENCES sites (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    
    def add_site(self, url, name=None):
        """Добавить сайт для мониторинга"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO sites (url, name) VALUES (?, ?)',
                (url, name or url)
            )
            conn.commit()
            site_id = cursor.lastrowid
            logger.info(f"Сайт добавлен: {url} (ID: {site_id})")
            return site_id
        except sqlite3.IntegrityError:
            logger.warning(f"Сайт уже существует: {url}")
            return None
        finally:
            conn.close()
    
    def remove_site(self, site_id):
        """Удалить сайт из мониторинга"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM sites WHERE id = ?', (site_id,))
        cursor.execute('DELETE FROM site_status WHERE site_id = ?', (site_id,))
        conn.commit()
        conn.close()
        logger.info(f"Сайт удален: ID {site_id}")
    
    def get_all_sites(self):
        """Получить список всех сайтов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, url, name, enabled FROM sites')
        sites = cursor.fetchall()
        conn.close()
        
        return [{'id': s[0], 'url': s[1], 'name': s[2], 'enabled': bool(s[3])} 
                for s in sites]
    
    def check_site(self, site_id, url):
        """Проверить доступность одного сайта"""
        start_time = time.time()
        is_up = False
        status_code = None
        error_message = None
        
        try:
            response = requests.get(
                url,
                timeout=10,
                allow_redirects=True,
                headers={'User-Agent': 'SiteMonitor/1.0'}
            )
            status_code = response.status_code
            response_time = time.time() - start_time
            
            # Считаем сайт доступным если статус 200-399
            is_up = 200 <= status_code < 400
            
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            error_message = "Timeout"
            is_up = False
        except requests.exceptions.ConnectionError:
            response_time = time.time() - start_time
            error_message = "Connection Error"
            is_up = False
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            is_up = False
        
        # Сохранить результат проверки
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO checks (site_id, status_code, response_time, is_up, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (site_id, status_code, response_time, int(is_up), error_message))
        
        # Обновить статус сайта
        cursor.execute('''
            SELECT is_up, consecutive_failures FROM site_status WHERE site_id = ?
        ''', (site_id,))
        
        old_status = cursor.fetchone()
        
        if old_status is None:
            # Первая проверка
            cursor.execute('''
                INSERT INTO site_status (site_id, is_up, last_check, consecutive_failures)
                VALUES (?, ?, ?, ?)
            ''', (site_id, int(is_up), datetime.now(), 0 if is_up else 1))
        else:
            old_is_up, old_failures = old_status
            consecutive_failures = 0 if is_up else (old_failures + 1 if not old_is_up else 1)
            
            cursor.execute('''
                UPDATE site_status 
                SET is_up = ?, last_check = ?, consecutive_failures = ?
                WHERE site_id = ?
            ''', (int(is_up), datetime.now(), consecutive_failures, site_id))
            
            # Отправить уведомление если статус изменился
            if old_is_up != is_up:
                site_info = self.get_site_info(site_id)
                if self.telegram_bot:
                    if is_up:
                        self.telegram_bot.send_message(
                            f"✅ Сайт восстановлен!\n"
                            f"URL: {url}\n"
                            f"Время ответа: {response_time:.2f}с\n"
                            f"Статус: {status_code}"
                        )
                    else:
                        self.telegram_bot.send_message(
                            f"❌ Сайт недоступен!\n"
                            f"URL: {url}\n"
                            f"Ошибка: {error_message or f'HTTP {status_code}'}\n"
                            f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
        
        conn.commit()
        conn.close()
        
        return {
            'is_up': is_up,
            'status_code': status_code,
            'response_time': response_time,
            'error_message': error_message
        }
    
    def get_site_info(self, site_id):
        """Получить информацию о сайте"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, url, name FROM sites WHERE id = ?', (site_id,))
        site = cursor.fetchone()
        
        if site:
            cursor.execute('''
                SELECT is_up, last_check, consecutive_failures 
                FROM site_status WHERE site_id = ?
            ''', (site_id,))
            status = cursor.fetchone()
            
            conn.close()
            return {
                'id': site[0],
                'url': site[1],
                'name': site[2],
                'is_up': status[0] if status else None,
                'last_check': status[1] if status else None,
                'consecutive_failures': status[2] if status else 0
            }
        
        conn.close()
        return None
    
    def run_check_cycle(self):
        """Выполнить проверку всех включенных сайтов"""
        sites = self.get_all_sites()
        enabled_sites = [s for s in sites if s['enabled']]
        
        logger.info(f"Начинаю проверку {len(enabled_sites)} сайтов")
        
        for site in enabled_sites:
            try:
                self.check_site(site['id'], site['url'])
            except Exception as e:
                logger.error(f"Ошибка при проверке {site['url']}: {e}")
        
        logger.info("Цикл проверки завершен")
    
    def start_monitoring(self, interval=60):
        """Запустить непрерывный мониторинг"""
        logger.info(f"Мониторинг запущен (интервал: {interval} секунд)")
        
        while True:
            try:
                self.run_check_cycle()
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Мониторинг остановлен пользователем")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")
                time.sleep(interval)
