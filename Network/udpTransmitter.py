# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por protocolo UDP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import time
import Queue
import pickle
import socket

import logger
import messageClass	# TODO: Si el communicador es iniciado desde otra carpeta, 
					# se debe cambiar el path, para que este import encuentre el archivo

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

	def send(self, message, destinationIp, destinationPort):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		if isinstance(message, messageClass.FileMessage) and message.sendInstance:
			del message.sendInstance # Se elimina el campo auxiliar, no es info util
			return self.sendFileInstance(message, destinationIp, destinationPort)
		elif isinstance(message, messageClass.FileMessage) and not message.sendInstance:
			return self.sendFile(message, destinationIp, destinationPort)
		elif isinstance(message, messageClass.Message) and message.sendInstance:
			del message.sendInstance
			return self.sendMessageInstance(message, destinationIp, destinationPort)
		elif isinstance(message, messageClass.Message) and not message.sendInstance:
			message = message.textMessage
			return self.sendMessage(message, destinationIp, destinationPort)
		else:
			logger.write('DEBUG', '[NETWORK] Mensaje con formato que no correspondes')
			#TODO borrar despues de limpiar, este ultimo else en realidad nunca deberia imprimirlo

	def sendFileInstance(self, message, destinationIp, destinationPort):
		'''Se envia primero la instancia archivo, con los parametros de prioridad, u otros
		que haya agregado el usuario y al final se envia el archivo de la misma manera que
		en el método send file, se hace en esta función porque no requiere la apertura de otro
		puerto. Además se permite que en el receptor determine en la instancia si el archivo 
		se recibió, no se podria hacer con una llamada a sendFile.'''
		try:
			transmissionSocket, receptionSocket, receptionPort = self.createSockets()
			# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
			transmissionSocket.sendto('START_OF_FILE_INSTANCE ' + self.localAddress + ' ' +  str(receptionPort), (destinationIp, destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			destinationPort, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			destinationPort = int(destinationPort)
			# Se obtiene el filename sin la ruta.
			fileDirectory, fileName = os.path.split(message.fileName) 
			filePath = message.fileName
			message.fileName = fileName # Se guarda el nombre del archivo antes de serializar.
			messageSerialized = pickle.dumps(message)
			# Emviamos la instancia, de ser menor a 1024 bytes el envio es de un solo paquete
			logger.write('DEBUG', '[NETWORK] Transfiriendo instancia de Mensaje.')
			bytesSent = 0
			while bytesSent < len(messageSerialized):
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE]
				bytesSent = bytesSent + BUFFER_SIZE
				transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
				receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
			transmissionSocket.sendto('END_OF_FILE_INSTANCE', (destinationIp, destinationPort))
			# Se abre el archivo y se recibe confirmación para comenzar a transmitir (READY)
			fileObject = open(message.fileName, 'rb') 
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
					bytesSent += len(outputData)
					transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
					receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
				fileObject.close()
				transmissionSocket.sendto('END_OF_FILE', (destinationIp, destinationPort))
				logger.write('INFO', '[NETWORK] Instancia de Archivo \'%s\' enviada correctamente!' % fileName)
				return True
			else:
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				return True # Para que no se vuelva a intentar el envio. El control esta en la notificación
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Instancia de Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			message.sendInstance = True # En caso de no enviar se requiere el campo auxiliar
			message.fileName = filePath 
			# Cerramos los sockets que permitieron la conexión con el cliente
			transmissionSocket.close()
			receptionSocket.close()
	
	def sendMessageInstance(self, message, destinationIp, destinationPort):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			transmissionSocket, receptionSocket, receptionPort = self.createSockets()
			# Indicamos al otro extremo que vamos a transmitir una instancia de mensaje, y que debe responder al puerto indicado
			transmissionSocket.sendto('START_OF_MESSAGE_INSTANCE ' + self.localAddress + ' ' +  str(receptionPort), (destinationIp, destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			destinationPort, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			destinationPort = int(destinationPort)
			messageSerialized = pickle.dumps(message) # Serialización de la clase
			logger.write('DEBUG', '[NETWORK] Transfiriendo instancia de Mensaje.')
			bytesSent = 0
			while bytesSent < len(messageSerialized):
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE] # Se envia la cadena de a partes, el receptor las une.
				bytesSent = bytesSent + BUFFER_SIZE
				transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
				receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
			transmissionSocket.sendto('END_OF_MESSAGE_INSTANCE', (destinationIp, destinationPort))
			logger.write('INFO', '[NETWORK] Instancia de Mensaje enviado correctamente!')	
			return True			
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Instancia de Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			message.sendInstance = True
			# Cerramos los sockets que permitieron la conexión con el cliente
			transmissionSocket.close()
			receptionSocket.close()

	def sendFile(self, message, destinationIp, destinationPort):
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			transmissionSocket, receptionSocket, receptionPort = self.createSockets()
			# Indicamos al otro extremo que vamos a transmitir un paquete, y que debe responder al puerto indicado
			transmissionSocket.sendto( 'START_OF_FILE ' + self.localAddress + ' ' +  str(receptionPort), (destinationIp, destinationPort))
			# Establecemos el nuevo puerto destino al cual enviar el paquete
			destinationPort, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			destinationPort = int(destinationPort)
			fileDirectory, fileName = os.path.split(message.fileName)
			fileObject = open(message.fileName, 'rb')
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
					bytesSent += len(outputData)
					transmissionSocket.sendto(outputData, (destinationIp, destinationPort))
					receivedData, addr = receptionSocket.recvfrom(BUFFER_SIZE) # ACK
				fileObject.close()
				transmissionSocket.sendto('END_OF_FILE', (destinationIp, destinationPort))
				logger.write('DEBUG', '[NETWORK] Archivo \'%s\' enviado correctamente!' % fileName)
				return True
			else:
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' fue rechazado!' % fileName)
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			transmissionSocket.close()
			receptionSocket.close()

	def sendMessage(self, message, destinationIp, destinationPort):
		'''Envío de mensaje simple'''
		try:
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)			
			transmissionSocket.sendto(message, (destinationIp, destinationPort))
			logger.write('DEBUG', '[NETWORK] Mensaje enviado correctamente a ' + destinationIp + '  ' + str(destinationPort))
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cerramos los sockets que permitieron la conexión con el cliente
			transmissionSocket.close() 

	def createSockets(self):
		# Crea un nuevo socket transmisor que usa el protocolo de transporte especificado
		transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		transmissionSocket.settimeout(TIMEOUT)
		# Crea un nuevo socket receptor que usa el protocolo de transporte especificado
		receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		receptionSocket.bind((self.localAddress, 0))
		receptionPort = receptionSocket.getsockname()[1]
		return transmissionSocket, receptionSocket, receptionPort