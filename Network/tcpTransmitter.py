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

import logger
import messageClass

BUFFER_SIZE = 1024 # Tamano del buffer en bytes (cantidad de caracteres)

class TcpTransmitter():

	def __init__(self):
		"""Creación de la clase de transmisión de paquetes TCP."""

	def send(self, message, remoteSocket):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		if isinstance(message, messageClass.FileMessage) and message.sendInstance:
			del message.sendInstance  # Se elimina el campo auxiliar, no es info útil
			return self.sendFileInstance(message, remoteSocket) 
		elif isinstance(message, messageClass.FileMessage) and not message.sendInstance:
			return self.sendFile(message, remoteSocket)
		elif isinstance(message, messageClass.Message) and message.sendInstance:
			del message.sendInstance
			return self.sendMessageInstance(message, remoteSocket)
		elif isinstance(message, messageClass.Message) and not message.sendInstance:
			message = message.textMessage 
			return self.sendMessage(message, remoteSocket)
		else:
			logger.write('DEBUG', '[NETWORK] Mensaje con formato que no correspondes')
			#TODO borrar despues de limpiar, este ultimo else en realidad nunca deberia imprimirlo


	def sendFileInstance(self, message, remoteSocket):
		'''Se envia primero la instancia archivo, con los parametros de prioridad, u otros
		que haya agregado el usuario y al final se envia el archivo de la misma manera que
		en el método send file, se hace en esta función porque no requiere la apertura de otro
		puerto. Además se permite que en el receptor determine en la instancia si el archivo 
		se recibió, no se podria hacer con una llamada a sendFile.'''
		try:
			# Se obtiene el filename sin la ruta.
			fileDirectory, fileName = os.path.split(message.fileName) 
			filePath = message.fileName # Se guarda el path del archivo en caso de no enviar
			message.fileName = filename # Solo se debe enviar el nombre
			#Continua con el envio de la instancia si el archivo a enviar existe
			remoteSocket.send('START_OF_FILE_INSTANCE')	# Indicamos al otro extremo que vamos a transmitir una instancia de mensaje
			remoteSocket.recv(BUFFER_SIZE) # Espera de confirmación ACK
			messageSerialized = pickle.dumps(message) # Serialización de la instancia
			logger.write('DEBUG', '[NETWORK] Transfiriendo instancia de Mensaje.')
			bytesSent = 0 
			while bytesSent < len(messageSerialized): # Comienza el envio de la instancia
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE]
				bytesSent = bytesSent + BUFFER_SIZE
				remoteSocket.send(outputData)
				remoteSocket.recv(BUFFER_SIZE) # ACK
			remoteSocket.send('END_OF_FILE_INSTANCE')
			# Se procede con la respuesta del receptor y envio del archivo
			if remoteSocket.recv(BUFFER_SIZE) == "READY":
				fileObject = open(filePath, 'rb')
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
					remoteSocket.send(outputData)
					remoteSocket.recv(BUFFER_SIZE) # ACK
				fileObject.close()
				remoteSocket.send('END_OF_FILE')
				logger.write('DEBUG', '[NETWORK] Instancia de Archivo \'%s\' enviado correctamente!' % fileName)
				return True
			else:
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				return True # Para que no se vuelva a intentar el envio. El control esta en la notificación	
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Instancia de Archivo (' + fileName +') no enviado: ' +  str(errorMessage))
			return False
		finally: # Se ejecuta sin importar los return previos
			message.sendInstance = True # En caso de error se requiere este campo auxiliar
			message.fileName = filePath # Se restaura el path absoluto
			remoteSocket.close() # Cierra la conexion del socket cliente

	def sendMessageInstance(self, message, remoteSocket):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			remoteSocket.send('START_OF_MESSAGE_INSTANCE') # Indicamos al otro extremo que vamos a transmitir una instancia de mensaje
			remoteSocket.recv(BUFFER_SIZE) # Espera de confirmación ACK
			messageSerialized = pickle.dumps(message) # Serialización de la instancia
			logger.write('DEBUG', '[NETWORK] Transfiriendo instancia de Mensaje.')
			bytesSent = 0 
			while bytesSent < len(messageSerialized): # Comienza el envio de la instancia
				outputData = messageSerialized[bytesSent:bytesSent + BUFFER_SIZE]
				bytesSent = bytesSent + BUFFER_SIZE
				remoteSocket.send(outputData)
				remoteSocket.recv(BUFFER_SIZE) # ACK
			remoteSocket.send('END_OF_MESSAGE_INSTANCE')
			logger.write('DEBUG', '[NETWORK] Instancia de Mensaje enviado correctamente!')
			return True				
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Instancia de Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			message.sendInstance = True
			remoteSocket.close() # Cerramos los sockets que permitieron la conexión con el cliente
			

	def sendFile(self, message, remoteSocket):				
		'''Envio de archivo simple, es decir unicamente el archivo sin una instancia de control.
		Esta función solo se llama en caso de que el archivo exista. Por lo que solo resta abrirlo.
		Se hacen sucecivas lecturas del archivo, y se envian. El receptor se encarga de recibir y 
		rearmar	el archivo. Se utiliza una sincronización de mensajes para evitar perder paquetes,
		además que lleguen en orden.'''
		try:
			fileDirectory, fileName = os.path.split(message.fileName)
			fileObject = open(message.fileName, 'rb')
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
				logger.write('DEBUG', '[NETWORK] Transfiriendo archivo \'%s\'...' % fileName)
				while bytesSent < fileSize:
					outputData = fileObject.read(BUFFER_SIZE)
					bytesSent += len(outputData)
					remoteSocket.send(outputData)
					remoteSocket.recv(BUFFER_SIZE) # ACK
				fileObject.close()
				remoteSocket.send('END_OF_FILE')
				logger.write('DEBUG', '[NETWORK] Archivo \'%s\' enviado correctamente!' % fileName)
			else:
				logger.write('WARNING', '[NETWORK] El archivo \'%s\' ya existe, fue rechazado!' % fileName)
				return True # Para que no se vuelva a intentar el envio. El control esta en la notificación		
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Archivo (' + message +') no enviado: ' +  str(errorMessage))
			return False
		finally:
			remoteSocket.close() # Cierra la conexion del socket cliente

	def sendMessage(self, message, remoteSocket):
		'''Envío de mensaje simple'''
		try:
			remoteSocket.send(message)
			logger.write('DEBUG', '[NETWORK] Mensaje enviado correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			remoteSocket.close() # Cierra la conexion del socket cliente