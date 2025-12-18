import bluetooth


print("hola")

def receive_data():
	print("inicializando receiveddata")
	server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
	server_sock.bind(("", bluetooth.PORT_ANY))
	server_sock.listen(1)
	port = server_sock.getsockname()[1]
	try:
		bluetooth.advertise_service(server_sock, "ESP32",
									service_id="00001101-0000-1000-8000-00805F9B34FB",
									service_classes=["00001101-0000-1000-8000-00805F9B34FB"],
									profiles=[bluetooth.SERIAL_PORT_PROFILE])

		print(f"Waiting for connection on RFCOMM channel {port}")

		print(f"Accepted connection from {client_info}")
	except Exception as e:
		print(f"El error es {e}")
	client_sock, client_info = server_sock.accept()
	try:
		while True:
			data = client_sock.recv(1024)
			if not data:
				break	
			print(f"Received: {data.decode('utf-8')}")
	
	except OSError:
		print("error in recv info")

	print("Disconnected.")
	client_sock.close()
	server_sock.close()

if __name__ == "__main__":
	print("inital function")
	receive_data()
