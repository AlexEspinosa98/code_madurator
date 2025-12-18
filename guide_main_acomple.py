import sys
import time
import threading
import serial
import board
import digitalio
import adafruit_max31865
import RPi.GPIO as GPIO
import subprocess
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMessageBox
from PyQt6.QtCore import QTimer, Qt
from generator_code import Ui_Generator  # Cambia según la clase generada
import re
from storage import CounterStorage



# Configuración del pin para PWM
led_pin = 19
GPIO.setmode(GPIO.BCM)
GPIO.setup(led_pin, GPIO.OUT)
pwm = GPIO.PWM(led_pin, 500)
pwm.start(0)  # Iniciar con ciclo de trabajo de 0%

#GPIO 16 to ozono
GPIO.setup(16, GPIO.OUT)
GPIO.output(16,GPIO.HIGH)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12,GPIO.LOW)

# Configuración del PT100 con MAX31865
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D17)  # Ajusta el pin según tu configuración (GPIO 17)
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=3)

# Variables globales
temp_actual = 0
duty_cycle = 0
stop_threads = False  # Bandera para detener los hilos
lock = threading.Lock()

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
            subprocess.run(['sudo', 'chmod', '666', '/dev/serial0'])
            time.sleep(1)
            return open_serial_port()
        else:
            print("estoy en else de opens_serial_port")
            time.sleep(1)
            subprocess.run(['sudo', 'chmod', '666', '/dev/serial0'])
            return open_serial_port()

# Inicialización del puerto serial
ser = open_serial_port()

# Clase MainWindow para la interfaz gráfica con PyQt6
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_Generator()
        
        self.ui.setupUi(self)
        self.count_flow = 0
        self.count_temperature = 0
        self.count_ozone = 0
        self.timer_on = 0
        self.ui.pushButton_15.clicked.connect(lambda:self.up_count(1,0.1))
        self.ui.pushButton_16.clicked.connect(lambda:self.up_count(1,-0.1))
        #17 set
        self.ui.pushButton_5.clicked.connect(lambda:self.up_count(2,1))
        self.ui.pushButton_3.clicked.connect(lambda:self.up_count(2,-1))
        # 2
        self.ui.pushButton_6.clicked.connect(lambda:self.up_count(3,0.1))
        self.ui.pushButton_4.clicked.connect(lambda:self.up_count(3,-0.1))
		# set 9
        self.ui.pushButton_18.clicked.connect(lambda:self.up_count(4,1))
        self.ui.pushButton_19.clicked.connect(lambda:self.up_count(4,-1))
        self.ui.pushButton_7.clicked.connect(lambda:self.init_processing()) # button init ozone
        self.monitoreo = False
        self.ui.pushButton_8.clicked.connect(lambda:self.finish_processing())
        try:
            # Descomenta la línea del estilo que deseas usar:
            with open("estilo_test.css", "r") as f:
            # with open("estilo_moderno.css", "r") as f:
            # with open("estilo_minimalista.css", "r") as f:
                self.setStyleSheet(f.read())
            print("Estilo CSS cargado correctamente.")
        except FileNotFoundError:
            print("Error: El archivo CSS no se e	ncontró. Asegúrate de que esté en la misma carpeta que tu script.")
            print("Cargando estilos por defecto de PyQt.")
        except Exception as e:
            print(f"Ocurrió un error al cargar el CSS: {e}")
        # fijo seleccionado etileno
        self.ui.radioButton.setChecked(True)
        
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Usar un QTimer para imprimir después de mostrar
        QTimer.singleShot(100, self.print_size)

        # Opcional: quitar minimizar
        flags = self.windowFlags()
        flags = flags & ~Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)
    def print_size(self):
        ancho = self.width()
        alto = self.height()
        print(f"Tamaño maximizado: ancho={ancho}, alto={alto}")
        
		#stop 8. init 7
    def finish_processing(self):
        self.monitoreo = False
        GPIO.output(16,GPIO.HIGH)
        GPIO.output(12,GPIO.LOW)
        # bajar todos los sensores que hacen procesamiento
        
    def init_processing(self):
        if self.ui.radioButton.isChecked():
            print("ethylene")
        elif self.ui.radioButton_2.isChecked():
            GPIO.output(16,GPIO.LOW)
            GPIO.output(12,GPIO.HIGH)
            print("ozone")
        else:
            print("ningun boton seleccionado")
        pass
        

    def up_count(self, number_count, count):
	    if number_count == 1:
		    self.count_flow += count
		    if self.count_flow <= 0:
			    QMessageBox.critical(
				    self,
				    "Emergencia",
				    "¡El contador de flujo ha llegado a cero o menos!"
			    )
			    self.count_flow = 0  # Opcional: reiniciar o dejar en 0
		    self.ui.lcdNumber_9.display(self.count_flow)

	    if number_count == 2:
		    self.count_temperature += count
		    if self.count_temperature <= 0:
			    QMessageBox.critical(
				    self,
				    "Emergencia",
				    "¡El contador de temperatura ha llegado a cero o menos!"
			    )
			    self.count_temperature = 0
		    self.ui.lcdNumber_5.display(self.count_temperature)

	    if number_count == 3:
		    self.count_ozone += count
		    if self.count_ozone <= 0:
			    QMessageBox.critical(
				    self,
				    "Emergencia",
				    "¡El contador de ozono ha llegado a cero o menos!"
			    )
			    self.count_ozone = 0
		    self.ui.lcdNumber_6.display(self.count_ozone)

	    if number_count == 4:
		    self.timer_on += count
		    if self.timer_on <= 0:
			    QMessageBox.critical(
				    self,
				    "Emergencia",
				    "¡El temporizador ha llegado a cero o menos!"
			    )
			    self.timer_on = 0
		    self.ui.lcdNumber_10.display(self.timer_on)
        
    def update_data(self, temp, hum, pr, et, oz):
        """Función para actualizar los datos en la interfaz."""
        self.ui.lcdNumber_3.display(et)
        self.ui.lcdNumber_4.display(pr)
        self.ui.lcdNumber_2.display(oz)
        self.ui.lcdNumber.display(temp)
        

    def closeEvent(self, event):
        """Este método se llama cuando se cierra la ventana."""
        global stop_threads
        stop_threads = True  # Indicar a los hilos que deben detenerse
        print("Cerrando la aplicación...")
        event.accept()  # Aceptar el evento de cierre


# Función para leer la temperatura del PT100
def read_pt100():
    global temp_actual, duty_cycle
    while not stop_threads:  # Condición de parada
        try:
            temp = sensor.temperature
            resistance = sensor.resistance
            with lock:
                temp_actual = temp
                if temp_actual > 100:
                    duty_cycle = 0
                elif temp_actual < 80:
                    duty_cycle = 100
                else:
                    duty_cycle = 0

            print(f'Temperatura: {temp_actual:.2f} °C, Resistencia: {resistance:.2f} ohms')
        except Exception as e:
            print(f'Error al leer el sensor PT100: {e}')
        time.sleep(1)

# Función para controlar el PWM basado en la temperatura
def control_pwm():
    """Función para controlar el PWM."""
    while not stop_threads:  # Condición de parada
        with lock:
            pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.1)

# Función para leer datos del puerto serial
def read_serial_data(main_window):
    global ser
    while not stop_threads:
        try:
            if ser.in_waiting > 0:
                raw_data = ser.readline().decode("utf-8", errors="ignore").strip()
                # print(f"Trama recibida: {raw_data}")

                # Buscar <ESP1> o <ESP2>
                match = raw_data # re.search(r"<(ESP1|ESP2)>(.*?)</\1>", raw_data)
                if not match:
                    continue  # Si no hay trama completa, saltar

                payload = match #.group(2)

                # Extraer cada valor con regex
                def extract(tag):
                    m = re.search(rf"<{tag}>(.*?)</{tag}>", payload)
                    return m.group(1) if m else None

                tmp = extract("TMP")
                hum = extract("HUM")
                prs = extract("PRS")
                et = extract("ET")
                o3 = extract("O3")

                if None in (tmp, hum, prs, et, o3):
                    # print("Advertencia: Algún valor no se encontró en la trama")
                    continue

                # Convertir a float
                temp = float(tmp)
                hum = float(hum)
                pr = float(prs)
                et = float(et)
                oz = float(o3)

                main_window.update_data(temp, hum, pr, et, oz)

        except serial.SerialException as e:
            print(f"Error serial: {e}")
            ser.close()
            ser = open_serial_port()
        except Exception as e:
            print(f"Error general serial: {e}")
            ser.close()
            ser = open_serial_port()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()

    # Crear e iniciar los hilos
    thread_sensor = threading.Thread(target=read_pt100)
    thread_pwm = threading.Thread(target=control_pwm)
    thread_serial = threading.Thread(target=read_serial_data, args=(window,))

    thread_sensor.start()
    thread_pwm.start()
    thread_serial.start()

    window.show()

    # Ejecutar el bucle de la aplicación
    exit_code = app.exec()

    # Esperar a que los hilos terminen antes de salir completamente
    thread_sensor.join()
    thread_pwm.join()
    thread_serial.join()

    sys.exit(exit_code)
