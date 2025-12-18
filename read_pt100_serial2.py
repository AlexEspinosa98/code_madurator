
import time
import board
import digitalio
import adafruit_max31865

spi = board.SPI()  # SCLK=GPIO11, MOSI=GPIO10, MISO=GPIO9
cs = digitalio.DigitalInOut(board.CE0)  # CS en CE0 (GPIO8, pin 24)

sensor = adafruit_max31865.MAX31865(
    spi, cs, rtd_nominal=100.0, ref_resistor=430.0, wires=3
)

print("Leyendo PT100 (Ctrl+C para salir)...")

def fault_to_hex(f):
    # En algunas versiones 'fault' es una tupla de flags.
    if isinstance(f, tuple):
        bits = ((1 if f[0] else 0) << 7) | ((1 if f[1] else 0) << 6) | \
               ((1 if f[2] else 0) << 5) | ((1 if f[3] else 0) << 4) | \
               ((1 if f[4] else 0) << 3) | ((1 if f[5] else 0) << 2)
        return bits
    return int(f)

while True:
    try:
        t = float(sensor.temperature)   # °C
        r = float(sensor.resistance)    # Ω
        f = sensor.fault
        if f:
            print(f"Falla detectada: {f} -> 0x{fault_to_hex(f):02X}")
            sensor.clear_faults()
        print(f"T={t:.2f} °C  |  R={r:.2f} Ω")
    except Exception as e:
        print("Error:", e)
    time.sleep(0.5)
