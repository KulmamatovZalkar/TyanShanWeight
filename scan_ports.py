# -*- coding: utf-8 -*-
"""
Скрипт для сканирования всех COM-портов и поиска весов.
Показывает информацию о каждом порте и пробует прочитать данные.
"""
import serial
import serial.tools.list_ports
import time
import sys

# Фикс кодировки для Windows консоли
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def scan_ports():
    """Сканировать все доступные COM-порты."""
    print("=" * 60)
    print("СКАНИРОВАНИЕ COM-ПОРТОВ")
    print("=" * 60)
    print()
    
    # Получаем список всех портов
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("[X] COM-порты не найдены!")
        return
    
    print(f"Найдено портов: {len(ports)}")
    print()
    
    for port in ports:
        print("-" * 60)
        print(f"Порт: {port.device}")
        print(f"   Описание: {port.description}")
        print(f"   Производитель: {port.manufacturer or 'Неизвестно'}")
        print(f"   VID:PID: {port.vid}:{port.pid}" if port.vid else "   VID:PID: -")
        print(f"   Серийный номер: {port.serial_number or '-'}")
        print(f"   Расположение: {port.location or '-'}")
        print()
        
        # Пробуем подключиться и прочитать данные
        try_read_data(port.device)
    
    print("=" * 60)
    print("[OK] Сканирование завершено")


def try_read_data(port_name: str, baudrates: list = None):
    """
    Попробовать прочитать данные с порта.
    
    Args:
        port_name: Имя порта (COM1, COM3 и т.д.)
        baudrates: Список скоростей для проверки
    """
    if baudrates is None:
        baudrates = [9600, 4800, 19200, 38400, 115200]
    
    for baudrate in baudrates:
        try:
            print(f"   Пробую {baudrate} baud... ", end="", flush=True)
            
            ser = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                bytesize=8,
                parity='N',
                stopbits=1,
                timeout=2
            )
            
            ser.reset_input_buffer()
            time.sleep(0.5)
            
            # Пробуем прочитать в течение 3 секунд
            start = time.time()
            data_lines = []
            
            while time.time() - start < 3:
                if ser.in_waiting > 0:
                    try:
                        raw = ser.readline()
                        text = raw.decode('utf-8', errors='replace').strip()
                        if text:
                            data_lines.append(text)
                            if len(data_lines) >= 3:  # Достаточно 3 строк
                                break
                    except:
                        pass
                time.sleep(0.05)
            
            ser.close()
            
            if data_lines:
                print(f"[OK] ДАННЫЕ ПОЛУЧЕНЫ!")
                print(f"   Пример данных:")
                for i, line in enumerate(data_lines[:3], 1):
                    print(f"      [{i}] {repr(line)}")
                print()
                return True  # Нашли рабочую скорость
            else:
                print("нет данных")
                
        except serial.SerialException as e:
            if "PermissionError" in str(e) or "Отказано" in str(e):
                print("[!] ЗАНЯТ (используется другой программой)")
                return False
            else:
                print(f"ошибка: {e}")
        except Exception as e:
            print(f"ошибка: {e}")
    
    print("   [X] Данные не получены ни на одной скорости")
    print()
    return False


def detailed_scan(port_name: str):
    """
    Детальное сканирование конкретного порта.
    
    Args:
        port_name: Имя порта
    """
    print(f"\nДетальное сканирование порта {port_name}")
    print("=" * 60)
    
    baudrates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
    
    for baudrate in baudrates:
        for parity in ['N', 'E', 'O']:
            parity_name = {'N': 'None', 'E': 'Even', 'O': 'Odd'}[parity]
            try:
                print(f"Пробую {baudrate} baud, Parity={parity_name}... ", end="", flush=True)
                
                parity_val = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}[parity]
                
                ser = serial.Serial(
                    port=port_name,
                    baudrate=baudrate,
                    bytesize=8,
                    parity=parity_val,
                    stopbits=1,
                    timeout=1
                )
                
                ser.reset_input_buffer()
                time.sleep(0.3)
                
                start = time.time()
                while time.time() - start < 2:
                    if ser.in_waiting > 0:
                        raw = ser.readline()
                        text = raw.decode('utf-8', errors='replace').strip()
                        if text and len(text) > 3:  # Минимум 3 символа
                            ser.close()
                            print(f"[OK] НАЙДЕНО! -> {repr(text)}")
                            return baudrate, parity
                    time.sleep(0.05)
                
                ser.close()
                print("-")
                
            except serial.SerialException:
                print("[!] ЗАНЯТ")
                return None, None
            except:
                print("ошибка")
    
    print("[X] Данные не найдены")
    return None, None


if __name__ == "__main__":
    print()
    print("============================================================")
    print("        УТИЛИТА ПОИСКА COM-ПОРТОВ И ВЕСОВ                  ")
    print("============================================================")
    print()
    
    # Базовое сканирование
    scan_ports()
    
    print()
    input("Нажмите Enter для выхода...")
