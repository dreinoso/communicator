# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por protocolo UDP.
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
import os

BUFFER_SIZE = 1024

class UdpLanTransmitter(threading.Thread):

	isActive = False
	destinationIp = ''
	destinationPort = 0
	udpConnectionIp = ''

	def __init__(self, _threadName, _isActive, _destinationIp, _destinationPort, _packetName, _udpConnectionIp):
		threading.Thread.__init__(self, name = _threadName)
		self.isActive = _isActive
		self.destinationIp = _destinationIp
		self.destinationPort = _destinationPort
		self.packetName = _packetName
		self.udpConnectionIp = _udpConnectionIp # Es lo mismo que localHost para recibir ACK del receptor

	def run(self):
		"""Comienzo de la ejecución y se envia el paquete."""
		self.sendUdpPacket()

	def sendUdpPacket(self):
		"""Envia un paquete por medio del protocolo UDP, realiza varios envios
 		de mensajes para sincronización."""
		try:
			udpReceptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			udpReceptionSocket.settimeout(4) #Para no parase en recevie from a causa de saltar excepción en bind
			udpReceptionSocket.bind((self.udpConnectionIp, 0))
			udpConnectionPort = udpReceptionSocket.getsockname()[1]
			udpTransmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			#Envio de palabra especial para enviar el paquete junto con la dirección a la que debe responder para realizar la sincronización del envió
			udpTransmissionSocket.sendto('START_OF_PACKET ' + self.udpConnectionIp + ' ' + str(udpConnectionPort), (self.destinationIp, self.destinationPort))
			newDestinationPort, addr = udpReceptionSocket.recvfrom(BUFFER_SIZE) # Redirigimos los envios a la conexión que se estableció exclusivamente
			self.destinationPort = int(newDestinationPort)
			packet = open(self.packetName, "rb") # Apertura del archivo a transmitir
			udpTransmissionSocket.sendto(self.packetName, (self.destinationIp, self.destinationPort)) # Envío del nombre del archivo
			data, addr = udpReceptionSocket.recvfrom(BUFFER_SIZE)
			outputData = packet.read(BUFFER_SIZE)
			while outputData != '':
				udpTransmissionSocket.sendto(outputData, (self.destinationIp, self.destinationPort))
				data, addr = udpReceptionSocket.recvfrom(BUFFER_SIZE)
				outputData = packet.read(BUFFER_SIZE)
			time.sleep(0.2) # Da tiempo al receptor para que saque el paquete anterior del buffer y asi no concatene
			udpTransmissionSocket.sendto('END_OF_PACKET', (self.destinationIp, self.destinationPort))
			packet.close()
			udpTransmissionSocket.close()
			udpReceptionSocket.close()
			logger.write('DEBUG', '[LAN] Archivo ' + self.packetName +  ' enviado correctamente.')
		except Exception, errorMessage:
			logger.write('WARNING', '[LAN] Paquete no enviado. Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
