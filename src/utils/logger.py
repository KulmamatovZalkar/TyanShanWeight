"""
Модуль логирования для приложения TyanShanWeight.
Настройка ротации логов и форматирования.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(log_dir: str = "logs", log_level: int = logging.INFO) -> logging.Logger:
    """
    Настройка логгера с ротацией файлов.
    
    Args:
        log_dir: Директория для логов
        log_level: Уровень логирования
        
    Returns:
        Настроенный логгер
    """
    # Создаем директорию для логов если не существует
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Имя файла лога с датой
    log_filename = os.path.join(log_dir, f"tyanshan_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Формат логов
    log_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Получаем корневой логгер
    logger = logging.getLogger('TyanShanWeight')
    logger.setLevel(log_level)
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Обработчик для файла с ротацией (5 файлов по 5MB)
    file_handler = RotatingFileHandler(
        log_filename,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)
    
    logger.info("Логирование инициализировано")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Получить дочерний логгер.
    
    Args:
        name: Имя модуля
        
    Returns:
        Логгер для модуля
    """
    return logging.getLogger(f'TyanShanWeight.{name}')
