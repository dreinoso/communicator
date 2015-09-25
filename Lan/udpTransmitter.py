# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por protocolo UDP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger

import os
import time
import Queue
import socket
import threading

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
TIMEOUT = 2

class UdpTransmitter(threading.Thread):

	def __init__(self, _threadName, _messageToSend, _localAddress, _destinationIp, _destinationPort):
		threading.Thread.__init__(self, name = _threadName)
		self.messageToSend = _messageToSend
		self.localAddress = _localAddress
		self.destinationIp = _destinationIp
		self.destinationPort = _destinationPort
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		self.transmitterSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.transmitterSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		self.receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.receptionSocket.bind((self.localAddress, 0))
		self.receptionPort = self.receptionSocket.getsockname()[1]

	def run(self):
		try:
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			if os.path.isfile(absoluteFilePath):
				# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
				self.transmitterSocket.sendto('START_OF_PACKET ' + self.localAddress + ' ' +  str(self.receptionPort), (self.destinationIp, self.destinationPort))
				# Establecemos el nuevo puerto destino al cual enviar el paquete
				self.destinationPort, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
				self.destinationPort = int(self.destinationPort)
				fileDirectory, fileName = os.path.split(absoluteFilePath)
				fileObject = open(absoluteFilePath, 'rb')
				# Enviamos el nombre del archivo
				self.transmitterSocket.sendto(fileName, (self.destinationIp, self.destinationPort))
				# Recibe confirmación para comenzar a transmitir (READY)
				receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
				if receivedData == "READY":
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
					logger.write('INFO', '[LAN] Transfiriendo archivo \'%s\'...' % fileName)
					while bytesSent < fileSize:
						outputData = fileObject.read(BUFFER_SIZE)
						bytesSent += len(outputData)
						self.transmitterSocket.sendto(outputData, (self.destinationIp, self.destinationPort))
						receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE) # ACK
					fileObject.close()
					self.transmitterSocket.sendto('END_OF_PACKET', (self.destinationIp, self.destinationPort))
					logger.write('INFO', '[LAN] Archivo \'%s\' enviado correctamente!' % fileName)
				else:
					logger.write('WARNING', '[LAN] El archivo \'%s\' fue rechazado!' % fileName)
			else:
				# Enviamos un texto plano al cliente especificado
				self.transmitterSocket.sendto(self.messageToSend, (self.destinationIp, self.destinationPort))
				logger.write('INFO', '[LAN] Mensaje enviado correctamente!')
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()