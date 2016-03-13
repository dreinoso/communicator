# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import json
import threading

import logger

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 4096
DOWNLOADS = 'Downloads'

class TcpReceptor(threading.Thread):

	receptionBuffer = None

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer):
		"""Creación de la clase para la recepción de paquetes TCP.
		@param _threadName: nombre del hilo
		@type: string
		@param socket para la recepción del paquete
		@type: socket
		@param _receptionBuffer: buffer para almacenar el mensaje o instancia
		@type: queue"""
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer

	def run(self):
		'''Una vez establecida la conexión este hilo se lanza, lo primero es leer
		el mensaje de sincronización para determinar que es lo que se esta por 
		recibir, de acuerdo a este contenido el comportamiento sera diferente.'''
		self.receiveFile()
		logger.write('DEBUG', '[NETWORK-TCP] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFile(self):
		'''Para la recepción del archivo, primero se verifica que le archivo no 
		exista, de existir el archivo, se avisa al transmisor. En caso de que no 
		exista se confirma al emisor para que comience a transmitir, se crea el 
		archivo y la capeta de descarga en caso de que no exista. Se escribe el 
		archivo a medida que llegan los paquetes.'''
		try:
			currentDirectory = os.getcwd()                 # Obtenemos el directorio actual de trabajo
			fileName = self.remoteSocket.recv(BUFFER_SIZE) # Obtenemos el nombre del archivo a recibir
			# Obtenemos el path relativo del archivo a descargar
			relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, fileName)
			# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
			if DOWNLOADS not in os.listdir(currentDirectory):
				os.mkdir(DOWNLOADS)
			# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
			if not os.path.isfile(relativeFilePath):
				fileObject = open(relativeFilePath, 'w+')
				logger.write('DEBUG', '[NETWORK-TCP] Descargando archivo \'%s\'...' % fileName)
				self.remoteSocket.send('READY')
				# Comenzamos a descargar el archivo
				while True:
					inputData = self.remoteSocket.recv(BUFFER_SIZE)
					if inputData != 'EOF':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						break
				self.receptionBuffer.put((10, fileName))
				logger.write('INFO', '[NETWORK-TCP] Archivo \'%s\' descargado correctamente!' % fileName)
				return True
			else:
				# Comunicamos al transmisor que el archivo ya existe
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[NETWORK-TCP] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
				return False
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK-TCP] Error al intentar descargar el archivo \'%s\': %s' % (fileName, str(errorMessage)))
			return False
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()