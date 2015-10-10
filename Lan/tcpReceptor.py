# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import pickle
import Queue
import socket
import threading

import messageClass
import logger

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
			if dataReceived == 'START_OF_FILE_INSTANCE':
				self.receiveFileInstance()
			elif dataReceived == 'START_OF_MESSAGE_INSTANCE':
				self.receiveMessageInstance()
			elif dataReceived == 'START_OF_FILE':
				self.receiveFile()
			else: # Se trata de un mensaje simple, solo se guarda 
				self.receptionBuffer.put(dataReceived)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cierra la conexion del socket cliente
			logger.write('DEBUG', '[LAN] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFileInstance(self):
		'''Primero se recive la instancia FileMessage propiamente dicha, para luego preprarse
		para el envio del archivo en si en caso de que este no se encuentre ya en el receptor.
		Es una combinación de los métodos de recepción de instancia mensaje y recepción de 
		archivo, pero tiene un control adicional. En caso de que el archivo se reciba se indica
		en uno de los campos de la instancia recibida.'''
		try:
			self.remoteSocket.send('ACK')
			inputData = self.remoteSocket.recv(BUFFER_SIZE)
			while inputData != 'END_OF_FILE_INSTANCE':
				serializedMessage = ''
				serializedMessage = serializedMessage + inputData
				self.remoteSocket.send('ACK')
				inputData = self.remoteSocket.recv(BUFFER_SIZE)
			message = pickle.loads(serializedMessage) # Deserialización de la instancia
			
			# Se prosigue con la recepcion del archivo
			currentDirectory = os.getcwd()                 # Obtenemos el directorio actual de trabajo
			fileName = message.fileName # Obtenemos el nombre del archivo a recibir
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
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						message.received = True
						logger.write('INFO', '[LAN] Archivo \'%s\' descargado correctamente!' % fileName)
						break
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[LAN] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar recibir una instancia de mensaje.')
		finally:
			self.receptionBuffer.put(message)
			self.remoteSocket.close()

	def receiveMessageInstance(self):
		'''Por medio de una sincronización de mensajes se recibe la cadena de a partes
		que corresponde a la instancia serializada, y se arma a medida que lleguen los 
		caracteres, cuando se tiene la cadena completa se la deserializa para obtener 
		la instancia y almacenarla en el buffer.'''
		try:
			self.remoteSocket.send('ACK')
			inputData = self.remoteSocket.recv(BUFFER_SIZE)
			while inputData != 'END_OF_MESSAGE_INSTANCE':
				serializedMessage = ''
				serializedMessage = serializedMessage + inputData
				self.remoteSocket.send('ACK')
				inputData = self.remoteSocket.recv(BUFFER_SIZE)
			message = pickle.loads(serializedMessage) # Deserialización de la instancia
			self.receptionBuffer.put(message)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar recibir una instancia de mensaje.')
		finally:
			# En caso de que se trate de un archivo, se debe esperar a que se reciba por el mismo puerto, 
			# por eso no se cierra el puerta 
			if not isinstance(message, messageClass.FileMessage):
				self.remoteSocket.close() # Cierra la conexion del socket cliente

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
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						self.receptionBuffer.put('ARCHIVO_RECIBIDO: ' + fileName)
						logger.write('INFO', '[LAN] Archivo \'%s\' descargado correctamente!' % fileName)
						break
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[LAN] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()

