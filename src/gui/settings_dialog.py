"""
Диалог настроек приложения.
Выбор COM-порта, параметров связи и URL API.
"""
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QTabWidget, QWidget, QGroupBox, QTextEdit,
    QListWidget, QMessageBox
)
from PySide6.QtCore import Qt

from .styles import SETTINGS_STYLE
from ..hardware.scale_reader import ScaleReader
from ..utils.config import ConfigManager, SerialConfig, ApiConfig
from ..utils.logger import get_logger

logger = get_logger('settings_dialog')


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Инициализация диалога.
        
        Args:
            config_manager: Менеджер конфигурации
            parent: Родительское окно
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.config = config_manager.config
        
        self.setWindowTitle("Настройки")
        self.setMinimumSize(500, 600)
        self.setStyleSheet(SETTINGS_STYLE)
        
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Настройка интерфейса."""
        layout = QVBoxLayout(self)
        
        # Вкладки
        tabs = QTabWidget()
        tabs.addTab(self._create_serial_tab(), "COM-порт")
        tabs.addTab(self._create_cameras_tab(), "Камеры")
        tabs.addTab(self._create_api_tab(), "API")
        tabs.addTab(self._create_fractions_tab(), "Фракции")
        tabs.addTab(self._create_advanced_tab(), "Дополнительно")
        
        layout.addWidget(tabs)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self._save_settings)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("settings_button")
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        
        layout.addLayout(buttons_layout)
    
    def _create_serial_tab(self) -> QWidget:
        """Вкладка настроек COM-порта."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Группа настроек порта
        port_group = QGroupBox("Параметры подключения")
        port_layout = QFormLayout(port_group)
        
        # COM-порт
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self._refresh_ports()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(40, 40)
        refresh_btn.clicked.connect(self._refresh_ports)
        
        port_row = QHBoxLayout()
        port_row.addWidget(self.port_combo, 1)
        port_row.addWidget(refresh_btn)
        
        port_layout.addRow("COM-порт:", port_row)
        
        # Baudrate
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['1200', '2400', '4800', '9600', '19200', '38400', '57600', '115200'])
        port_layout.addRow("Скорость (baud):", self.baudrate_combo)
        
        # Data bits
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(['5', '6', '7', '8'])
        port_layout.addRow("Биты данных:", self.databits_combo)
        
        # Parity
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(['Нет (N)', 'Четный (E)', 'Нечетный (O)'])
        port_layout.addRow("Четность:", self.parity_combo)
        
        # Stop bits
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(['1', '1.5', '2'])
        port_layout.addRow("Стоп-биты:", self.stopbits_combo)
        
        layout.addWidget(port_group)
        
        # Кнопка тестирования
        test_btn = QPushButton("Тест подключения")
        test_btn.clicked.connect(self._test_connection)
        layout.addWidget(test_btn)
        
        # Результат теста (увеличена область)
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMinimumHeight(200)
        self.test_result.setPlaceholderText("Нажмите 'Тест подключения' для проверки связи с весами...")
        self.test_result.setStyleSheet("background-color: #FFFFFF; color: #000000; font-family: Consolas, monospace; font-size: 12px;")
        layout.addWidget(self.test_result)
        
        layout.addStretch()
        
        return widget
    
    def _create_api_tab(self) -> QWidget:
        """Вкладка настроек API."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        api_group = QGroupBox("Настройки API (Webhook)")
        api_layout = QFormLayout(api_group)
        
        # URL
        self.api_url_edit = QLineEdit()
        self.api_url_edit.setPlaceholderText("https://example.com/webhook")
        api_layout.addRow("URL:", self.api_url_edit)
        
        # Таймаут
        self.api_timeout_spin = QSpinBox()
        self.api_timeout_spin.setRange(5, 120)
        self.api_timeout_spin.setSuffix(" сек")
        api_layout.addRow("Таймаут:", self.api_timeout_spin)
        
        # Количество повторов
        self.api_retry_spin = QSpinBox()
        self.api_retry_spin.setRange(1, 10)
        api_layout.addRow("Повторных попыток:", self.api_retry_spin)
        
        # Задержка между попытками
        self.api_delay_spin = QSpinBox()
        self.api_delay_spin.setRange(1, 60)
        self.api_delay_spin.setSuffix(" сек")
        api_layout.addRow("Задержка между попытками:", self.api_delay_spin)

        layout.addWidget(api_group)

        # Завод
        from PySide6.QtWidgets import QComboBox
        factory_group = QGroupBox("Завод")
        factory_layout = QFormLayout(factory_group)

        self.factory_combo = QComboBox()
        self.factory_combo.setEditable(False)
        self.factory_combo.addItem("— Не выбран —", "")
        factory_layout.addRow("Завод терминала:", self.factory_combo)

        load_factories_btn = QPushButton("🔄 Загрузить заводы с сервера")
        load_factories_btn.clicked.connect(self._on_load_factories_clicked)
        factory_layout.addRow("", load_factories_btn)

        info_factory = QLabel(
            "Выберите завод, на котором установлен этот терминал.\n"
            "Все взвешивания будут привязаны к этому заводу при отправке на сервер."
        )
        info_factory.setWordWrap(True)
        info_factory.setStyleSheet("color: #888; font-size: 11px;")
        factory_layout.addRow("", info_factory)

        layout.addWidget(factory_group)
        
        # Информация о формате
        info_group = QGroupBox("Формат данных")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel("""
Данные отправляются POST-запросом в формате JSON:
{
    "datetime": "2026-01-19T16:50:00",
    "car_number": "А123БВ",
    "tara": 5000.0,
    "brutto": 15000.0,
    "netto": 10000.0,
    "fio": "Иванов И.И.",
    "fraction": "Щебень 5-20"
}
        """)
        info_text.setWordWrap(True)
        info_text.setStyleSheet("font-family: monospace; font-size: 12px;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        layout.addStretch()
        
        return widget
    
    def _create_cameras_tab(self) -> QWidget:
        """Вкладка настройки камер."""
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Опции захвата
        options_group = QGroupBox("Автозахват кадров")
        options_layout = QVBoxLayout(options_group)
        
        self.capture_tara_check = QCheckBox("Захватывать при фиксации тары")
        self.capture_brutto_check = QCheckBox("Захватывать при фиксации брутто")
        
        options_layout.addWidget(self.capture_tara_check)
        options_layout.addWidget(self.capture_brutto_check)
        layout.addWidget(options_group)
        
        # Таблица камер
        layout.addWidget(QLabel("Список камер:"))
        
        self.cameras_table = QTableWidget()
        self.cameras_table.setColumnCount(3)
        self.cameras_table.setHorizontalHeaderLabels(["Вкл", "Название", "URL потока"])
        self.cameras_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cameras_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cameras_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.cameras_table)
        
        # Кнопки управления
        btn_layout = QHBoxLayout()
        
        add_cam_btn = QPushButton("+ Добавить камеру")
        add_cam_btn.clicked.connect(self._add_camera)
        btn_layout.addWidget(add_cam_btn)
        
        remove_cam_btn = QPushButton("- Удалить")
        remove_cam_btn.setObjectName("reset_button")
        remove_cam_btn.clicked.connect(self._remove_camera)
        btn_layout.addWidget(remove_cam_btn)
        
        test_cam_btn = QPushButton("Тест камеры")
        test_cam_btn.clicked.connect(self._test_camera)
        btn_layout.addWidget(test_cam_btn)
        
        layout.addLayout(btn_layout)
        
        # Результат теста камеры
        self.camera_test_result = QLabel("")
        self.camera_test_result.setStyleSheet("color: #B0B0B0; font-size: 12px;")
        self.camera_test_result.setWordWrap(True)
        layout.addWidget(self.camera_test_result)
        
        return widget
    
    def _add_camera(self) -> None:
        """Добавить камеру в таблицу."""
        from PySide6.QtWidgets import QTableWidgetItem, QCheckBox
        
        row = self.cameras_table.rowCount()
        self.cameras_table.insertRow(row)
        
        # Чекбокс включения
        check = QCheckBox()
        check.setChecked(True)
        self.cameras_table.setCellWidget(row, 0, check)
        
        # Название
        self.cameras_table.setItem(row, 1, QTableWidgetItem(f"Камера {row + 1}"))
        
        # URL
        self.cameras_table.setItem(row, 2, QTableWidgetItem(""))
    
    def _remove_camera(self) -> None:
        """Удалить выбранную камеру."""
        row = self.cameras_table.currentRow()
        if row >= 0:
            self.cameras_table.removeRow(row)
    
    def _test_camera(self) -> None:
        """Тестировать выбранную камеру."""
        row = self.cameras_table.currentRow()
        if row < 0:
            self.camera_test_result.setText("Выберите камеру для тестирования")
            return
        
        url_item = self.cameras_table.item(row, 2)
        if not url_item or not url_item.text().strip():
            self.camera_test_result.setText("URL камеры не указан")
            return
        
        url = url_item.text().strip()
        self.camera_test_result.setText(f"Тестирование {url}...")
        
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        
        try:
            import cv2
            cap = cv2.VideoCapture(url)
            
            if not cap.isOpened():
                self.camera_test_result.setText("❌ Не удалось открыть поток")
                return
            
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                h, w = frame.shape[:2]
                self.camera_test_result.setText(f"✅ OK: {w}x{h} пикселей")
            else:
                self.camera_test_result.setText("❌ Не удалось прочитать кадр")
        except ImportError:
            self.camera_test_result.setText("❌ Нужно установить opencv-python: pip install opencv-python")
        except Exception as e:
            self.camera_test_result.setText(f"❌ Ошибка: {e}")
    
    def _load_cameras_to_table(self) -> None:
        """Загрузить камеры из конфига в таблицу."""
        from PySide6.QtWidgets import QTableWidgetItem, QCheckBox
        
        self.cameras_table.setRowCount(0)
        
        for cam in self.config.cameras:
            row = self.cameras_table.rowCount()
            self.cameras_table.insertRow(row)
            
            check = QCheckBox()
            check.setChecked(cam.get('enabled', True))
            self.cameras_table.setCellWidget(row, 0, check)
            
            self.cameras_table.setItem(row, 1, QTableWidgetItem(cam.get('name', '')))
            self.cameras_table.setItem(row, 2, QTableWidgetItem(cam.get('url', '')))
    
    def _get_cameras_from_table(self) -> list:
        """Получить камеры из таблицы."""
        cameras = []
        
        for row in range(self.cameras_table.rowCount()):
            check_widget = self.cameras_table.cellWidget(row, 0)
            enabled = check_widget.isChecked() if check_widget else True
            
            name_item = self.cameras_table.item(row, 1)
            name = name_item.text() if name_item else f"Камера {row + 1}"
            
            url_item = self.cameras_table.item(row, 2)
            url = url_item.text() if url_item else ""
            
            cameras.append({'name': name, 'url': url, 'enabled': enabled})
        
        return cameras

    def _create_fractions_tab(self) -> QWidget:
        """Вкладка списка фракций."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Список фракций/материалов:"))
        
        self.fractions_list = QListWidget()
        layout.addWidget(self.fractions_list)
        
        # Кнопки управления списком
        btn_layout = QHBoxLayout()
        
        self.fraction_edit = QLineEdit()
        self.fraction_edit.setPlaceholderText("Новая фракция...")
        btn_layout.addWidget(self.fraction_edit, 1)
        
        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_fraction)
        btn_layout.addWidget(add_btn)
        
        remove_btn = QPushButton("Удалить")
        remove_btn.setObjectName("reset_button")
        remove_btn.clicked.connect(self._remove_fraction)
        btn_layout.addWidget(remove_btn)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def _create_advanced_tab(self) -> QWidget:
        """Вкладка дополнительных настроек."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Стабилизация веса
        stab_group = QGroupBox("Стабилизация веса")
        stab_layout = QFormLayout(stab_group)
        
        self.stable_count_spin = QSpinBox()
        self.stable_count_spin.setRange(3, 20)
        stab_layout.addRow("Количество значений:", self.stable_count_spin)
        
        self.stable_threshold_spin = QDoubleSpinBox()
        self.stable_threshold_spin.setRange(1, 100)
        self.stable_threshold_spin.setSuffix(" кг")
        stab_layout.addRow("Порог отклонения:", self.stable_threshold_spin)
        
        layout.addWidget(stab_group)
        
        # Паттерн веса
        pattern_group = QGroupBox("Парсинг данных весов")
        pattern_layout = QFormLayout(pattern_group)
        
        self.pattern_edit = QLineEdit()
        self.pattern_edit.setPlaceholderText(r"[+-]?\s*(\d+\.?\d*)\s*(?:kg|кг)?")
        pattern_layout.addRow("Регулярное выражение:", self.pattern_edit)
        
        pattern_help = QLabel(
            "Паттерн должен содержать группу (\\d+\\.?\\d*) для числа.\n"
            "Примеры данных: '+  1234.5 kg', 'ST,GS,+001234.5 kg', '1234.5'"
        )
        pattern_help.setWordWrap(True)
        pattern_help.setStyleSheet("color: #B0B0B0; font-size: 12px;")
        pattern_layout.addRow(pattern_help)
        
        layout.addWidget(pattern_group)
        
        # Резервное копирование
        backup_group = QGroupBox("Обслуживание")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_btn = QPushButton("💾 Создать резервную копию базы данных")
        backup_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        backup_btn.clicked.connect(self._backup_db)
        backup_layout.addWidget(backup_btn)
        
        layout.addWidget(backup_group)
        
        layout.addStretch()
        
        return widget

    def _backup_db(self) -> None:
        """Создание бэкапа базы данных."""
        import shutil
        import os
        from datetime import datetime
        from PySide6.QtWidgets import QFileDialog
        
        db_path = "weighings.db"
        if not os.path.exists(db_path):
             QMessageBox.warning(self, "Ошибка", "Файл базы данных не найден")
             return
             
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить бэкап",
            f"backup_weighings_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
            "SQLite Database (*.db)"
        )
        
        if filename:
            try:
                shutil.copy2(db_path, filename)
                QMessageBox.information(self, "Успех", f"Бэкап сохранен:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать бэкап:\n{e}")
    
    def _refresh_ports(self) -> None:
        """Обновить список COM-портов."""
        current = self.port_combo.currentText()
        self.port_combo.clear()
        
        ports = ScaleReader.get_available_ports()
        self.port_combo.addItems(ports)
        
        # Восстанавливаем выбранный порт
        index = self.port_combo.findText(current)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        elif current:
            self.port_combo.setEditText(current)
    
    def _test_connection(self) -> None:
        """Тестировать подключение к порту с отображением сырых данных."""
        import serial
        import time
        
        self.test_result.clear()
        self.test_result.append("🔍 Тестирование подключения...")
        self.test_result.append(f"Порт: {self.port_combo.currentText()}")
        self.test_result.append(f"Скорость: {self.baudrate_combo.currentText()}")
        self.test_result.append("")
        
        # Обновляем UI
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Останавливаем текущее чтение весов, если активно
        main_window = self.parent()
        reader_was_running = False
        if main_window and hasattr(main_window, 'manager'):
            if main_window.manager.scale_reader.isRunning():
                self.test_result.append("⏸ Останавливаю чтение весов для теста...")
                QApplication.processEvents()
                main_window.manager.scale_reader.stop()
                reader_was_running = True
                time.sleep(0.5)  # Даем время закрыть порт
        
        config = self._get_serial_config()
        
        try:
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}
            
            test_serial = serial.Serial(
                port=config.port,
                baudrate=config.baudrate,
                bytesize=config.bytesize,
                parity=parity_map.get(config.parity, serial.PARITY_NONE),
                stopbits=stopbits_map.get(config.stopbits, serial.STOPBITS_ONE),
                timeout=0.5
            )
            
            self.test_result.append("✅ Порт открыт успешно!")
            self.test_result.append("⏳ Ожидание данных (5 секунд)...")
            self.test_result.append("-" * 40)
            QApplication.processEvents()
            
            test_serial.reset_input_buffer()
            
            start = time.time()
            data_received = False
            line_count = 0
            
            while time.time() - start < 5:
                if test_serial.in_waiting > 0:
                    try:
                        raw_bytes = test_serial.readline()
                        try:
                            raw_data = raw_bytes.decode('utf-8', errors='replace').strip()
                        except:
                            raw_data = raw_bytes.decode('cp1251', errors='replace').strip()
                        
                        if raw_data:
                            data_received = True
                            line_count += 1
                            self.test_result.append(f"[{line_count}] {repr(raw_data)}")
                            QApplication.processEvents()
                    except Exception as e:
                        self.test_result.append(f"Ошибка чтения: {e}")
                else:
                    time.sleep(0.05)
                    QApplication.processEvents()
            
            test_serial.close()
            
            self.test_result.append("-" * 40)
            if data_received:
                self.test_result.append(f"✅ Получено {line_count} строк данных")
                self.test_result.append("💡 Если вес не отображается, проверьте регулярное выражение в настройках")
            else:
                self.test_result.append("⚠️ Данные не получены за 5 секунд")
                self.test_result.append("Проверьте:")
                self.test_result.append("• Включены ли весы?")
                self.test_result.append("• Правильные ли параметры связи?")
                self.test_result.append("• Отправляют ли весы данные автоматически?")
                
        except serial.SerialException as e:
            self.test_result.append(f"❌ Ошибка открытия порта: {e}")
        except Exception as e:
            self.test_result.append(f"❌ Неизвестная ошибка: {e}")
        finally:
            # Восстанавливаем чтение весов, если было активно
            if reader_was_running and main_window and hasattr(main_window, 'manager'):
                self.test_result.append("")
                self.test_result.append("▶ Возобновляю чтение весов...")
                QApplication.processEvents()
                main_window.manager.scale_reader.start()
    
    def _add_fraction(self) -> None:
        """Добавить фракцию в список."""
        text = self.fraction_edit.text().strip()
        if text:
            self.fractions_list.addItem(text)
            self.fraction_edit.clear()
    
    def _remove_fraction(self) -> None:
        """Удалить выбранную фракцию."""
        current = self.fractions_list.currentRow()
        if current >= 0:
            self.fractions_list.takeItem(current)
    
    def _get_serial_config(self) -> SerialConfig:
        """Получить настройки COM-порта из формы."""
        parity_map = {'Нет (N)': 'N', 'Четный (E)': 'E', 'Нечетный (O)': 'O'}
        
        return SerialConfig(
            port=self.port_combo.currentText(),
            baudrate=int(self.baudrate_combo.currentText()),
            bytesize=int(self.databits_combo.currentText()),
            parity=parity_map.get(self.parity_combo.currentText(), 'N'),
            stopbits=float(self.stopbits_combo.currentText())
        )
    
    def _load_settings(self) -> None:
        """Загрузить настройки в форму."""
        config = self.config
        
        # COM-порт
        self.port_combo.setEditText(config.serial.port)
        self.baudrate_combo.setCurrentText(str(config.serial.baudrate))
        self.databits_combo.setCurrentText(str(config.serial.bytesize))
        
        parity_map = {'N': 'Нет (N)', 'E': 'Четный (E)', 'O': 'Нечетный (O)'}
        self.parity_combo.setCurrentText(parity_map.get(config.serial.parity, 'Нет (N)'))
        
        self.stopbits_combo.setCurrentText(str(config.serial.stopbits))
        
        # API
        self.api_url_edit.setText(config.api.url)
        self.api_timeout_spin.setValue(config.api.timeout)
        self.api_retry_spin.setValue(config.api.retry_count)
        self.api_delay_spin.setValue(config.api.retry_delay)

        # Завод (если уже есть в конфиге — добавляем как первый пункт)
        factory_id = getattr(config, 'factory_id', '') or ''
        factory_name = getattr(config, 'factory_name', '') or ''
        if factory_id and self.factory_combo.findData(factory_id) < 0:
            self.factory_combo.addItem(factory_name or factory_id, factory_id)
        if factory_id:
            idx = self.factory_combo.findData(factory_id)
            if idx >= 0:
                self.factory_combo.setCurrentIndex(idx)
        
        # Фракции
        self.fractions_list.clear()
        self.fractions_list.addItems(config.fractions)
        
        # Камеры
        self._load_cameras_to_table()
        self.capture_tara_check.setChecked(config.capture_on_tara)
        self.capture_brutto_check.setChecked(config.capture_on_brutto)
        
        # Дополнительно
        self.stable_count_spin.setValue(config.weight_stable_count)
        self.stable_threshold_spin.setValue(config.weight_stable_threshold)
        self.pattern_edit.setText(config.weight_pattern)
    
    def _save_settings(self) -> None:
        """Сохранить настройки."""
        parity_map = {'Нет (N)': 'N', 'Четный (E)': 'E', 'Нечетный (O)': 'O'}
        
        # Обновляем конфиг
        self.config.serial.port = self.port_combo.currentText()
        self.config.serial.baudrate = int(self.baudrate_combo.currentText())
        self.config.serial.bytesize = int(self.databits_combo.currentText())
        self.config.serial.parity = parity_map.get(self.parity_combo.currentText(), 'N')
        self.config.serial.stopbits = float(self.stopbits_combo.currentText())
        
        self.config.api.url = self.api_url_edit.text().strip()
        self.config.api.timeout = self.api_timeout_spin.value()
        self.config.api.retry_count = self.api_retry_spin.value()
        self.config.api.retry_delay = self.api_delay_spin.value()

        # Завод
        self.config.factory_id = self.factory_combo.currentData() or ""
        self.config.factory_name = self.factory_combo.currentText() if self.config.factory_id else ""
        
        self.config.fractions = [
            self.fractions_list.item(i).text() 
            for i in range(self.fractions_list.count())
        ]
        
        self.config.cameras = self._get_cameras_from_table()
        self.config.capture_on_tara = self.capture_tara_check.isChecked()
        self.config.capture_on_brutto = self.capture_brutto_check.isChecked()
        
        self.config.weight_stable_count = self.stable_count_spin.value()
        self.config.weight_stable_threshold = self.stable_threshold_spin.value()
        self.config.weight_pattern = self.pattern_edit.text().strip() or self.config.weight_pattern
        
        # Сохраняем
        self.config_manager.save(self.config)

        logger.info("Настройки сохранены")
        self.accept()

    def _on_load_factories_clicked(self) -> None:
        """Загрузить список заводов с сервера и заполнить combobox."""
        import requests
        from PySide6.QtWidgets import QMessageBox

        url = self.api_url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Сначала заполните URL API")
            return

        # URL lookup = webhook URL + "lookup/?type=factories"
        base_url = url.rstrip('/')
        lookup_url = base_url + '/lookup/?type=factories'

        try:
            response = requests.get(lookup_url, timeout=10)
            if not response.ok:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Сервер вернул HTTP {response.status_code}"
                )
                return
            data = response.json()
            if not isinstance(data, list):
                QMessageBox.critical(self, "Ошибка", "Неверный формат ответа сервера")
                return

            # Сохраняем текущий выбор
            current_id = self.factory_combo.currentData() or ""

            self.factory_combo.clear()
            self.factory_combo.addItem("— Не выбран —", "")
            for f in data:
                self.factory_combo.addItem(f.get('title', ''), f.get('id', ''))

            # Восстанавливаем выбор
            if current_id:
                idx = self.factory_combo.findData(current_id)
                if idx >= 0:
                    self.factory_combo.setCurrentIndex(idx)

            QMessageBox.information(
                self, "Готово",
                f"Загружено заводов: {len(data)}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить заводы:\n{e}")
