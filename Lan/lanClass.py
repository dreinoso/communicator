 # coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger
import contactList
import tcpLanReceptor
import tcpLanTransmitter
import udpLanReceptor
import udpLanTransmitter

import os
import time
import Queue
import socket
import inspect
import threading
import commentjson

TIMEOUT = 1.5
PACKET_SIZE = 1024
CONNECTION_LIMIT = 5

JSON_FILE = 'config.json'
JSON_CONFIG = commentjson.load(open(JSON_FILE))

class Lan(object):

	localHost = JSON_CONFIG["LAN"]["LOCAL_HOST"]
	lanProtocol = JSON_CONFIG["LAN"]["PROTOCOL"]
	udpReceptionPort = JSON_CONFIG["LAN"]["UDP_PORT"]
	tcpReceptionPort = JSON_CONFIG["LAN"]["TCP_PORT"]
	tcpReceptionSocket = socket.socket
	udpTransmissionSocket = socket.socket
	udpReceptionSocket = socket.socket
	receptionBuffer = Queue.Queue()
	isActive = False

	def __init__(self, _receptionBuffer):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		self.receptionBuffer = _receptionBuffer
		if JSON_CONFIG["LAN"]["AUTOMATIC_IP"]:
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("8.8.8.8",80)) # Conectando al servidor de DNS se obtiene la dirección IP
			self.localHost = s.getsockname()[0]
			s.close()			
		
	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		puertos ocupados en el Host"""
		self.udpTransmissionSocket.close()
		self.udpReceptionSocket.close()
		self.tcpReceptionSocket.close()
		logger.write('INFO','[LAN] Objeto destruido.')

	def connect(self):
		'''Se realizan las conexiones de los protocolos UDP y TCP para la comunicación
		por medio de LAN.'''
		try: # Intenta conexión UDP
			self.udpTransmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.udpReceptionSocket	   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			if JSON_CONFIG["LAN"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado
				udpCommand = 'fuser -k -s ' + str(self.udpReceptionPort) + '/udp' # -k = kill;  -s: modo silecioso
    			os.system(udpCommand + '\n' + udpCommand)
			self.udpReceptionSocket.settimeout(TIMEOUT) #Para no parase en recevie from a causa de saltar excepción en bind
			self.udpReceptionSocket.bind((self.localHost, self.udpReceptionPort))
		except socket.error , errorMessage:
			self.bindFailed = True
			logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + ' para UDP " (' +str(errorMessage) + ')')
		try: # Intenta conexión TCP
			if JSON_CONFIG["LAN"]["CLOSE_PORT"]: # Para cerrar el puerto en caso de estar ocupado
				tcpCommand = 'fuser -k -s ' + str(self.tcpReceptionPort) + '/tcp'
				os.system(tcpCommand + '\n' + tcpCommand)
			self.tcpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			#self.tcpReceptionSocket.setblocking(0) No se usa porque tira un error.. osea como que sigue de largo.. para el informe..
			self.tcpReceptionSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.tcpReceptionSocket.bind((self.localHost, self.tcpReceptionPort))
			self.tcpReceptionSocket.listen(CONNECTION_LIMIT)
			self.tcpReceptionSocket.settimeout(TIMEOUT)
		except socket.error , errorMessage:
			self.bindFailed = True 
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
		if(self.lanProtocol == 'UDP'):
			try:
				self.udpTransmissionSocket.sendto(messageToSend, (destinationIp, destinationUdpPort))
				return True
			except socket.error , errorMessage:
				logger.write('WARNING', '[LAN] Mensaje no enviado. Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
				return False
		else:
			try:
				#print 'Enviando con lh ' + self.localHost + ' TCP origen ' + str(self.tcpReceptionPort) + ' lh destino ' + destinationIp + ' TCP destinto ' + str(destinationTcpPort)
				tcpTransmissionSocket = socket.socket() # Siempre se crea para conexiones diferentes, por eso no es variable de clase
				tcpTransmissionSocket.connect((destinationIp, destinationTcpPort))
				tcpTransmissionSocket.send(messageToSend)
				tcpTransmissionSocket.close()
				return True
			except socket.error , errorMessage:
				logger.write('WARNING', '[LAN] Mensaje no enviado. Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
				return False

	def sendPacket(self, destinationIp, destinationTcpPort, destinationUdpPort, packetName):
		""" Envia un paquete de datos al destino indicado.
		@param detinationIP: dirección IP del destinatario
		@type emailDestination: str
		@param destinationTcpPort: N° de puerto TCP del destinatario
		@type destinationTcpPort: int
		@param destinationUdpPort: N° de puerto UDP del destinatario
		@type destinationUdpPort: int
		@param message: cadena de texto a enviar
		@type message: str """
		if (self.lanProtocol == 'UDP'):
			threadName = 'UDP_TRANSMITTER_THREAD'
			transmitterThread = udpLanTransmitter.UdpLanTransmitter(threadName, self.isActive, destinationIp, destinationUdpPort, packetName, self.localHost)
			transmitterThread.start()
			return True # Se supone un envio exitoso, de no ocurrir se expresara por una adevertencia. Esto es asi para evitar la espera de envio
		else:
			threadName = 'TCP_TRANSMITTER_THREAD'
			transmitterThread = tcpLanTransmitter.TcpLanTransmitter(threadName, self.isActive, destinationIp, destinationTcpPort, packetName)
			transmitterThread.start()
			return True # Se supone un envio exitoso, de no ocurrir se expresara por una adevertencia. Esto es asi para evitar la espera de envio
			
	def receive(self):
		"""Comienza la recepción de datos por medio de los protocolos TCP y UDP
		para esto requiere la inciación de hilos que esperen los datos en paralelo
		a la ejecución del programa."""
		udpLanThread = threading.Thread(target = self.receiveUdp, name = 'udpLanReceptor')
		tcpLanThread = threading.Thread(target = self.receiveTcp, name = 'tcpLanReceptor')
		udpLanThread.start()
		tcpLanThread.start()

	def receiveTcp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto TCP establecido para guardarlos en el buffer."""
		while self.isActive:
			try:
				connectionSocket, addr = self.tcpReceptionSocket.accept()
				connectionSocket.settimeout(TIMEOUT)
				threadName = 'TCP_RECEPTOR_THREAD'
				receptorThread = tcpLanReceptor.TcpLanReceptor(threadName, connectionSocket, self.receptionBuffer, self.isActive)
				receptorThread.start()
			except socket.timeout, errorMessage:
				pass
			except socket.error, errorMessage:
				logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
		try:
			self.tcpReceptionSocket.close()
		except Exception, e:
			logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
		logger.write('WARNING', '[LAN] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def receiveUdp(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		y mensajes que lleguen al puerto UDP establecido para guardarlos en el buffer."""	
		while self.isActive:
			try:
				data, addr = self.udpReceptionSocket.recvfrom(PACKET_SIZE) 
				if data.startswith('START_OF_PACKET'):
					threadName = 'UDP_RECEPTOR_THREAD'
					receptorThread = udpLanReceptor.UdpLanReceptor(threadName, self.receptionBuffer, self.isActive, data, self.localHost)
					receptorThread.start()
				else:
					self.receptionBuffer.put(data)
			except socket.timeout, errorMessage:
				pass # Esta excepción es parte de la ejecución, no implica un error
			except socket.error, errorMessage:
				logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
		logger.write('WARNING', '[LAN] Funcion \'%s\' terminada' % inspect.stack()[0][3])
