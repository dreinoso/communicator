# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import pickle
import Queue
import socket
import threading

import logger
import messageClass

BUFFER_SIZE = 1024 # Tamano del buffer en bytes (cantidad de caracteres)

class TcpTransmitter(threading.Thread):

	def __init__(self, _threadName, _remoteSocket, _messageToSend):
		"""Creación de la clase de transmisión de paquetes TCP.
		@param _threadName: nombre del hilo
		@type: string
		@param socket para el envio del archivo
		@type: socket
		@param messageToSend: mensaje que puede corresponder a una instancia o un String 
		@type: string
		@type: Message"""
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.messageToSend = _messageToSend

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
			if os.path.isfile(absoluteFilePath): # En caso de que se encuetre el archivo lo envia, sino sera un mensaje
				self.sendFile()
			else:
				self.sendMessage()

	def sendFileInstance(self):
		'''Se envia primero la instancia archivo, con los parametros de prioridad, u otros
		que haya agregado el usuario y al final se envia el archivo de la misma manera que
		en el método send file, se hace en esta función porque no requiere la apertura de otro
		puerto. Además se permite que en el receptor determine en la instancia si el archivo 
		se recibió, no se podria hacer con una llamada a sendFile.'''
		try:
			#Primero se intenta la apertura del archivo
			relativeFilePath = self.messageToSend.fileName
			absoluteFilePath = os.path.abspath(relativeFilePath)
			if os.path.isfile(absoluteFilePath): # En caso de que se encuetre el archivo lo envia
				fileDirectory, fileName = os.path.split(absoluteFilePath)
				fileObject = open(absoluteFilePath, 'rb')
				#Continua con el envio de la instancia si el archivo a enviar existe
				self.remoteSocket.send('START_OF_FILE_INSTANCE')	# Indicamos al otro extremo que vamos a transmitir una instancia de mensaje
				self.remoteSocket.recv(BUFFER_SIZE) # Espera de confirmación ACK
				fileDirectory, fileName = os.path.split(absoluteFilePath) # Se obtiene el filename sin la ruta.
				fileName = self.messageToSend.fileName # Se guarda el nombre del archivo antes de serializar
				self.messageToSend = pickle.dumps(self.messageToSend) # Serialización de la instancia
				logger.write('DEBUG', '[LAN] Transfiriendo instancia de Mensaje.')
				bytesSent = 0 
				while bytesSent < len(self.messageToSend): # Comienza el envio de la instancia
					outputData = self.messageToSend[bytesSent:bytesSent + BUFFER_SIZE]
					bytesSent = bytesSent + BUFFER_SIZE
					self.remoteSocket.send(outputData)
					self.remoteSocket.recv(BUFFER_SIZE) # ACK
				self.remoteSocket.send('END_OF_FILE_INSTANCE')
				# Se procede con la respuesta del receptor y envio del archivo
				if self.remoteSocket.recv(BUFFER_SIZE) == "READY":
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
						self.remoteSocket.send(outputData)
						self.remoteSocket.recv(BUFFER_SIZE) # ACK
					fileObject.close()
					self.remoteSocket.send('END_OF_FILE')
					logger.write('INFO', '[LAN] Instancia de Archivo \'%s\' enviado correctamente!' % fileName)
			else:
				logger.write('WARNING', '[LAN] Envio cancelado, el archivo (' + self.messageToSend.fileName + ') para la instancia de archivo que se pretende enviar no existe.')
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Instancia de Archivo (' + fileName +') no enviado: ' +  str(errorMessage))
		finally:
			self.remoteSocket.close() # Cierra la conexion del socket cliente

	def sendMessageInstance(self):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			self.remoteSocket.send('START_OF_MESSAGE_INSTANCE') # Indicamos al otro extremo que vamos a transmitir una instancia de mensaje
			self.remoteSocket.recv(BUFFER_SIZE) # Espera de confirmación ACK
			self.messageToSend = pickle.dumps(self.messageToSend) # Serialización de la instancia
			logger.write('DEBUG', '[LAN] Transfiriendo instancia de Mensaje.')
			bytesSent = 0 
			while bytesSent < len(self.messageToSend): # Comienza el envio de la instancia
				outputData = self.messageToSend[bytesSent:bytesSent + BUFFER_SIZE]
				bytesSent = bytesSent + BUFFER_SIZE
				self.remoteSocket.send(outputData)
				self.remoteSocket.recv(BUFFER_SIZE) # ACK
			self.remoteSocket.send('END_OF_MESSAGE_INSTANCE')
			logger.write('INFO', '[LAN] Instancia de archivo enviado correctamente!')				
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Instancia de Mensaje no enviado: %s' % str(errorMessage))
		finally:
			self.remoteSocket.close() # Cerramos los sockets que permitieron la conexión con el cliente
			

	def sendFile(self):				
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			relativeFilePath = self.messageToSend
			absoluteFilePath = os.path.abspath(relativeFilePath)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			fileObject = open(absoluteFilePath, 'rb')
			self.remoteSocket.send('START_OF_FILE')
			self.remoteSocket.recv(BUFFER_SIZE) # ACK
			self.remoteSocket.send(fileName) # Enviamos el nombre del archivo
			# Recibe confirmación para comenzar a transmitir (READY)
			if self.remoteSocket.recv(BUFFER_SIZE) == "READY":
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
					self.remoteSocket.send(outputData)
					self.remoteSocket.recv(BUFFER_SIZE) # ACK
				fileObject.close()
				self.remoteSocket.send('END_OF_FILE')
				logger.write('INFO', '[LAN] Archivo \'%s\' enviado correctamente!' % fileName)
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Archivo (' + self.messageToSend +') no enviado: ' +  str(errorMessage))
		finally:
			self.remoteSocket.close() # Cierra la conexion del socket cliente

	def sendMessage(self):
		'''Envío de mensaje simple'''
		try:
			self.remoteSocket.send(self.messageToSend)
			logger.write('INFO', '[LAN] Mensaje enviado correctamente!')
		except Exception as errorMessage:
			logger.write('WARNING', '[LAN] Mensaje no enviado: %s' % str(errorMessage))
		finally:
			self.remoteSocket.close() # Cierra la conexion del socket cliente