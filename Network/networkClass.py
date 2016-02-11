# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import json
import time
import Queue
import socket
import inspect
import threading

import logger
import contactList
import tcpReceptor
import udpReceptor
import tcpTransmitter
import udpTransmitter

TIMEOUT = 1.5
BUFFER_SIZE = 1024
CONNECTION_LIMIT = 5

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Network(object):

	localAddress = None
	localInterface = None

	networkProtocol = JSON_CONFIG["NETWORK"]["PROTOCOL"]
	tcpReceptionPort = JSON_CONFIG["NETWORK"]["TCP_PORT"]
	udpReceptionPort = JSON_CONFIG["NETWORK"]["UDP_PORT"]

	receptionBuffer = Queue.PriorityQueue()
	successfulConnection = None
	isActive = False

	def __init__(self, _receptionBuffer):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		self.receptionBuffer = _receptionBuffer

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
			self.tcpReceptionSocket.bind((self.localAddress, self.tcpReceptionPort))
			self.tcpReceptionSocket.listen(CONNECTION_LIMIT)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
			# Creamos los sockets para una conexión UDP
			self.udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.udpReceptionSocket.bind((self.localAddress, self.udpReceptionPort))
			self.udpReceptionSocket.settimeout(TIMEOUT)
			######################################################################
			self.tcpTransmitter = tcpTransmitter.TcpTransmitter()
			self.udpTransmitter = udpTransmitter.UdpTransmitter(self.localAddress)
			######################################################################
			self.successfulConnection = True
			return True
		except socket.error as errorMessage:
			logger.write('ERROR', '[NETWORK] %s.' % str(errorMessage))
			self.successfulConnection = False
			return False

	def send(self, message, destinationIp, destinationTcpPort, destinationUdpPort):
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
			if self.networkProtocol == 'TCP':
				# Crea un nuevo socket que usa el protocolo de transporte especificado
				remoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Conecta el socket con el dispositivo remoto sobre el puerto especificado
				remoteSocket.connect((destinationIp, destinationTcpPort))
				logger.write('DEBUG', '[NETWORK-TCP] Conectado con la dirección \'%s\'.' % destinationIp)
				return self.tcpTransmitter.send(message, remoteSocket)
			else:
				return self.udpTransmitter.send(message, destinationIp, destinationUdpPort)
		except socket.error as errorMessage:
			logger.write('WARNING','[NETWORK] %s.' % errorMessage)
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
				ipAddress = addr[0]
				remoteSocket.settimeout(TIMEOUT)
				threadName = 'Thread-TCPReceptor'
				# Aplicamos el filtro de recepción en caso de estar activado...
				if JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
					ipAddressFounded = False
					for valueList in contactList.allowedIpAddress.values():
						if ipAddress in valueList:
							logger.write('DEBUG', '[NETWORK-TCP] Conexion desde \'%s\' aceptada.' % ipAddress)
							receptorThread = tcpReceptor.TcpReceptor(threadName, remoteSocket, self.receptionBuffer)
							ipAddressFounded = True
							receptorThread.start()
							break
					if not ipAddressFounded:
						logger.write('WARNING', '[NETWORK-TCP] Mensaje de \'%s\' rechazado!' % ipAddress)
						remoteSocket.close()
				# ... sino, recibimos todos los mensajes independientemente del origen
				else:
					logger.write('DEBUG', '[NETWORK-TCP] Conexion desde \'%s\' aceptada.' % ipAddress)
					receptorThread = tcpReceptor.TcpReceptor(threadName, remoteSocket, self.receptionBuffer)
					receptorThread.start()
			# Para que no se quede esperando indefinidamente en el'accept'
			except socket.timeout as errorMessage:
				pass
		self.tcpReceptionSocket.close()
		logger.write('WARNING','[NETWORK-TCP] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def receiveUdp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto UDP establecido para guardarlos en el buffer."""	
		while self.isActive:
			try:
				dataReceived, addr = self.udpReceptionSocket.recvfrom(BUFFER_SIZE)
				if dataReceived.startswith('START_OF_FILE'):
					# Recibimos el puerto al que se debe responder
					remoteAddress = dataReceived.split()[1]
					remotePort = int(dataReceived.split()[2])
					threadName = 'Thread-File'
					receptorThread = udpReceptor.UdpReceptor(threadName, self.receptionBuffer, self.localAddress, remoteAddress, remotePort)
					receptorThread.start()
				elif dataReceived.startswith('START_OF_INSTANCE'):
					# Recibimos el puerto al que se debe responder
					remoteAddress = dataReceived.split()[1]
					remotePort = int(dataReceived.split()[2])
					threadName = 'Thread-MessageInstance'
					receptorThread = udpReceptor.UdpReceptor(threadName,self.receptionBuffer, self.localAddress, remoteAddress, remotePort)
					receptorThread.start()
				else:
					self.receptionBuffer.put((10, dataReceived))
					logger.write('DEBUG', '[NETWORK-UDP] Ha llegado un nuevo mensaje!')
			# Esta excepción es parte de la ejecución, no implica un error
			except socket.timeout, errorMessage:
				pass
		self.udpReceptionSocket.close()
		logger.write('WARNING', '[NETWORK-UDP] Funcion \'%s\' terminada.' % inspect.stack()[0][3])
