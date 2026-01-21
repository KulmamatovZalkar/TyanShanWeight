"""
HTTP клиент для отправки данных на API (webhook).
Поддержка retry и фоновой отправки.
"""
import json
import threading
import time
import base64
import os
from typing import Optional, Callable
from queue import Queue

import requests

from .models import Weighing
from .database import Database
from ..utils.logger import get_logger
from ..utils.config import ApiConfig

logger = get_logger('api_client')


class ApiClient:
    """Клиент для отправки данных на API."""
    
    def __init__(self, config: ApiConfig, database: Database):
        """
        Инициализация API клиента.
        
        Args:
            config: Настройки API
            database: Экземпляр базы данных
        """
        self.config = config
        self.database = database
        self._send_queue: Queue = Queue()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._on_send_callback: Optional[Callable[[int, bool, str], None]] = None
    
    def set_callback(self, callback: Callable[[int, bool, str], None]) -> None:
        """
        Установить callback для уведомления о результате отправки.
        
        Args:
            callback: Функция (weighing_id, success, response)
        """
        self._on_send_callback = callback
    
    def start(self) -> None:
        """Запустить фоновый поток отправки."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("API клиент запущен")
        
        # Отправить неотправленные записи при старте
        self._queue_unsent()
    
    def stop(self) -> None:
        """Остановить фоновый поток отправки."""
        self._running = False
        self._send_queue.put(None)  # Сигнал для выхода из цикла
        
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        
        logger.info("API клиент остановлен")
    
    def queue_send(self, weighing: Weighing) -> None:
        """
        Добавить запись в очередь на отправку.
        
        Args:
            weighing: Запись для отправки
        """
        if weighing.id:
            self._send_queue.put(weighing.id)
            logger.debug(f"Добавлена в очередь запись #{weighing.id}")
    
    def _queue_unsent(self) -> None:
        """Добавить неотправленные записи в очередь."""
        unsent = self.database.get_unsent()
        for weighing in unsent:
            self._send_queue.put(weighing.id)
        
        if unsent:
            logger.info(f"Добавлено {len(unsent)} неотправленных записей в очередь")
    
    def _worker_loop(self) -> None:
        """Основной цикл фонового потока."""
        while self._running:
            try:
                weighing_id = self._send_queue.get(timeout=1)
                
                if weighing_id is None:  # Сигнал остановки
                    break
                
                weighing = self.database.get_by_id(weighing_id)
                if weighing and not weighing.sent:
                    success, response = self._send_with_retry(weighing)
                    
                    self.database.update_sent_status(weighing_id, success, response)
                    
                    if self._on_send_callback:
                        self._on_send_callback(weighing_id, success, response)
                        
            except Exception as e:
                if self._running:  # Игнорируем ошибки при остановке
                    logger.debug(f"Ожидание в очереди: {e}")
    def _encode_photo(self, path: str) -> Optional[str]:
        """Загрузить фото и закодировать в Base64."""
        if not path or not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Ошибка кодирования фото {path}: {e}")
            return None

    def _send_with_retry(self, weighing: Weighing) -> tuple[bool, str]:
        """
        Отправить данные с повторными попытками.
        
        Args:
            weighing: Запись для отправки
            
        Returns:
            (успех, ответ сервера или ошибка)
        """
        if not self.config.url:
            logger.warning("URL API не настроен")
            return False, "URL не настроен"
        
        # Подготовка данных с фото
        data = weighing.to_dict()
        
        # Кодируем фото
        if weighing.photos_tara:
            data['photos_tara_base64'] = [
                self._encode_photo(p) for p in weighing.photos_tara if p
            ]
            # Очищаем None
            data['photos_tara_base64'] = [p for p in data['photos_tara_base64'] if p]

        if weighing.photos_brutto:
            data['photos_brutto_base64'] = [
                self._encode_photo(p) for p in weighing.photos_brutto if p
            ]
            data['photos_brutto_base64'] = [p for p in data['photos_brutto_base64'] if p]

        # Интервалы повтора по ТЗ: 5s, 30s, 60s, 5min (300s)
        # Итого 5 попыток (1 начальная + 4 повтора)
        retry_intervals = [5, 30, 60, 300]
        max_attempts = len(retry_intervals) + 1
        
        for attempt in range(max_attempts):
            response_code = None
            response_text = ""
            success = False
            
            try:
                response = requests.post(
                    self.config.url,
                    json=data,
                    timeout=self.config.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                response_code = response.status_code
                response_text = response.text
                
                # Парсим ответ для проверки статуса duplicate
                try:
                    resp_json = response.json()
                    is_duplicate = resp_json.get('status') == 'duplicate'
                except:
                    is_duplicate = False

                if response.ok or is_duplicate:
                    if is_duplicate:
                        logger.info(f"Запись #{weighing.id} уже есть на сервере (duplicate)")
                    else:
                        logger.info(f"Запись #{weighing.id} успешно отправлена")
                    
                    success = True
                    # Логируем успех
                    self.database.log_webhook_attempt(weighing.id, True, response_code, response_text[:500])
                    return True, response_text[:500]
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"Ошибка отправки #{weighing.id}: {error_msg}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Таймаут при отправке #{weighing.id} (попытка {attempt + 1})")
                response_text = "Timeout"
            except requests.exceptions.ConnectionError:
                logger.warning(f"Ошибка соединения при отправке #{weighing.id} (попытка {attempt + 1})")
                response_text = "ConnectionError"
            except Exception as e:
                logger.error(f"Неизвестная ошибка при отправке #{weighing.id}: {e}")
                response_text = str(e)
                self.database.log_webhook_attempt(weighing.id, False, None, response_text)
                return False, str(e)
            
            # Логируем неудачную попытку
            if not success:
                self.database.log_webhook_attempt(weighing.id, False, response_code, response_text[:500])

            # Ожидание перед повторной попыткой
            if attempt < max_attempts - 1:
                delay = retry_intervals[attempt]
                logger.debug(f"Ожидание {delay}с перед следующей попыткой...")
                time.sleep(delay)
        
        return False, f"Не удалось отправить после {self.config.retry_count} попыток"
    
    def send_immediate(self, weighing: Weighing) -> tuple[bool, str]:
        """
        Синхронная отправка (для тестирования).
        
        Args:
            weighing: Запись для отправки
            
        Returns:
            (успех, ответ)
        """
        return self._send_with_retry(weighing)
