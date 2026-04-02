import sqlite3
import json
from typing import List, Optional
from contextlib import contextmanager

from .models import Weighing
from ..utils.logger import get_logger

logger = get_logger('database')


class Database:
    """Класс для работы с SQLite базой данных."""

    def __init__(self, db_path: str = "weighings.db"):
        """
        Инициализация базы данных.
        
        Args:
            db_path: Путь к файлу базы данных
        """
        self.db_path = db_path
        self._create_tables()
    
    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения с БД."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка БД: {e}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self) -> None:
        """Создание таблиц при первом запуске."""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS weighings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    datetime TEXT NOT NULL,
                    car_number TEXT NOT NULL,
                    tara REAL NOT NULL,
                    brutto REAL NOT NULL,
                    netto REAL NOT NULL,
                    fio TEXT,
                    fraction TEXT,
                    sent INTEGER DEFAULT 0,
                    api_response TEXT,
                    photos_tara TEXT,
                    photos_brutto TEXT,
                    notes TEXT
                )
            ''')
            
            # Индекс для быстрого поиска неотправленных записей
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_weighings_sent 
                ON weighings(sent)
            ''')
            
            # Таблица логов вебхуков
            conn.execute('''
                CREATE TABLE IF NOT EXISTS webhook_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    weighing_id INTEGER,
                    datetime TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    response_code INTEGER,
                    response_body TEXT,
                    FOREIGN KEY(weighing_id) REFERENCES weighings(id)
                )
            ''')
            
            # Миграции
            try:
                conn.execute('ALTER TABLE weighings ADD COLUMN photos_tara TEXT')
            except sqlite3.OperationalError:
                pass
                
            try:
                conn.execute('ALTER TABLE weighings ADD COLUMN photos_brutto TEXT')
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute('ALTER TABLE weighings ADD COLUMN notes TEXT')
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute('ALTER TABLE weighings ADD COLUMN counterparty_id TEXT')
            except sqlite3.OperationalError:
                pass

            try:
                conn.execute('ALTER TABLE weighings ADD COLUMN counterparty_name TEXT')
            except sqlite3.OperationalError:
                pass

            logger.info(f"База данных инициализирована: {self.db_path}")
    
    def log_webhook_attempt(self, weighing_id: int, success: bool, response_code: Optional[int], response_body: str) -> None:
        """
        Залогировать попытку отправки вебхука.
        """
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    INSERT INTO webhook_logs (weighing_id, datetime, success, response_code, response_body)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    weighing_id,
                    datetime.now().isoformat(),
                    1 if success else 0,
                    response_code,
                    response_body
                ))
        except Exception as e:
            logger.error(f"Ошибка логирования вебхука: {e}")

    def save(self, weighing: Weighing) -> int:
        """
        Сохранить запись взвешивания (Создание или Обновление).
        """
        with self._get_connection() as conn:
            if weighing.id is not None:
                # Обновление существующей записи
                conn.execute('''
                    UPDATE weighings SET
                        datetime = ?, car_number = ?, tara = ?, brutto = ?, netto = ?,
                        fio = ?, fraction = ?, sent = ?, api_response = ?,
                        photos_tara = ?, photos_brutto = ?, notes = ?,
                        counterparty_id = ?, counterparty_name = ?
                    WHERE id = ?
                ''', (
                    weighing.datetime, weighing.car_number, weighing.tara, weighing.brutto, weighing.netto,
                    weighing.fio, weighing.fraction, int(weighing.sent), weighing.api_response,
                    json.dumps(weighing.photos_tara), json.dumps(weighing.photos_brutto), weighing.notes,
                    weighing.counterparty_id, weighing.counterparty_name,
                    weighing.id
                ))
                logger.info(f"Обновлена запись #{weighing.id}: {weighing.car_number}")
            else:
                # Новая запись
                cursor = conn.execute('''
                    INSERT INTO weighings
                    (datetime, car_number, tara, brutto, netto, fio, fraction, sent, api_response, photos_tara, photos_brutto, notes, counterparty_id, counterparty_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    weighing.datetime,
                    weighing.car_number,
                    weighing.tara,
                    weighing.brutto,
                    weighing.netto,
                    weighing.fio,
                    weighing.fraction,
                    int(weighing.sent),
                    weighing.api_response,
                    json.dumps(weighing.photos_tara),
                    json.dumps(weighing.photos_brutto),
                    weighing.notes,
                    weighing.counterparty_id,
                    weighing.counterparty_name,
                ))
                weighing.id = cursor.lastrowid
                logger.info(f"Сохранена новая запись #{weighing.id}: {weighing.car_number}")
            
            return weighing.id

    def get_incomplete_weighings(self) -> list[Weighing]:
        """
        Получить список незавершенных взвешиваний (где брутто = 0).
        """
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM weighings 
                WHERE brutto = 0 
                ORDER BY datetime DESC
            ''')
            rows = cursor.fetchall()
            return [self._row_to_weighing(row) for row in rows]

    def get_incomplete_by_number(self, car_number: str) -> Optional[Weighing]:
        """Найти незавершенное взвешивание по номеру."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM weighings 
                WHERE brutto = 0 AND car_number = ?
                ORDER BY datetime DESC LIMIT 1
            ''', (car_number,))
            row = cursor.fetchone()
            return self._row_to_weighing(row) if row else None
    
    def delete_weighing(self, weighing_id: int) -> bool:
        """Удалить запись взвешивания."""
        try:
            with self._get_connection() as conn:
                conn.execute('DELETE FROM weighings WHERE id = ?', (weighing_id,))
            logger.info(f"Удалена запись #{weighing_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления записи #{weighing_id}: {e}")
            return False

    def update_sent_status(self, weighing_id: int, sent: bool, api_response: str = "") -> bool:
        """Обновить статус отправки."""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    UPDATE weighings 
                    SET sent = ?, api_response = ?
                    WHERE id = ?
                ''', (int(sent), api_response, weighing_id))
                
            logger.info(f"Обновлен статус записи #{weighing_id}: sent={sent}")
            return True
        except Exception as e:
            logger.error(f"Ошибка обновления статуса: {e}")
            return False
    
    def get_unsent(self) -> List[Weighing]:
        """Получить неотправленные записи."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM weighings WHERE sent = 0 ORDER BY id
            ''')
            rows = cursor.fetchall()
            return [self._row_to_weighing(row) for row in rows]
    
    def get_by_id(self, weighing_id: int) -> Optional[Weighing]:
        """Получить запись по ID."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM weighings WHERE id = ?
            ''', (weighing_id,))
            row = cursor.fetchone()
            return self._row_to_weighing(row) if row else None
    
    def get_recent(self, limit: int = 50) -> List[Weighing]:
        """Получить последние записи."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM weighings ORDER BY id DESC LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
            return [self._row_to_weighing(row) for row in rows]

    def get_filtered(self, start_date: Optional[str] = None, end_date: Optional[str] = None, car_number: Optional[str] = None) -> List[Weighing]:
        """
        Получить записи с фильтрацией.
        
        Args:
            start_date: Начальная дата (ISO)
            end_date: Конечная дата (ISO)
            car_number: Госномер (частичное совпадение)
        """
        query = "SELECT * FROM weighings WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND datetime >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND datetime <= ?"
            params.append(end_date)
            
        if car_number:
            query += " AND car_number LIKE ?"
            params.append(f"%{car_number}%")
            
        query += " ORDER BY id DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_weighing(row) for row in rows]

    def _row_to_weighing(self, row: sqlite3.Row) -> Weighing:
        """Преобразовать строку БД в объект Weighing."""
        photos_tara = []
        if 'photos_tara' in row.keys() and row['photos_tara']:
            try:
                photos_tara = json.loads(row['photos_tara'])
            except:
                pass
                
        photos_brutto = []
        if 'photos_brutto' in row.keys() and row['photos_brutto']:
            try:
                photos_brutto = json.loads(row['photos_brutto'])
            except:
                pass
        
        notes = ""
        if 'notes' in row.keys() and row['notes']:
            notes = row['notes']

        counterparty_id = ""
        if 'counterparty_id' in row.keys() and row['counterparty_id']:
            counterparty_id = row['counterparty_id']
        counterparty_name = ""
        if 'counterparty_name' in row.keys() and row['counterparty_name']:
            counterparty_name = row['counterparty_name']

        return Weighing(
            id=row['id'],
            datetime=row['datetime'],
            car_number=row['car_number'],
            tara=row['tara'],
            brutto=row['brutto'],
            netto=row['netto'],
            fio=row['fio'] or "",
            fraction=row['fraction'] or "",
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            notes=notes,
            sent=bool(row['sent']),
            api_response=row['api_response'] or "",
            photos_tara=photos_tara,
            photos_brutto=photos_brutto
        )
