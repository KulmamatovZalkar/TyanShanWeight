"""
Стили приложения TyanShanWeight.
Современный темный дизайн для удобства операторов.
"""

# Основные цвета
COLORS = {
    'primary': '#2196F3',        # Синий
    'primary_dark': '#1976D2',
    'primary_light': '#64B5F6',
    'success': '#4CAF50',        # Зеленый
    'success_dark': '#388E3C',
    'warning': '#FF9800',        # Оранжевый
    'danger': '#F44336',         # Красный
    'background': '#1E1E1E',     # Темный фон
    'surface': '#2D2D2D',        # Поверхность
    'surface_light': '#3D3D3D',
    'text': '#FFFFFF',           # Белый текст
    'text_secondary': '#B0B0B0',
    'border': '#404040',
}

# Основной стиль приложения
MAIN_STYLE = f"""
QMainWindow {{
    background-color: {COLORS['background']};
}}

QWidget {{
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 14px;
    color: {COLORS['text']};
}}

QLabel {{
    color: {COLORS['text']};
}}

QLabel#weight_display {{
    font-size: 72px;
    font-weight: bold;
    color: {COLORS['primary_light']};
    padding: 20px;
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
}}

QLabel#weight_display[stable="true"] {{
    color: {COLORS['success']};
    border-color: {COLORS['success']};
}}

QLabel#weight_label {{
    font-size: 16px;
    color: {COLORS['text_secondary']};
}}

QLabel#value_label {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS['text']};
    padding: 10px;
    background-color: {COLORS['surface']};
    border-radius: 5px;
}}

QLineEdit {{
    padding: 8px;
    font-size: 16px;
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    color: {COLORS['text']};
    min-height: 24px;
}}

QLineEdit:focus {{
    border-color: {COLORS['primary']};
}}

QLineEdit:disabled {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text_secondary']};
}}

QComboBox {{
    padding: 12px;
    font-size: 16px;
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 8px;
    color: {COLORS['text']};
}}

QComboBox:focus {{
    border-color: {COLORS['primary']};
}}

QComboBox::drop-down {{
    border: none;
    padding-right: 10px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid {COLORS['text']};
    margin-right: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: #333333;
    color: #FFFFFF;
    border: 2px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    selection-color: #FFFFFF;
}}

QTextEdit {{
    background-color: #000000;
    color: #FFFFFF;
    border: 2px solid {COLORS['border']};
    border-radius: 5px;
    font-size: 16px;
    padding: 5px;
}}

QPushButton {{
    padding: 15px 30px;
    font-size: 16px;
    font-weight: bold;
    background-color: {COLORS['primary']};
    color: {COLORS['text']};
    border: none;
    border-radius: 8px;
    min-height: 50px;
}}

QPushButton:hover {{
    background-color: {COLORS['primary_dark']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary_light']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text_secondary']};
}}

QPushButton#tara_button {{
    background-color: {COLORS['warning']};
}}

QPushButton#tara_button:hover {{
    background-color: #F57C00;
}}

QPushButton#brutto_button {{
    background-color: {COLORS['success']};
}}

QPushButton#brutto_button:hover {{
    background-color: {COLORS['success_dark']};
}}

QPushButton#save_button {{
    background-color: {COLORS['primary']};
    font-size: 18px;
}}

QPushButton#reset_button {{
    background-color: {COLORS['danger']};
}}

QPushButton#reset_button:hover {{
    background-color: #D32F2F;
}}

QPushButton#settings_button {{
    background-color: {COLORS['surface_light']};
    padding: 10px 20px;
    min-height: 40px;
}}

QGroupBox {{
    font-size: 16px;
    font-weight: bold;
    color: {COLORS['text']};
    border: 2px solid {COLORS['border']};
    border-radius: 10px;
    margin-top: 15px;
    padding-top: 15px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    background-color: {COLORS['background']};
}}

QStatusBar {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    font-size: 12px;
    padding: 5px;
}}

QStatusBar QLabel {{
    padding: 0 10px;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QFrame#connection_indicator {{
    border-radius: 8px;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}}

QFrame#connection_indicator[connected="true"] {{
    background-color: {COLORS['success']};
}}

QFrame#connection_indicator[connected="false"] {{
    background-color: {COLORS['danger']};
}}

QMessageBox {{
    background-color: {COLORS['surface']};
}}

QMessageBox QLabel {{
    color: {COLORS['text']};
    font-size: 14px;
}}

QDialog {{
    background-color: {COLORS['background']};
}}

QSpinBox, QDoubleSpinBox {{
    padding: 10px;
    font-size: 14px;
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 5px;
    color: {COLORS['text']};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['primary']};
}}

QTabWidget::pane {{
    border: 2px solid {COLORS['border']};
    border-radius: 5px;
    background-color: {COLORS['surface']};
}}

QTabBar::tab {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text']};
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['primary']};
}}

QTableWidget {{
    background-color: #1E1E1E;
    alternate-background-color: #2D2D2D;
    color: #FFFFFF;
    border: 2px solid {COLORS['border']};
    border-radius: 5px;
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    selection-color: #FFFFFF;
}}

QTableWidget::item {{
    padding: 5px;
    border: none;
    color: #FFFFFF;
}}

QTableWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: #FFFFFF;
}}

QHeaderView::section {{
    background-color: {COLORS['surface_light']};
    color: {COLORS['text']};
    padding: 10px;
    border: none;
    border-bottom: 2px solid {COLORS['border']};
}}

QListWidget {{
    background-color: #FFFFFF;
    color: #000000;
    border: 2px solid {COLORS['border']};
    border-radius: 5px;
    font-size: 14px;
}}

QListWidget::item {{
    padding: 5px;
    color: #000000;
}}

QListWidget::item:selected {{
    background-color: {COLORS['primary']};
    color: #FFFFFF;
}}
"""

# Стиль для диалога настроек
SETTINGS_STYLE = MAIN_STYLE + f"""
QLabel#section_title {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['primary_light']};
    margin-top: 10px;
}}

/* Компактные стили для диалога настроек */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    min-height: 30px;
    padding: 5px;
    font-size: 14px;
}}

QPushButton {{
    padding: 5px 15px;
    min-height: 35px;
    font-size: 14px;
}}
"""
