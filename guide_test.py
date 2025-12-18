from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
import sys
import serial
import time
import os
import board
import digitalio
import adafruit_max31865
import subprocess
import threading

# Configuración del PT100 con MAX31865
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D17)  # Ajusta el pin según tu configuración (GPIO 5)
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=3)

# Función para abrir el puerto serial
def open_serial_port():
    try:
        return serial.Serial(
            port='/dev/serial0',  # Puerto serial
            baudrate=115200,      # Velocidad en baudios
            timeout=1             # Tiempo de espera para la lectura
        )
    except serial.SerialException as e:
        if "Permission denied" in str(e):
            print("Permiso denegado para acceder a /dev/serial0. Ejecutando chmod...")
            # Ejecutar chmod 666 para habilitar permisos
            subprocess.run(['sudo', 'chmod', '666', '/dev/serial0'])
            time.sleep(1)  # Esperar un segundo para asegurarse de que los permisos se aplicaron
            # Intentar abrir el puerto de nuevo
            return open_serial_port()
        else:
            raise e

# Inicialización del puerto serial
ser = open_serial_port()

print('Esperando datos del sensor...')

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Interfaz de Sensores")
        self.label_temp = QLabel('Temperatura: 0.00 °C', self)
        self.label_hum = QLabel('Humedad: 0.00 %', self)
        self.label_pr = QLabel('Presión: 0.00 hPa', self)
        self.label_et = QLabel('ET: 0.00', self)

        layout = QVBoxLayout()
        layout.addWidget(self.label_temp)
        layout.addWidget(self.label_hum)
        layout.addWidget(self.label_pr)
        layout.addWidget(self.label_et)

        central_widget = QWidget(self)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def update_data(self, temp, hum, pr, et):
        """Función para actualizar los datos en la interfaz."""
        self.label_temp.setText(f'Temperatura: {temp:.2f} °C')
        self.label_hum.setText(f'Humedad: {hum:.2f} %')
        self.label_pr.setText(f'Presión: {pr:.2f} hPa')
        self.label_et.setText(f'ET: {et:.2f}')

def read_pt100():
    """Función para leer la temperatura del PT100."""
    try:
        temp = sensor.temperature
        resistance = sensor.resistance  # Leer la resistencia directamente
        return temp, resistance
    except Exception as e:
        print(f'Error al leer el sensor PT100: {e}')
        return None, None

def read_serial_data(main_window):
    """Función para leer datos del puerto serial y procesar la cadena recibida."""
    global ser
    while True:
        try:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').rstrip()
                print(f'Datos recibidos: {data}')

                # Procesar la cadena para extraer valores
                try:
                    if data:
                        print("temp", data[data.find('<TMP>') + 5:data.find('</TMP>')])
                        print("hum", data[data.find('<HUM>') + 5:data.find('</HUM>')])
                        print("pres", data[data.find('<PR>') + 4:data.find('</PR>')])
                        print("et",data[data.find('<ET>') + 4:data.find('</ET>')] )
					
                        temp = float(data[data.find('<TMP>') + 5:data.find('</TMP>')])
                        hum = float(data[data.find('<HUM>') + 5:data.find('</HUM>')])
                        pr = float(data[data.find('<PR>') + 4:data.find('</PR>')])
                        et = float(data[data.find('<ET>') + 4:data.find('</ET>')])
                    
                        # Actualizar la interfaz con los datos extraídos
                        main_window.update_data(temp, hum, pr, et)

                except ValueError as e:
                    print(f"Error al convertir los valores: {e}")
                except Exception as e:
                    print(f"Error al procesar los datos: {e}")

            # Leer el sensor PT100
            pt100_temp, pt100_resistance = read_pt100()
            if pt100_temp is not None and pt100_resistance is not None:
                print(f'Temperatura PT100: {pt100_temp:.2f} °C, Resistencia: {pt100_resistance:.2f} ohms')

        except serial.SerialException as e:
            print(f"Error de comunicación serial: {e}")
            ser.close()
            subprocess.run(['sudo', 'chmod', '666', '/dev/serial0'])
            time.sleep(1)  # Esperar un momento antes de reiniciar
            ser = open_serial_port()  # Reiniciar la conexión serial
        except Exception as e:
            print(f"Error general: {e}")
            ser.close()
            subprocess.run(['sudo', 'chmod', '666', '/dev/serial0'])
            time.sleep(1)  # Esperar un momento antes de reiniciar
            ser = open_serial_port()  # Reiniciar la conexión serial

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    # Crear e iniciar el hilo para leer datos del puerto serial
    thread_serial = threading.Thread(target=read_serial_data, args=(window,))
    thread_serial.start()

    window.show()
    sys.exit(app.exec())
