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
import udpReceptor
import tcpReceptor
import udpTransmitter
import tcpTransmitter

TIMEOUT = 1.5
BUFFER_SIZE = 1024
CONNECTION_LIMIT = 5

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Network(object):

	localAddress = JSON_CONFIG["NETWORK"]["LOCAL_ADDRESS"]
	lanProtocol = JSON_CONFIG["NETWORK"]["PROTOCOL"]
	localInterface = None

	udpReceptionPort = JSON_CONFIG["NETWORK"]["UDP_PORT"]
	tcpReceptionPort = JSON_CONFIG["NETWORK"]["TCP_PORT"]

	receptionBuffer = Queue.PriorityQueue()
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
			activeInterfacesFile = open('/tmp/activeInterfaces').read()
			deletedActiveInterface = activeInterfacesFile.replace(self.localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(deletedActiveInterface)
			activeInterfacesFile.close()
			self.udpReceptionSocket.close()
			self.tcpReceptionSocket.close()
		except Exception as errorMessage:
			pass
		finally:
			logger.write('INFO', '[NETWORK] Objeto destruido.')

	def connect(self, _activeInterface):
		'''Se realizan las conexiones de los protocolos UDP y TCP para la comunicación
		por medio de NETWORK.'''
		self.localInterface = _activeInterface
		commandToExecute = 'ip addr show ' + self.localInterface + ' | grep inet'
		# Obtenemos la dirección IP local asignada por DHCP
		self.localAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
		try: # Intenta conexión UDP
			self.udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			'''if JSON_CONFIG["NETWORK"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado
				udpCommand = 'fuser -k -s ' + str(self.udpReceptionPort) + '/udp' # -k = kill; -s: modo silecioso 
				os.system(udpCommand + '\n' + udpCommand)'''
			self.udpReceptionSocket.bind((self.localAddress, self.udpReceptionPort))
			self.udpReceptionSocket.settimeout(TIMEOUT)
			#####################################################################
			self.udpTransmitter = udpTransmitter.UdpTransmitter(self.localAddress)
			#####################################################################
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Excepción en "' + str(inspect.stack()[0][3]) + ' para UDP " (' +str(errorMessage) + ')')
		try: # Intenta conexión TCP
			self.tcpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.tcpReceptionSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			'''if JSON_CONFIG["NETWORK"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado
				tcpCommand = 'fuser -k -s ' + str(self.udpReceptionPort) + '/tcp' # -k = kill; -s: modo silecioso 
				os.system(tcpCommand + '\n' + tcpCommand)'''
			self.tcpReceptionSocket.bind((self.localAddress, self.tcpReceptionPort))
			self.tcpReceptionSocket.listen(CONNECTION_LIMIT)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
			####################################################
			self.tcpTransmitter = tcpTransmitter.TcpTransmitter()
			####################################################
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Excepción en "' + str(inspect.stack()[0][3]) + ' para TCP " (' +str(errorMessage) + ')')

	
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
			if self.lanProtocol == 'TCP':
				# Crea un nuevo socket que usa el protocolo de transporte especificado
				remoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Conecta el socket con el dispositivo remoto sobre el puerto especificado
				remoteSocket.connect((destinationIp, destinationTcpPort))
				logger.write('DEBUG', '[NETWORK] Conectado con la dirección \'%s\'.' % destinationIp)
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
		receiveUdpThread = threading.Thread(target = self.receiveUdp, name = 'udpReceptor')
		receiveTcpThread = threading.Thread(target = self.receiveTcp, name = 'tcpReceptor')
		receiveUdpThread.start()
		receiveTcpThread.start()
		receiveUdpThread.join()
		receiveTcpThread.join()

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
							logger.write('DEBUG', '[NETWORK] Conexion desde \'%s\' aceptada.' % ipAddress)
							receptorThread = tcpReceptor.TcpReceptor(threadName, remoteSocket, self.receptionBuffer)
							ipAddressFounded = True
							receptorThread.start()
							break
					if not ipAddressFounded:
						logger.write('WARNING', '[NETWORK] Mensaje de \'%s\' rechazado!' % ipAddress)
						remoteSocket.close()
				# ... sino, recibimos todos los mensajes independientemente del origen
				else:
					logger.write('DEBUG', '[NETWORK] Conexion desde \'%s\' aceptada.' % ipAddress)
					receptorThread = tcpReceptor.TcpReceptor(threadName, remoteSocket, self.receptionBuffer)
					receptorThread.start()
			# Para que no se quede esperando indefinidamente en el'accept'
			except socket.timeout as errorMessage:
				pass
		self.tcpReceptionSocket.close()
		logger.write('WARNING','[NETWORK] Función \'%s\' terminada.' % inspect.stack()[0][3])

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
					logger.write('DEBUG', '[NETWORK] Ha llegado un nuevo mensaje!')
			# Esta excepción es parte de la ejecución, no implica un error
			except socket.timeout, errorMessage:
				pass
		self.udpReceptionSocket.close()
		logger.write('WARNING', '[NETWORK] Funcion \'%s\' terminada.' % inspect.stack()[0][3])
