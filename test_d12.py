# -*- coding: utf-8 -*-
"""
Скрипт для запроса веса с китайских D12 весов.
Пробует разные команды для получения данных.
"""
import serial
import time
import sys

# Фикс кодировки
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def try_commands(port_name: str, baudrate: int = 9600):
    """Попробовать отправить команды на весы."""
    
    # Типичные команды для китайских весов
    commands = [
        b'\x02',           # STX - Start of Text
        b'W\r\n',          # W - Weight request
        b'P\r\n',          # P - Print/Send
        b'R\r\n',          # R - Read
        b'S\r\n',          # S - Stable
        b'\x05',           # ENQ - Enquiry
        b'$\r\n',          # Dollar sign command
        b'?\r\n',          # Question mark
        b'READ\r\n',       # READ command
        b'\x1B P\r\n',     # ESC + P
        b'GW\r\n',         # Get Weight
        b'\r\n',           # Just CR LF
    ]
    
    print(f"Подключение к {port_name} @ {baudrate}...")
    
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=2
        )
        
        print("[OK] Порт открыт")
        print()
        
        # Сначала просто слушаем 5 секунд
        print("1. Слушаю порт 5 секунд (без команд)...")
        ser.reset_input_buffer()
        
        start = time.time()
        while time.time() - start < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"   ПОЛУЧЕНО: {repr(data)}")
            time.sleep(0.1)
        
        print()
        print("2. Отправляю команды...")
        print("-" * 50)
        
        for cmd in commands:
            print(f"   Команда: {repr(cmd)} ... ", end="", flush=True)
            
            ser.reset_input_buffer()
            ser.write(cmd)
            ser.flush()
            
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"ОТВЕТ: {repr(response)}")
            else:
                print("нет ответа")
        
        print("-" * 50)
        print()
        
        # Ждем еще немного
        print("3. Слушаю еще 5 секунд...")
        start = time.time()
        while time.time() - start < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"   ПОЛУЧЕНО: {repr(data)}")
            time.sleep(0.1)
        
        ser.close()
        print()
        print("[OK] Тест завершен")
        
    except serial.SerialException as e:
        print(f"[X] Ошибка: {e}")
    except Exception as e:
        print(f"[X] Ошибка: {e}")


if __name__ == "__main__":
    print()
    print("============================================================")
    print("   ТЕСТ КОМАНД ДЛЯ КИТАЙСКИХ ВЕСОВ D12")
    print("============================================================")
    print()
    
    # Используем COM4 как определено сканером
    port = input("Введите COM-порт (например COM4): ").strip() or "COM4"
    baud = input("Введите скорость (по умолчанию 9600): ").strip() or "9600"
    
    print()
    try_commands(port, int(baud))
    
    print()
    input("Нажмите Enter для выхода...")
