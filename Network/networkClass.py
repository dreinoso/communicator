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

import tcpReceptor
import tcpTransmitter
import udpTransmitter

''' For best match with hardware and network realities, the value of bufsize should be
	a relatively small power of 2, for example, 4096'''
TIMEOUT = 1.5
BUFFER_SIZE = 4096 # Tamano del buffer en bytes (cantidad de caracteres)
CONNECTION_LIMIT = 5

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Network(object):

	tcpPort = JSON_CONFIG["NETWORK"]["TCP_PORT"]
	udpPort = JSON_CONFIG["NETWORK"]["UDP_PORT"]

	localInterface = None
	localAddress = None

	successfulConnection = None
	receptionQueue = None
	isActive = False

	def __init__(self, _receptionQueue):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionQueue: Buffer para la recepción de datos
		@type: list"""
		self.receptionQueue = _receptionQueue

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
			logger.write('INFO', '[NETWORK] Objeto destruido.')

	def connect(self, _localInterface):
		'''Se realizan las conexiones de los protocolos UDP y TCP para la comunicación
		por medio de NETWORK.'''
		self.localInterface = _localInterface
		try:
			# Obtenemos la dirección IP local asignada estáticamente o por DHCP
			commandToExecute = 'ip addr show ' + self.localInterface + ' | grep inet'
			self.localAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
			# Creamos los sockets para una conexión TCP
			self.tcpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.tcpReceptionSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.tcpReceptionSocket.bind((self.localAddress, self.tcpPort))
			self.tcpReceptionSocket.listen(CONNECTION_LIMIT)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
			# Creamos los sockets para una conexión UDP
			self.udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.udpReceptionSocket.bind((self.localAddress, self.udpPort))
			self.udpReceptionSocket.settimeout(TIMEOUT)
			#####################################################
			self.tcpTransmitter = tcpTransmitter.TcpTransmitter()
			self.udpTransmitter = udpTransmitter.UdpTransmitter()
			#####################################################
			self.successfulConnection = True
			return True
		except socket.error as errorMessage:
			logger.write('ERROR', '[NETWORK] %s.' % str(errorMessage))
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
		try:
			if isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
				# Crea un nuevo socket que usa el protocolo de transporte especificado
				clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Conecta el socket con el dispositivo remoto sobre el puerto especificado
				clientSocket.connect((destinationHost, destinationTcpPort))
				logger.write('DEBUG', '[NETWORK-TCP] Conectado con la dirección \'%s\'.' % destinationHost)
				return self.tcpTransmitter.sendFile(message.fileName, clientSocket)
			else:
				return self.udpTransmitter.send(message, destinationHost, destinationUdpPort)
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] %s.' % errorMessage)
			return False
	
	def receive(self):
		"""Comienza la recepción de datos por medio de los protocolos TCP y UDP
		para esto requiere la inciación de hilos que esperen los datos en paralelo
		a la ejecución del programa."""
		self.isActive = True
		receiveTcpThread = threading.Thread(target = self.receiveTcp, name = 'tcpReceptor')
		receiveUdpThread = threading.Thread(target = self.receiveUdp, name = 'udpReceptor')
		receiveTcpThread.start()
		receiveUdpThread.start()
		receiveTcpThread.join()
		receiveUdpThread.join()

	def receiveTcp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto TCP establecido para guardarlos en el buffer."""
		while self.isActive:
			try:
				# Espera por una conexion entrante y devuelve un nuevo socket que representa la conexion, como asi tambien la direccion del cliente
				remoteSocket, addr = self.tcpReceptionSocket.accept()
				remoteSocket.settimeout(TIMEOUT)
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
					logger.write('DEBUG', '[NETWORK-TCP] Conexion desde \'%s\' aceptada.' % ipAddress)
					receptorThread = tcpReceptor.TcpReceptor('Thread-Receptor', remoteSocket, self.receptionQueue)
					receptorThread.start()
				# El cliente no fue encontrado, por lo que debemos rechazar su mensaje
				else:
					logger.write('WARNING', '[NETWORK-TCP] Mensaje de \'%s\' rechazado!' % ipAddress)
					remoteSocket.close()
			# Para que el bloque 'try' (en la funcion 'accept') no se quede esperando indefinidamente
			except socket.timeout as errorMessage:
				pass
		self.tcpReceptionSocket.close()
		logger.write('WARNING','[NETWORK-TCP] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def receiveUdp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto UDP establecido para guardarlos en el buffer."""	
		while self.isActive:
			try:
				receivedData, addr = self.udpReceptionSocket.recvfrom(BUFFER_SIZE)
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
					logger.write('DEBUG', '[NETWORK-UDP] Conexion desde \'%s\' aceptada.' % ipAddress)
					if receivedData.startswith('INSTANCE'):
						# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
						serializedMessage = receivedData[len('INSTANCE'):]
						# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
						messageInstance = pickle.loads(serializedMessage)
						self.receptionQueue.put((messageInstance.priority, messageInstance))
						logger.write('INFO', '[NETWORK-UDP] Ha llegado una nueva instancia de mensaje!')
					else:
						self.receptionQueue.put((10, receivedData))
						logger.write('INFO', '[NETWORK-UDP] Ha llegado un nuevo mensaje!')
				# El cliente no fue encontrado, por lo que debemos rechazar su mensaje
				else:
					logger.write('WARNING', '[NETWORK-UDP] Mensaje de \'%s\' rechazado!' % ipAddress)
			# Esta excepción es parte de la ejecución, no implica un error
			except socket.timeout, errorMessage:
				pass
		self.udpReceptionSocket.close()
		logger.write('WARNING', '[NETWORK-UDP] Funcion \'%s\' terminada.' % inspect.stack()[0][3])