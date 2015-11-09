# coding=utf-8

import os
import json
import Queue
import pickle
import threading
import bluetooth

import logger
import messageClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
DOWNLOADS = 'Downloads'

class BluetoothReceptor(threading.Thread):

	receptionBuffer = Queue.Queue()

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer

	def run(self):
		try:
			dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
			if dataReceived == 'START_OF_FILE_INSTANCE':
				self.receiveFileInstance()
			elif dataReceived == 'START_OF_MESSAGE_INSTANCE':
				self.receiveMessageInstance()
			elif dataReceived == 'START_OF_FILE':
				self.receiveFile()
			else: # Se trata de un mensaje simple, solo se guarda 
				self.receptionBuffer.put((100 - JSON_CONFIG["COMMUNICATOR"]["MESSAGE_PRIORITY"], dataReceived))
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar descargar el archivo \'%s\'.'% errorMessage )
		finally:
			logger.write('DEBUG', '[BLUETOOTH] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFileInstance(self):
		'''Primero se recive la instancia FileMessage propiamente dicha, para luego preprarse
		para el envio del archivo en si en caso de que este no se encuentre ya en el receptor.
		Es una combinación de los métodos de recepción de instancia mensaje y recepción de 
		archivo, pero tiene un control adicional. En caso de que el archivo se reciba se indica
		en uno de los campos de la instancia recibida.'''
		try:
			message = ''
			self.remoteSocket.send('ACK')
			inputData = self.remoteSocket.recv(BUFFER_SIZE)
			serializedMessage = ''
			while inputData != 'END_OF_FILE_INSTANCE':
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
				logger.write('DEBUG', '[BLUETOOTH] Descargando archivo \'%s\'...' % fileName)
				self.remoteSocket.send('READY')
				while True:
					inputData = self.remoteSocket.recv(BUFFER_SIZE)
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						message.received = True
						logger.write('DEBUG', '[BLUETOOTH] Archivo \'%s\' descargado correctamente!' % fileName)
						break
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar recibir una instancia de mensaje %s.' % errorMessage)
		finally:
			if message != None:
				self.receptionBuffer.put((100 - message.priority, message))
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()

	def receiveMessageInstance(self):
		'''Por medio de una sincronización de mensajes se recibe la cadena de a partes
		que corresponde a la instancia serializada, y se arma a medida que lleguen los 
		caracteres, cuando se tiene la cadena completa se la deserializa para obtener 
		la instancia y almacenarla en el buffer.'''
		try:
			self.remoteSocket.send('ACK')
			inputData = self.remoteSocket.recv(BUFFER_SIZE)
			serializedMessage = ''
			while inputData != 'END_OF_MESSAGE_INSTANCE':
				serializedMessage = serializedMessage + inputData
				self.remoteSocket.send('ACK')
				inputData = self.remoteSocket.recv(BUFFER_SIZE)
			message = pickle.loads(serializedMessage) # Deserialización de la instancia
			self.receptionBuffer.put((100 - message.priority, message))
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar recibir una instancia de mensaje ' + str(errorMessage))
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()

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
				logger.write('DEBUG', '[BLUETOOTH] Descargando archivo \'%s\'...' % fileName)
				self.remoteSocket.send('READY')
				while True:
					inputData = self.remoteSocket.recv(BUFFER_SIZE)
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						self.receptionBuffer.put((100 - JSON_CONFIG["COMMUNICATOR"]["FILE_PRIORITY"], 'ARCHIVO_RECIBIDO: ' + fileName))
						logger.write('DEBUG', '[BLUETOOTH] Archivo \'%s\' descargado correctamente!' % fileName)
						break
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()
