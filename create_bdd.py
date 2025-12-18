import sqlite3

# Conectar o crear la base de datos
conexion = sqlite3.connect('sensor_data.db')

# Crear un cursor
cursor = conexion.cursor()

# Crear la tabla sensor_readings
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sensor_readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        temperature_measurement FLOAT NOT NULL,
        humidity FLOAT NOT NULL,
        pressure FLOAT NOT NULL,
        ethylene FLOAT NOT NULL,
        n FLOAT NOT NULL,
        ozone FLOAT NOT NULL,
        temperature_bar FLOAT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Guardar cambios
conexion.commit()

# Cerrar la conexión
conexion.close()