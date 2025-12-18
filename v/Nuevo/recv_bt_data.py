from bluepy.btle import Peripheral, UUID, DefaultDelegate

class MyDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, cHandle, data):
        print("Notification:", data.decode("utf-8"))

# Reemplaza 'ESP32_DEVICE_ADDRESS' con la dirección BLE de tu ESP32
p = Peripheral('ESP32_DEVICE_ADDRESS', 'random')
p.setDelegate(MyDelegate())

# Reemplaza 'SERVICE_UUID' y 'CHARACTERISTIC_UUID' con tus UUIDs
svc = p.getServiceByUUID(UUID('SERVICE_UUID'))
ch = svc.getCharacteristics('CHARACTERISTIC_UUID')[0]

print("Esperando notificaciones...")
while True:
    if p.waitForNotifications(1.0):
        continue
    print("Esperando...")
