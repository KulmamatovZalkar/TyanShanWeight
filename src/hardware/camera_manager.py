"""
Модуль работы с IP-камерами.
Захват кадров с HLS/RTSP потоков.
"""
import os
import cv2
import time
import threading
from datetime import datetime
from typing import Optional, List, Callable
from dataclasses import dataclass

from ..utils.logger import get_logger

logger = get_logger('camera')


@dataclass
class CameraConfig:
    """Конфигурация камеры."""
    name: str
    url: str
    enabled: bool = True


class CameraManager:
    """
    Менеджер IP-камер.
    Захват кадров с нескольких камер.
    """
    
    def __init__(self, images_dir: str = "images"):
        """
        Инициализация менеджера камер.
        
        Args:
            images_dir: Директория для сохранения изображений
        """
        self.images_dir = images_dir
        self.cameras: List[CameraConfig] = []
        
        # Создаем директорию если не существует
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
            logger.info(f"Создана директория для изображений: {images_dir}")
    
    def add_camera(self, name: str, url: str, enabled: bool = True) -> None:
        """
        Добавить камеру.
        
        Args:
            name: Имя камеры
            url: URL потока (HLS, RTSP)
            enabled: Включена ли камера
        """
        camera = CameraConfig(name=name, url=url, enabled=enabled)
        self.cameras.append(camera)
        logger.info(f"Добавлена камера: {name} -> {url}")
    
    def remove_camera(self, index: int) -> bool:
        """
        Удалить камеру по индексу.
        
        Args:
            index: Индекс камеры
            
        Returns:
            True если удалено успешно
        """
        if 0 <= index < len(self.cameras):
            removed = self.cameras.pop(index)
            logger.info(f"Удалена камера: {removed.name}")
            return True
        return False
    
    def set_cameras(self, cameras: List[dict]) -> None:
        """
        Установить список камер из конфигурации.
        
        Args:
            cameras: Список словарей с параметрами камер
        """
        self.cameras = [
            CameraConfig(
                name=c.get('name', f'Камера {i+1}'),
                url=c.get('url', ''),
                enabled=c.get('enabled', True)
            )
            for i, c in enumerate(cameras)
        ]
        logger.info(f"Загружено {len(self.cameras)} камер")
    
    def get_cameras_config(self) -> List[dict]:
        """Получить конфигурацию камер для сохранения."""
        return [
            {'name': c.name, 'url': c.url, 'enabled': c.enabled}
            for c in self.cameras
        ]
    
    def capture_frame(self, camera: CameraConfig, timeout: float = 10.0) -> Optional[str]:
        """
        Захватить кадр с камеры.
        
        Args:
            camera: Конфигурация камеры
            timeout: Таймаут подключения
            
        Returns:
            Путь к сохраненному изображению или None
        """
        if not camera.enabled or not camera.url:
            return None
        
        logger.info(f"Захват кадра с камеры: {camera.name}")
        
        try:
            # Открываем видеопоток
            cap = cv2.VideoCapture(camera.url)
            
            if not cap.isOpened():
                logger.error(f"Не удалось открыть поток: {camera.url}")
                return None
            
            # Даем время на буферизацию
            time.sleep(1)
            
            # Читаем несколько кадров чтобы получить актуальный
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.2)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                logger.error(f"Не удалось прочитать кадр с камеры: {camera.name}")
                return None
            
            # Генерируем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_name = "".join(c for c in camera.name if c.isalnum() or c in ('_', '-'))
            filename = f"{timestamp}_{safe_name}.jpg"
            filepath = os.path.join(self.images_dir, filename)
            
            # Сохраняем изображение
            cv2.imwrite(filepath, frame)
            logger.info(f"Сохранено изображение: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Ошибка захвата кадра с {camera.name}: {e}")
            return None
    
    def capture_all(self, car_number: str = "") -> List[str]:
        """
        Захватить кадры со всех активных камер.
        
        Args:
            car_number: Госномер для именования файлов
            
        Returns:
            Список путей к сохраненным изображениям
        """
        saved_files = []
        
        for camera in self.cameras:
            if camera.enabled:
                filepath = self.capture_frame(camera)
                if filepath:
                    saved_files.append(filepath)
        
        logger.info(f"Захвачено {len(saved_files)} изображений")
        return saved_files
    
    def capture_all_async(self, car_number: str = "", 
                          callback: Optional[Callable[[List[str]], None]] = None) -> None:
        """
        Асинхронный захват кадров со всех камер.
        
        Args:
            car_number: Госномер
            callback: Функция обратного вызова с результатами
        """
        def _capture():
            result = self.capture_all(car_number)
            if callback:
                callback(result)
        
        thread = threading.Thread(target=_capture, daemon=True)
        thread.start()
    
    def test_camera(self, url: str) -> tuple[bool, str]:
        """
        Проверить доступность камеры.
        
        Args:
            url: URL потока
            
        Returns:
            (успех, сообщение)
        """
        try:
            logger.info(f"Тестирование камеры: {url}")
            
            cap = cv2.VideoCapture(url)
            
            if not cap.isOpened():
                return False, "Не удалось открыть поток"
            
            # Пробуем прочитать кадр
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                height, width = frame.shape[:2]
                return True, f"OK: {width}x{height}"
            else:
                return False, "Не удалось прочитать кадр"
                
        except Exception as e:
            return False, f"Ошибка: {e}"
