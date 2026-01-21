"""
TyanShanWeight — Приложение для взвешивания грузовиков.
Точка входа в приложение.
"""
import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logger
from src.utils.config import ConfigManager
from src.gui.main_window import MainWindow


def main():
    """Главная функция приложения."""
    
    # Определяем директорию приложения
    if getattr(sys, 'frozen', False):
        # Запуск из EXE
        app_dir = os.path.dirname(sys.executable)
    else:
        # Запуск из исходников
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    os.chdir(app_dir)
    
    # Инициализация логирования
    log_dir = os.path.join(app_dir, 'logs')
    logger = setup_logger(log_dir)
    logger.info("=" * 50)
    logger.info("Запуск TyanShanWeight")
    logger.info(f"Директория: {app_dir}")
    
    # Загрузка конфигурации
    config_path = os.path.join(app_dir, 'config.json')
    config_manager = ConfigManager(config_path)
    
    # Создание Qt приложения
    app = QApplication(sys.argv)
    app.setApplicationName("TyanShanWeight")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("TyanShan")
    
    # Настройка шрифта
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Создание и отображение главного окна
    window = MainWindow(config_manager)
    window.show()
    
    logger.info("Приложение запущено")
    
    # Запуск цикла событий
    exit_code = app.exec()
    
    logger.info(f"Приложение завершено с кодом: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
