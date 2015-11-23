# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por protocolo UDP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import pickle
import socket

import logger
import messageClass

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
TIMEOUT = 2

class UdpTransmitter(object):

	def __init__(self, _localAddress):
		"""Creación de la clase para recepción de paquetes UDP.
		@param _threadName: nombre del hilo
		@type: string
		@param message: mensaje que puede corresponder a una instancia o un String 
		@type: string
		@type: Message
		@param _localAddress: dirección ip del transmisor
		@type: string
		@param _destinationIp: dirección ip del receptor
		@type: string
		@param _destinationPort: número de puerto destino
		@type: int"""
		self.localAddress = _localAddress

	def createSockets(self):
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		transmissionSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		receptionSocket.bind((self.localAddress, 0))
		receptionPort = receptionSocket.getsockname()[1]
		return transmissionSocket, receptionSocket, receptionPort

	def send(self, message, destinationIp, destinationPort):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.SimpleMessage) and not message.isInstance:
			return self.sendMessage(message.plainText, destinationIp, destinationPort)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.FileMessage) and not message.isInstance:
			return self.sendFile(message.fileName, destinationIp, destinationPort)
		# Comprobación de envío de instancia de mensaje
		else:
			return self.sendMessageInstance(message, destinationIp, destinationPort)

	def sendMessage(self, plainText, destinationIp, destinationPort):
		'''Envío de mensaje simple'''
		try:
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)			
			transmissionSocket.sendto(plainText, (destinationIp, destinationPort))
			logger.write('INFO', '[NETWORK] Mensaje enviado correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cierra la conexion del socket cliente
			transmissionSocket.close()

	def sendFile(self, fileName, destinationIp, destinationPort):
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			transmissionSocket, receptionSocket, receptionPort = self.createSockets()
			# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
			transmissionSocket.sendto('START_OF_FILE ' + self.localAddress + ' ' +  str(receptionPort), (destinationIp, destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			destinationPort, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			destinationPort = int(destinationPort)
			absoluteFilePath = os.path.abspath(fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			# Enviamos el nombre del archivo
			transmissionSocket.sendto(fileName, (destinationIp, destinationPort))
			# Recibe confirmación para comenzar a transmitir (READY)
			receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE)
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
				logger.write('DEBUG', '[NETWORK] Transfiriendo archivo \'%s\'...' % fileName)
				while bytesSent < fileSize:
					outputData = fileObject.read(BUFFER_SIZE)
					transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
					bytesSent += len(outputData)
					receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
				fileObject.close()
				transmissionSocket.sendto('EOF', (destinationIp, destinationPort))
				logger.write('INFO', '[NETWORK] Archivo \'%s\' enviado correctamente!' % fileName)
				return True
			# Recibe 'FILE_EXISTS'
			else:
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				# Devolvemos 'True' para que no intente reenviar el archivo
				return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Archivo \'%s\' no enviado: %s' % (fileName, str(errorMessage)))
			return False
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			receptionSocket.close()
			transmissionSocket.close()
	
	def sendMessageInstance(self, message, destinationIp, destinationPort):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			transmissionSocket, receptionSocket, receptionPort = self.createSockets()
			# Indicamos al otro extremo que vamos a transmitir una instancia de mensaje, y que debe responder al puerto indicado
			transmissionSocket.sendto('START_OF_INSTANCE ' + self.localAddress + ' ' +  str(receptionPort), (destinationIp, destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			destinationPort, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			destinationPort = int(destinationPort)
			# Serialización de la clase
			messageSerialized = pickle.dumps(message)
			bytesSent = 0
			while bytesSent < len(messageSerialized):
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE] # Se envia la cadena de a partes, el receptor las une.
				transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
				bytesSent = bytesSent + BUFFER_SIZE
				receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
			transmissionSocket.sendto('END_OF_INSTANCE', (destinationIp, destinationPort))
			#################################################################################
			if isinstance(message, messageClass.FileMessage):
				return self.sendFile(message.fileName, destinationIp, destinationPort)
			else:
				logger.write('INFO', '[NETWORK] Instancia de mensaje enviada correctamente!')
				return True
			##################################################################################	
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Instancia de mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			receptionSocket.close()
			transmissionSocket.close()