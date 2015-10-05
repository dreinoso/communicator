# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por protocolo UDP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import logger
import messageClass	# TODO: Si el communicador es iniciado desde otra carpeta, 
					# se debe cambiar el path, para que este import encuentre el archivo

import os
import time
import Queue
import pickle
import socket
import threading

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
TIMEOUT = 20

class UdpTransmitter(threading.Thread):

	def __init__(self, _threadName, _messageToSend, _localAddress, _destinationIp, _destinationPort):
		threading.Thread.__init__(self, name = _threadName)
		self.messageToSend = _messageToSend
		self.localAddress = _localAddress
		self.destinationIp = _destinationIp
		self.destinationPort = _destinationPort
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		self.transmitterSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.transmitterSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		self.receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.receptionSocket.bind((self.localAddress, 0))
		self.receptionPort = self.receptionSocket.getsockname()[1]

	def run(self):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		if isinstance(self.messageToSend, messageClass.FileMessage):
			self.sendFileInstance()
		elif isinstance(self.messageToSend, messageClass.Message):
			self.sendMessageInstance()
		else: 
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			if os.path.isfile(absoluteFilePath): # En caso de que se encuetre el archivo lo envia, sino sera un mensaje.
				self.sendFile()
			else:
				self.sendMessage()

	def sendFileInstance(self):
		'''Se envia primero la instancia archivo, con los parametros de prioridad, u otros
		que haya agregado el usuario y al final se envia el archivo con una llamada al método
		correspondiente'''
		try:
			# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
			self.transmitterSocket.sendto('START_OF_MESSAGE_INSTANCE ' + self.localAddress + ' ' +  str(self.receptionPort), (self.destinationIp, self.destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			self.destinationPort, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			self.destinationPort = int(self.destinationPort)
			fileName = messageToSend.fileName # Se guarda el nombre del archivo antes de serializar.
			self.messageToSend = pickle.dumps(self.messageToSend)
			# Emviamos la instancia, de ser menor a 1024 bytes el envio es de un solo paquete
			logger.write('DEBUG', '[LAN] Transfiriendo instancia de Mensaje.')
			bytesSent = 0
			while bytesSent < len(self.messageToSend):
				outputData = self.messageToSend[bytesSent:bytesSent + BUFFER_SIZE]
				bytesSent = bytesSent + BUFFER_SIZE
				self.transmitterSocket.sendto(outputData, (self.destinationIp, self.destinationPort))
				receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE) # ACK
			self.transmitterSocket.sendto('END_OF_MESSAGE_INSTANCE', (self.destinationIp, self.destinationPort))
			logger.write('INFO', '[LAN] Instancia de archivo enviado correctamente!')				
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Instancia de Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()
		messageToSend = fileName # Se establece el nombre del archivo para el método sendFile 
		self.sendFile() # Se envia el archivo comunmente.


	def sendMessageInstance(self):
		try:
			# Indicamos al otro extremo que vamos a transmitir una instancia de mensaje, y que debe responder al puerto indicado
			self.transmitterSocket.sendto('START_OF_MESSAGE_INSTANCE ' + self.localAddress + ' ' +  str(self.receptionPort), (self.destinationIp, self.destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			self.destinationPort, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			self.destinationPort = int(self.destinationPort)
			self.messageToSend = pickle.dumps(self.messageToSend) # Serialización de la clase
			logger.write('DEBUG', '[LAN] Transfiriendo instancia de Mensaje.')
			bytesSent = 0
			while bytesSent < len(self.messageToSend):
				outputData = self.messageToSend[bytesSent:bytesSent + BUFFER_SIZE] # Se envia la cadena de a partes, el receptor las une.
				bytesSent = bytesSent + BUFFER_SIZE
				self.transmitterSocket.sendto(outputData, (self.destinationIp, self.destinationPort))
				receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE) # ACK
			self.transmitterSocket.sendto('END_OF_MESSAGE_INSTANCE', (self.destinationIp, self.destinationPort))
			logger.write('DEBUG', '[LAN] Instancia de Mensaje enviado correctamente!')				
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Instancia de Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()

	def sendFile(self):
		try:
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
			#if byInstance: syncMessage = 'START_OF_FILE_BY_INSTANCE' # Para que no se almacene la instancia del archivo, y además el "nombre del archivo" en el receptor
			#else: syncMessage = 'START_OF_FILE' # Para envio de archivo simple
			self.transmitterSocket.sendto( 'START_OF_FILE ' + self.localAddress + ' ' +  str(self.receptionPort), (self.destinationIp, self.destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			self.destinationPort, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			self.destinationPort = int(self.destinationPort)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			# Enviamos el nombre del archivo
			self.transmitterSocket.sendto(fileName, (self.destinationIp, self.destinationPort))
			# Recibe confirmación para comenzar a transmitir (READY)
			receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE)
			if receivedData == "READY":
				# Guardamos la posición inicial del archivo (donde comienza)
				fileBeginning = fileObject.tell()
				# Apuntamos al final del archivo
				fileObject.seek(0, os.SEEK_END)
				# Obtenemos la posición final del mismo (que sería el tamaño)
				fileSize = fileObject.tell()
				# Apuntamos nuevamente al comienzo del archivo, para comenzar a transmitir
				fileObject.seek(fileBeginning, os.SEEK_SET)
				# Envio del contenido del archivo
				bytesSent = 0
				logger.write('INFO', '[LAN] Transfiriendo archivo \'%s\'...' % fileName)
				while bytesSent < fileSize:
					outputData = fileObject.read(BUFFER_SIZE)
					bytesSent += len(outputData)
					self.transmitterSocket.sendto(outputData, (self.destinationIp, self.destinationPort))
					receivedData, addr = self.receptionSocket.recvfrom(BUFFER_SIZE) # ACK
				fileObject.close()
				self.transmitterSocket.sendto('END_OF_FILE', (self.destinationIp, self.destinationPort))
				logger.write('INFO', '[LAN] Archivo \'%s\' enviado correctamente!' % fileName)
			else:
				logger.write('WARNING', '[LAN] El archivo \'%s\' fue rechazado!' % fileName)
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()

	def sendMessage(self):
		try:
			self.transmitterSocket.sendto(self.messageToSend, (self.destinationIp, self.destinationPort))
			logger.write('INFO', '[LAN] Mensaje enviado correctamente a ' + self.destinationIp + '  ' + str(self.destinationPort))
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Mensaje no enviado: %s' % str(errorMessage))
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			self.transmitterSocket.close()
			self.receptionSocket.close()