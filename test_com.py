import serial

ser = serial.Serial(
    port='COM4',     # свой COM
    baudrate=9600,   # возможно 19200 / 38400
    timeout=1
)

while True:
    data = ser.readline()
    if data:
        print(data)
