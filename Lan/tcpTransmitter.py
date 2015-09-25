# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import Queue
import socket
import threading

import logger

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class TcpTransmitter(threading.Thread):

	def __init__(self, _threadName, _remoteSocket, _messageToSend):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.messageToSend = _messageToSend

	def run(self):
 		"""Envia un paquete por medio del protocolo TCP, realiza varios envios
 		de mensajes para sincronización"""
		try:
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			if os.path.isfile(absoluteFilePath):
				fileDirectory, fileName = os.path.split(absoluteFilePath)
				fileObject = open(absoluteFilePath, 'rb')
				self.remoteSocket.send('START_OF_PACKET')
				self.remoteSocket.recv(BUFFER_SIZE) # ACK
				self.remoteSocket.send(fileName) # Enviamos el nombre del archivo
				# Recibe confirmación para comenzar a transmitir (READY)
				if self.remoteSocket.recv(BUFFER_SIZE) == "READY":
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
						self.remoteSocket.send(outputData)
						self.remoteSocket.recv(BUFFER_SIZE) # ACK
					fileObject.close()
					self.remoteSocket.send('END_OF_PACKET')
					logger.write('INFO', '[LAN] Archivo \'%s\' enviado correctamente!' % fileName)
				else:
					logger.write('WARNING', '[LAN] El archivo \'%s\' fue rechazado!' % fileName)
			else:
				# Enviamos un texto plano al cliente especificado
				self.remoteSocket.send(self.messageToSend)
				logger.write('INFO', '[LAN] Mensaje enviado correctamente!')
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close