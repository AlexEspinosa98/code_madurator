

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
from PyQt6.QtCore import QTimer, Qt, QTime, QDateTime
from generator_ui import Ui_Generator  # Cambia según la clase generada
import re
from counter_module import Counter
from storage import CounterStorage, DataStorage
from serial_parser import SerialDataParser

GPIO.setmode(GPIO.BCM)

# Configuración del pin para PWM (se mueve a 21 para liberar 16/8 al motor)
PWM_PIN = 21
GPIO.setup(PWM_PIN, GPIO.OUT)
pwm = GPIO.PWM(PWM_PIN, 500)
pwm.start(0)  # Iniciar con ciclo de trabajo de 0%

# Pines para motor paso a paso (DIR/STEP)
MOTOR_DIR = 16  # solicitado: usar 16
MOTOR_STEP = 8  # solicitado: usar 8
GPIO.setup(MOTOR_DIR, GPIO.OUT)
GPIO.setup(MOTOR_STEP, GPIO.OUT)
STEP_DELAY = 0.000408  # mismo retardo que motor.py

#GPIO 19 to ozono (antes era 16, se mueve para liberar DIR del motor)
GPIO.setup(19, GPIO.OUT)
GPIO.output(19,GPIO.HIGH)
GPIO.setup(12, GPIO.OUT)
GPIO.output(12,GPIO.LOW)

# GPIO VENTILADOR INTERNO (antes pin 8, ahora 20 para no chocar con STEP)
FAN_PIN = 20
GPIO.setup(FAN_PIN, GPIO.OUT)
GPIO.output(FAN_PIN,GPIO.HIGH)

# GPIO TO ETHYLENO
# Pines para Etileno
GPIO.setup(23, GPIO.OUT)  # Activa en HIGH
GPIO.setup(18, GPIO.OUT)  # Activa en LOW
GPIO.output(23, GPIO.LOW)  # Inicial apagado
GPIO.output(18, GPIO.HIGH) # Inicial apagado


# Configuración del PT100 con MAX31865
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D17)  # Ajusta el pin según tu configuración (GPIO 17)
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=3)

# Variables globales
temp_actual = 0
duty_cycle = 0
stop_threads = False  # Bandera para detener los hilos
lock = threading.Lock()
motor_stop_event = threading.Event()

# --- Lógica de motor paso a paso (basado en repositoy_madurator/motor.py) ---
def calculate_steps(flow_value):
    """Relación lineal usada en motor.py para convertir caudal a pasos."""
    return int(-4.36 + 1758.17 * flow_value)

def set_direction_clockwise():
    GPIO.output(MOTOR_DIR, GPIO.LOW)  # mismo sentido que motor.py

def run_stepper_steps(num_steps, delay=STEP_DELAY):
    """Ejecuta una cantidad de pasos con posibilidad de detenerse."""
    set_direction_clockwise()
    for _ in range(num_steps):
        if motor_stop_event.is_set():
            break
        GPIO.output(MOTOR_STEP, True)
        time.sleep(delay)
        GPIO.output(MOTOR_STEP, False)
        time.sleep(delay)

def start_stepper_for_flow(flow_value):
    """Lanza el motor en un hilo en función del caudal configurado."""
    steps = max(0, calculate_steps(flow_value))
    if steps == 0:
        return None
    motor_stop_event.clear()
    t = threading.Thread(target=run_stepper_steps, args=(steps,), daemon=True)
    t.start()
    return t

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

# --- NUEVO BLOQUE: Validador de sensores ---
class SensorValidator:
    def __init__(self, tolerance=0.25, invalid_values=None, confirm_reads=2):
        self.last_valid = None
        self.pending = None
        self.pending_count = 0
        self.tolerance = tolerance
        self.invalid_values = invalid_values or []
        self.confirm_reads = confirm_reads

    def validate(self, new_value):
        # Si el valor es inválido → devolver 0
        if new_value in self.invalid_values:
            return 0

        # Primer valor siempre válido
        if self.last_valid is None:
            self.last_valid = new_value
            return new_value

        # Calcular diferencia relativa
        if self.last_valid != 0:
            diff_ratio = abs(new_value - self.last_valid) / abs(self.last_valid)
        else:
            diff_ratio = 1 if new_value != 0 else 0

        if diff_ratio > self.tolerance:
            # Cambio brusco → pedir confirmación
            if self.pending == new_value:
                self.pending_count += 1
                if self.pending_count >= self.confirm_reads:
                    self.last_valid = new_value
                    self.pending = None
                    self.pending_count = 0
                    return new_value
                else:
                    return self.last_valid
            else:
                self.pending = new_value
                self.pending_count = 1
                return self.last_valid
        else:
            # Cambio dentro de tolerancia → aceptar
            self.last_valid = new_value
            self.pending = None
            self.pending_count = 0
            return new_value


class SerialReader:
    def __init__(self, serial_port, parser, storage, ui_update_callback):
        """
        serial_port: instancia de serial.Serial
        parser: instancia de SerialDataParser
        storage: instancia de DataStorage
        ui_update_callback: función que recibe un dict con los datos
        """
        self.serial_port = serial_port
        self.parser = parser
        self.storage = storage
        self.ui_update_callback = ui_update_callback

    def run(self):
        while not stop_threads:
            try:
                if self.serial_port.in_waiting > 0:
                    raw = self.serial_port.readline().decode("utf-8", errors="ignore").strip()
                    if raw:
                        print(f"Trama recibida: {raw}")
                    parsed = self.parser.parse(raw)
                    if parsed is None:
                        continue
                    # Actualizar UI
                    self.ui_update_callback(parsed)
                    # Guardar en BD
                    self.storage.save_reading(parsed)
            except serial.SerialException as e:
                print(f"Error serial: {e}")
                self.serial_port.close()
                self.serial_port = open_serial_port()
            except Exception as e:
                print(f"Error general serial: {e}")
                self.serial_port.close()
                self.serial_port = open_serial_port()

# Inicialización del puerto serial
ser = open_serial_port()

# Clase MainWindow para la interfaz gráfica con PyQt6
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_Generator()
        
        self.ui.setupUi(self)
        # fijo seleccionado etileno
        self.ui.button_ethylene.setChecked(True)
        self.ui.label_12.setText("Ethylene PPM")
        self.ui.label_monitor_gas.setText("Ethylene PPM")
        # change radio buton 
        self.ui.button_ozone.toggled.connect(self.update_label)
        self.ui.button_ethylene.toggled.connect(self.update_label)
        
        # Init Storage
        self.storage = CounterStorage()
        self.stepper_thread = None  # hilo actual del motor
        self.current_flow_steps = 0

        # init all counts
        self.counters = {
            "flow": Counter(
                name="Flujo",
                min_value=0,
                max_value=100,
                message="El contador de flujo salió del rango",
                parent=self,
                initial_value=self.storage.load_setpoint("flow")
            ),
            "temperature": Counter(
                name="Temperatura",
                min_value=0,
                max_value=300,
                message="El contador de temperatura salió del rango",
                parent=self,
                initial_value=self.storage.load_setpoint("temperature")
            ),
            "timer": Counter(
                name="Temporizador",
                min_value=0,
                max_value=999,
                message="El temporizador salió del rango",
                parent=self,
                initial_value=self.storage.load_setpoint("timer")
            ),
            "ethylene": Counter(
                name="Etileno",
                min_value=0,
                max_value=10,
                message="El contador de etileno salió del rango",
                parent=self,
                initial_value=self.storage.load_setpoint("ethylene")
            ),
            "ozone": Counter(
                name="Ozono",
                min_value=0,
                max_value=10,
                message="El contador de ozono salió del rango",
                parent=self,
                initial_value=self.storage.load_setpoint("ozone")
            )
        }
        
        # Init database with database information
        self.initialize_lcds()
        
        # button of configuration
        #   temp
        self.ui.up_gas_2.clicked.connect(lambda: self.change_counter("temperature",+1, self.ui.lcd_config_gas_2))
        self.ui.down_gas_2.clicked.connect(lambda: self.change_counter("temperature",-1, self.ui.lcd_config_gas_2))
        self.ui.set_gas_2.clicked.connect(lambda: self.set_counter("temperature", self.ui.lcd_monitor_temp))
        self.ui.reset_gas_2.clicked.connect(lambda: self.reset_counter("temperature", self.ui.lcd_config_gas_2))

        # flow
        self.ui.up_gas_3.clicked.connect(lambda: self.change_counter("flow",+0.1, self.ui.lcd_config_gas_3))
        self.ui.down_gas_3.clicked.connect(lambda: self.change_counter("flow",-0.1, self.ui.lcd_config_gas_3))
        self.ui.set_gas_3.clicked.connect(lambda: self.set_counter("flow", self.ui.lcd_monitor_flow))
        self.ui.reset_gas_3.clicked.connect(lambda: self.reset_counter("flow", self.ui.lcd_config_gas_3))

        # time
        self.ui.up_gas_4.clicked.connect(lambda: self.change_counter("timer",+1, self.ui.lcd_config_gas_4))
        self.ui.down_gas_4.clicked.connect(lambda: self.change_counter("timer",-1, self.ui.lcd_config_gas_4))
        self.ui.set_gas_4.clicked.connect(lambda: self.set_counter("timer", self.ui.lcd_monitor_flow))
        self.ui.reset_gas_4.clicked.connect(lambda: self.reset_counter("timer", self.ui.lcd_config_gas_4))

        # dynamic gas
        self.ui.up_gas.clicked.connect(lambda: self.change_dynamic_counter(+1))
        self.ui.down_gas.clicked.connect(lambda: self.change_dynamic_counter(-1))
        self.ui.set_gas.clicked.connect(lambda: self.set_dynamic_counter())
        self.ui.reset_gas.clicked.connect(lambda: self.reset_dynamic_counter())
        
        # Primero asegúrate que los botones sean checkable
        self.ui.but_init.setCheckable(True)
        self.ui.but_stop.setCheckable(True)
        
        # init variables flags
        self.monitoreo = False
        self.ozono_activo = False
        self.ethylene_activo = False

        # Reset radio buttons 
        self.ui.button_ethylene.clicked.connect(lambda: self.reset_dynamic_counter())
        self.ui.button_ozone.clicked.connect(lambda: self.reset_dynamic_counter())

        # Estilo visual
        self.ui.but_init.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;  /* Verde normal */
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #1e8449;  /* Verde oscuro cuando presionado */
            }
            QPushButton:disabled {
                background-color: #bdc3c7;  /* Gris cuando deshabilitado */
                color: #ecf0f1;
            }
        """)

        self.ui.but_stop.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;  /* Rojo normal */
                color: white;
                border-radius: 6px;
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #c0392b;  /* Rojo oscuro cuando presionado */
            }
            QPushButton:disabled {
                background-color: #bdc3c7;  /* Gris cuando deshabilitado */
                color: #ecf0f1;
            }
        """)

        
        

        self.ui.but_init.setCheckable(True)
        self.ui.but_stop.setCheckable(True)

                        # Estado inicial
        self.ui.but_init.setEnabled(True)
        self.ui.but_stop.setEnabled(False)

        self.ui.but_init.setChecked(False)
        self.ui.but_stop.setChecked(True)  # Por seguridad: detenido
        # But funcion
        
        self.ui.but_init.clicked.connect(lambda: self.init_processing())
        self.ui.but_stop.clicked.connect(lambda: self.finish_processing())
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Opcional: quitar minimizar
        flags = self.windowFlags()
        flags = flags & ~Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)

        # validator

        # Validadores
        self.validators = {
            "ET": SensorValidator(tolerance=0.3, invalid_values=[-1]),   # Etileno: ignora -1
            "O3": SensorValidator(tolerance=0.4, invalid_values=[0]),    # Ozono: ignora 0
            "TMP": SensorValidator(tolerance=0.2),                       # Temperatura
            "HUM": SensorValidator(tolerance=0.2),                       # Humedad
        }



        # timer
        self.timer_clock = QTimer(self)
        self.timer_clock.timeout.connect(self.update_clock)
        self.timer_clock.start(1000)  # cada 1000 ms = 1 segundo


        self.process_timer = None
        self.update_clock()  # inicializar de una vez

    def update_clock(self):
        """Actualiza el label_hour con la hora actual"""
        current_time = QDateTime.currentDateTime().toString("dd/MM/yyyy HH:mm:ss")
        self.ui.label_hour.setText(current_time)

    def update_label(self, checked):
        if checked:
            boton = self.sender()
            self.ui.label_12.setText(f"{boton.text().lower().capitalize()} PPM")
            self.ui.label_monitor_gas.setText(f"{boton.text().lower().capitalize()} PPM")
            self.refresh_dynamic_displays()
                #stop 8. init 7
                
    # init all display with database
    def initialize_lcds(self):
        # Flow
        self.ui.lcd_config_gas_3.display(self.counters["flow"].value)
        self.ui.lcd_monitor_flow.display(self.counters["flow"].setpoint)

        # Temperature
        self.ui.lcd_config_gas_2.display(self.counters["temperature"].value)
        self.ui.lcd_monitor_temp.display(self.counters["temperature"].setpoint)

        # Timer
        # self.ui.lcd_config_gas_4.display(self.counters["timer"].value)
        # self.ui.lcd_monitor_.display(self.counters["timer"].setpoint)

        # Dinámico: determinar si etileno o ozono está seleccionado
        self.refresh_dynamic_displays()

    # button configuration and counter
    def change_counter(self, key, delta, lcd_widget):
        counter = self.counters[key]
        counter.change(delta)
        lcd_widget.display(counter.value)
        
    def get_active_dynamic_counter(self):
        if self.ui.button_ethylene.isChecked():
            return self.counters["ethylene"]
        elif self.ui.button_ozone.isChecked():
            return self.counters["ozone"]
        else:
            return None

    def change_dynamic_counter(self, delta):
        counter = self.get_active_dynamic_counter()
        if counter is None:
            QMessageBox.warning(
                self,
                "Atención",
                "No hay un modo seleccionado."
            )
            return
        counter.change(delta)
        self.ui.lcd_config_gas.display(counter.value)
        
    def set_counter(self, key, lcd_set_widget):
        counter = self.counters[key]
        counter.set_current()
        lcd_set_widget.display(counter.setpoint)
        self.storage.save_setpoint(key, counter.setpoint)

    def reset_counter(self, key, lcd_widget):
        counter = self.counters[key]
        counter.reset_to_setpoint()
        lcd_widget.display(counter.value)
    
    def get_active_dynamic_key(self):
        if self.ui.button_ethylene.isChecked():
            return "ethylene"
        elif self.ui.button_ozone.isChecked():
            return "ozone"
        else:
            return None

    def refresh_dynamic_displays(self):
        """Actualiza los LCDs de gas según el radio seleccionado."""
        key = self.get_active_dynamic_key()
        if key is None:
            return
        counter = self.counters[key]
        self.ui.lcd_config_gas.display(counter.value)
        self.ui.lcd_monitor_gas.display(counter.setpoint)
    
    def set_dynamic_counter(self):
        key = self.get_active_dynamic_key()
        if key is None:
            QMessageBox.warning(self, "Atención", "No hay un modo seleccionado.")
            return
        self.set_counter(key, self.ui.lcd_monitor_gas)
        self.refresh_dynamic_displays()

    def reset_dynamic_counter(self):
        key = self.get_active_dynamic_key()
        if key is None:
            QMessageBox.warning(self, "Atención", "No hay un modo seleccionado.")
            return
        self.reset_counter(key, self.ui.lcd_config_gas)
        self.refresh_dynamic_displays()
    # ------ button dynamic 
    
    def finish_processing(self):
        self.monitoreo = False
        self.ozono_Activo = False
        self.ethylene_activo = False
        motor_stop_event.set()  # detener motor si estaba en marcha
        GPIO.output(19,GPIO.HIGH)
        GPIO.output(12,GPIO.LOW)
        
        #stop etileno
        GPIO.output(23, GPIO.LOW)  # Encender con lógica HIGH
        GPIO.output(18, GPIO.HIGH)   # Encender con lógica LOW

            # Visual
        self.ui.but_init.setChecked(False)
        self.ui.but_init.setEnabled(True)

        self.ui.but_stop.setChecked(True)
        self.ui.but_stop.setEnabled(False)
        # bajar todos los sensores que hacen procesamiento
        
        # habilitando botones de nuevo
        for button in [
            self.ui.up_gas, self.ui.down_gas, self.ui.set_gas, self.ui.reset_gas,
            self.ui.up_gas_2, self.ui.down_gas_2, self.ui.set_gas_2, self.ui.reset_gas_2,
            self.ui.up_gas_3, self.ui.down_gas_3, self.ui.set_gas_3, self.ui.reset_gas_3,
            self.ui.up_gas_4, self.ui.down_gas_4, self.ui.set_gas_4, self.ui.reset_gas_4
        ]:
            button.setEnabled(True)
        # --- NUEVO: limpiar el timer ---
        if self.process_timer is not None:
            self.process_timer.stop()
            self.process_timer = None
        
    def init_processing(self):
        key = self.get_active_dynamic_key()
        if key == 'ozone':
            motor_stop_event.set()  # no debe girar motor en modo ozono
            GPIO.output(12, GPIO.HIGH)
            GPIO.output(19, GPIO.LOW)
            self.ozono_activo = True
        elif key == 'ethylene':
            motor_stop_event.clear()
            GPIO.output(23, GPIO.HIGH)  # Encender con lógica HIGH
            GPIO.output(18, GPIO.LOW)   # Encender con lógica LOW
            self.ethylene_activo = True
            # Iniciar motor según el caudal configurado SOLO para etileno
            flow_value = self.counters["flow"].setpoint
            self.current_flow_steps = calculate_steps(flow_value)
            self.stepper_thread = start_stepper_for_flow(flow_value)
        
        self.monitoreo = True
        
        # Visual
        self.ui.but_init.setChecked(True)
        self.ui.but_init.setEnabled(False)

        self.ui.but_stop.setChecked(False)
        self.ui.but_stop.setEnabled(True)
        for button in [
            self.ui.up_gas, self.ui.down_gas, self.ui.set_gas, self.ui.reset_gas,
            self.ui.up_gas_2, self.ui.down_gas_2, self.ui.set_gas_2, self.ui.reset_gas_2,
            self.ui.up_gas_3, self.ui.down_gas_3, self.ui.set_gas_3, self.ui.reset_gas_3,
            self.ui.up_gas_4, self.ui.down_gas_4, self.ui.set_gas_4, self.ui.reset_gas_4
        ]:
            button.setEnabled(False)
        horas = self.counters["timer"].setpoint
        if horas <= 0:
            QMessageBox.warning(self, "Atención", "El tiempo configurado debe ser mayor a 0 horas.")
            return

        # Hora de inicio
        start_time = QDateTime.currentDateTime()
        self.ui.label_hour_init.setText(start_time.toString("dd/MM HH:mm"))

        # Hora de fin
        finish_time = start_time.addSecs(int(horas) * 3600)
        self.ui.label_hour_finish.setText(finish_time.toString("dd/MM HH:mm"))

        # Programar auto-stop
        if self.process_timer is not None:
            self.process_timer.stop()
        self.process_timer = QTimer(self)
        self.process_timer.setSingleShot(True)
        self.process_timer.timeout.connect(self.finish_processing)
        self.process_timer.start(int(horas) * 3600 * 1000)  # en milisegundos

    def update_data(self, data):
        # Validar cada dato
        valid_data = {}
        for key, value in data.items():
            if key in self.validators:
                valid_data[key] = self.validators[key].validate(value)
            else:
                valid_data[key] = value

        # Usar valores ya filtrados
        self.ui.lcd_temp.display(valid_data["TMP"])
        self.ui.lcd_humedad.display(valid_data["HUM"])
        self.ui.lcd_ozone.display(valid_data["O3"])
        self.ui.lcd_ethylene.display(valid_data["ET"])

        # --- Control con valores validados ---
        if self.monitoreo and self.get_active_dynamic_key() == "ozone":
            setpoint = self.counters["ozone"].setpoint
            actual = valid_data["O3"]
            if actual is None:
                return
            if actual > setpoint and self.ozono_activo:
                GPIO.output(12, GPIO.LOW)
                GPIO.output(19, GPIO.HIGH)
                self.ozono_activo = False
            elif actual < setpoint * 0.75 and not self.ozono_activo:
                GPIO.output(12, GPIO.HIGH)
                GPIO.output(19, GPIO.LOW)
                self.ozono_activo = True

        if self.monitoreo and self.get_active_dynamic_key() == "ethylene":
            setpoint = self.counters["ethylene"].setpoint
            actual = valid_data["ET"]
            if actual is None:
                return
            if actual > setpoint and self.ethylene_activo:
                GPIO.output(23, GPIO.LOW)
                GPIO.output(18, GPIO.HIGH)
                self.ethylene_activo = False
            elif actual < setpoint * 0.75 and not self.ethylene_activo:
                GPIO.output(23, GPIO.HIGH)
                GPIO.output(18, GPIO.LOW)
                self.ethylene_activo = True

        

    def closeEvent(self, event):
        """Este método se llama cuando se cierra la ventana."""
        global stop_threads
        stop_threads = True  # Indicar a los hilos que deben detenerse
        motor_stop_event.set()
        print("Cerrando la aplicación...")
        event.accept()  # Aceptar el evento de cierre


# Función para leer la temperatura del PT100

def read_pt100():
    global temp_actual, duty_cycle
    MAX_TEMP_ETHYLENE = 100  # Temperatura máxima para apagar etileno
    TEMP_RESTART = MAX_TEMP_ETHYLENE * 0.75  # Umbral para volver a encender (25% menos)

    while not stop_threads:  # Condición de parada
        try:
            temp = sensor.temperature
            resistance = sensor.resistance
            with lock:
                temp_actual = temp

                # --- Nueva lógica para etileno ---
                if window.ethylene_activo:  # Solo si etileno está activo
                    if temp_actual >= MAX_TEMP_ETHYLENE and window.ethylene_activo:
                        # Apagar etileno
                        GPIO.output(23, GPIO.LOW)
                        GPIO.output(18, GPIO.HIGH)
                        window.ethylene_activo = False
                        print(f"⚠️ Etileno apagado por temperatura alta ({temp_actual:.2f} °C)")

                    elif temp_actual <= TEMP_RESTART and window.ethylene_activo:
                        # Encender etileno nuevamente
                        GPIO.output(23, GPIO.HIGH)
                        GPIO.output(18, GPIO.LOW)
                        window.ethylene_activo = True
                        print(f"✅ Etileno encendido por temperatura baja ({temp_actual:.2f} °C)")
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


def get_cpu_temperature():
    with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
        temp_str = f.read()
    return int(temp_str) / 1000.0  # La temperatura viene en miligrados

# Función para monitorear temperatura en un hilo
def temperature_monitor():
    TEMP_THRESHOLD = 60
    while True:
        temp = get_cpu_temperature()
        print(f"Temperatura actual: {temp:.2f}°C")

        if temp >= TEMP_THRESHOLD:
            GPIO.output(FAN_PIN, GPIO.HIGH)  # Encender ventilador
            print("⚠️ Temperatura alta: ventilador encendido")
        else:
            GPIO.output(FAN_PIN, GPIO.LOW)  # Apagar ventilador
            print("✅ Temperatura normal: ventilador apagado")

        time.sleep(5)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    
    parser = SerialDataParser()
    storage = DataStorage()
    reader = SerialReader(
        serial_port=ser,
        parser=parser,
        storage=storage,
        ui_update_callback=window.update_data
    )

    # Crear e iniciar los hilos
    thread_sensor = threading.Thread(target=read_pt100)
    thread_pwm = threading.Thread(target=control_pwm)
    thread_serial = threading.Thread(target=reader.run)
    temp_thread = threading.Thread(target=temperature_monitor, daemon=True)
    temp_thread.start()
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
