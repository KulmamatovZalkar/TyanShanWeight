"""
Модуль чтения веса с COM-порта через QThread.
Обеспечивает непрерывное чтение и отправку сигналов в GUI.
"""
from typing import Optional, List

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal, QMutex, QMutexLocker

from .scale_protocols import ScaleProtocol, create_protocol
from ..utils.logger import get_logger
from ..utils.config import SerialConfig

logger = get_logger('scale_reader')


class ScaleReader(QThread):
    """
    Поток для чтения данных с весов по COM-порту.
    
    Signals:
        weight_received(float): Новое значение веса
        raw_data_received(str): Сырые данные для отладки
        connection_changed(bool): Изменение статуса соединения
        error_occurred(str): Сообщение об ошибке
    """
    
    weight_received = Signal(float)
    raw_data_received = Signal(str)
    connection_changed = Signal(bool)
    error_occurred = Signal(str)
    
    def __init__(self, config: SerialConfig, protocol: Optional[ScaleProtocol] = None):
        """
        Инициализация читателя весов.
        
        Args:
            config: Настройки COM-порта
            protocol: Протокол парсинга данных (по умолчанию generic)
        """
        super().__init__()
        
        self.config = config
        self.protocol = protocol or create_protocol()
        
        self._serial: Optional[serial.Serial] = None
        self._running = False
        self._connected = False
        self._mutex = QMutex()
        
        # Буфер для накопления неполных строк
        self._buffer = ""
    
    @staticmethod
    def get_available_ports() -> List[str]:
        """
        Получить список доступных COM-портов.
        
        Returns:
            Список имен портов
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def configure(self, config: SerialConfig) -> None:
        """
        Обновить конфигурацию порта.
        
        Args:
            config: Новые настройки
        """
        with QMutexLocker(self._mutex):
            self.config = config
            
            # Переподключиться с новыми настройками
            if self._connected:
                self._disconnect()
                self._connect()
    
    def set_protocol(self, protocol: ScaleProtocol) -> None:
        """Установить протокол парсинга."""
        with QMutexLocker(self._mutex):
            self.protocol = protocol
    
    def _connect(self) -> bool:
        """Подключиться к COM-порту."""
        try:
            # Маппинг parity
            parity_map = {
                'N': serial.PARITY_NONE,
                'E': serial.PARITY_EVEN,
                'O': serial.PARITY_ODD
            }
            
            # Маппинг stopbits
            stopbits_map = {
                1: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO
            }
            
            self._serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                bytesize=self.config.bytesize,
                parity=parity_map.get(self.config.parity, serial.PARITY_NONE),
                stopbits=stopbits_map.get(self.config.stopbits, serial.STOPBITS_ONE),
                timeout=self.config.timeout
            )
            
            self._connected = True
            self.connection_changed.emit(True)
            logger.info(f"Подключено к {self.config.port} @ {self.config.baudrate}")
            return True
            
        except serial.SerialException as e:
            error_msg = f"Ошибка подключения к {self.config.port}: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._connected = False
            self.connection_changed.emit(False)
            return False
    
    def _disconnect(self) -> None:
        """Отключиться от COM-порта."""
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception as e:
                logger.warning(f"Ошибка при закрытии порта: {e}")
        
        self._serial = None
        self._connected = False
        self.connection_changed.emit(False)
        logger.info("Отключено от COM-порта")
    
    def run(self) -> None:
        """Основной цикл чтения данных."""
        self._running = True
        
        if not self._connect():
            return
        
        while self._running:
            try:
                if self._serial and self._serial.is_open:
                    # Читаем данные
                    if self._serial.in_waiting > 0:
                        raw_bytes = self._serial.readline()
                        
                        try:
                            raw_data = raw_bytes.decode('utf-8', errors='replace').strip()
                        except UnicodeDecodeError:
                            raw_data = raw_bytes.decode('cp1251', errors='replace').strip()
                        
                        if raw_data:
                            self.raw_data_received.emit(raw_data)
                            
                            # Парсим вес
                            weight = self.protocol.parse(raw_data)
                            if weight is not None:
                                self.weight_received.emit(weight)
                    else:
                        self.msleep(50)  # Небольшая пауза если нет данных
                else:
                    # Попытка переподключения
                    self.msleep(1000)
                    self._connect()
                    
            except serial.SerialException as e:
                error_msg = f"Ошибка чтения: {e}"
                logger.error(error_msg)
                self.error_occurred.emit(error_msg)
                self._connected = False
                self.connection_changed.emit(False)
                self.msleep(2000)  # Пауза перед переподключением
                
            except Exception as e:
                logger.error(f"Неизвестная ошибка в цикле чтения: {e}")
                self.msleep(1000)
        
        self._disconnect()
    
    def stop(self) -> None:
        """Остановить поток чтения."""
        self._running = False
        self.wait(3000)  # Ожидаем завершения потока
    
    def is_connected(self) -> bool:
        """Проверить статус подключения."""
        return self._connected
    
    def test_connection(self, config: SerialConfig) -> tuple[bool, str]:
        """
        Тест подключения к порту.
        
        Args:
            config: Настройки для тестирования
            
        Returns:
            (успех, сообщение)
        """
        try:
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}
            
            test_serial = serial.Serial(
                port=config.port,
                baudrate=config.baudrate,
                bytesize=config.bytesize,
                parity=parity_map.get(config.parity, serial.PARITY_NONE),
                stopbits=stopbits_map.get(config.stopbits, serial.STOPBITS_ONE),
                timeout=2
            )
            
            # Попробуем прочитать данные
            test_serial.reset_input_buffer()
            
            # Ждем данные до 3 секунд
            import time
            start = time.time()
            data_received = False
            
            while time.time() - start < 3:
                if test_serial.in_waiting > 0:
                    raw = test_serial.readline()
                    data_received = True
                    test_serial.close()
                    return True, f"Соединение успешно. Получены данные: {raw[:50]}"
                time.sleep(0.1)
            
            test_serial.close()
            
            if data_received:
                return True, "Соединение успешно"
            else:
                return True, "Порт открыт, но данные не получены (проверьте весы)"
                
        except serial.SerialException as e:
            return False, f"Ошибка: {e}"
        except Exception as e:
            return False, f"Неизвестная ошибка: {e}"
