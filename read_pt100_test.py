
import time
import board
import digitalio
import adafruit_max31865

# ==============================
# Configuración SPI y chip select
# ==============================
# SPI0 por hardware: SCLK=GPIO11, MOSI=GPIO10, MISO=GPIO9
spi = board.SPI()

# CS en GPIO17 (pin físico 11)
cs = digitalio.DigitalInOut(board.D17)
cs.direction = digitalio.Direction.OUTPUT

# Inicializar el sensor MAX31865
sensor = adafruit_max31865.MAX31865(
    spi,
    cs,
    rtd_nominal=100.0,   # PT100
    ref_resistor=430.0,  # Resistencia de referencia
    wires=3               # Número de hilos del sensor
)

# Cambiar filtro a 60 Hz (en Colombia)
try:
    sensor.filter_50hz = False
except AttributeError:
    pass

print("Leyendo PT100...\n")
while True:
    try:
        t = sensor.temperature
        r = sensor.resistance
        f = sensor.fault

        # Validar que no sean tuplas
        if isinstance(t, tuple) or isinstance(r, tuple):
            print("Error: lectura inválida del sensor (posible fallo de conexión)")
        else:
            if f:
                print(f"Falla 0x{f:02X}")
                sensor.clear_faults()
            print(f"T={t:.2f} °C  |  R={r:.2f} Ω")

    except Exception as e:
        print("Error:", e)

    time.sleep(0.5)
