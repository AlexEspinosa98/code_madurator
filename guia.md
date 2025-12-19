# Arranque automático de `guide_finally.py` en Raspberry Pi

Esta guía deja el temporizador en horas (ver `guide_finally.py`) y configura el arranque automático al iniciar la Raspberry Pi.

## 1. Requisitos previos
- Ruta del proyecto (ajusta según tu instalación): `/home/pi/patente/code_madurator`
- Python 3 y dependencias instaladas en el sistema o en un entorno virtual (`PyQt6`, `adafruit-circuitpython-max31865`, etc.).

## 2. Archivo de servicio `systemd`
1. Crear el servicio:
   ```bash
   sudo nano /etc/systemd/system/guide_finally.service
   ```
2. Contenido sugerido (ajusta `User`, `WorkingDirectory`, `ExecStart`, `DISPLAY` si usas otra sesión gráfica):
   ```ini
   [Unit]
   Description=UI Madurator (guide_finally.py)
   After=network.target graphical.target
   Wants=graphical.target

   [Service]
   Type=simple
   User=pi
   WorkingDirectory=/home/pi/patente/code_madurator
   ExecStart=/usr/bin/python3 /home/pi/patente/code_madurator/guide_finally.py
   Environment=DISPLAY=:0
   Environment=XAUTHORITY=/home/pi/.Xauthority
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   ```

## 3. Habilitar y probar
```bash
sudo systemctl daemon-reload
sudo systemctl enable guide_finally.service   # Arranca en cada boot
sudo systemctl start guide_finally.service    # Inicia ahora
sudo systemctl status guide_finally.service   # Verifica logs/estado
```

## 4. Detener o deshabilitar
```bash
sudo systemctl stop guide_finally.service
sudo systemctl disable guide_finally.service
```

## Notas
- Si usas entorno virtual, cambia `ExecStart` a la ruta del `python` de tu venv.
- Asegúrate de que la cuenta (`User`) tenga permisos sobre `/dev/serial0`, GPIO y los archivos del proyecto.
- Si la interfaz gráfica no se abre, revisa que `DISPLAY` y `XAUTHORITY` apunten al escritorio que uses.
