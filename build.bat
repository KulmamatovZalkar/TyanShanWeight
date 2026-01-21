@echo off
REM Скрипт сборки TyanShanWeight в EXE
REM Запускать из корня проекта

echo ======================================
echo TyanShanWeight - Сборка EXE
echo ======================================

REM Проверка виртуального окружения
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
call venv\Scripts\activate.bat

REM Установка зависимостей
echo Установка зависимостей...
pip install -r requirements.txt
pip install pyinstaller

REM Сборка
echo Сборка EXE...
pyinstaller build\tyanshan.spec --clean --noconfirm

echo ======================================
echo Готово! EXE находится в dist\TyanShanWeight\
echo ======================================
pause
