# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import logger

BUFFER_SIZE = 4096 # Tamano del buffer en bytes (cantidad de caracteres)

class TcpTransmitter():

	def __init__(self):
		"""Constructor de la clase de transmisión de paquetes TCP."""

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
			# Cierra la conexion del socket cliente
			remoteSocket.close()