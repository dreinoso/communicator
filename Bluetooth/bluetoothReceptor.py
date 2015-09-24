# coding=utf-8

import os
import Queue
import threading
import bluetooth

import logger

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
DOWNLOADS = 'downloads'

class BluetoothReceptor(threading.Thread):

	receptionBuffer = Queue.Queue()

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer

	def run(self):
		try:
			''' Operacion bloqueante, que espera recibir al menos un byte o hasta que el extremo remoto este cerrado.
				Cuando el otro extremo este desconectado y todos los caracteres hayan sido leidos, la funcion retorna
				una cadena vacia. '''
			dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
			if dataReceived == 'START_OF_PACKET':
				currentDirectory = os.getcwd()                 # Obtenemos el directorio actual de trabajo
				fileName = self.remoteSocket.recv(BUFFER_SIZE) # Obtenemos el nombre del archivo a recibir
				relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, fileName) # Obtenemos el path relativo del archivo a descargar
				# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
				if DOWNLOADS not in os.listdir(currentDirectory):
					os.mkdir(DOWNLOADS)
				# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
				if not os.path.isfile(relativeFilePath):
					fileObject = open(relativeFilePath, 'w+')
					logger.write('INFO', '[BLUETOOTH] Descargando archivo \'%s\' ...' % fileName)
					self.remoteSocket.send('READY')
					while True:
						inputData = self.remoteSocket.recv(BUFFER_SIZE)
						if inputData != 'END_OF_PACKET':
							fileObject.write(inputData)
						else: 
							fileObject.close()
							logger.write('INFO', '[BLUETOOTH] Archivo \'%s\' descargado correctamente!' % fileName)
				else:
					self.remoteSocket.send('FILE_EXISTS') # Comunicamos al transmisor que el archivo ya existe
					logger.write('WARNING', '[BLUETOOTH] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
			else:
				self.receptionBuffer.put(dataReceived)
		except bluetooth.BluetoothError:
			pass
		finally:
			# Cierra la conexion del socket cliente
			self.remoteSocket.close()
			logger.write('DEBUG', '[BLUETOOTH] \'%s\' terminado y cliente desconectado.' % self.getName())