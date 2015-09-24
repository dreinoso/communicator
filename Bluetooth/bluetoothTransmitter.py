# coding=utf-8

import os
import time
import inspect
import threading
import bluetooth

import logger

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class BluetoothTransmitter(threading.Thread):

	def __init__(self, _threadName, _remoteSocket, _messageToSend):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.messageToSend = _messageToSend

	def run(self):
		try:
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			if os.path.isfile(absoluteFilePath):
				fileDirectory, fileName = os.path.split(absoluteFilePath)
				fileObject = open(absoluteFilePath, 'rb')
				self.remoteSocket.send('START_OF_PACKET')
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
					logger.write('INFO', '[BLUETOOTH] Transfiriendo archivo \'%s\' ...' % fileName)
					while bytesSent < fileSize:
						outputData = fileObject.read(BUFFER_SIZE)
						bytesSent += len(outputData)
						self.remoteSocket.send(outputData)
					fileObject.close()
					self.remoteSocket.send('END_OF_PACKET')
					logger.write('INFO', '[BLUETOOTH] Archivo \'%s\' enviado correctamente!' % fileName)
				else:
					logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' fue rechazado!' % fileName)
			else:
				# Enviamos un texto plano al cliente especificado
				self.remoteSocket.send(self.messageToSend)
				logger.write('INFO', '[BLUETOOTH] Mensaje enviado correctamente!')
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Mensaje no enviado. Excepción en "' + str(inspect.stack()[0][3]) + '" (' +str(errorMessage) + ')')
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()
