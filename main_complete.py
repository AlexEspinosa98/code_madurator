import RPi.GPIO as GPIO
import time
import threading
import board
import digitalio
import adafruit_max31865

# Configuración del pin para PWM
led_pin = 19
GPIO.setmode(GPIO.BCM)
GPIO.setup(led_pin, GPIO.OUT)
pwm = GPIO.PWM(led_pin, 500)
pwm.start(0)  # Iniciar con ciclo de trabajo de 0%

# Configuración del PT100 con MAX31865
spi = board.SPI()
cs = digitalio.DigitalInOut(board.D17)  # Ajusta el pin según tu configuración
sensor = adafruit_max31865.MAX31865(spi, cs, rtd_nominal=100, ref_resistor=430.0, wires=3)

# Variables globales
temp_actual = 0
duty_cycle = 0
lock = threading.Lock()

def read_pt100():
    """Función para leer la temperatura y ajustar el PWM."""
    global temp_actual, duty_cycle
    while True:
        try:
            temp = sensor.temperature
            resistance = sensor.resistance
            with lock:  # Bloquear el acceso a las variables globales
                temp_actual = temp
                # Ajustar el ciclo de vida según la temperatura
                if temp_actual > 100:
                    duty_cycle = 0
                elif temp_actual < 80:
                    duty_cycle = 100
                else:
                    duty_cycle = 0  # Puedes ajustar este valor para otras temperaturas intermedias
                
            print(f'Temperatura: {temp_actual:.2f} °C, Resistencia: {resistance:.2f} ohms')
        except Exception as e:
            print(f'Error al leer el sensor PT100: {e}')
        time.sleep(1)  # Leer el sensor cada segundo

def control_pwm():
    """Función para controlar el PWM basado en la temperatura."""
    while True:
        with lock:  # Asegurarse de que el acceso a duty_cycle sea seguro
            #print("duty_cycle",duty_cycle) 
            pwm.ChangeDutyCycle(duty_cycle)
        time.sleep(0.1)  # Ajustar el ciclo cada 20 ms

# Crear hilos para lectura del sensor y control de PWM
thread_sensor = threading.Thread(target=read_pt100)
thread_pwm = threading.Thread(target=control_pwm)

# Iniciar hilos
thread_sensor.start()
thread_pwm.start()

# Mantener el script corriendo
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pwm.stop()
    GPIO.cleanup()
