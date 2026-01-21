from datetime import datetime, timedelta
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel, QDateEdit, QLineEdit, QGroupBox,
    QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from ..data.database import Database
from ..data.models import Weighing
from .styles import COLORS

class HistoryWindow(QDialog):
    """Окно просмотра истории взвешиваний."""
    
    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self.database = database
        
        self.setWindowTitle("Журнал взвешиваний")
        self.resize(1000, 600)
        self.setStyleSheet(f"background-color: {COLORS['background']}; color: {COLORS['text']};")
        
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # --- Фильтры ---
        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_group)
        
        # Даты
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        
        filter_layout.addWidget(QLabel("С:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("По:"))
        filter_layout.addWidget(self.date_to)
        
        # Госномер
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по госномеру...")
        filter_layout.addWidget(self.search_input)
        
        # Кнопка поиска
        self.btn_search = QPushButton("Найти")
        self.btn_search.clicked.connect(self._load_data)
        self.btn_search.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; padding: 5px 15px;")
        filter_layout.addWidget(self.btn_search)
        
        layout.addWidget(filter_group)
        
        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Время", "Авто", "Водитель", "Груз", "Нетто (кг)", "Заметки", "Статус"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch) # Груз растягивается
        header.setSectionResizeMode(6, QHeaderView.Stretch) # Заметки растягиваются
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # --- Кнопки действий ---
        action_layout = QHBoxLayout()
        
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        self.btn_export = QPushButton("📤 Экспорт в Excel")
        self.btn_export.setStyleSheet("background-color: #007ACC; color: white; padding: 5px 20px;")
        self.btn_export.clicked.connect(self._export_to_excel)
        action_layout.addWidget(self.btn_export)
        
        action_layout.addStretch()
        action_layout.addWidget(self.btn_close)
        
        layout.addLayout(action_layout)

    def _load_data(self) -> None:
        """Загрузка данных с учетом фильтров."""
        start_date = self.date_from.date().toString("yyyy-MM-dd") + "T00:00:00"
        end_date = self.date_to.date().toString("yyyy-MM-dd") + "T23:59:59"
        car_number = self.search_input.text().strip()
        
        weighings = self.database.get_filtered(
            start_date=start_date,
            end_date=end_date,
            car_number=car_number if car_number else None
        )
        
        self.table.setRowCount(len(weighings))
        
        for i, w in enumerate(weighings):
            # ID
            self.table.setItem(i, 0, QTableWidgetItem(str(w.id)))
            
            # Время (форматирование)
            try:
                dt = datetime.fromisoformat(w.datetime)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = w.datetime
            self.table.setItem(i, 1, QTableWidgetItem(time_str))
            
            # Авто
            self.table.setItem(i, 2, QTableWidgetItem(w.car_number))
            
            # Водитель
            self.table.setItem(i, 3, QTableWidgetItem(w.fio))
            
            # Груз/Фракция
            self.table.setItem(i, 4, QTableWidgetItem(w.fraction))
            
            # Нетто
            netto_item = QTableWidgetItem(f"{w.netto:.0f}")
            netto_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            netto_item.setFont(self.table.font()) # Жирный?
            self.table.setItem(i, 5, netto_item)

            # Заметки
            self.table.setItem(i, 6, QTableWidgetItem(w.notes))
            
            # Статус
            status_text = "Отправлено" if w.sent else "Не отправлено"
            status_item = QTableWidgetItem(status_text)
            if w.sent:
                status_item.setForeground(QColor(COLORS['success']))
            else:
                status_item.setForeground(QColor(COLORS['danger']))
            self.table.setItem(i, 7, status_item)
            
        self.setWindowTitle(f"История взвешиваний (Найдено: {len(weighings)})")

    def _export_to_excel(self) -> None:
        """Экспорт текущей выборки в Excel."""
        # Собираем данные из таблицы
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        
        if rows == 0:
             QMessageBox.warning(self, "Ошибка", "Нет данных для экспорта")
             return
             
        # Диалог сохранения
        from PySide6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить отчет", 
            f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
            
        try:
            import xlsxwriter
            workbook = xlsxwriter.Workbook(filename)
            worksheet = workbook.add_worksheet()
            
            # Стили
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D3D3D3',
                'border': 1
            })
            
            # Заголовки
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(cols)]
            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, header_format)
                
            # Данные
            for row in range(rows):
                for col in range(cols):
                    item = self.table.item(row, col)
                    text = item.text() if item else ""
                    
                    # Пытаемся конвертировать числа
                    try:
                        if col == 0: # ID
                            val = int(text)
                            worksheet.write_number(row + 1, col, val)
                        elif col == 5: # Нетто
                            val = float(text)
                            worksheet.write_number(row + 1, col, val)
                        else:
                            worksheet.write(row + 1, col, text)
                    except:
                         worksheet.write(row + 1, col, text)
                         
            # Автоширина (примерная)
            worksheet.set_column(0, 0, 5)  # ID
            worksheet.set_column(1, 1, 16) # Время
            worksheet.set_column(2, 2, 12) # Авто
            worksheet.set_column(3, 3, 20) # Водитель
            worksheet.set_column(4, 4, 15) # Груз
            worksheet.set_column(5, 5, 10) # Нетто
            worksheet.set_column(6, 6, 25) # Заметки
            worksheet.set_column(7, 7, 12) # Статус

            workbook.close()
            QMessageBox.information(self, "Успех", f"Отчет сохранен:\n{filename}")
            
        except Exception as e:
             QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

