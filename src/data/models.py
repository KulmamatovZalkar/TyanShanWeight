"""
Модели данных для приложения взвешивания.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Weighing:
    """Модель записи взвешивания."""
    
    id: Optional[int] = None
    datetime: str = field(default_factory=lambda: datetime.now().isoformat())
    car_number: str = ""
    tara: float = 0.0
    brutto: float = 0.0
    netto: float = 0.0
    fio: str = ""
    fraction: str = ""
    counterparty_id: str = ""
    counterparty_name: str = ""
    notes: str = ""
    sent: bool = False
    api_response: str = ""
    photos_tara: list = field(default_factory=list)  # Список путей к фото тары
    photos_brutto: list = field(default_factory=list)  # Список путей к фото брутто
    
    def calculate_netto(self) -> float:
        """Вычислить нетто = брутто - тара."""
        if self.brutto > 0 and self.tara > 0:
            self.netto = self.brutto - self.tara
        return self.netto
    
    def is_complete(self) -> bool:
        """Проверить, что все обязательные поля заполнены."""
        return all([
            self.car_number.strip(),
            self.tara > 0,
            self.brutto > 0,
            self.brutto >= self.tara  # Брутто не может быть меньше тары
        ])
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для API."""
        data = {
            'id': self.id,
            'datetime': self.datetime,
            'car_number': self.car_number,
            'tara': self.tara,
            'brutto': self.brutto,
            'netto': self.netto,
            'fio': self.fio,
            'fraction': self.fraction,
            'notes': self.notes,
        }
        if self.counterparty_id:
            data['counterparty_id'] = self.counterparty_id
        return data
    
    def __str__(self) -> str:
        return (
            f"Взвешивание #{self.id}: {self.car_number} | "
            f"Тара: {self.tara:.1f} кг | Брутто: {self.brutto:.1f} кг | "
            f"Нетто: {self.netto:.1f} кг"
        )
