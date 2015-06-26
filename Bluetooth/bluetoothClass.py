 # coding=utf-8

import contactList
import bluetoothReader
import logger

import Queue
import inspect
import bluetooth

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
	

	def __init__(self, _receptionBuffer):
		self.receptionBuffer = _receptionBuffer
		# Creamos un nuevo socket Bluetooth que usa el protocolo de transporte especificado
		self.localSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		# Enlazamos al adaptador local algun puerto disponible usando SDP (Service Discovery Protocol)
		self.localSocket.bind(('', bluetooth.PORT_ANY))
		# Especificamos el numero de conexiones permitidas (todavia sin aceptar) antes de rechazar las nuevas entrantes
		self.localSocket.listen(CONNECTIONS)
		# Especificamos el tiempo de espera de conexiones
		self.localSocket.settimeout(TIMEOUT)
		# Especificamos el anuncio de nuestro servicio
		bluetooth.advertise_service(self.localSocket, self.localServiceName,
									service_id = self.localUUID,
									service_classes = [self.localUUID, bluetooth.SERIAL_PORT_CLASS],
									profiles = [bluetooth.SERIAL_PORT_PROFILE])
		# Almacenamos el puerto asignado por el 'bind'
		self.localPort = self.localSocket.getsockname()[1]

	def __del__(self):
		self.localSocket.close()
		logger.write('INFO', '[BLUETOOTH] Objeto destruido.')

	def send(self, destinationServiceName, destinationMAC, destinationUUID, messageToSend):
		logger.write('DEBUG','[BLUETOOTH] Buscando el servicio \'%s\'.' % destinationServiceName)
		serviceMatches = bluetooth.find_service(uuid = destinationUUID, address = destinationMAC)
		if len(serviceMatches) == 0:
			logger.write('DEBUG', '[BLUETOOTH] No se pudo encontrar el servicio \'%s\'.' % destinationServiceName)
			return False
		else:
			firstMatch = serviceMatches[0]
			name = firstMatch['name']
			host = firstMatch['host']
			port = firstMatch['port']
			logger.write('DEBUG', '[BLUETOOTH] Conectando con la direccion \'%s\'...' % host)
			# Crea un nuevo socket Bluetooth que usa el protocolo de transporte especificado
			self.remoteSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
			# Conecta el socket con el dispositivo remoto (host) sobre el puerto (channel) especificado
			self.remoteSocket.connect((host, port))
			logger.write('DEBUG', '[BLUETOOTH] Conectado con el dispositivo Bluetooth.')
			self.remoteSocket.send(messageToSend)
			#print '[BLUETOOTH] Mensaje enviado al cliente especificado.'
			# Cierra la conexion del socket cliente
			self.remoteSocket.send('FIN')
			self.remoteSocket.close()
			return True

	def receive(self):
		queueThreads = Queue.Queue() # BORRAR: el cliente seria el que termina el thread creado. por lo que no haria falta
		while self.isActive:
			try:
				# Espera por una conexion entrante y devuelve un nuevo socket que representa la conexion, como asi tambien la direccion del cliente
				remoteSocket, remoteAddress = self.localSocket.accept()
				remoteSocket.settimeout(TIMEOUT)
				logger.write('DEBUG', '[BLUETOOTH] Conexion desde \'%s\' aceptada.' % remoteAddress[0])
				threadName = 'Thread-%s' % remoteAddress[0]
				readerThread = bluetoothReader.BluetoothReader(threadName, remoteSocket, self.receptionBuffer)
				readerThread.start()
				queueThreads.put(readerThread)
			except bluetooth.BluetoothError, msg:
				# Para que el bloque 'try' no se quede esperando indefinidamente
				pass
		# Terminamos los hilos creados (por la opcion 'Salir' del menu principal)
		while not queueThreads.empty():
			readerThread = queueThreads.get()
			readerThread.killReaderThread = True
		logger.write('WARNING','[BLUETOOTH] Funcion \'%s\' terminada.' % inspect.stack()[0][3])
