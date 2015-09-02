# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """
import logger

import socket
import threading
import time
import inspect
import Queue

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class LanTransmitter(threading.Thread):

	receptionBuffer = Queue.Queue()
	isActive = False
	destinationIp = ''
	destinationPort = 0

	def __init__(self, _threadName, _receptionBuffer, _isActive, _destinationIp, _destinationPort, _packetName):
		threading.Thread.__init__(self, name = _threadName)
		self.receptionBuffer = _receptionBuffer
		self.isActive = _isActive
		self.destinationIp = _destinationIp
		self.destinationPort = _destinationPort
		self.packetName = _packetName

	def run(self):
		"""Comienzo de la ejecución y se envia el paquete ya sea por protocolo 
		TCP o UDP dependiendo de como este implementado."""
		if (self.getName == 'ThreadUDP'):
			resultOk = self.sendUdpPacket()
		else:
			resultOk = self.sendTcpPacket()
		return resultOk

	def sendUdpPacket(self):
		"""Envia un paquete por medio del protocolo UDP, realiza varios envios
 		de mensajes para sincronización."""
		pass

 	def sendTcpPacket(self):
 		"""Envia un paquete por medio del protocolo TCP, realiza varios envios
 		de mensajes para sincronización"""
 		try:
			tcpPacketSocket = socket.socket()
			tcpPacketSocket.connect((self.destinationIp, self.destinationPort))
			print 'Conexión establecida'
			packet = open(self.packetName, "rb")
			outputData = packet.read(BUFFER_SIZE)
			#tcpPacketSocket.send('START_OF_PACKET',len('START_OF_PACKET')) Ver si conviene asi..
			tcpPacketSocket.send('START_OF_PACKET')
			tcpPacketSocket.recv(BUFFER_SIZE) # Evita que el receptor tome todo junto del buffer, es para separar los envios
			tcpPacketSocket.send(self.packetName)
			tcpPacketSocket.recv(BUFFER_SIZE)
			while outputData != '' and self.isActive: # Control de finalización de envio y disponibilidad de módulo
				# Enviar contenido.
				tcpPacketSocket.send(outputData)
				outputData = packet.read(BUFFER_SIZE)
			time.sleep(0.2) # Da tiempo al receptor para que saque el paquete anterior del buffer y asi no concatene
			tcpPacketSocket.send('END_OF_PACKET')
			packet.close()
			tcpPacketSocket.close()
			logger.write('DEBUG', '[LAN] Archivo ' + self.packetName +  ' enviado correctamente.')
		except Exception, errorMessage:
			logger.write('WARNING', '[LAN] Paquete no enviado. Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')