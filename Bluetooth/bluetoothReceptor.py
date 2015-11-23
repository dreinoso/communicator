# coding=utf-8

import os
import time
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
			if dataReceived == 'START_OF_FILE':
				self.receiveFile()
			elif dataReceived == 'START_OF_INSTANCE':
				self.receiveMessageInstance()
			# Se trata de un texto plano, sólo se lo almacena 
			else:
				self.receptionBuffer.put((10, dataReceived))
				logger.write('INFO', '[BLUETOOTH] Ha llegado un nuevo mensaje!')
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar recibir un mensaje: \'%s\'.'% errorMessage )
		finally:
			logger.write('DEBUG', '[BLUETOOTH] \'%s\' terminado y cliente desconectado.' % self.getName())

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
				logger.write('DEBUG', '[BLUETOOTH] Descargando archivo \'%s\'...' % fileName)
				self.remoteSocket.send('READY')
				while True:
					inputData = self.remoteSocket.recv(BUFFER_SIZE)
					if inputData != 'EOF':
						fileObject.write(inputData)
						time.sleep(0.1) # IMPORTANTE, no borrar.
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						logger.write('INFO', '[BLUETOOTH] Archivo \'%s\' descargado correctamente!' % fileName)
						break
				self.remoteSocket.send('ACK') # IMPORTANTE, no borrar.
				return True
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
				return False
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar descargar el archivo \'%s\': %s' % (fileName, str(errorMessage)))
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
				logger.write('INFO', '[BLUETOOTH] Instancia de mensaje recibido correctamente!')
			###########################################################
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar recibir una instancia de mensaje ' + str(errorMessage))
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()