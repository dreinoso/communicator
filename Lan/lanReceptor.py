# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """
import logger

import threading
import socket
import inspect
import Queue

# Tamano del buffer en bytes (cantidad de caracteres)
PACKET_SIZE = 1024

class LanReceptor(threading.Thread):
	
	isActive = False
	remoteSocket = ''
	receptionBuffer = Queue.Queue()

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer, _isActive):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer
		self.isActive = _isActive

	def run(self):
		"""Comienzo de la ejecución, en caso de ser TCP debe determinar si se 
		trata de un mensaje o un paquete, mientras que para UDP siempre se tratará
		de un paquete, ya que la recepción es inmediata. No requiere una conexión."""
		if (self.getName == 'ThreadUDP'):
			self.receiveUdpPacket() # No se pretende un hilo para recepción de mensajes UDP, no genera conexión ni retardo
		else:
			self.receiveTcpMessage()

	def receiveTcpMessage(self):
		'''Se recibe el mensaje a partir de la conexión previamente establecida, 
		de modo que se determine si se trata de un paquete, se llama otra función 
		para encargarse de la recepción. Mientras que si se trata de un mensaje 
		simplemente lo guarda en el buffer.'''
		try:
			inputData = self.remoteSocket.recv(PACKET_SIZE)
			if (inputData == 'START_OF_PACKET'):
				self.receiveTcpPacket()
			else:
				self.receptionBuffer.put(inputData)
				self.remoteSocket.close()	
		except socket.timeout, errorMessage:
			pass
		except socket.error, errorMessage:
			logger.write('WARNING', '[LAN] Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')

	def receiveTcpPacket(self):
		"""Recepción de un paquete completo, debe crear el paquete con el nombre
		del archivo que haya indicado el emisor. Se basa para su funcionamiento
		en la recepción de mensajes de control para sincronizar la comunicación."""
		end = False
		try:
			self.remoteSocket.send('ACK')
			packetName = self.remoteSocket.recv(PACKET_SIZE)
			print 'Recibiendo.. ' + packetName
			packet = open(packetName, "wb")
			self.remoteSocket.send('ACK')
		except Exception, errorMessage:
			logger.write('WARNING', '[LAN] No se pudo recibir paquete (' + packetName + '). Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
		while not end and self.isActive:
			try:
				inputData = self.remoteSocket.recv(PACKET_SIZE)
				if inputData != 'END_OF_PACKET':
					packet.write(inputData)
				else: 
					end = True
					packet.close()
					self.remoteSocket.close()
					self.receptionBuffer.put('Paquete (' + packetName + ') recibido con exito.')
					logger.write('INFO', '[LAN] Paquete recibido (' + packetName + ')')
			except Exception, errorMessage:
				logger.write('WARNING', '[LAN] No se pudo recibir paquete (' + packetName + '). Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
				break

	def receiveUdpPacket(self):
		pass
