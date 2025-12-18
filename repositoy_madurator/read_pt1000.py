importar digital
importar adafruit_max31865


# Crear un sensor de objeto, comunicándose a través del bus SPI predeterminado de la placa.
spi = tablero.SPI()
cs = digitalio.DigitalInOut(board.D5) # Selección de chip de la placa MAX31865.
sensor = adafruit_max31865.MAX31865(spi,cs)

sensor = adafruit_max31865.MAX31865( spi, cs, rtd_nominal=100, ref_resistor=430.0, cables=2)

# Bucle principal para imprimir la temperatura cada segundo.
mientras que Verdadero:
    # Lea la temperatura.
    temp = sensor.temperatura
    # Imprime el valor. 
    print( "Temperatura: {0:0.3f}C" .formato(temp))
     # Retraso por un segundo.
    tiempo.dormir(1.0)
