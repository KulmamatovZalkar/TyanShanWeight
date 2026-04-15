"""
Центральный менеджер процесса взвешивания.
Координирует работу всех компонентов.
"""
from datetime import datetime
from typing import Optional, Callable
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

from .weight_stabilizer import WeightStabilizer
from ..data.models import Weighing
from ..data.database import Database
from ..data.api_client import ApiClient
from ..hardware.scale_reader import ScaleReader
from ..hardware.scale_protocols import create_protocol
from ..hardware.camera_manager import CameraManager
from ..utils.config import ConfigManager, AppConfig
from ..utils.logger import get_logger

logger = get_logger('weighing_manager')


class WeighingState(Enum):
    """Состояния процесса взвешивания."""
    IDLE = auto()           # Ожидание
    TARA_FIXED = auto()     # Тара зафиксирована
    BRUTTO_FIXED = auto()   # Брутто зафиксировано
    READY_TO_SAVE = auto()  # Готово к сохранению


class WeighingManager(QObject):
    """
    Менеджер процесса взвешивания.
    
    Signals:
        weight_updated(float, bool): Новый вес и флаг стабильности
        tara_fixed(float): Тара зафиксирована
        brutto_fixed(float): Брутто зафиксировано
        netto_calculated(float): Нетто вычислено
        weighing_saved(Weighing): Запись сохранена
        state_changed(WeighingState): Изменение состояния
        connection_status(bool): Статус подключения к весам
        error(str): Сообщение об ошибке
    """
    
    weight_updated = Signal(float, bool)  # вес, стабильность
    tara_fixed = Signal(float)
    brutto_fixed = Signal(float)
    netto_calculated = Signal(float)
    weighing_saved = Signal(object)  # Weighing
    state_changed = Signal(object)  # WeighingState
    connection_status = Signal(bool)
    error = Signal(str)
    lookups_loaded = Signal(dict)  # справочники с сервера
    
    def __init__(self, config_manager: ConfigManager):
        """
        Инициализация менеджера.
        
        Args:
            config_manager: Менеджер конфигурации
        """
        super().__init__()
        
        self.config_manager = config_manager
        self.config = config_manager.config
        
        # Компоненты
        self.database = Database(self.config.db_path)
        self.api_client = ApiClient(self.config.api, self.database)
        self.api_client.set_factory_id(getattr(self.config, 'factory_id', '') or '')
        self.stabilizer = WeightStabilizer(
            buffer_size=self.config.weight_stable_count,
            threshold=self.config.weight_stable_threshold
        )
        
        # Создаем протокол и читатель весов
        protocol = create_protocol(pattern=self.config.weight_pattern)
        self.scale_reader = ScaleReader(self.config.serial, protocol)
        
        # Менеджер камер
        self.camera_manager = CameraManager(self.config.images_path)
        self.camera_manager.set_cameras(self.config.cameras)
        
        # Текущее взвешивание
        self._current_weighing: Optional[Weighing] = None
        self._state = WeighingState.IDLE
        self._current_weight: float = 0.0
        self._is_stable: bool = False
        self._manual_mode: bool = False
        
        # Защита от двойного сохранения
        self._last_save_time: Optional[datetime] = None
        self._save_cooldown_seconds = 5
        
        # Подключаем сигналы
        self._connect_signals()
    
    @property
    def state(self) -> WeighingState:
        """Текущее состояние взвешивания."""
        return self._state

    def _connect_signals(self) -> None:
        """Подключить сигналы от компонентов."""
        self.scale_reader.weight_received.connect(self._on_weight_received)
        self.scale_reader.connection_changed.connect(self._on_connection_changed)
        self.scale_reader.error_occurred.connect(self._on_scale_error)
        
        self.api_client.set_callback(self._on_api_send_result)
    
    def start(self) -> None:
        """Запустить менеджер."""
        logger.info("Запуск менеджера взвешивания")
        self.scale_reader.start()
        self.api_client.start()
        # Загружаем справочники в фоне
        import threading
        threading.Thread(target=self._load_lookups, daemon=True).start()

    def _load_lookups(self) -> None:
        """Загрузить справочники с сервера (фоновый поток)."""
        data = self.api_client.fetch_lookups()
        if data:
            self.lookups_loaded.emit(data)
    
    def stop(self) -> None:
        """Остановить менеджер."""
        logger.info("Остановка менеджера взвешивания")
        self.scale_reader.stop()
        self.api_client.stop()

    def set_manual_mode(self, enabled: bool) -> None:
        """Включить/выключить ручной режим."""
        self._manual_mode = enabled
        logger.info(f"Ручной режим: {enabled}")
        if enabled:
            self._is_stable = True
            self.weight_updated.emit(self._current_weight, True)

    def set_manual_weight(self, weight: float) -> None:
        """Установить вес вручную."""
        if not self._manual_mode:
            return
        self.stabilizer.reset()
        self._current_weight = weight
        self._is_stable = True
        self.weight_updated.emit(weight, True)
    
    def _on_weight_received(self, weight: float) -> None:
        """Обработка нового значения веса."""
        if self._manual_mode:
            return

        self.stabilizer.add_value(weight)
        self._current_weight = weight
        self._is_stable = self.stabilizer.is_stable()
        
        # Получаем стабильное значение если доступно
        stable_value = self.stabilizer.get_stable_value()
        display_weight = stable_value if stable_value else weight
        
        self.weight_updated.emit(display_weight, self._is_stable)
    
    def _on_connection_changed(self, connected: bool) -> None:
        """Обработка изменения статуса подключения."""
        self.connection_status.emit(connected)
        if connected:
            logger.info("Весы подключены")
        else:
            logger.warning("Весы отключены")
    
    def _on_scale_error(self, error_msg: str) -> None:
        """Обработка ошибки весов."""
        self.error.emit(f"Ошибка весов: {error_msg}")
    
    def _on_api_send_result(self, weighing_id: int, success: bool, response: str) -> None:
        """Обработка результата отправки на API."""
        if success:
            logger.info(f"Запись #{weighing_id} успешно отправлена на API")
        else:
            logger.warning(f"Ошибка отправки #{weighing_id}: {response}")
    
    def fix_tara(self, weight: Optional[float] = None) -> bool:
        """
        Зафиксировать тару.
        
        Args:
            weight: Явное значение веса (для ручного режима)
            
        Returns:
            True если успешно зафиксировано
        """
        # Если вес не передан, берем текущий с весов
        if weight is None:
            weight = self._current_weight
            
            # Проверка стабильности только для автоматического режима (когда вес с весов)
            if not self._is_stable and not self._manual_mode:
                self.error.emit("Дождитесь стабилизации веса для фиксации тары")
                return False
        
        if weight <= 0:
            self.error.emit("Невозможно зафиксировать тару: вес должен быть больше 0")
            return False
        
        # Создаем новое взвешивание
        self._current_weighing = Weighing(tara=weight)
        self._state = WeighingState.TARA_FIXED
        
        self.tara_fixed.emit(weight)
        self.state_changed.emit(self._state)
        
        logger.info(f"Тара зафиксирована: {weight} кг")
        
        # Захват фото
        if self.config.capture_on_tara:
            self._capture_photos(is_tara=True)
            
        return True
    
    def fix_brutto(self, weight: Optional[float] = None) -> bool:
        """
        Зафиксировать брутто.
        
        Args:
            weight: Явное значение веса (для ручного режима)
            
        Returns:
            True если успешно зафиксировано
        """
        if self._current_weighing is None:
            # Если пытаемся зафиксировать брутто без тары, но в ручном режиме
            # можно предположить, что пользователь хочет просто ввести все данные.
            # Но для порядка лучше требовать последовательность или создать взвешивание с тарой 0?
            # Нет, требуем тару.
            self.error.emit("Сначала зафиксируйте тару")
            return False
        
        # Если вес не передан, берем текущий с весов
        if weight is None:
            weight = self._current_weight
        
            if not self._is_stable and not self._manual_mode:
                self.error.emit("Дождитесь стабилизации веса для фиксации брутто")
                return False
        
        if weight <= 0:
            self.error.emit("Невозможно зафиксировать брутто: вес должен быть больше 0")
            return False
        
        if weight < self._current_weighing.tara:
            self.error.emit("Брутто не может быть меньше тары")
            return False
        
        self._current_weighing.brutto = weight
        self._current_weighing.calculate_netto()
        self._state = WeighingState.BRUTTO_FIXED
        
        self.brutto_fixed.emit(weight)
        self.netto_calculated.emit(self._current_weighing.netto)
        self.state_changed.emit(self._state)
        
        logger.info(f"Брутто зафиксировано: {weight} кг, нетто: {self._current_weighing.netto} кг")
        
        if self.config.capture_on_brutto:
            self._capture_photos(is_tara=False)
            
        return True
    
    def load_weighing(self, weighing: Weighing) -> None:
        """
        Загрузить существующее (незавершенное) взвешивание.
        """
        self._current_weighing = weighing
        # Если загружаем, то Тара уже есть. 
        # Ставим состояние TARA_FIXED, чтобы можно было взвешивать Брутто.
        self._state = WeighingState.TARA_FIXED  
        
        # Эмитим сигналы для UI
        self.tara_fixed.emit(weighing.tara)
        # Если есть и другие данные, обновляем UI через сигналы? 
        # Пока UI сам подтянет через геттеры или мы должны явно установить.
        # В MainWindow мы будем вызывать load_weighing, а потом setting fields.
        
        logger.info(f"Загружено взвешивание #{weighing.id}: Тара={weighing.tara}")

    def set_weighing_data(self, car_number: str, fio: str, fraction: str, notes: str = "") -> None:
        """
        Установить данные взвешивания.
        
        Args:
            car_number: Госномер
            fio: ФИО водителя
            fraction: Фракция/материал
            notes: Заметки
        """
        if self._current_weighing:
            self._current_weighing.car_number = car_number.strip().upper()
            self._current_weighing.fio = fio.strip()
            self._current_weighing.fraction = fraction.strip()
            self._current_weighing.notes = notes.strip()
            
            # Проверяем готовность к сохранению
            if self._current_weighing.is_complete():
                self._state = WeighingState.READY_TO_SAVE
                self.state_changed.emit(self._state)
    
    def save_weighing(self, car_number: str, fio: str, fraction: str, notes: str = "", counterparty_id: str = "", counterparty_name: str = "") -> bool:
        """
        Сохранить взвешивание.
        
        Args:
            car_number: Госномер
            fio: ФИО водителя
            fraction: Фракция
            notes: Заметки
            
        Returns:
            True если успешно сохранено
        """
        if not self._current_weighing:
            self.error.emit("Нет активного взвешивания")
            return False
            
        # Обновляем данные
        self._current_weighing.car_number = car_number
        self._current_weighing.fio = fio
        self._current_weighing.fraction = fraction
        self._current_weighing.notes = notes
        self._current_weighing.counterparty_id = counterparty_id
        self._current_weighing.counterparty_name = counterparty_name
        
        # Проверяем возможность сохранения
        # Можно сохранить если:
        # 1. Зафиксирована Тара (тогда это "Заезд")
        # 2. Зафиксирована Тара и Брутто (тогда это "Выезд" или "Полное взвешивание")
        
        if self._state == WeighingState.TARA_FIXED:
            # Сохранение только Тары (Заезд)
            # Брутто и Нетто уже 0 по умолчанию в модели, но убедимся
            if not self._current_weighing.id: # Если это новая запись
                self._current_weighing.datetime = datetime.now().isoformat()
            
            # Сохраняем (INSERT или UPDATE)
            try:
                self.database.save(self._current_weighing)
                self.weighing_saved.emit(self._current_weighing)
                
                # Сброс после сохранения
                self.reset()
                return True
            except Exception as e:
                logger.error(f"Ошибка сохранения в БД: {e}")
                self.error.emit(f"Ошибка сохранения: {e}")
                return False

        elif self._state in [WeighingState.BRUTTO_FIXED, WeighingState.READY_TO_SAVE]:
             # Сохранение полного цикла
            if not self._current_weighing.datetime:
                self._current_weighing.datetime = datetime.now().isoformat()
                
            try:
                # Сначала в БД
                self.database.save(self._current_weighing)
                
                # Потом в API (в отдельном потоке через ApiClient)
                self.api_client.queue_send(self._current_weighing)
                
                self.weighing_saved.emit(self._current_weighing)
                
                # Сброс
                self.reset()
                return True
            except Exception as e:
                logger.error(f"Ошибка сохранения: {e}")
                self.error.emit(f"Ошибка сохранения: {e}")
                return False
        
        else:
             self.error.emit("Нечего сохранять (нужна хотя бы Тара)")
             return False
             
    def reset(self) -> None:
        """Сброс состояния."""
        self._current_weighing = None
        self._state = WeighingState.IDLE
        # Не сбрасываем _manual_mode, он глобальный
        self.tara_fixed.emit(0.0)
        self.brutto_fixed.emit(0.0)
        self.netto_calculated.emit(0.0)
        self.state_changed.emit(self._state)
        logger.info("Состояние сброшено")
    
    def get_current_weighing(self) -> Optional[Weighing]:
        """Получить текущее взвешивание."""
        return self._current_weighing
    
    def get_state(self) -> WeighingState:
        """Получить текущее состояние."""
        return self._state
    
    def update_config(self) -> None:
        """Обновить конфигурацию из менеджера."""
        self.config = self.config_manager.config
        
        # Обновляем стабилизатор
        self.stabilizer.configure(
            buffer_size=self.config.weight_stable_count,
            threshold=self.config.weight_stable_threshold
        )
        
        # Обновляем читатель весов
        self.scale_reader.configure(self.config.serial)
        
        # Обновляем протокол
        protocol = create_protocol(pattern=self.config.weight_pattern)
        self.scale_reader.set_protocol(protocol)
        
        # Обновляем API клиент
        self.api_client.config = self.config.api
        self.api_client.set_factory_id(getattr(self.config, 'factory_id', '') or '')
        
        # Обновляем камеры
        self.camera_manager.images_dir = self.config.images_path
        self.camera_manager.set_cameras(self.config.cameras)
        
        logger.info("Конфигурация обновлена")
    
    def _capture_photos(self, is_tara: bool) -> None:
        """
        Захватить фото с камер.
        
        Args:
            is_tara: True если это взвешивание тары, False - брутто
        """
        if not self._current_weighing:
            return
            
        car_number = self._current_weighing.car_number or "unknown"
        
        def on_captured(files: list):
            if not self._current_weighing:
                return
                
            if is_tara:
                self._current_weighing.photos_tara.extend(files)
            else:
                self._current_weighing.photos_brutto.extend(files)
            
            logger.info(f"Сохранено {len(files)} фото для {'тары' if is_tara else 'брутто'}")
        
        self.camera_manager.capture_all_async(car_number, callback=on_captured)
