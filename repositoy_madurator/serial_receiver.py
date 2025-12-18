import serial
import time

# Función para abrir el puerto serial
def open_serial_port():
    return serial.Serial(
        port='/dev/serial0',  # Puerto serial
        baudrate=115200,      # Velocidad en baudios
        timeout=1             # Tiempo de espera para la lectura
    )

# Inicialización del puerto serial
ser = open_serial_port()

print('Esperando datos del sensor...')

while True:
    try:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').rstrip()
            print(f'Datos recibidos: {data}')
    except Exception as e:
        print(f"Error: {e}")
        ser.close()
        time.sleep(1)  # Espera un momento antes de reiniciar
        ser = open_serial_port()  # Reiniciar la conexión serial
