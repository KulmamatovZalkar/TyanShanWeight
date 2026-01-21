@echo off
REM Скрипт запуска TyanShanWeight
REM Запускать из корня проекта

echo Запуск TyanShanWeight...

REM Проверка виртуального окружения
if exist venv (
    call venv\Scripts\activate.bat
)

python main.py
