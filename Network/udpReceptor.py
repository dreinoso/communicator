# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger
import messageClass

import os
import Queue
import socket
import pickle
import threading

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
DOWNLOADS = 'Downloads'
TIMEOUT = 2

class UdpReceptor(threading.Thread):

	def __init__(self, _threadName, _receptionBuffer, _localAddress, _remoteAddress, _remotePort):
		"""Creación de la clase para recepción de paquetes UDP.
		@param _threadName: nombre del hilo
		@type: string
		@param messageToSend: mensaje que puede corresponder a una instancia o un String 
		@type: string
		@type: Message
		@param _localAddress: dirección ip del receptor
		@type: string
		@param _remoteAddress: dirección ip del transmisor
		@type: string
		@param _remotePort: número de puerto del transmisor
		@type: int"""
		threading.Thread.__init__(self, name = _threadName)
		self.receptionBuffer = _receptionBuffer
		self.localAddress = _localAddress
		self.remoteAddress = _remoteAddress
		self.remotePort = _remotePort
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		self.transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.transmissionSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		self.receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.receptionSocket.bind((self.localAddress, 0))
		self.receptionPort = self.receptionSocket.getsockname()[1]

	def run(self):
		'''Al recibirse un mensaje UDP, se debe determinar si se trata de un archivo o de alguna
		instancia. Esto lo determina LanClass, y se indica en el nombre del hilo. A diferencia de 
		TCP en caso de que se reciba un mensaje simple solo se guarda no requiere conexión
		por lo que no hay un método para esa recepción.'''
		if str(self.name) == 'Thread-UDPReceptor-FileInstance':
			self.receiveFileInstance()
		elif str(self.name) == 'Thread-UDPReceptor-MessageInstance':
			self.receiveMessageInstance()
		else:
			self.receiveFile()

	def receiveFileInstance(self):
		'''Primero se recive la instancia FileMessage propiamente dicha, para luego preprarse
		para el envio del archivo en si en caso de que este no se encuentre ya en el receptor.
		Es una combinación de los métodos de recepción de instancia mensaje y recepción de 
		archivo, pero tiene un control adicional. En caso de que el archivo se reciba se indica
		en uno de los campos de la instancia recibida.'''
		try:
			message = ''
			# Indicamos al otro extremo nuestro puerto al cual debe enviar el paquete
			self.transmissionSocket.sendto(str(self.receptionPort), (self.remoteAddress, self.remotePort))
			inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			while inputData != 'END_OF_FILE_INSTANCE':
				serializedMessage = ''
				serializedMessage = serializedMessage + inputData
				self.transmissionSocket.sendto('ACK', (self.remoteAddress, self.remotePort))
				inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			message = pickle.loads(serializedMessage) # Deserialización de la instancia
			# Obtenemos el nombre del archivo a recibir
			# Obtenemos el directorio actual de trabajo
			currentDirectory = os.getcwd()
			# Obtenemos el path relativo del archivo a descargar
			relativeFilePath = os.path.join(currentDirectory, DOWNLOADS, message.fileName)
			# Verificamos si el directorio 'DOWNLOADS' no está creado en el directorio actual
			if DOWNLOADS not in os.listdir(currentDirectory):
				os.mkdir(DOWNLOADS)
			# Verificamos si el archivo a descargar no existe en la carpeta 'DOWNLOADS'
			if not os.path.isfile(relativeFilePath):
				fileObject = open(relativeFilePath, 'w+')
				logger.write('DEBUG', '[NETWORK] Descargando archivo \'%s\'...' % message.fileName)
				self.transmissionSocket.sendto('READY', (self.remoteAddress, self.remotePort))
				# Comenzamos a descargar el archivo
				while True:
					inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.transmissionSocket.sendto('ACK', (self.remoteAddress, self.remotePort))
					else: 
						fileObject.close()
						logger.write('DEBUG', '[NETWORK] Archivo \'%s\' descargado correctamente!' % message.fileName)
						message.received = True 
						break
			else:
				# Comunicamos al transmisor que el archivo ya existe
				self.transmissionSocket.sendto('FILE_EXISTS', (self.remoteAddress, self.remotePort))
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe! Imposible descargar.' % message.fileName)
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar descargar el archivo')
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmissionSocket.close()
			self.receptionSocket.close()
			if message != None:
				self.receptionBuffer.put(message)
			logger.write('DEBUG', '[NETWORK] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveMessageInstance(self):
		'''Por medio de una sincronización de mensajes se recibe la cadena de a partes
		que corresponde a la instancia serializada, y se arma a medida que lleguen los 
		caracteres, cuando se tiene la cadena completa se la deserializa para obtener 
		la instancia y almacenarla en el buffer.'''
		try:
			# Indicamos al otro extremo nuestro puerto al cual debe enviar el paquete
			self.transmissionSocket.sendto(str(self.receptionPort), (self.remoteAddress, self.remotePort))
			inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			while inputData != 'END_OF_MESSAGE_INSTANCE':
				serializedMessage = ''
				serializedMessage = serializedMessage + inputData
				self.transmissionSocket.sendto('ACK', (self.remoteAddress, self.remotePort))
				inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			message = pickle.loads(serializedMessage) # Deserialización de la instancia
			self.receptionBuffer.put(message)
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar recibir instancia de mensaje.')
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmissionSocket.close()
			self.receptionSocket.close()
			logger.write('DEBUG', '[NETWORK] \'%s\' terminado y cliente desconectado.' % self.getName())

	def receiveFile(self):
		'''Para la recepción del archivo, primero se verifica que le archivo no 
		exista, de existir el archivo, se avisa al transmisor. En caso de que no 
		exista se confirma al emisor para que comience a transmitir, se crea el 
		archivo y la capeta de descarga en caso de que no exista. Se escribe el 
		archivo a medida que llegan los paquetes.'''
		try:
			# Indicamos al otro extremo nuestro puerto al cual debe enviar el paquete
			self.transmissionSocket.sendto(str(self.receptionPort), (self.remoteAddress, self.remotePort))
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
				logger.write('DEBUG', '[NETWORK] Descargando archivo \'%s\'...' % fileName)
				self.transmissionSocket.sendto('READY', (self.remoteAddress, self.remotePort))
				# Comenzamos a descargar el archivo
				while True:
					inputData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
					if inputData != 'END_OF_FILE':
						fileObject.write(inputData)
						self.transmissionSocket.sendto('ACK', (self.remoteAddress, self.remotePort))
					else: 
						fileObject.close()
						logger.write('DEBUG', '[NETWORK] Archivo \'%s\' descargado correctamente!' % fileName)
						self.receptionBuffer.put('ARCHIVO_RECIBIDO: ' + fileName)
						break
			else:
				# Comunicamos al transmisor que el archivo ya existe
				self.transmissionSocket.sendto('FILE_EXISTS', (self.remoteAddress, self.remotePort))
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
		except socket.error as errorMessage:
			logger.write('WARNING', '[NETWORK] Error al intentar descargar el archivo \'%s\'.' % fileName)
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmissionSocket.close()
			self.receptionSocket.close()
			logger.write('DEBUG', '[NETWORK] \'%s\' terminado y cliente desconectado.' % self.getName())