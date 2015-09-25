# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
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
DOWNLOADS = 'downloads'

class TcpReceptor(threading.Thread):

	receptionBuffer = Queue.Queue()

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer

	def run(self):
		try:
			dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
			if dataReceived == 'START_OF_PACKET':
				self.remoteSocket.send('ACK')
				currentDirectory = os.getcwd()                 # Obtenemos el directorio actual de trabajo
				fileName = self.remoteSocket.recv(BUFFER_SIZE) # Obtenemos el nombre del archivo a recibir
				relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, fileName) # Obtenemos el path relativo del archivo a descargar
				# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
				if DOWNLOADS not in os.listdir(currentDirectory):
					os.mkdir(DOWNLOADS)
				# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
				if not os.path.isfile(relativeFilePath):
					fileObject = open(relativeFilePath, 'w+')
					logger.write('INFO', '[LAN] Descargando archivo \'%s\'...' % fileName)
					self.remoteSocket.send('READY')
					while True:
						inputData = self.remoteSocket.recv(BUFFER_SIZE)
						if inputData != 'END_OF_PACKET':
							fileObject.write(inputData)
							self.remoteSocket.send('ACK')
						else: 
							fileObject.close()
							logger.write('INFO', '[LAN] Archivo \'%s\' descargado correctamente!' % fileName)
							break
				else:
					self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
					logger.write('WARNING', '[LAN] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
			else:
				self.receptionBuffer.put(dataReceived)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()
			logger.write('DEBUG', '[LAN] \'%s\' terminado y cliente desconectado.' % self.getName())