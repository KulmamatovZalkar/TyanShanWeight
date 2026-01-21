"""
Модуль стабилизации веса (антидребезг).
Определяет стабильное значение веса при колебаниях.
"""
from collections import deque
from typing import Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger('weight_stabilizer')


class WeightStabilizer:
    """
    Стабилизатор значений веса.
    
    Анализирует последние N значений и определяет,
    когда вес стабилизировался (отклонение меньше порога).
    """
    
    def __init__(self, buffer_size: int = 5, threshold: float = 10.0):
        """
        Инициализация стабилизатора.
        
        Args:
            buffer_size: Количество значений для анализа
            threshold: Максимальное отклонение для стабильного веса (кг)
        """
        self.buffer_size = buffer_size
        self.threshold = threshold
        self._buffer: deque = deque(maxlen=buffer_size)
        self._last_stable_value: Optional[float] = None
    
    def add_value(self, weight: float) -> None:
        """
        Добавить новое значение веса.
        
        Args:
            weight: Значение веса в кг
        """
        self._buffer.append(weight)
    
    def is_stable(self) -> bool:
        """
        Проверить, стабилен ли вес.
        
        Returns:
            True если буфер заполнен и отклонение меньше порога
        """
        if len(self._buffer) < self.buffer_size:
            return False
        
        min_val = min(self._buffer)
        max_val = max(self._buffer)
        deviation = max_val - min_val
        
        return deviation <= self.threshold
    
    def get_stable_value(self) -> Optional[float]:
        """
        Получить стабильное значение веса.
        
        Returns:
            Среднее значение если стабильно, иначе None
        """
        if self.is_stable():
            stable_value = sum(self._buffer) / len(self._buffer)
            self._last_stable_value = stable_value
            return round(stable_value, 1)
        return None
    
    def get_current_value(self) -> Tuple[Optional[float], bool]:
        """
        Получить текущее значение и статус стабильности.
        
        Returns:
            (текущее значение, стабильно ли)
        """
        if not self._buffer:
            return None, False
        
        current = self._buffer[-1]
        is_stable = self.is_stable()
        
        if is_stable:
            return round(sum(self._buffer) / len(self._buffer), 1), True
        else:
            return round(current, 1), False
    
    def clear(self) -> None:
        """Очистить буфер."""
        self._buffer.clear()
        self._last_stable_value = None
    
    def configure(self, buffer_size: int = None, threshold: float = None) -> None:
        """
        Обновить настройки стабилизатора.
        
        Args:
            buffer_size: Новый размер буфера
            threshold: Новый порог стабильности
        """
        if buffer_size is not None:
            self.buffer_size = buffer_size
            # Создаем новый буфер с сохранением последних значений
            old_values = list(self._buffer)
            self._buffer = deque(maxlen=buffer_size)
            self._buffer.extend(old_values[-buffer_size:])
        
        if threshold is not None:
            self.threshold = threshold
    
    @property
    def fill_level(self) -> float:
        """Уровень заполнения буфера (0.0 - 1.0)."""
        return len(self._buffer) / self.buffer_size if self.buffer_size > 0 else 0.0
    
    def get_deviation(self) -> Optional[float]:
        """
        Получить текущее отклонение значений.
        
        Returns:
            Разница между max и min значениями
        """
        if len(self._buffer) < 2:
            return None
        
        return max(self._buffer) - min(self._buffer)
