"""
Протоколы парсинга данных с разных моделей весов.
"""
import re
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger('scale_protocols')


class ScaleProtocol(ABC):
    """Базовый класс протокола весов."""
    
    @abstractmethod
    def parse(self, data: str) -> Optional[float]:
        """
        Парсинг строки данных с весов.
        
        Args:
            data: Сырые данные с весов
            
        Returns:
            Вес в кг или None при ошибке
        """
        pass
    
    @abstractmethod
    def is_stable(self, data: str) -> bool:
        """
        Проверить, стабилен ли вес (не в движении).
        
        Args:
            data: Сырые данные с весов
            
        Returns:
            True если вес стабилен
        """
        pass


class GenericProtocol(ScaleProtocol):
    """
    Универсальный протокол с настраиваемым regex.
    
    Поддерживаемые форматы:
    - "+  1234.5 kg"
    - "1234.5"
    - "ST,GS,+001234.5 kg"
    - "   12345 кг"
    """
    
    # Маркеры нестабильности веса (в движении)
    UNSTABLE_MARKERS = ['US', 'unstable', 'motion', 'движ']
    
    def __init__(self, pattern: str = r"[+-]?\s*(\d+\.?\d*)\s*(?:kg|кг)?"):
        """
        Инициализация протокола.
        
        Args:
            pattern: Регулярное выражение для извлечения веса.
                     Должно содержать группу захвата для числа.
        """
        self.pattern = pattern
        self._compiled = re.compile(pattern, re.IGNORECASE)
    
    def parse(self, data: str) -> Optional[float]:
        """Извлечь значение веса из строки."""
        if not data:
            return None
        
        try:
            # Убираем непечатаемые символы
            clean_data = data.strip()
            
            match = self._compiled.search(clean_data)
            if match:
                weight_str = match.group(1)
                weight = float(weight_str)
                
                # Проверяем знак
                if clean_data.startswith('-'):
                    weight = -weight
                
                logger.debug(f"Распознан вес: {weight} кг из '{clean_data}'")
                return weight
            else:
                logger.warning(f"Не удалось распознать вес из: '{clean_data}'")
                return None
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Ошибка парсинга веса: {e}")
            return None
    
    def is_stable(self, data: str) -> bool:
        """Проверить стабильность веса."""
        if not data:
            return False
        
        data_lower = data.lower()
        for marker in self.UNSTABLE_MARKERS:
            if marker.lower() in data_lower:
                return False
        
        # Если нет маркеров нестабильности, считаем стабильным
        # Также проверяем наличие маркера стабильности
        stable_markers = ['st', 'stable', 'gs']  # GS = Gross Stable
        for marker in stable_markers:
            if marker in data_lower:
                return True
        
        # По умолчанию считаем стабильным
        return True


class CASProtocol(ScaleProtocol):
    """
    Протокол для весов CAS.
    
    Формат: ST,GS,+    1234.5 kg
    ST = Status (ST=Stable, US=Unstable)
    GS = Gross
    """
    
    def __init__(self):
        self._pattern = re.compile(r'([SU][TS]),\s*([GN][SET]),\s*([+-]?)\s*(\d+\.?\d*)\s*(kg|кг)?', re.IGNORECASE)
    
    def parse(self, data: str) -> Optional[float]:
        """Извлечь вес из формата CAS."""
        if not data:
            return None
        
        try:
            match = self._pattern.search(data.strip())
            if match:
                sign = match.group(3)
                weight = float(match.group(4))
                
                if sign == '-':
                    weight = -weight
                
                return weight
            return None
        except Exception as e:
            logger.warning(f"Ошибка парсинга CAS: {e}")
            return None
    
    def is_stable(self, data: str) -> bool:
        """Проверить стабильность по маркеру ST/US."""
        if not data:
            return False
        
        return 'ST,' in data.upper() or 'ST ' in data.upper()


def create_protocol(protocol_type: str = "generic", pattern: str = None) -> ScaleProtocol:
    """
    Фабрика протоколов.
    
    Args:
        protocol_type: Тип протокола ("generic", "cas")
        pattern: Кастомный regex паттерн для generic протокола
        
    Returns:
        Экземпляр протокола
    """
    if protocol_type.lower() == "cas":
        return CASProtocol()
    else:
        return GenericProtocol(pattern) if pattern else GenericProtocol()
