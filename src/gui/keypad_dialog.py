from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, QWidget, QHBoxLayout
)
from PySide6.QtCore import Qt, Slot, QSize
from PySide6.QtGui import QFont

class KeypadDialog(QDialog):
    """
    Диалог с цифровой клавиатурой для ввода веса.
    """
    def __init__(self, parent=None, initial_value: float = 0.0):
        super().__init__(parent)
        self.setWindowTitle("Ввод веса")
        self.setFixedSize(300, 400)
        self.setStyleSheet("background-color: #2D2D2D; color: white;")
        
        layout = QVBoxLayout(self)
        
        # Дисплей
        self.display = QLineEdit()
        self.display.setText(str(initial_value))
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.display.setStyleSheet("""
            QLineEdit {
                font-size: 32px;
                padding: 10px;
                border: 2px solid #555;
                background-color: #000;
                color: #0F0;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(self.display)
        
        # Кнопки
        grid = QGridLayout()
        grid.setSpacing(5)
        
        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('.', 3, 1), ('C', 3, 2),
        ]
        
        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(60, 60)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    color: white;
                    font-size: 24px;
                    border: none;
                    border-radius: 5px;
                }
                QPushButton:pressed {
                    background-color: #666;
                }
                QPushButton:hover {
                    background-color: #555;
                }
            """)
            if text == 'C':
                btn.setStyleSheet(btn.styleSheet().replace("#444", "#D32F2F"))
                btn.clicked.connect(self._clear)
            else:
                btn.clicked.connect(lambda checked=False, t=text: self._add_char(t))
            grid.addWidget(btn, row, col)
            
        layout.addLayout(grid)
        
        # OK / Cancel
        action_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                padding: 10px;
                font-size: 16px;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        action_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        ok_btn.clicked.connect(self.accept)
        action_layout.addWidget(ok_btn)
        
        layout.addLayout(action_layout)
        
    def _add_char(self, char: str) -> None:
        current = self.display.text()
        if current == "0" and char != ".":
            current = ""
        if char == "." and "." in current:
            return
        self.display.setText(current + char)
        
    def _clear(self) -> None:
        self.display.setText("0")
        
    def get_value(self) -> float:
        try:
            return float(self.display.text())
        except ValueError:
            return 0.0
