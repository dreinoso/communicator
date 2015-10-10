# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger
import tcpTransmitter
import udpTransmitter
import udpReceptor
import tcpReceptor
import contactList

import os
import time
import Queue
import socket
import inspect
import threading
import json

TIMEOUT = 1.5
BUFFER_SIZE = 1024
CONNECTION_LIMIT = 5

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Lan(object):

	localAddress = JSON_CONFIG["LAN"]["LOCAL_ADDRESS"]
	lanProtocol = JSON_CONFIG["LAN"]["PROTOCOL"]
	setIp = JSON_CONFIG["LAN"]["SET_IP"]
	localInterface = None

	tcpReceptionSocket = socket.socket
	tcpReceptionPort = JSON_CONFIG["LAN"]["TCP_PORT"]
	udpReceptionSocket = socket.socket
	udpReceptionPort = JSON_CONFIG["LAN"]["UDP_PORT"]

	receptionBuffer = Queue.Queue()
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
			logger.write('INFO', '[LAN] Objeto destruido.')

	def connect(self, _activeInterface):
		'''Se realizan las conexiones de los protocolos UDP y TCP para la comunicación
		por medio de LAN.'''
		self.localInterface = _activeInterface
		commandToExecute = 'ip addr show ' + self.localInterface + ' | grep inet'
		# Obtenemos la dirección IP local asignada por DHCP
		if self.setIp: 
			self.localAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
		try: # Intenta conexión UDP
			self.udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			if JSON_CONFIG["LAN"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado 
				udpCommand = 'fuser -k -s ' + str(self.udpReceptionPort) + '/udp' # -k = kill; -s: modo silecioso 
				os.system(udpCommand + '\n' + udpCommand)
			self.udpReceptionSocket.bind((self.localAddress, self.udpReceptionPort))
			self.udpReceptionSocket.settimeout(TIMEOUT)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + ' para UDP " (' +str(errorMessage) + ')')
		try: # Intenta conexión TCP
			self.tcpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.tcpReceptionSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			if JSON_CONFIG["LAN"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado 
				tcpCommand = 'fuser -k -s ' + str(self.udpReceptionPort) + '/tcp' # -k = kill; -s: modo silecioso 
				os.system(tcpCommand + '\n' + tcpCommand)
			self.tcpReceptionSocket.bind((self.localAddress, self.tcpReceptionPort))
			self.tcpReceptionSocket.listen(CONNECTION_LIMIT)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + ' para TCP " (' +str(errorMessage) + ')')

	
	def send(self, destinationIp, destinationTcpPort, destinationUdpPort, messageToSend):
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
			if(self.lanProtocol == 'UDP'):
				# Lanzamos un hilo que se va a encargar de manejar la transmisión del mensaje
				threadName = 'Thread-%s' % self.localAddress
				transmitterThread = udpTransmitter.UdpTransmitter(threadName, messageToSend, self.localAddress, destinationIp, destinationUdpPort)
				transmitterThread.start()
				return True
			else:
				# Crea un nuevo socket que usa el protocolo de transporte especificado
				remoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				# Conecta el socket con el dispositivo remoto sobre el puerto especificado
				remoteSocket.connect((destinationIp, destinationTcpPort))
				logger.write('DEBUG', '[LAN] Conectado con la dirección \'%s\'.' % destinationIp)
				# Lanzamos un hilo que se va a encargar de manejar la transmisión del mensaje
				threadName = 'Thread-%s' % self.localAddress
				transmitterThread = tcpTransmitter.TcpTransmitter(threadName, remoteSocket, messageToSend)
				transmitterThread.start()
				return True
		except socket.error as errorMessage:
			logger.write('WARNING','[LAN] %s.' % errorMessage)
			return False
	
	def receive(self):
		"""Comienza la recepción de datos por medio de los protocolos TCP y UDP
		para esto requiere la inciación de hilos que esperen los datos en paralelo
		a la ejecución del programa."""
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
				threadName = 'Thread-TCPReceptor'
				receptorThread = tcpReceptor.TcpReceptor(threadName, remoteSocket, self.receptionBuffer)
				receptorThread.start()
			except socket.timeout as errorMessage:
				# Para que no se quede esperando indefinidamente en el'accept'
				pass
		self.tcpReceptionSocket.close()
		logger.write('WARNING','[LAN] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def receiveUdp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto UDP establecido para guardarlos en el buffer."""	
		while self.isActive:
			try:
				data, addr = self.udpReceptionSocket.recvfrom(BUFFER_SIZE)
				if data.startswith('START_OF_FILE_INSTANCE '):
					# Recibimos el puerto al que se debe responder
					remoteAddress = data.split()[1]
					remotePort = int(data.split()[2])
					threadName = 'Thread-UDPReceptor-FileInstance'
					receptorThread = udpReceptor.UdpReceptor(threadName,self.receptionBuffer, self.localAddress, remoteAddress, remotePort)
					receptorThread.start()
				elif data.startswith('START_OF_MESSAGE_INSTANCE '):
					# Recibimos el puerto al que se debe responder
					remoteAddress = data.split()[1]
					remotePort = int(data.split()[2])
					threadName = 'Thread-UDPReceptor-MessageInstance'
					receptorThread = udpReceptor.UdpReceptor(threadName,self.receptionBuffer, self.localAddress, remoteAddress, remotePort)
					receptorThread.start()
				elif data.startswith('START_OF_FILE '):
					# Recibimos el puerto al que se debe responder
					remoteAddress = data.split()[1]
					remotePort = int(data.split()[2])
					threadName = 'Thread-UDPReceptor-File'
					receptorThread = udpReceptor.UdpReceptor(threadName, self.receptionBuffer, self.localAddress, remoteAddress, remotePort)
					receptorThread.start()
				else:
					logger.write('INFO', '[LAN] Ha llegado un nuevo mensaje!')
					self.receptionBuffer.put(data)
			except socket.timeout, errorMessage:
				pass # Esta excepción es parte de la ejecución, no implica un error
		self.udpReceptionSocket.close()
		logger.write('WARNING', '[LAN] Funcion \'%s\' terminada.' % inspect.stack()[0][3])
