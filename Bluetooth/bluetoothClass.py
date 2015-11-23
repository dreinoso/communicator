# coding=utf-8

import json
import Queue
import inspect
import threading
import bluetooth

import logger
import contactList
import bluetoothReceptor
import bluetoothTransmitter

TIMEOUT = 1.5
CONNECTIONS = 3

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Bluetooth(object):

	bluetoothProtocol = JSON_CONFIG["BLUETOOTH"]["PROTOCOL"]
	localServiceName = JSON_CONFIG["BLUETOOTH"]["SERVICE"]
	localUUID = JSON_CONFIG["BLUETOOTH"]["UUID"]
	localSocketRFCOMM = bluetooth.BluetoothSocket()
	localSocketL2CAP = bluetooth.BluetoothSocket()
	localPortRFCOMM = 0
	localPortL2CAP = 0

	bluetoothTransmitter = bluetoothTransmitter.BluetoothTransmitter()

	receptionBuffer = Queue.PriorityQueue()
	isActive = False

	def __init__(self, _receptionBuffer):
		self.receptionBuffer = _receptionBuffer
		# Creamos un nuevo socket Bluetooth que usa el protocolo de transporte especificado
		self.localSocketRFCOMM = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		self.localSocketL2CAP = bluetooth.BluetoothSocket(bluetooth.L2CAP)
		# Enlazamos al adaptador local algun puerto disponible usando SDP (Service Discovery Protocol)
		self.localSocketRFCOMM.bind(('', bluetooth.PORT_ANY))
		self.localSocketL2CAP.bind(('', bluetooth.PORT_ANY))
		# Especificamos el numero de conexiones permitidas (todavia sin aceptar) antes de rechazar las nuevas entrantes
		self.localSocketRFCOMM.listen(CONNECTIONS)
		self.localSocketL2CAP.listen(CONNECTIONS)
		# Especificamos el tiempo de espera de conexiones (funcion 'accept')
		self.localSocketRFCOMM.settimeout(TIMEOUT)
		self.localSocketL2CAP.settimeout(TIMEOUT)
		# Especificamos el anuncio de nuestro servicio
		bluetooth.advertise_service(self.localSocketRFCOMM, self.localServiceName,
									service_id = self.localUUID,
									service_classes = [self.localUUID, bluetooth.SERIAL_PORT_CLASS],
									profiles = [bluetooth.SERIAL_PORT_PROFILE])
		bluetooth.advertise_service(self.localSocketL2CAP, self.localServiceName,
									service_id = self.localUUID,
									service_classes = [self.localUUID])
		# Almacenamos el puerto asignado por el 'bind'
		self.localPortRFCOMM = self.localSocketRFCOMM.getsockname()[1]
		self.localPortL2CAP = self.localSocketL2CAP.getsockname()[1]

	def __del__(self):
		logger.write('INFO', '[BLUETOOTH] Objeto destruido.')

	def connect(self):
		'VOLVER A CREAR EL SOCKET RFCOMM'
		pass #TODO

	def send(self, messageToSend, destinationServiceName, destinationMAC, destinationUUID):
		logger.write('DEBUG', '[BLUETOOTH] Buscando el servicio \'%s\'.' % destinationServiceName)
		serviceMatches = bluetooth.find_service(uuid = destinationUUID, address = destinationMAC)
		# Buscamos alguna coincidencia de servicios Bluetooth especificos
		if len(serviceMatches) == 0:
			logger.write('DEBUG', '[BLUETOOTH] No se pudo encontrar el servicio \'%s\'.' % destinationServiceName)
			return False
		else:
			try:
				firstMatch = serviceMatches[0]
				name = firstMatch['name']
				host = firstMatch['host']
				port = firstMatch['port']
				# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
				remoteSocket = bluetooth.BluetoothSocket(self.bluetoothProtocol)
				# Conecta el socket con el dispositivo remoto (host) sobre el puerto (channel) especificado
				remoteSocket.connect((host, port))
				logger.write('DEBUG', '[BLUETOOTH] Conectado con la dirección \'%s\'.' % host)
				return self.bluetoothTransmitter.send(messageToSend, remoteSocket)
			except bluetooth.btcommon.BluetoothError as bluetoothError:
				# (11, 'Resource temporarily unavailable')
				# (16, 'Device or resource busy')
				logger.write('WARNING','[BLUETOOTH] %s.' % bluetoothError)
				return False

	def receive(self):
		rfcommThread = threading.Thread(target = self.receiveRFCOMM, name = 'rfcommReceptor')
		rfcommThread.start()
		rfcommThread.join()

	def receiveRFCOMM(self):
		while self.isActive:
			try:
				# Espera por una conexión entrante y devuelve un nuevo socket que representa la conexión, como así también la dirección del cliente
				remoteSocket, addr = self.localSocketRFCOMM.accept()
				macAddress = addr[0]
				remoteSocket.settimeout(TIMEOUT)
				threadName = 'Thread-%s' % macAddress
				# Aplicamos el filtro de recepción en caso de estar activado...
				if JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
					macAddressFounded = False
					for valueList in contactList.allowedMacAddress.values():
						if macAddress in valueList:
							logger.write('DEBUG', '[BLUETOOTH] Conexion desde \'%s\' aceptada.' % macAddress)
							receptorThread = bluetoothReceptor.BluetoothReceptor(threadName, remoteSocket, self.receptionBuffer)
							macAddressFounded = True
							receptorThread.start()
							break
					if not macAddressFounded:
						logger.write('WARNING', '[BLUETOOTH] Mensaje de \'%s\' rechazado!' % macAddress)
						remoteSocket.close()
				# ... sino, recibimos todos los mensajes independientemente del origen
				else:
					logger.write('DEBUG', '[BLUETOOTH] Conexion desde \'%s\' aceptada.' % macAddress)
					receptorThread = bluetoothReceptor.BluetoothReceptor(threadName, remoteSocket, self.receptionBuffer)
					receptorThread.start()
			# Para que el bloque 'try' (en la funcion 'accept') no se quede esperando indefinidamente
			except bluetooth.BluetoothError, msg:
				pass
		self.localSocketRFCOMM.close()
		logger.write('WARNING','[BLUETOOTH] Función \'%s\' terminada.' % inspect.stack()[0][3])