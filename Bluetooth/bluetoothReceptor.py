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

BUFFER_SIZE = 4096 # Tamano del buffer en bytes (cantidad de caracteres)
DOWNLOADS = 'Downloads'

class BluetoothReceptor(threading.Thread):

	receptionQueue = None

	def __init__(self, _threadName, _remoteSocket, _receptionQueue):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionQueue = _receptionQueue

	def run(self):
		try:
			receivedData = self.remoteSocket.recv(BUFFER_SIZE)
			# Debemos iniciar una descarga de archivo
			if receivedData == 'START_OF_FILE':
				self.receiveFile()
			# Recibimos una instancia de objeto
			elif receivedData.startswith('INSTANCE'):
				# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
				serializedMessage = receivedData[len('INSTANCE'):]
				# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
				messageInstance = pickle.loads(serializedMessage)
				self.receptionQueue.put((messageInstance.priority, messageInstance))
				logger.write('INFO', '[BLUETOOTH] Ha llegado una nueva instancia de mensaje!')
			# Se trata de un texto plano, sólo se lo almacena 
			else:
				self.receptionQueue.put((10, receivedData))
				logger.write('INFO', '[BLUETOOTH] Ha llegado un nuevo mensaje!')
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar recibir un mensaje: \'%s\'.'% errorMessage )
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()
			logger.write('DEBUG', '[BLUETOOTH] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFile(self):
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
						time.sleep(0.15) # IMPORTANTE, no borrar.
						self.remoteSocket.send('ACK')
					else: 
						fileObject.close()
						break
				self.remoteSocket.send('ACK') # IMPORTANTE, no borrar.
				self.receptionQueue.put((10, fileName))
				logger.write('INFO', '[BLUETOOTH] Archivo \'%s\' descargado correctamente!' % fileName)
				return True
			else:
				self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
				logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
				return False
		except bluetooth.BluetoothError as errorMessage:
			logger.write('WARNING', '[BLUETOOTH] Error al intentar descargar el archivo \'%s\': %s' % (fileName, str(errorMessage)))
			return False