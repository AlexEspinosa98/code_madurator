import serial
import time
import board
import digitalio
import adafruit_max31865

# Configuración del PT100 con MAX31865
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D5)  # Ajusta el pin según tu configuración (GPIO 5)
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=3)

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

def read_pt100():
    try:
        temp = sensor.temperature
        resistance = sensor.resistance  # Leer la resistencia directamente
        return temp, resistance
    except Exception as e:
        print(f'Error al leer el sensor PT100: {e}')
        return None, None

while True:
    try:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').rstrip()
            print(f'Datos recibidos: {data}')

            # Leer el sensor PT100
            pt100_temp, pt100_resistance = read_pt100()
            if pt100_temp is not None and pt100_resistance is not None:
                print(f'Temperatura PT100: {pt100_temp:.2f} °C, Resistencia: {pt100_resistance:.2f} ohms')

    except Exception as e:
        print(f"Error: {e}")
        ser.close()
        time.sleep(1)  # Espera un momento antes de reiniciar
        ser = open_serial_port()  # Reiniciar la conexión serial
