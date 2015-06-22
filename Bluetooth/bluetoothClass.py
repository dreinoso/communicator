import Queue
import inspect
import bluetooth

import contactList
import bluetoothReader

CONNECTIONS = 3
TIMEOUT = 1.5

class Bluetooth(object):

	localPort = ''
	localServiceName = contactList.BLUETOOTH_SERVICE_NAME
	localUUID = contactList.BLUETOOTH_UUID
	localSocket = bluetooth.BluetoothSocket
	remoteSocket = bluetooth.BluetoothSocket
	isActive = False

	receptionBuffer = list()
	processNotifications = True
	warningNotifications = True
	errorNotifications = True

	def __init__(self, _receptionBuffer, _processNotifications, _warningNotifications, _errorNotifications):
		self.receptionBuffer = _receptionBuffer
		self.processNotifications = _processNotifications
		self.warningNotifications = _warningNotifications
		self.errorNotifications = _errorNotifications
		# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
		self.localSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		# Enlaza algun puerto disponible usando SDP (Service Discovery Protocol) al adaptador local
		self.localSocket.bind(('', bluetooth.PORT_ANY))
		# Especificamos el numero de conexiones permitidas (todavia sin aceptar) antes de rechazar las nuevas entrantes
		self.localSocket.listen(CONNECTIONS)
		# Especificamos el tiempo de espera de conexiones
		self.localSocket.settimeout(TIMEOUT)
		bluetooth.advertise_service(self.localSocket, self.localServiceName,
									service_id = self.localUUID,
									service_classes = [self.localUUID, bluetooth.SERIAL_PORT_CLASS],
									profiles = [bluetooth.SERIAL_PORT_PROFILE])
		self.localPort = self.localSocket.getsockname()[1]

	def __del__(self):
		self.localSocket.close()
		print 'Objeto ' + self.__class__.__name__ + ' destruido.'

	def sendPacket(self, destinationServiceName, destinationMAC, destinationUUID, messageToSend):
		print 'Buscando el servicio \'%s\' sobre la direccion %s' % (destinationServiceName, destinationMAC)
		serviceMatches = bluetooth.find_service(uuid = destinationUUID, address = destinationMAC)
		if len(serviceMatches) == 0:
			print 'No se pudo encontrar el servicio \'%s\'' % destinationServiceName
		else:
			firstMatch = serviceMatches[0]
			name = firstMatch['name']
			host = firstMatch['host']
			port = firstMatch['port']
			print 'Conectando al servicio \'%s\' sobre la direccion %s...' % (name, host)
			# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
			self.remoteSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
			# Conecta el socket con el dispositivo remoto (host) sobre el puerto (channel) especificado
			self.remoteSocket.connect((host, port))
			print('Conectado con el dispositivo Bluetooth.')
			self.remoteSocket.send(messageToSend)
			# Cierra la conexion del socket cliente
			self.remoteSocket.send('FIN')
			self.remoteSocket.close()

	def send(self, destinationServiceName, destinationMAC, destinationUUID, messageToSend):
		print 'Buscando el servicio \'%s\' sobre la direccion %s' % (destinationServiceName, destinationMAC)
		serviceMatches = bluetooth.find_service(uuid = destinationUUID, address = destinationMAC)
		if len(serviceMatches) == 0:
			#print 'No se pudo encontrar el servicio \'%s\'' % destinationServiceName
			return False
		else:
			firstMatch = serviceMatches[0]
			name = firstMatch['name']
			host = firstMatch['host']
			port = firstMatch['port']
			print 'Conectando al servicio \'%s\' sobre la direccion %s...' % (name, host)
			# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
			self.remoteSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
			# Conecta el socket con el dispositivo remoto (host) sobre el puerto (channel) especificado
			self.remoteSocket.connect((host, port))
			print('Conectado con el dispositivo Bluetooth.')
			self.remoteSocket.send(messageToSend)
			# Cierra la conexion del socket cliente
			self.remoteSocket.send('FIN')
			self.remoteSocket.close()
			return True

	def receivePacket(self):
		queueThreads = Queue.Queue() # BORRAR: el cliente seria el que termina el thread creado. por lo que no haria falta
		while self.isActive:
			try:
				# Espera por una conexion entrante y devuelve un nuevo socket que representa la conexion, como asi tambien la direccion del cliente
				remoteSocket, remoteAddress = self.localSocket.accept()
				remoteSocket.settimeout(TIMEOUT)
				print 'Conexion desde ' + remoteAddress[0] + ' aceptada.'
				threadName = 'Thread%s' % contactList.sourceBluetooth[remoteAddress[0]]
				readerThread = bluetoothReader.BluetoothReader(threadName, remoteSocket, self.receptionBuffer)
				readerThread.start()
				queueThreads.put(readerThread)
			except bluetooth.BluetoothError:
				pass
		# Terminamos los hilos creados (por la opcion 'Salir' del menu principal)
		while not queueThreads.empty():
			readerThread = queueThreads.get()
			readerThread.killReaderThread = True
		print '[BLUETOOTH] Funcion \'%s\' terminada.' % inspect.stack()[0][3]
