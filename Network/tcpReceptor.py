# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import json
import time
import Queue
import pickle
import socket
import threading

import logger
import messageClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
DOWNLOADS = 'Downloads'

class TcpReceptor(threading.Thread):

	receptionBuffer = Queue.Queue()

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
		try:
			dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
			if dataReceived == 'START_OF_FILE':
				self.receiveFile()
			elif dataReceived == 'START_OF_INSTANCE':
				self.receiveMessageInstance()
			# Se trata de un texto plano, sólo se lo almacena 
			else:
				self.receptionBuffer.put((10, dataReceived))
				logger.write('INFO', '[NETWORK] Mensaje recibido correctamente!')
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar recibir un mensaje: \'%s\'.'% errorMessage )
		finally:
			logger.write('DEBUG', '[NETWORK] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFile(self):
		'''Para la recepción del archivo, primero se verifica que le archivo no 
		exista, de existir el archivo, se avisa al transmisor. En caso de que no 
		exista se confirma al emisor para que comience a transmitir, se crea el 
		archivo y la capeta de descarga en caso de que no exista. Se escribe el 
		archivo a medida que llegan los paquetes.'''
		try:
			self.remoteSocket.send('ACK')
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
				logger.write('DEBUG', '[NETWORK] Descargando archivo \'%s\'...' % fileName)
				self.remoteSocket.send('READY')
				# Comenzamos a descargar el archivo
				while True:
					inputData = self.remoteSocket.recv(BUFFER_SIZE)
					if inputData != 'EOF':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						logger.write('INFO', '[NETWORK] Archivo \'%s\' descargado correctamente!' % fileName)
						break
				return True
			else:
				# Comunicamos al transmisor que el archivo ya existe
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
				return False
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar descargar el archivo \'%s\': %s' % (fileName, str(errorMessage)))
			return False
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()

	def receiveMessageInstance(self):
		'''Por medio de una sincronización de mensajes se recibe la cadena de a partes
		que corresponde a la instancia serializada, y se arma a medida que lleguen los 
		caracteres, cuando se tiene la cadena completa se la deserializa para obtener 
		la instancia y almacenarla en el buffer.'''
		try:
			serializedMessage = ''
			self.remoteSocket.send('ACK')
			while True:
				inputData = self.remoteSocket.recv(BUFFER_SIZE)
				if inputData != 'END_OF_INSTANCE':
					serializedMessage = serializedMessage + inputData
					self.remoteSocket.send('ACK')
				else:
					# Deserialización de la instancia
					message = pickle.loads(serializedMessage)
					break
			###########################################################
			if isinstance(message, messageClass.FileMessage):
				self.remoteSocket.recv(BUFFER_SIZE) # START_OF_FILE
				if self.receiveFile():
					self.receptionBuffer.put((100 - message.priority, message))
			else:
				self.receptionBuffer.put((100 - message.priority, message))
				logger.write('INFO', '[NETWORK] Ha llegado una nueva instancia de mensaje!')
			###########################################################
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar recibir una instancia de mensaje ' + str(errorMessage))
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()