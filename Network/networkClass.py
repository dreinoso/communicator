# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import json
import pickle
import socket
import inspect
import threading

import logger
import contactList
import messageClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

TIMEOUT = 1.5
DOWNLOADS = 'Downloads'

class Network(object):

	MEDIA_NAME = None

	TCP_PORT = JSON_CONFIG["NETWORK"]["TCP_PORT"]
	UDP_PORT = JSON_CONFIG["NETWORK"]["UDP_PORT"]
	BUFFER_SIZE = JSON_CONFIG["NETWORK"]["BUFFER_SIZE"]
	CONNECTIONS = JSON_CONFIG["NETWORK"]["CONNECTIONS"]

	localInterface = None
	localIPAddress = None

	successfulConnection = None
	receptionQueue = None
	isActive = False

	def __init__(self, _receptionQueue, _MEDIA_NAME):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionQueue: Buffer para la recepción de datos
		@type: list"""
		self.receptionQueue = _receptionQueue
		self.MEDIA_NAME = _MEDIA_NAME

	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		puertos ocupados en el Host"""
		try:
			# Eliminamos del archivo la interfaz usada en esta misma instancia
			dataToWrite = open('/tmp/activeInterfaces').read().replace(self.localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
			self.tcpReceptionSocket.close()
			self.udpReceptionSocket.close()
		except Exception as errorMessage:
			pass
		finally:
			logger.write('INFO', '[%s] Objeto destruido.' % self.MEDIA_NAME)

	def connect(self, _localIPAddress):
		'''Se realizan las conexiones de los protocolos UDP y TCP para la comunicación
		por medio de NETWORK.'''
		self.localIPAddress = _localIPAddress
		try:
			# Creamos los sockets para una conexión TCP
			self.tcpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.tcpReceptionSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.tcpReceptionSocket.bind((self.localIPAddress, self.TCP_PORT))
			self.tcpReceptionSocket.listen(self.CONNECTIONS)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
			# Creamos los sockets para una conexión UDP
			self.udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.udpReceptionSocket.bind((self.localIPAddress, self.UDP_PORT))
			self.udpReceptionSocket.settimeout(TIMEOUT)
			self.successfulConnection = True
			return True
		except socket.error as errorMessage:
			logger.write('ERROR', '[%s] %s.' % (self.MEDIA_NAME, str(errorMessage)))
			self.successfulConnection = False
			return False

	def send(self, message, destinationHost, destinationTcpPort, destinationUdpPort):
		""" Envia una cadena de texto.
		@param detinationIP: dirección IP del destinatario
		@type emailDestination: str
		@param destinationTcpPort: N° de puerto TCP del destinatario
		@type destinationTcpPort: int
		@param destinationUdpPort: N° de puerto UDP del destinatario
		@type destinationUdpPort: int
		@param message: cadena de texto a enviar
		@type message: str """
		# Comprobamos si el host destino es alcanzable, es decir, si existe
		pingResponse = os.system('ping -c 3 ' + destinationHost + ' >/dev/null 2>&1') # El '>/dev/null 2>&1' silencia stdout y stderr
		if pingResponse is 0:
			try:
				# Comprobación de envío de archivo
				if isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
					# Crea un nuevo socket que usa el protocolo de transporte especificado
					clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
					# Conecta el socket con el dispositivo remoto sobre el puerto especificado
					clientSocket.connect((destinationHost, destinationTcpPort))
					logger.write('DEBUG', '[%s-TCP] Conectado con la dirección \'%s\'.' % (self.MEDIA_NAME, destinationHost))
					return self.sendFile(message.fileName, clientSocket)
				# Comprobación de envío de texto plano
				elif isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
					return self.sendMessage(message.plainText, destinationHost, destinationUdpPort)
				# Entonces se trata de enviar una instancia de mensaje
				else:
					return self.sendMessageInstance(message, destinationHost, destinationUdpPort)
			except socket.error as errorMessage:
				logger.write('WARNING', '[%s] %s.' % (self.MEDIA_NAME, errorMessage))
				return False
		else:
			logger.write('WARNING', '[%s] El host destino \'%s\' es inalcanzable!' % (self.MEDIA_NAME, destinationHost))
			return False

	def sendFile(self, fileName, clientSocket):
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			absoluteFilePath = os.path.abspath(fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			clientSocket.send(fileName) # Enviamos el nombre del archivo
			# Recibe confirmación para comenzar a transmitir (READY)
			if clientSocket.recv(self.BUFFER_SIZE) == "READY":
				# Guardamos la posición inicial del archivo (donde comienza)
				fileBeginning = fileObject.tell()
				# Apuntamos al final del archivo
				fileObject.seek(0, os.SEEK_END)
				# Obtenemos la posición final del mismo (que sería el tamaño)
				fileSize = fileObject.tell()
				# Apuntamos nuevamente al comienzo del archivo, para comenzar a transmitir
				fileObject.seek(fileBeginning, os.SEEK_SET)
				# Envio del contenido del archivo
				bytesSent = 0
				logger.write('DEBUG', '[%s-TCP] Transfiriendo archivo \'%s\'...' % (self.MEDIA_NAME, fileName))
				while bytesSent < fileSize:
					outputData = fileObject.read(self.BUFFER_SIZE)
					clientSocket.send(outputData)
					bytesSent += len(outputData)
					clientSocket.recv(self.BUFFER_SIZE) # ACK
				fileObject.close()
				clientSocket.send('EOF')
				logger.write('INFO', '[%s-TCP] Archivo \'%s\' enviado correctamente!' % (self.MEDIA_NAME, fileName))
				return True
			# Recibe 'FILE_EXISTS'
			else:
				logger.write('WARNING', '[%s-TCP] El archivo \'%s\' ya existe, fue rechazado!' % (self.MEDIA_NAME, fileName))
				# Devolvemos 'True' para que no intente reenviar el archivo
				return True
		except Exception as errorMessage:
			logger.write('WARNING', '[%s-TCP] Archivo \'%s\' no enviado: %s' % (self.MEDIA_NAME, fileName, str(errorMessage)))
			return False
		finally:
			# Cierra la conexion del socket cliente
			clientSocket.close()

	def sendMessage(self, plainText, destinationHost, destinationUdpPort):
		'''Envío de mensaje simple'''
		try:
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)			
			transmissionSocket.sendto(plainText, (destinationHost, destinationUdpPort))
			logger.write('INFO', '[%s-UDP] Mensaje enviado correctamente!' % self.MEDIA_NAME)
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[%s-UDP] Mensaje no enviado: %s' % (self.MEDIA_NAME, str(errorMessage)))
			return False
		finally:
			# Cerramos el socket que permitió la conexión con el cliente
			transmissionSocket.close()

	def sendMessageInstance(self, message, destinationHost, destinationUdpPort):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Transmitimos la instancia serializada al destino correspondiente
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			transmissionSocket.sendto(serializedMessage, (destinationHost, destinationUdpPort))
			logger.write('INFO', '[%s-UDP] Instancia de mensaje enviada correctamente!' % self.MEDIA_NAME)
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[%s-UDP] Instancia de mensaje no enviada: %s' % (self.MEDIA_NAME, str(errorMessage)))
			return False
		finally:
			# Cerramos el socket que permitió la conexión con el cliente
			transmissionSocket.close()

	def receive(self):
		"""Comienza la recepción de datos por medio de los protocolos TCP y UDP
		para esto requiere la inciación de hilos que esperen los datos en paralelo
		a la ejecución del programa."""
		self.isActive = True
		receiveTcpThread = threading.Thread(target = self.receiveTCP, name = 'tcpReceptor')
		receiveUdpThread = threading.Thread(target = self.receiveUDP, name = 'udpReceptor')
		receiveTcpThread.start()
		receiveUdpThread.start()
		receiveTcpThread.join()
		receiveUdpThread.join()

	def receiveTCP(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto TCP establecido para guardarlos en el buffer."""
		while self.isActive:
			try:
				# Espera por una conexion entrante y devuelve un nuevo socket que representa la conexion, como asi tambien la direccion del cliente
				remoteSocket, addr = self.tcpReceptionSocket.accept()
				enabledFilter = False
				ipAddress = addr[0]
				# Aplicamos el filtro de recepción en caso de estar activado
				if JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
					enabledFilter = True
					for valueList in contactList.allowedHosts.values():
						if ipAddress in valueList:
							# Deshabilitamos el filtro ya que el cliente estaba registrado
							enabledFilter = False
							break
				# El filtro está activado y el cliente fue encontrado, o el filtro no está habilitado
				if not enabledFilter:
					#logger.write('DEBUG', '[NETWORK-TCP] Conexion desde \'%s\' aceptada.' % ipAddress)
					receptorThread = threading.Thread(target = self.receiveFile, args = (remoteSocket, ))
					receptorThread.start()
				# El cliente no fue encontrado, por lo que debemos rechazar su mensaje
				else:
					logger.write('WARNING', '[%s-TCP] Mensaje de \'%s\' rechazado!' % (self.MEDIA_NAME, ipAddress))
					remoteSocket.close()
			# Para que el bloque 'try' (en la funcion 'accept') no se quede esperando indefinidamente
			except socket.timeout as errorMessage:
				pass
		self.tcpReceptionSocket.close()
		logger.write('WARNING','[%s-TCP] Función \'%s\' terminada.' % (self.MEDIA_NAME, inspect.stack()[0][3]))

	def receiveUDP(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto UDP establecido para guardarlos en el buffer."""	
		while self.isActive:
			try:
				receivedData, addr = self.udpReceptionSocket.recvfrom(self.BUFFER_SIZE)
				enabledFilter = False
				ipAddress = addr[0]
				# Aplicamos el filtro de recepción en caso de estar activado
				if JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
					enabledFilter = True
					for valueList in contactList.allowedHosts.values():
						if ipAddress in valueList:
							# Deshabilitamos el filtro ya que el cliente estaba registrado
							enabledFilter = False
							break
				# El filtro está activado y el cliente fue encontrado, o el filtro no está habilitado
				if not enabledFilter:
					#logger.write('DEBUG', '[NETWORK-UDP] Conexión desde \'%s\' aceptada.' % ipAddress)
					if receivedData.startswith('INSTANCE'):
						# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
						serializedMessage = receivedData[len('INSTANCE'):]
						# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
						messageInstance = pickle.loads(serializedMessage)
						self.receptionQueue.put((messageInstance.priority, messageInstance))
						logger.write('INFO', '[%s-UDP] Ha llegado una nueva instancia de mensaje!' % self.MEDIA_NAME)
					else:
						self.receptionQueue.put((10, receivedData))
						logger.write('INFO', '[%s-UDP] Ha llegado un nuevo mensaje!' % self.MEDIA_NAME)
				# El cliente no fue encontrado, por lo que debemos rechazar su mensaje
				else:
					logger.write('WARNING', '[%s-UDP] Mensaje de \'%s\' rechazado!' % (self.MEDIA_NAME, ipAddress))
			# Esta excepción es parte de la ejecución, no implica un error
			except socket.timeout, errorMessage:
				pass
		self.udpReceptionSocket.close()
		logger.write('WARNING', '[%s-UDP] Función \'%s\' terminada.' % (self.MEDIA_NAME, inspect.stack()[0][3]))

	def receiveFile(self, remoteSocket):
		'''Para la recepción del archivo, primero se verifica que le archivo no 
		exista, de existir el archivo, se avisa al transmisor. En caso de que no 
		exista se confirma al emisor para que comience a transmitir, se crea el 
		archivo y la capeta de descarga en caso de que no exista. Se escribe el 
		archivo a medida que llegan los paquetes.'''
		try:
			currentDirectory = os.getcwd()                 # Obtenemos el directorio actual de trabajo
			fileName = remoteSocket.recv(self.BUFFER_SIZE) # Obtenemos el nombre del archivo a recibir
			# Obtenemos el path relativo del archivo a descargar
			relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, fileName)
			# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
			if DOWNLOADS not in os.listdir(currentDirectory):
				os.mkdir(DOWNLOADS)
			# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
			if not os.path.isfile(relativeFilePath):
				fileObject = open(relativeFilePath, 'w+')
				logger.write('DEBUG', '[%s-TCP] Descargando archivo \'%s\'...' % (self.MEDIA_NAME, fileName))
				remoteSocket.send('READY')
				# Comenzamos a descargar el archivo
				while True:
					inputData = remoteSocket.recv(self.BUFFER_SIZE)
					if inputData != 'EOF':
						fileObject.write(inputData)
						remoteSocket.send('ACK')
					else: 
						fileObject.close()
						break
				self.receptionQueue.put((10, fileName))
				logger.write('INFO', '[%s-TCP] Archivo \'%s\' descargado correctamente!' % (self.MEDIA_NAME, fileName))
				return True
			else:
				# Comunicamos al transmisor que el archivo ya existe
				remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[%s-TCP] El archivo \'%s\' ya existe! Imposible descargar.' % (self.MEDIA_NAME, fileName))
				return False
		except socket.error as errorMessage:
			logger.write('WARNING', '[%s-TCP] Error al intentar descargar el archivo \'%s\': %s' % (self.MEDIA_NAME, fileName, str(errorMessage)))
			return False
		finally:
			# Cierra la conexion del socket cliente
			remoteSocket.close()