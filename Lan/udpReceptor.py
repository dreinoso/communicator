# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger

import os
import Queue
import socket
import threading

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
DOWNLOADS = 'downloads'
TIMEOUT = 2

class UdpReceptor(threading.Thread):

	def __init__(self, _threadName, _localAddress, _remoteAddress, _remotePort):
		threading.Thread.__init__(self, name = _threadName)
		self.localAddress = _localAddress
		self.remoteAddress = _remoteAddress
		self.remotePort = _remotePort
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		self.transmitterSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.transmitterSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		self.receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.receptionSocket.bind((self.localAddress, 0))
		self.receptionPort = self.receptionSocket.getsockname()[1]

	def run(self):
		try:
			# Indicamos al otro extremo nuestro puerto al cual debe enviar el paquete
			self.transmitterSocket.sendto(str(self.receptionPort), (self.remoteAddress, self.remotePort))
			# Obtenemos el nombre del archivo a recibir
			fileName, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			# Obtenemos el directorio actual de trabajo
			currentDirectory = os.getcwd()
			# Obtenemos el path relativo del archivo a descargar
			relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, fileName)
			# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
			if DOWNLOADS not in os.listdir(currentDirectory):
				os.mkdir(DOWNLOADS)
			# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
			if not os.path.isfile(relativeFilePath):
				fileObject = open(relativeFilePath, 'w+')
				logger.write('INFO', '[LAN] Descargando archivo \'%s\'...' % fileName)
				self.transmitterSocket.sendto('READY', (self.remoteAddress, self.remotePort))
				# Comenzamos a descargar el archivo
				while True:
					inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
					if inputData != 'END_OF_PACKET':
						fileObject.write(inputData)
						self.transmitterSocket.sendto('ACK', (self.remoteAddress, self.remotePort))
					else: 
						fileObject.close()
						logger.write('INFO', '[LAN] Archivo \'%s\' descargado correctamente!' % fileName)
						break
			else:
				# Comunicamos al transmisor que el archivo ya existe
				self.transmitterSocket.sendto('FILE_EXISTS', (self.remoteAddress, self.remotePort))
				logger.write('WARNING', '[LAN] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except socket.error as errorMessage:
			logger.write('WARNING', '[LAN] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()
			logger.write('DEBUG', '[LAN] \'%s\' terminado y cliente desconectado.' % self.getName())