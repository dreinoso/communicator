# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import copy
import pickle
import socket

import logger
import messageClass

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class TcpTransmitter():

	def __init__(self):
		"""Creación de la clase de transmisión de paquetes TCP."""

	def send(self, message, remoteSocket):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.SimpleMessage) and not message.isInstance:
			return self.sendMessage(message.plainText, remoteSocket)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.FileMessage) and not message.isInstance:
			return self.sendFile(message.fileName, remoteSocket)
		# Entonces se trata de enviar una instancia de mensaje
		else:
			# Copiamos el objeto antes de borrar el campo 'isInstance', por un posible fallo de envío
			tmpMessage = copy.copy(message)
			# Eliminamos el último campo del objeto, ya que el receptor no lo necesita
			delattr(tmpMessage, 'isInstance')
			return self.sendMessageInstance(tmpMessage, remoteSocket)

	def sendMessage(self, plainText, remoteSocket):
		'''Envío de mensaje simple'''
		try:
			remoteSocket.send(plainText)
			logger.write('INFO', '[NETWORK-TCP] Mensaje enviado correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK-TCP] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cierra la conexion del socket cliente
			remoteSocket.close()

	def sendFile(self, fileName, remoteSocket):
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			absoluteFilePath = os.path.abspath(fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			remoteSocket.send('START_OF_FILE')
			remoteSocket.recv(BUFFER_SIZE) # ACK
			remoteSocket.send(fileName) # Enviamos el nombre del archivo
			# Recibe confirmación para comenzar a transmitir (READY)
			if remoteSocket.recv(BUFFER_SIZE) == "READY":
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
				logger.write('DEBUG', '[NETWORK-TCP] Transfiriendo archivo \'%s\'...' % fileName)
				while bytesSent < fileSize:
					outputData = fileObject.read(BUFFER_SIZE)
					remoteSocket.send(outputData)
					bytesSent += len(outputData)
					remoteSocket.recv(BUFFER_SIZE) # ACK
				fileObject.close()
				remoteSocket.send('EOF')
				logger.write('INFO', '[NETWORK-TCP] Archivo \'%s\' enviado correctamente!' % fileName)
				return True
			# Recibe 'FILE_EXISTS'
			else:
				logger.write('WARNING', '[NETWORK-TCP] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				# Devolvemos 'True' para que no intente reenviar el archivo
				return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK-TCP] Archivo \'%s\' no enviado: %s' % (fileName, str(errorMessage)))
			return False
		finally:
			remoteSocket.close() # Cierra la conexion del socket cliente

	def sendMessageInstance(self, message, remoteSocket):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			remoteSocket.send('START_OF_INSTANCE') # Indicamos al otro extremo que vamos a transmitir una instancia de mensaje
			remoteSocket.recv(BUFFER_SIZE) # Espera de confirmación ACK
			# Serialización de la instancia
			messageSerialized = pickle.dumps(message)
			bytesSent = 0 
			while bytesSent < len(messageSerialized): # Comienza el envio de la instancia
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE]
				remoteSocket.send(outputData)
				bytesSent = bytesSent + BUFFER_SIZE
				remoteSocket.recv(BUFFER_SIZE) # ACK
			remoteSocket.send('END_OF_INSTANCE')
			################################################################################
			if isinstance(message, messageClass.FileMessage):
				return self.sendFile(message.fileName, remoteSocket)
			else:
				logger.write('INFO', '[NETWORK-TCP] Instancia de mensaje enviada correctamente!')
				return True
			################################################################################
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK-TCP] Instancia de mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cierra la conexion del socket cliente
			remoteSocket.close()