"""
Главное окно приложения TyanShanWeight.
Интерфейс оператора для взвешивания грузовиков.
"""
from typing import Optional
from datetime import datetime
import cv2

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QGroupBox,
    QStatusBar, QFrame, QMessageBox, QSpacerItem, QSizePolicy,
    QSplitter, QFormLayout, QCheckBox, QDoubleSpinBox, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFileDialog
)
from PySide6.QtCore import Qt, Slot, QTimer, QSize, QStringListModel
from PySide6.QtGui import QKeySequence, QShortcut, QImage, QPixmap, QFont
from PySide6.QtWidgets import QCompleter

from .styles import MAIN_STYLE, COLORS
from .settings_dialog import SettingsDialog
from .history_window import HistoryWindow
from .keypad_dialog import KeypadDialog
from ..core.weighing_manager import WeighingManager, WeighingState
from ..utils.config import ConfigManager
from ..utils.logger import get_logger

logger = get_logger('main_window')


class MainWindow(QMainWindow):
    """Главное окно приложения."""
    
    def __init__(self, config_manager: ConfigManager):
        # ... (init code same as before)
        super().__init__()
        
        self.config_manager = config_manager
        self.manager = WeighingManager(config_manager)
        
        self.setWindowTitle("TyanShanWeight — Весовой терминал")
        self.setMinimumSize(1200, 800)
        self.showMaximized()
        self.setStyleSheet(MAIN_STYLE)
        
        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._start_timers()
        
        # Запускаем менеджер
        self.manager.start()
        
        # Загружаем историю
        self._update_history_table()
    
    def _setup_ui(self) -> None:
        """Настройка интерфейса."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Верхняя панель (Часы, Дата, Статус)
        main_layout.addWidget(self._create_top_bar())
        
        # Основная рабочая область (Сплиттер)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._create_left_panel())   # Ввод данных и Вес
        splitter.addWidget(self._create_right_panel())  # Камера и Таблица
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        
        main_layout.addWidget(splitter)
        
        # Нижняя панель (Кнопки действий)
        main_layout.addWidget(self._create_action_bar())

        # Принудительно вызываем обработчик стартового режима ПОСЛЕ создания всех кнопок
        self._on_manual_mode_changed(self.manual_mode_btn.isChecked())

    def _create_top_bar(self) -> QFrame:
        """Создание верхней панели."""
        frame = QFrame()
        frame.setStyleSheet("background-color: #2D2D2D; border-radius: 5px; padding: 5px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Логотип / Название
        title = QLabel("TyanShanWeight")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        layout.addWidget(title)

        # Завод
        factory_name = getattr(self.config_manager.config, 'factory_name', '') or ''
        self.factory_label = QLabel(f"🏭 {factory_name}" if factory_name else "🏭 завод не выбран")
        self.factory_label.setStyleSheet(
            "font-size: 13px; color: #FFA500; font-weight: bold; padding: 4px 10px; "
            "background-color: #1A1A1A; border-radius: 4px; margin-left: 12px;"
        )
        layout.addWidget(self.factory_label)

        layout.addStretch()
        
        # Кнопка Журнал (База)
        # Кнопка Журнал (База)
        history_btn = QPushButton("📋 Журнал / База")
        history_btn.setMinimumWidth(160)
        history_btn.setCursor(Qt.PointingHandCursor)
        history_btn.setStyleSheet("""
            QPushButton {
                background-color: #007ACC; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #0086E6; }
            QPushButton:pressed { background-color: #005C99; }
        """)
        history_btn.clicked.connect(self._open_history)
        layout.addWidget(history_btn)
        
        layout.addSpacing(10)
        
        # Кнопка Быстрый Отчет
        export_btn = QPushButton("📤 Отчет за сегодня")
        export_btn.setMinimumWidth(160)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #008CBA; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #00A3D9; }
            QPushButton:pressed { background-color: #00688B; }
        """)
        export_btn.clicked.connect(self._export_today_report)
        layout.addWidget(export_btn)
        
        layout.addSpacing(10)
        
        pending_btn = QPushButton("⏳ Ожидающие")
        pending_btn.setMinimumWidth(160)
        pending_btn.setCursor(Qt.PointingHandCursor)
        pending_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background-color: #FFAC33; }
            QPushButton:pressed { background-color: #E68A00; }
        """)
        pending_btn.clicked.connect(self._on_pending_clicked)
        layout.addWidget(pending_btn)
        
        layout.addSpacing(20)

        # Статус соединения
# ...



        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: #FF4444; font-size: 16px;")
        layout.addWidget(self.connection_indicator)
        
        self.connection_label = QLabel("Нет связи")
        self.connection_label.setStyleSheet("color: #AAAAAA; font-size: 14px;")
        layout.addWidget(self.connection_label)
        
        layout.addSpacing(20)
        
        # Дата и Время
        self.datetime_label = QLabel()
        self.datetime_label.setStyleSheet("font-size: 16px; color: #00CCFF; font-weight: bold;")
        layout.addWidget(self.datetime_label)
        
        layout.addSpacing(20)
        
        # Кнопка настроек
        settings_btn = QPushButton("⚙ Настройки")
        settings_btn.setObjectName("settings_button")
        settings_btn.setFixedWidth(120)
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)
        
        return frame
    
    def _create_left_panel(self) -> QWidget:
        """Левая панель: Вес и Ввод данных."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 10, 0)
        
        # --- Блок Веса ---
        weight_group = QGroupBox("Текущий вес")
        weight_layout = QVBoxLayout(weight_group)
        
        # Переключатель ручного режима (Кнопка)
        # Переключатель ручного режима (Кнопка)
        self.manual_mode_btn = QPushButton("РЕЖИМ: АВТО")
        self.manual_mode_btn.setCheckable(True)
        self.manual_mode_btn.setCursor(Qt.PointingHandCursor)
        self.manual_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-size: 16px; 
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:checked {
                background-color: #FF9800;
            }
        """)
        self.manual_mode_btn.setChecked(True)
        self.manual_mode_btn.toggled.connect(self._on_manual_mode_changed)
        # Принудительно вызываем обработчик, чтобы применились стили (moved to end)
        weight_layout.addWidget(self.manual_mode_btn)
        
        self.weight_display = QLabel("0.0 кг")
        self.weight_display.setAlignment(Qt.AlignCenter)
        self.weight_display.setObjectName("weight_display")
        weight_layout.addWidget(self.weight_display)
        
        # Индикатор (или поле ввода) ручного режима (заглушка, т.к. ввод теперь в Tara/Brutto)
        self.manual_input_label = QLabel("РУЧНОЙ ВВОД В ТАБЛИЦЕ НИЖЕ")
        self.manual_input_label.setAlignment(Qt.AlignCenter)
        self.manual_input_label.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 18px;")
        self.manual_input_label.hide()
        weight_layout.addWidget(self.manual_input_label)
        
        self.stable_indicator = QLabel("⌛ Ожидание стабилизации...")
        self.stable_indicator.setAlignment(Qt.AlignCenter)
        self.stable_indicator.setStyleSheet("color: #FFaa00; font-size: 14px;")
        weight_layout.addWidget(self.stable_indicator)
        
        layout.addWidget(weight_group)
        



        # --- Инфо о зафиксированном весе ---
        fixed_group = QGroupBox("Текущее взвешивание")
        fixed_layout = QGridLayout(fixed_group)
        
        # ТАРА
        fixed_layout.addWidget(QLabel("ТАРА:"), 0, 0)
        self.tara_input = QDoubleSpinBox()
        self.tara_input.setRange(0, 100000)
        self.tara_input.setDecimals(1)
        self.tara_input.setSuffix(" кг")
        self.tara_input.setReadOnly(True)
        self.tara_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.tara_input.setAlignment(Qt.AlignRight)
        self.tara_input.setStyleSheet("background-color: transparent; border: none; font-size: 24px; font-weight: bold; color: white;")
        self.tara_input.valueChanged.connect(self._on_manual_weight_changed)
        fixed_layout.addWidget(self.tara_input, 0, 1)
        
        fixed_layout.addWidget(self.tara_input, 0, 1)
        
        # БРУТТО
        fixed_layout.addWidget(QLabel("БРУТТО:"), 1, 0)
        self.brutto_input = QDoubleSpinBox()
        self.brutto_input.setRange(0, 100000)
        self.brutto_input.setDecimals(1)
        self.brutto_input.setSuffix(" кг")
        self.brutto_input.setReadOnly(True)
        self.brutto_input.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.brutto_input.setAlignment(Qt.AlignRight)
        self.brutto_input.setStyleSheet("background-color: transparent; border: none; font-size: 24px; font-weight: bold; color: white;")
        self.brutto_input.valueChanged.connect(self._on_manual_weight_changed)
        fixed_layout.addWidget(self.brutto_input, 1, 1)
        
        fixed_layout.addWidget(self.brutto_input, 1, 1)
        
        # НЕТТО
        fixed_layout.addWidget(QLabel("НЕТТО:"), 2, 0)
        self.netto_display = QLabel("—")
        self.netto_display.setObjectName("netto_label")
        self.netto_display.setAlignment(Qt.AlignRight)
        self.netto_display.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 24px;")
        fixed_layout.addWidget(self.netto_display, 2, 1, 1, 2) # Span 2 columns
        
        layout.addWidget(fixed_group)

        
        # --- Ввод данных ---
        input_group = QGroupBox("Данные автомобиля")
        input_layout = QFormLayout(input_group)
        input_layout.setSpacing(10) # Уменьшил spacing
        input_layout.setContentsMargins(5, 5, 5, 5) # Уменьшил margins
        
        self.car_number_edit = QLineEdit()
        self.car_number_edit.setPlaceholderText("A 123 AA")
        self.car_number_edit.setFixedHeight(50)
        self.car_number_edit.setStyleSheet("font-size: 16px;")
        self.car_number_edit.textChanged.connect(self._to_uppercase)
        self.car_number_edit.textChanged.connect(self._on_data_changed)
        self.car_number_edit.editingFinished.connect(self._check_pending_weighing)
        self.car_number_edit.returnPressed.connect(lambda: self.fio_edit.setFocus())
        input_layout.addRow("Госномер:", self.car_number_edit)
        
        self.fio_edit = QLineEdit()
        self.fio_edit.setPlaceholderText("Иванов И.И.")
        self.fio_edit.setFixedHeight(50)
        self.fio_edit.textChanged.connect(self._on_data_changed)
        self.fio_edit.returnPressed.connect(lambda: self.fraction_combo.setFocus())
        input_layout.addRow("Водитель:", self.fio_edit)
        
        # Компания (контрагент)
        self.company_combo = QComboBox()
        self.company_combo.setFixedHeight(50)
        self.company_combo.setEditable(True)
        self.company_combo.setInsertPolicy(QComboBox.NoInsert)
        self.company_combo.lineEdit().setPlaceholderText("Начните вводить...")
        self.company_combo.currentTextChanged.connect(self._on_data_changed)
        input_layout.addRow("Компания:", self.company_combo)
        self._server_counterparties = []

        self.fraction_combo = QComboBox()
        self.fraction_combo.setFixedHeight(50)
        self.fraction_combo.addItems(self.config_manager.config.fractions)
        self.fraction_combo.setEditable(False)
        self.fraction_combo.currentTextChanged.connect(self._on_data_changed)
        input_layout.addRow("Груз:", self.fraction_combo)

        # Заметки
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Дополнительная информация...")
        self.notes_edit.setFixedHeight(80)
        self.notes_edit.textChanged.connect(self._on_data_changed)
        input_layout.addRow("Заметки:", self.notes_edit)
        
        layout.addWidget(input_group)
        # Удаляем addStretch чтобы не сжимало контент слишком сильно
        # layout.addStretch() 
        
        return widget

    def _create_right_panel(self) -> QWidget:
        """Правая панель: Камера и Таблица."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 0, 0, 0)
        
        # --- Камера ---
        camera_group = QGroupBox("Видеонаблюдение")
        camera_layout = QVBoxLayout(camera_group)
        
        # Виджет для отображения камеры
        self.camera_view = QLabel("Нет сигнала")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumHeight(400)
        self.camera_view.setStyleSheet("background-color: #000000; color: #555555; border-radius: 5px;")
        self.camera_view.setScaledContents(True)  # Растягивать изображение
        camera_layout.addWidget(self.camera_view)
        
        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self._on_camera_changed)
        camera_layout.addWidget(self.camera_selector)
        
        layout.addWidget(camera_group)
        
        # --- Таблица журнала ---
        history_group = QGroupBox("Журнал взвешиваний (Сегодня)")
        history_layout = QVBoxLayout(history_group)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Время", "Авто", "Груз", "Нетто", "Статус"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_group)
        
        return widget
    
    def _create_action_bar(self) -> QWidget:
        """Нижняя панель с кнопками действий."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(20)
        
        # Кнопка ТАРА
        self.btn_tara = QPushButton("🚛 Зафиксировать ТАРУ [F1]")
        self.btn_tara.setObjectName("tara_button")
        self.btn_tara.setFixedHeight(60)
        self.btn_tara.setCursor(Qt.PointingHandCursor)
        self.btn_tara.clicked.connect(self._fix_tara)
        layout.addWidget(self.btn_tara)
        
        # Кнопка БРУТТО
        self.btn_brutto = QPushButton("⚖ Зафиксировать БРУТТО [F2]")
        self.btn_brutto.setObjectName("brutto_button")
        self.btn_brutto.setFixedHeight(60)
        self.btn_brutto.setCursor(Qt.PointingHandCursor)
        self.btn_brutto.clicked.connect(self._fix_brutto)
        layout.addWidget(self.btn_brutto)
        
        # Кнопка СОХРАНИТЬ
        self.btn_save = QPushButton("💾 Сохранить [F3]")
        self.btn_save.setObjectName("save_button")
        self.btn_save.setFixedHeight(60)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_weighing)
        layout.addWidget(self.btn_save)
        
        # Кнопка СБРОС
        self.btn_reset = QPushButton("✖ Сброс [Esc]")
        self.btn_reset.setObjectName("reset_button")
        self.btn_reset.setFixedHeight(60)
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.clicked.connect(self._reset_weighing)
        layout.addWidget(self.btn_reset)
        
        return widget
        
    def _start_timers(self) -> None:
        """Запуск таймеров обновления интерфейса."""
        # Таймер времени
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()
        
        # Таймер камеры (обновление превью)
        # В этой версии инициализируем объект захвата при выборе камеры
        self.cap = None
        self.camera_timer = QTimer(self)
        self.camera_timer.timeout.connect(self._update_camera_preview)
        self.camera_timer.start(100) # 10 кадров в секунду (для плавности, если канал позволяет)
        
        # Таймер обновления списка камер при старте
        QTimer.singleShot(500, self._update_camera_list)
        
    def _update_clock(self) -> None:
        """Обновление часов."""
        now = datetime.now()
        self.datetime_label.setText(now.strftime("%d.%m.%Y %H:%M:%S"))
        
    def _update_camera_list(self) -> None:
        """Обновить список доступных камер."""
        self.camera_selector.blockSignals(True)
        self.camera_selector.clear()
        cameras = self.config_manager.config.cameras
        for i, cam in enumerate(cameras):
            if cam.get('enabled', True):
                self.camera_selector.addItem(cam.get('name', f'Камера {i+1}'), cam.get('url'))
        self.camera_selector.blockSignals(False)
        
        # Инициализируем первую камеру если есть
        if self.camera_selector.count() > 0:
            self._on_camera_changed(0)
    
    def _on_camera_changed(self, index: int) -> None:
        """Смена активной камеры."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        url = self.camera_selector.itemData(index)
        if url:
             # В реальном приложении это должно быть в отдельном потоке
            try:
                self.cap = cv2.VideoCapture(url)
            except Exception as e:
                logger.error(f"Ошибка открытия камеры {url}: {e}")
        
    def _update_camera_preview(self) -> None:
        """Обновление картинки с камеры."""
        if self.camera_selector.count() == 0 or self.cap is None or not self.cap.isOpened():
            self.camera_view.setText("Нет сигнала")
            return
            
        try:
            ret, frame = self.cap.read()
            if ret:
                # Конвертация BGR -> RGB
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Масштабирование с сохранением пропорций
                pixmap = QPixmap.fromImage(qt_image)
                self.camera_view.setPixmap(pixmap.scaled(
                    self.camera_view.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                ))
            else:
                # Если кадр не прочитан (например, поток прервался), пробуем переоткрыть?
                # Для простоты пока ничего не делаем, или можно self.cap.release()
                pass
            
        except Exception as e:
            # logger.error(f"Ошибка обновления превью: {e}") 
            pass

    def _connect_signals(self) -> None:
        """Подключение сигналов."""
        self.manager.weight_updated.connect(self._on_weight_updated)
        self.manager.tara_fixed.connect(self._on_tara_fixed)
        self.manager.brutto_fixed.connect(self._on_brutto_fixed)
        self.manager.netto_calculated.connect(self._on_netto_calculated)
        self.manager.weighing_saved.connect(self._on_weighing_saved)
        self.manager.state_changed.connect(self._on_state_changed)
        self.manager.connection_status.connect(self._on_connection_status)
        self.manager.error.connect(self._show_error)
        self.manager.lookups_loaded.connect(self._on_lookups_loaded)

    def _setup_shortcuts(self) -> None:
        """Настройка горячих клавиш."""
        # Используем QShortcut для глобальной доступности в окне
        QShortcut(QKeySequence(Qt.Key_F1), self).activated.connect(self._fix_tara)
        QShortcut(QKeySequence(Qt.Key_F2), self).activated.connect(self._fix_brutto)
        QShortcut(QKeySequence(Qt.Key_F3), self).activated.connect(self._save_weighing)
        QShortcut(QKeySequence(Qt.Key_Escape), self).activated.connect(self._reset_weighing)
        QShortcut(QKeySequence(Qt.Key_F5), self).activated.connect(self._open_settings)

    @Slot(float, bool)
    def _on_weight_updated(self, weight: float, is_stable: bool) -> None:
        self.weight_display.setText(f"{weight:.1f} кг")
        self.weight_display.setProperty("stable", is_stable)
        
        # Обновляем стиль для смены цвета рамки
        self.weight_display.style().unpolish(self.weight_display)
        self.weight_display.style().polish(self.weight_display)
        
        if is_stable:
            self.stable_indicator.setText("✔ Вес стабилизирован")
            self.stable_indicator.setStyleSheet("color: #00FF00; font-size: 14px;")
        else:
            self.stable_indicator.setText("⌛ Ожидание стабилизации...")
            self.stable_indicator.setStyleSheet("color: #FFaa00; font-size: 14px;")

    @Slot(float)
    def _on_tara_fixed(self, weight: float) -> None:
        # Обновляем поле ввода (оно служит индикатором в обоих режимах)
        self.tara_input.blockSignals(True) # Чтобы не триггерить пересчет
        self.tara_input.setValue(weight)
        self.tara_input.blockSignals(False)
        self._on_manual_weight_changed() # Пересчитать нетто
    
    @Slot(float)
    def _on_brutto_fixed(self, weight: float) -> None:
        # Обновляем поле ввода (оно служит индикатором в обоих режимах)
        self.brutto_input.blockSignals(True)
        self.brutto_input.setValue(weight)
        self.brutto_input.blockSignals(False)
        self._on_manual_weight_changed()

    @Slot(float)
    def _on_netto_calculated(self, weight: float) -> None:
        self.netto_display.setText(f"{weight:.1f} кг")

    @Slot(object)
    def _on_weighing_saved(self, weighing) -> None:
        QMessageBox.information(self, "Успех", f"Взвешивание сохранено!\nНетто: {weighing.netto} кг")
        self._update_history_table()

    @Slot(object)
    def _on_state_changed(self, state: WeighingState) -> None:
        # Обновление состояния кнопок
        self.btn_tara.setEnabled(state == WeighingState.IDLE)
        self.btn_brutto.setEnabled(state == WeighingState.TARA_FIXED)
        self.btn_save.setEnabled(state in (WeighingState.BRUTTO_FIXED, WeighingState.READY_TO_SAVE))
        
        # Стиль кнопок можно менять динамически при желании
        
    @Slot(bool)
    def _on_connection_status(self, connected: bool) -> None:
        if connected:
            self.connection_indicator.setText("●")
            self.connection_indicator.setStyleSheet("color: #00FF00; font-size: 16px;")
            self.connection_label.setText("Подключено")
        else:
            self.connection_indicator.setText("●")
            self.connection_indicator.setStyleSheet("color: #FF4444; font-size: 16px;")
            self.connection_label.setText("Нет связи")

    @Slot(str)
    def _show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Ошибка", message)

    @Slot(dict)
    def _on_lookups_loaded(self, data: dict) -> None:
        """Справочники загружены с сервера — настраиваем автоподсказки."""
        # Автоподсказки для госномера
        cars = data.get('cars', [])
        if cars:
            car_completer = QCompleter(cars, self)
            car_completer.setCaseSensitivity(Qt.CaseInsensitive)
            car_completer.setFilterMode(Qt.MatchContains)
            self.car_number_edit.setCompleter(car_completer)

        # Автоподсказки для водителя
        drivers = data.get('drivers', [])
        if drivers:
            driver_completer = QCompleter(drivers, self)
            driver_completer.setCaseSensitivity(Qt.CaseInsensitive)
            driver_completer.setFilterMode(Qt.MatchContains)
            self.fio_edit.setCompleter(driver_completer)

        # Обновляем грузы из сервера (добавляем к локальным)
        fractions = data.get('fractions', [])
        if fractions:
            server_fractions = [f['title'] for f in fractions]
            existing = [self.fraction_combo.itemText(i) for i in range(self.fraction_combo.count())]
            for f in server_fractions:
                if f not in existing:
                    self.fraction_combo.addItem(f)

        # Заполняем dropdown компаний
        self._server_counterparties = data.get('counterparties', [])
        if self._server_counterparties:
            self.company_combo.clear()
            self.company_combo.addItem('')  # пустой первый элемент
            for c in self._server_counterparties:
                self.company_combo.addItem(c['title'], c['id'])
            # Автоподсказка при вводе
            company_completer = QCompleter([c['title'] for c in self._server_counterparties], self)
            company_completer.setCaseSensitivity(Qt.CaseInsensitive)
            company_completer.setFilterMode(Qt.MatchContains)
            self.company_combo.setCompleter(company_completer)

        logger.info(f"Автоподсказки настроены: {len(cars)} номеров, {len(drivers)} водителей, {len(fractions)} грузов")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config_manager, self)
        # Останавливаем камеру пока настройки открыты (чтобы не занимать ресурсы)
        if self.cap:
            self.cap.release()
            self.cap = None
            
        if dialog.exec():
            self.manager.update_config()
            # Обновляем список фракций
            self.fraction_combo.clear()
            self.fraction_combo.addItems(self.config_manager.config.fractions)
            self._update_camera_list()
            # Обновляем метку завода в шапке
            factory_name = getattr(self.config_manager.config, 'factory_name', '') or ''
            if hasattr(self, 'factory_label'):
                self.factory_label.setText(
                    f"🏭 {factory_name}" if factory_name else "🏭 завод не выбран"
                )
            
        # Восстанавливаем камеру
        if self.camera_selector.count() > 0:
            self._on_camera_changed(self.camera_selector.currentIndex())

    def _get_counterparty(self) -> tuple:
        """Получить id и название выбранного контрагента."""
        idx = self.company_combo.currentIndex()
        cp_id = self.company_combo.itemData(idx) if idx > 0 else ""
        cp_name = self.company_combo.currentText().strip()
        return cp_id or "", cp_name

    def _fix_tara(self) -> None:
        if self.manual_mode_btn.isChecked():  # Ручной режим
            tara_val = self.tara_input.value()
            if tara_val <= 0:
                QMessageBox.warning(self, "Ошибка", "Введите вес тары!")
                return
            self.manager.fix_tara(tara_val)
            # Сразу сохраняем как ожидающую (brutto=0)
            car = self.car_number_edit.text().strip()
            if not car:
                QMessageBox.warning(self, "Ошибка", "Введите госномер!")
                return
            if car:
                cp_id, cp_name = self._get_counterparty()
                self.manager.save_weighing(
                    car,
                    self.fio_edit.text(),
                    self.fraction_combo.currentText(),
                    self.notes_edit.toPlainText(),
                    cp_id, cp_name
                )
                QMessageBox.information(
                    self, "Тара зафиксирована",
                    f"Тара: {tara_val:.0f} кг\n"
                    f"Машина {car} добавлена в ожидающие."
                )
        else:
            self.manager.fix_tara()

    def _fix_brutto(self) -> None:
        if self.manual_mode_btn.isChecked(): # Ручной режим
            self.manager.fix_brutto(self.brutto_input.value())
        else:
            self.manager.fix_brutto()

    def _save_weighing(self) -> None:
        # Снимаем фокус с полей, чтобы применились введенные значения
        self.setFocus()
        
        if self.manual_mode_btn.isChecked():
            tara_val = self.tara_input.value()
            brutto_val = self.brutto_input.value()
            
            # 1. Логика для ЗАЕЗДА (Только Тара)
            if tara_val > 0 and brutto_val == 0:
                # Если мы еще не зафиксировали тару, фиксируем сейчас
                if self.manager.state == WeighingState.IDLE:
                    if not self.manager.fix_tara(tara_val):
                        return
                
                # Сохраняем как "Незавершенное"
                cp_id, cp_name = self._get_counterparty()
                if self.manager.save_weighing(
                    self.car_number_edit.text(),
                    self.fio_edit.text(),
                    self.fraction_combo.currentText(),
                    self.notes_edit.toPlainText(),
                    cp_id, cp_name
                ):
                    QMessageBox.information(
                        self, "Заезд", 
                        f"Взвешивание (ТАРА) сохранено.\n\n"
                        f"Машина {self.car_number_edit.text()} добавлена в список ожидающих."
                    )
                    return

            # 2. Логика для ВЫЕЗДА (Тара + Брутто)
            elif tara_val > 0 and brutto_val > 0:
                # Брутто меньше тары?
                if brutto_val < tara_val:
                    QMessageBox.warning(self, "Ошибка", "Брутто не может быть меньше Тары!")
                    return
                
                # Фиксируем Брутто (если еще не)
                if self.manager.state != WeighingState.BRUTTO_FIXED:
                     # Если мы были в IDLE (сразу ввели оба веса), сначала фиксируем тару
                     if self.manager.state == WeighingState.IDLE:
                         if not self.manager.fix_tara(tara_val): return
                     
                     if not self.manager.fix_brutto(brutto_val):
                         return
            
            # 3. Нет веса
            elif tara_val == 0 and brutto_val == 0:
                QMessageBox.warning(self, "Ошибка", "Введите вес!")
                return
        
        # Сохранение (для Авто режима или если прошли проверки выше)
        cp_id, cp_name = self._get_counterparty()
        self.manager.save_weighing(
            self.car_number_edit.text(),
            self.fio_edit.text(),
            self.fraction_combo.currentText(),
            self.notes_edit.toPlainText(),
            cp_id, cp_name
        )

    def _reset_weighing(self) -> None:
        self.manager.reset()
        self.netto_display.setText("— кг")
        self.car_number_edit.clear()
        self.fio_edit.clear()
        self.company_combo.setCurrentIndex(0)
        self.notes_edit.clear()

    def _on_data_changed(self) -> None:
        self.manager.set_weighing_data(
            self.car_number_edit.text(),
            self.fio_edit.text(),
            self.fraction_combo.currentText(),
            self.notes_edit.toPlainText()
        )
        
    def _to_uppercase(self, text: str) -> None:
        """Перевести в верхний регистр."""
        if text != text.upper():
            self.car_number_edit.setText(text.upper())
            
    def _open_history(self) -> None:
        """Открыть окно истории."""
        dialog = HistoryWindow(self.manager.database, self)
        dialog.exec()

    def _export_today_report(self) -> None:
        """Быстрый экспорт отчета за сегодня."""
        try:
            import xlsxwriter
            
            # Получаем данные за сегодня
            today_str = datetime.now().date().isoformat()
            weighings = self.manager.database.get_filtered(
                start_date=f"{today_str}T00:00:00",
                end_date=f"{today_str}T23:59:59"
            )
            
            if not weighings:
                QMessageBox.information(self, "Инфо", "За сегодня нет завершенных взвешиваний.")
                return

            filename, _ = QFileDialog.getSaveFileName(
                self, "Сохранить отчет за сегодня",
                f"report_{today_str}.xlsx",
                "Excel Files (*.xlsx)"
            )

            if not filename:
                return

            workbook = xlsxwriter.Workbook(filename)
            worksheet = workbook.add_worksheet("Отчет")

            # Форматы
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'bg_color': '#D3D3D3', 'border': 1})
            date_format = workbook.add_format({'num_format': 'dd.mm.yyyy hh:mm', 'border': 1})
            cell_format = workbook.add_format({'border': 1})

            # Заголовки
            headers = ["ID", "Дата/Время", "Автомобиль", "Тара (кг)", "Брутто (кг)", "Нетто (кг)", "Фракция", "Водитель", "Примечание"]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Данные
            for row, w in enumerate(weighings, start=1):
                try:
                    dt = datetime.fromisoformat(w.datetime) if w.datetime else ""
                except:
                    dt = w.datetime

                worksheet.write(row, 0, w.id, cell_format)
                worksheet.write_datetime(row, 1, dt, date_format) if isinstance(dt, datetime) else worksheet.write(row, 1, str(dt), cell_format)
                worksheet.write(row, 2, w.car_number, cell_format)
                worksheet.write(row, 3, w.tara, cell_format)
                worksheet.write(row, 4, w.brutto, cell_format)
                worksheet.write(row, 5, w.netto, cell_format)
                worksheet.write(row, 6, w.fraction, cell_format)
                worksheet.write(row, 7, w.fio, cell_format)
                worksheet.write(row, 8, w.notes, cell_format)

            # Автоширина
            worksheet.set_column(0, 0, 5)
            worksheet.set_column(1, 1, 18)
            worksheet.set_column(2, 2, 12)
            worksheet.set_column(3, 5, 10)
            worksheet.set_column(6, 7, 20)
            worksheet.set_column(8, 8, 30)

            workbook.close()
            QMessageBox.information(self, "Успех", f"Отчет за сегодня сохранен:\n{filename}")
            
        except ImportError:
            QMessageBox.critical(self, "Ошибка", "Не установлен пакет xlsxwriter.\nПожалуйста, установите его.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчет:\n{e}")

    def _on_pending_clicked(self) -> None:
        """Открыть список ожидающих машин."""
        # DEBUG: Проверка нажатия
        print("DEBUG: Pending button clicked!") 
        # QMessageBox.information(self, "Debug", "Кнопка нажата!") # Раскомментируйте если консоль не видна
        
        try:
            pending = self.manager.database.get_incomplete_weighings()
            if not pending:
                QMessageBox.information(self, "Инфо", "Нет ожидающих машин (незавершенных взвешиваний)")
                return
                
            dialog = QDialog(self)
            dialog.setWindowTitle("Ожидающие автомобили")
            dialog.setMinimumSize(600, 400)
            dialog.setStyleSheet(self.styleSheet())
            
            layout = QVBoxLayout(dialog)
            
            table = QTableWidget()
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["Дата", "Авто", "Тара", "Водитель"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            table.setRowCount(len(pending))
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            
            for i, w in enumerate(pending):
                # Время
                try:
                    dt = datetime.fromisoformat(w.datetime) if w.datetime else None
                    time_display = dt.strftime("%d.%m %H:%M") if dt else "-"
                except:
                    time_display = str(w.datetime)

                table.setItem(i, 0, QTableWidgetItem(time_display))
                table.setItem(i, 1, QTableWidgetItem(w.car_number))
                table.setItem(i, 2, QTableWidgetItem(str(w.tara)))
                table.setItem(i, 3, QTableWidgetItem(w.fio))
                
            layout.addWidget(table)
            
            btn_layout = QHBoxLayout()
            select_btn = QPushButton("Выбрать")
            select_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
            select_btn.clicked.connect(dialog.accept)
            btn_layout.addWidget(select_btn)

            def delete_selected():
                row = table.currentRow()
                if row < 0:
                    QMessageBox.warning(dialog, "Ошибка", "Выберите запись для удаления")
                    return
                w = pending[row]
                confirm = QMessageBox.question(
                    dialog, "Удалить?",
                    f"Удалить ожидающую запись?\n{w.car_number} — тара {w.tara:.0f} кг",
                    QMessageBox.Yes | QMessageBox.No
                )
                if confirm == QMessageBox.Yes:
                    self.manager.database.delete_weighing(w.id)
                    pending.pop(row)
                    table.removeRow(row)
                    if not pending:
                        dialog.reject()

            delete_btn = QPushButton("Удалить")
            delete_btn.setStyleSheet("background-color: #F44336; color: white; padding: 10px;")
            delete_btn.clicked.connect(delete_selected)
            btn_layout.addWidget(delete_btn)

            cancel_btn = QPushButton("Отмена")
            cancel_btn.clicked.connect(dialog.reject)
            btn_layout.addWidget(cancel_btn)

            layout.addLayout(btn_layout)

            if dialog.exec() == QDialog.Accepted:
                row = table.currentRow()
                if row >= 0:
                    selected_weighing = pending[row]
                    self.manager.load_weighing(selected_weighing)
                    
                    # Заполняем поля UI
                    # Блокируем сигналы, чтобы не триггерить лишние обновления
                    self.car_number_edit.blockSignals(True)
                    self.fio_edit.blockSignals(True)
                    self.fraction_combo.blockSignals(True)
                    self.notes_edit.blockSignals(True)

                    self.car_number_edit.setText(selected_weighing.car_number)
                    self.fio_edit.setText(selected_weighing.fio)
                    self.fraction_combo.setCurrentText(selected_weighing.fraction)
                    self.notes_edit.setText(selected_weighing.notes)
                    
                    self.car_number_edit.blockSignals(False)
                    self.fio_edit.blockSignals(False)
                    self.fraction_combo.blockSignals(False)
                    self.notes_edit.blockSignals(False)
                    
                    # Принудительно обновляем данные в менеджере
                    self._on_data_changed()
                    
                    QMessageBox.information(self, "Загружено", f"Автомобиль {selected_weighing.car_number} выбран. Взвесьте БРУТТО.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть список ожидающих:\n{e}")

    def _open_keypad(self, target_input: QDoubleSpinBox) -> None:
        """Открыть цифровую клавиатуру."""
        dialog = KeypadDialog(self, target_input.value())
        if dialog.exec():
            value = dialog.get_value()
            target_input.setValue(value)

    def _open_pending_trucks(self) -> None:
        """Открыть список ожидающих (незавершенных) машин."""
        pending = self.manager.database.get_incomplete_weighings()
        
        if not pending:
            QMessageBox.information(self, "Инфо", "Нет ожидающих машин")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Ожидающие автомобили")
        dialog.setMinimumSize(600, 400)
        # Применяем общий стиль
        dialog.setStyleSheet(self.styleSheet())
        
        layout = QVBoxLayout(dialog)
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Дата", "Авто", "Тара", "Водитель"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setRowCount(len(pending))
        
        for i, w in enumerate(pending):
            try:
                # Если w.datetime это строка, конвертируем
                dt_str = w.datetime
                if not dt_str:
                    time_display = "-"
                else:
                    dt = datetime.fromisoformat(dt_str)
                    time_display = dt.strftime("%d.%m %H:%M")
            except:
                time_display = str(w.datetime)

            table.setItem(i, 0, QTableWidgetItem(time_display))
            table.setItem(i, 1, QTableWidgetItem(w.car_number))
            table.setItem(i, 2, QTableWidgetItem(str(w.tara)))
            table.setItem(i, 3, QTableWidgetItem(w.fio))
            
        layout.addWidget(table)
        
        btn_layout = QHBoxLayout()
        select_btn = QPushButton("Выбрать")
        select_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px;")
        select_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        if dialog.exec() == QDialog.Accepted:
            row = table.currentRow()
            if row >= 0:
                selected_weighing = pending[row]
                self.manager.load_weighing(selected_weighing)
                
                # Заполняем поля UI
                self.car_number_edit.setText(selected_weighing.car_number)
                self.fio_edit.setText(selected_weighing.fio)
                self.fraction_combo.setCurrentText(selected_weighing.fraction)
                self.notes_edit.setText(selected_weighing.notes)
                
                QMessageBox.information(self, "Загружено", f"Автомобиль {selected_weighing.car_number} выбран. Взвесьте БРУТТО.")

    def _on_manual_mode_changed(self, checked: bool) -> None:
        """Переключение ручного режима."""
        self.manager.set_manual_mode(checked)
        
        if checked:
            self.manual_mode_btn.setText("РЕЖИМ: РУЧНОЙ")
            self.weight_display.hide()
            self.manual_input_label.show()
            self.stable_indicator.hide()
            
            # Кнопки фиксации доступны и в ручном режиме
            self.btn_tara.show()
            self.btn_brutto.show()

            
            # Убираем суффикс и делаем доступным
            self.tara_input.setReadOnly(False)
            self.tara_input.setSuffix("") 
            self.tara_input.setStyleSheet("background-color: #333; border: 1px solid #555; font-size: 24px; color: white;")
            
            self.brutto_input.setReadOnly(False)
            self.brutto_input.setSuffix("")
            self.brutto_input.setStyleSheet("background-color: #333; border: 1px solid #555; font-size: 24px; color: white;")

            # Стиль кнопки для наглядности
            self.manual_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800; 
                    color: white; 
                    font-size: 16px; 
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
        else:
            self.manual_mode_btn.setText("РЕЖИМ: АВТО")
            self.weight_display.show()
            self.manual_input_label.hide()
            self.stable_indicator.show()
            
            # Скрываем кнопки
            # Кнопок больше нет
            
            # Показываем кнопки фиксации
            self.btn_tara.show()
            self.btn_brutto.show()

            
            # Блокируем ввод и возвращаем суффикс
            self.tara_input.setReadOnly(True)
            self.tara_input.setSuffix(" кг")
            # Восстанавливаем стиль Auto (прозрачный)
            self.tara_input.setStyleSheet("background-color: transparent; border: none; font-size: 24px; font-weight: bold; color: white;")
            
            self.brutto_input.setReadOnly(True)
            self.brutto_input.setSuffix(" кг")
            self.brutto_input.setStyleSheet("background-color: transparent; border: none; font-size: 24px; font-weight: bold; color: white;")
            
            self.manual_mode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50; 
                    color: white; 
                    font-size: 16px; 
                    font-weight: bold;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)

    def _on_manual_weight_changed(self) -> None:
        """Изменение вручную введенного веса (расчет нетто)."""
        tara = self.tara_input.value()
        brutto = self.brutto_input.value()
        
        # Если введены оба значения, считаем нетто
        # В ручном режиме мы не блокируем отрицательное нетто, но показываем как есть
        netto = brutto - tara
        
        self.netto_display.setText(f"{netto:.1f} кг")
        
        # Обновляем менеджер, если нужно (например, если сохранение берет данные из менеджера)
        # Но лучше при сохранении брать из GUI в ручном режиме.
        
    def _update_history_table(self) -> None:
        """Обновить таблицу истории."""
        # Получаем данные за последние 24 часа или последние 50 записей
        weighings = self.manager.database.get_recent(50)
        self.history_table.setRowCount(len(weighings))
        
        for i, w in enumerate(weighings):
            # Время
            try:
                dt = datetime.fromisoformat(w.datetime)
                time_str = dt.strftime("%H:%M")
            except:
                time_str = w.datetime
            
            # Статус отправки
            status_item = QTableWidgetItem("✔" if w.sent else "⏳")
            status_item.setToolTip("Отправлено на сервер" if w.sent else "В очереди")
            
            self.history_table.setItem(i, 0, QTableWidgetItem(time_str))
            self.history_table.setItem(i, 1, QTableWidgetItem(w.car_number))
            self.history_table.setItem(i, 2, QTableWidgetItem(w.fraction))
            self.history_table.setItem(i, 3, QTableWidgetItem(f"{w.netto:.0f}"))
            self.history_table.setItem(i, 4, status_item)

    def _check_pending_weighing(self) -> None:
        """Проверить, есть ли незавершенное взвешивание для этого номера."""
        # Блокируем повторный вызов если диалог уже открыт или данные обновляются
        if getattr(self, '_checking_pending', False):
            return
            
        number = self.car_number_edit.text().strip()
        if len(number) < 3: 
            return
        
        # Если мы уже работаем с этой машиной (ID совпадает), то не спрашиваем
        current = self.manager.get_current_weighing()
        if current and current.id and current.car_number == number:
            return

        # Ищем в базе
        self._checking_pending = True
        try:
            pending = self.manager.database.get_incomplete_by_number(number)
            if pending:
                tara_str = f"{pending.tara:.0f}"
                
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Машина на территории")
                msg_box.setText(f"Автомобиль {number} уже заезжал.\nТара: {tara_str} кг.\n\nЗагрузить данные для взвешивания БРУТТО?")
                msg_box.setIcon(QMessageBox.Question)
                yes_btn = msg_box.addButton("Да", QMessageBox.YesRole)
                no_btn = msg_box.addButton("Нет", QMessageBox.NoRole)
                msg_box.setDefaultButton(yes_btn)
                msg_box.exec()
                
                if msg_box.clickedButton() == yes_btn:
                    self.manager.load_weighing(pending)
                    # Обновляем поля UI (блокируем сигналы чтобы не зациклить)
                    self.fio_edit.blockSignals(True)
                    self.fraction_combo.blockSignals(True)
                    self.notes_edit.blockSignals(True)
                    
                    self.fio_edit.setText(pending.fio)
                    self.fraction_combo.setCurrentText(pending.fraction)
                    self.notes_edit.setText(pending.notes)
                    
                    self.fio_edit.blockSignals(False)
                    self.fraction_combo.blockSignals(False)
                    self.notes_edit.blockSignals(False)
                    
                    # Фокус на брутто
                    if self.manual_mode_btn.isChecked():
                        self.brutto_input.setFocus()
                        self.brutto_input.selectAll()
        finally:
            self._checking_pending = False

    def keyPressEvent(self, event) -> None:
        """Перехват нажатий клавиш для навигации."""
        focused_widget = self.focusWidget()
        
        # Навигация Enter -> Следующее поле
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Если это не QTextEdit (там Enter нужен для новой строки)
            # Хотя пользователь просил "на следующее поле", обычно для заметок Enter - это переход строки.
            # Но сделаем как просили, если это не многострочное поле или если нажат Ctrl+Enter
            if not isinstance(focused_widget, QTextEdit):
                self.focusNextChild()
                event.accept()
                return
        
        # Навигация стрелками (только если виджет не использует их сам)
        if event.key() == Qt.Key_Down:
            if not isinstance(focused_widget, (QTextEdit, QDoubleSpinBox, QComboBox)):
                self.focusNextChild()
                event.accept()
                return
        elif event.key() == Qt.Key_Up:
            if not isinstance(focused_widget, (QTextEdit, QDoubleSpinBox, QComboBox)):
                self.focusPreviousChild()
                event.accept()
                return
            
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        """Обработка закрытия окна."""
        if self.cap:
            self.cap.release()
            
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Выход")
        msg_box.setText("Вы уверены, что хотите выйти из программы?")
        msg_box.setIcon(QMessageBox.Question)
        yes_btn = msg_box.addButton("Да", QMessageBox.YesRole)
        no_btn = msg_box.addButton("Нет", QMessageBox.NoRole)
        msg_box.setDefaultButton(no_btn)
        msg_box.exec()
        
        reply = QMessageBox.Yes if msg_box.clickedButton() == yes_btn else QMessageBox.No
        
        if reply == QMessageBox.Yes:
            logger.info("Закрытие приложения")
            self.manager.stop()
            event.accept()
        else:
            event.ignore()
