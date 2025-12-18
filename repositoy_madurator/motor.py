# Importar las bibliotecas necesarias
import RPi.GPIO as GPIO
from time import sleep

# Definir los pines GPIO para dirección y paso
DIR = 24  # Pin 24 para dirección
STEP = 26  # Pin 26 para paso

# Definir la velocidad y aceleración inicial
MAX_SPEED = 1500  # Velocidad máxima en pasos por segundo
ACCELERATION = 100  # Aceleración en pasos por segundo cuadrado

def calculate_steps(x):
    return int(-4.36 + 1758.17 * x)

# Configurar la numeración de pines de la Raspberry Pi
GPIO.setmode(GPIO.BOARD)

# Configurar los pines GPIO como salida
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)

# Establecer la velocidad y la dirección del motor
def set_direction_clockwise():
    GPIO.output(DIR, GPIO.LOW)  # Sentido de las manecillas del reloj

# Función para hacer un paso del motor
def step_motor():
    GPIO.output(STEP, GPIO.HIGH)
    sleep(0.009)  # Puedes ajustar este tiempo según sea necesario
    GPIO.output(STEP, GPIO.LOW)
    sleep(0.009)  # Puedes ajustar este tiempo según sea necesario

# Función para configurar la velocidad del motor
def set_speed(speed):
    global MAX_SPEED
    MAX_SPEED = speed

# Función para configurar la aceleración del motor
def set_acceleration(acceleration):
    global ACCELERATION
    ACCELERATION = acceleration

# Configuración inicial del motor
set_direction_clockwise()  # Establecer el sentido de las manecillas del reloj

# Definir el número total de pasos deseado
#num_steps = 1600

try:
    # caudal ejemplo (x)
    #caudal = 4.55
    caudal = 10
    #calcular el numero de pasos
    #num_steps = calculate_steps(caudal)
    
    # Establecer la velocidad y aceleración inicial
    current_speed = 0
    current_acceleration = 0
    num_steps = 3600
    #while current_speed < MAX_SPEED:
    #    current_speed += ACCELERATION
    #    step_motor()

    # Re	alizar el número especificado de pasos
    step_count = 0
    for x in range(0,num_steps):
        step_count +=1
        GPIO.output(STEP, True)
        sleep(0.000408)  # Puedes ajustar este tiempo según sea necesario
        GPIO.output(STEP, False)
        sleep(0.000408)  # Puedes ajustar este	 tiempo según sea necesario

    
    
    print(f"Se completaron {step_count} pasos.")

except KeyboardInterrupt:
    # En caso de interrupción del teclado, limpiar los pines GPIO
    GPIO.cleanup()

finally:
    # Limpiar los pines GPIO al finalizar el programa
    GPIO.cleanup()
