"""
Модуль управления конфигурацией приложения.
Загрузка, сохранение и валидация настроек.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from .logger import get_logger

logger = get_logger('config')


@dataclass
class SerialConfig:
    """Настройки COM-порта."""
    port: str = "COM1"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"  # N, E, O
    stopbits: float = 1  # 1, 1.5, 2
    timeout: float = 1.0


@dataclass
class ApiConfig:
    """Настройки API."""
    url: str = "https://your-domain.com/api/v1/transactions/webhook/weighing/"
    timeout: int = 30
    retry_count: int = 3
    retry_delay: int = 5


@dataclass
class AppConfig:
    """Главная конфигурация приложения."""
    serial: SerialConfig = field(default_factory=SerialConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    factory_id: str = ""  # UUID завода в AccountingDRF
    factory_name: str = ""  # Название завода (для UI)
    fractions: List[str] = field(default_factory=lambda: [
        "Щебень 5-20",
        "Щебень 20-40",
        "Щебень 40-70",
        "Песок",
        "ПГС",
        "Отсев"
    ])
    cameras: List[dict] = field(default_factory=lambda: [
        {"name": "Камера 1 (въезд)", "url": "https://stream.kt.kg:5443/live/camera25.m3u8", "enabled": True},
        {"name": "Камера 2 (весы)", "url": "https://stream.kt.kg:5443/live/camera16.m3u8", "enabled": True},
        {"name": "Камера 3 (выезд)", "url": "https://stream.kt.kg:5443/live/camera12.m3u8", "enabled": True},
        {"name": "Камера 4 (общий)", "url": "https://stream.kt.kg:5443/live/camera19.m3u8", "enabled": True},
    ])
    weight_stable_count: int = 5  # Количество стабильных значений
    weight_stable_threshold: float = 10.0  # Порог стабильности в кг
    db_path: str = "weighings.db"
    images_path: str = r"C:\Weights\images"
    weight_pattern: str = r"[+-]?\s*(\d+\.?\d*)\s*(?:kg|кг)?"  # Регулярка для парсинга веса
    capture_on_tara: bool = True  # Захват кадров при фиксации тары
    capture_on_brutto: bool = True  # Захват кадров при фиксации брутто


class ConfigManager:
    """Менеджер конфигурации."""
    
    DEFAULT_CONFIG_PATH = "config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация менеджера конфигурации.
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self.load()
    
    def load(self) -> AppConfig:
        """
        Загрузить конфигурацию из файла.
        
        Returns:
            Загруженная или дефолтная конфигурация
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = AppConfig(
                    serial=SerialConfig(**data.get('serial', {})),
                    api=ApiConfig(**data.get('api', {})),
                    factory_id=data.get('factory_id', ''),
                    factory_name=data.get('factory_name', ''),
                    fractions=data.get('fractions', AppConfig().fractions),
                    cameras=data.get('cameras', AppConfig().cameras),
                    weight_stable_count=data.get('weight_stable_count', 5),
                    weight_stable_threshold=data.get('weight_stable_threshold', 10.0),
                    db_path=data.get('db_path', 'weighings.db'),
                    images_path=data.get('images_path', r"C:\Weights\images"),
                    weight_pattern=data.get('weight_pattern', AppConfig().weight_pattern),
                    capture_on_tara=data.get('capture_on_tara', True),
                    capture_on_brutto=data.get('capture_on_brutto', True)
                )
                logger.info(f"Конфигурация загружена из {self.config_path}")
                return config
                
            except Exception as e:
                logger.warning(f"Ошибка загрузки конфигурации: {e}. Используются значения по умолчанию.")
                return AppConfig()
        else:
            logger.info("Файл конфигурации не найден. Создаем с значениями по умолчанию.")
            config = AppConfig()
            self.save(config)
            return config
    
    def save(self, config: Optional[AppConfig] = None) -> bool:
        """
        Сохранить конфигурацию в файл.
        
        Args:
            config: Конфигурация для сохранения
            
        Returns:
            Успешность сохранения
        """
        if config:
            self.config = config
        
        try:
            data = {
                'serial': asdict(self.config.serial),
                'api': asdict(self.config.api),
                'factory_id': self.config.factory_id,
                'factory_name': self.config.factory_name,
                'fractions': self.config.fractions,
                'cameras': self.config.cameras,
                'weight_stable_count': self.config.weight_stable_count,
                'weight_stable_threshold': self.config.weight_stable_threshold,
                'db_path': self.config.db_path,
                'images_path': self.config.images_path,
                'weight_pattern': self.config.weight_pattern,
                'capture_on_tara': self.config.capture_on_tara,
                'capture_on_brutto': self.config.capture_on_brutto
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Конфигурация сохранена в {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def update_serial(self, **kwargs) -> None:
        """Обновить настройки COM-порта."""
        for key, value in kwargs.items():
            if hasattr(self.config.serial, key):
                setattr(self.config.serial, key, value)
        self.save()
    
    def update_api(self, **kwargs) -> None:
        """Обновить настройки API."""
        for key, value in kwargs.items():
            if hasattr(self.config.api, key):
                setattr(self.config.api, key, value)
        self.save()
