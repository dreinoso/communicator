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

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

TIMEOUT = 1.5
CONNECTIONS = 3

class Bluetooth(object):

	localServiceName = JSON_CONFIG["BLUETOOTH"]["SERVICE"]
	localUUID = JSON_CONFIG["BLUETOOTH"]["UUID"]

	localInterface = None
	localMACAddress = None
	localPortRFCOMM = None

	successfulConnection = None
	receptionQueue = None
	isActive = False

	def __init__(self, _receptionQueue):
		self.receptionQueue = _receptionQueue

	def __del__(self):
		try:
			# Eliminamos del archivo la MAC usada en esta misma instancia
			dataToWrite = open('/tmp/activeInterfaces').read().replace(self.localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		except Exception as errorMessage:
			pass
		finally:
			logger.write('INFO', '[BLUETOOTH] Objeto destruido.')

	# La función 'receiveRFCOMM' cierra el socket al finalizar, por eso hay que hacer esto de nuevo
	def connect(self, _localMACAddress):
		self.localMACAddress = _localMACAddress
		try:
			# Creamos un nuevo socket Bluetooth que usa el protocolo de transporte especificado
			self.serverSocketRFCOMM = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
			# Enlazamos al adaptador local algun puerto disponible
			self.serverSocketRFCOMM.bind((self.localMACAddress, bluetooth.PORT_ANY))
			# Especificamos el numero de conexiones permitidas (todavia sin aceptar) antes de rechazar las nuevas entrantes
			self.serverSocketRFCOMM.listen(CONNECTIONS)
			# Especificamos el tiempo de espera de conexiones (funcion 'accept')
			self.serverSocketRFCOMM.settimeout(TIMEOUT)
			# Utilizamos SDP para anunciar nuestro servicio como un puerto serial
			bluetooth.advertise_service(self.serverSocketRFCOMM, self.localServiceName,
										service_id = self.localUUID,
										service_classes = [self.localUUID, bluetooth.SERIAL_PORT_CLASS],
										profiles = [bluetooth.SERIAL_PORT_PROFILE])
			# Almacenamos el puerto asignado por el 'bind'
			self.localPortRFCOMM = self.serverSocketRFCOMM.getsockname()[1]
			#######################################################################
			self.bluetoothTransmitter = bluetoothTransmitter.BluetoothTransmitter()
			#######################################################################
			self.successfulConnection = True
			return True
		except bluetooth._bluetooth.error as bluetoothError:
			logger.write('ERROR', '[BLUETOOTH] Código de error %s - %s.' % (bluetoothError[0], bluetoothError[1]))
			self.successfulConnection = False
			return False

	def send(self, messageToSend, destinationServiceName, destinationMAC, destinationUUID):
		logger.write('DEBUG', '[BLUETOOTH] Buscando el servicio \'%s\'.' % destinationServiceName)
		# Buscamos un servicio Bluetooth específico
		serviceMatches = bluetooth.find_service(uuid = destinationUUID, address = destinationMAC)
		# Verificamos si hubo alguna coincidencia
		if len(serviceMatches) > 0:
			try:
				firstMatch = serviceMatches[0]
				name = firstMatch['name']
				host = firstMatch['host']
				port = firstMatch['port']
				# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
				clientSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
				# Conecta el socket con el dispositivo remoto (host) sobre el puerto (channel) especificado
				clientSocket.connect((host, port))
				logger.write('DEBUG', '[BLUETOOTH] Conectado con la dirección \'%s\'.' % host)
				return self.bluetoothTransmitter.send(messageToSend, clientSocket)
			except bluetooth.btcommon.BluetoothError as bluetoothError:
				# (11, 'Resource temporarily unavailable')
				# (16, 'Device or resource busy')
				logger.write('WARNING','[BLUETOOTH] %s.' % bluetoothError)
				return False
		else:
			logger.write('DEBUG', '[BLUETOOTH] No se pudo encontrar el servicio \'%s\'.' % destinationServiceName)
			return False

	def receive(self):
		self.isActive = True
		rfcommThread = threading.Thread(target = self.receiveRFCOMM, name = 'rfcommReceptor')
		rfcommThread.start()
		rfcommThread.join()

	def receiveRFCOMM(self):
		while self.isActive:
			try:
				# Espera por una conexión entrante y devuelve un nuevo socket que representa la conexión, como así también la dirección del cliente
				remoteSocket, addr = self.serverSocketRFCOMM.accept()
				remoteSocket.settimeout(TIMEOUT)
				enabledFilter = False
				macAddress = addr[0]
				# Aplicamos el filtro de recepción en caso de estar activado
				if JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
					enabledFilter = True
					for valueList in contactList.allowedMacAddress.values():
						if ipAddress in valueList:
							# Deshabilitamos el filtro ya que el cliente estaba registrado
							enabledFilter = False
							break
				# El filtro está activado y el cliente fue encontrado, o el filtro no está habilitado
				if not enabledFilter:
					logger.write('DEBUG', '[BLUETOOTH] Conexión desde \'%s\' aceptada.' % macAddress)
					receptorThread = bluetoothReceptor.BluetoothReceptor('Thread-Receptor', remoteSocket, self.receptionQueue)
					receptorThread.start()
				# El cliente no fue encontrado, por lo que debemos rechazar su mensaje
				else:
					logger.write('WARNING', '[BLUETOOTH] Mensaje de \'%s\' rechazado!' % macAddress)
					remoteSocket.close()
			# Para que el bloque 'try' (en la funcion 'accept') no se quede esperando indefinidamente
			except bluetooth.BluetoothError, msg:
				pass
		self.serverSocketRFCOMM.close()
		logger.write('WARNING','[BLUETOOTH] Función \'%s\' terminada.' % inspect.stack()[0][3])