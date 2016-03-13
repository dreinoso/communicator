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

TIMEOUT = 2
BUFFER_SIZE = 4096 # Tamano del buffer en bytes (cantidad de caracteres)

class UdpTransmitter(object):

	def __init__(self):
		"""Constructor de la clase de transmisión de paquetes UDP."""

	def send(self, message, destinationIp, destinationPort):
		'''Dependiendo del tipo de mensaje de que se trate, el envio del mensaje
		se comportara diferente'''
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
			return self.sendMessage(message.plainText, destinationIp, destinationPort)
		# Entonces se trata de enviar una instancia de mensaje
		else:
			return self.sendMessageInstance(message, destinationIp, destinationPort)

	def sendMessage(self, plainText, destinationIp, destinationPort):
		'''Envío de mensaje simple'''
		try:
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)			
			transmissionSocket.sendto(plainText, (destinationIp, destinationPort))
			logger.write('INFO', '[NETWORK-UDP] Mensaje enviado correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK-UDP] Mensaje no enviado: %s' % str(errorMessage))
			return False
		finally:
			# Cerramos el socket que permitió la conexión con el cliente
			transmissionSocket.close()
	
	def sendMessageInstance(self, message, destinationIp, destinationPort):
		'''Envió de la instancia mensaje. Primero debe realizarse una serialización de la clase
		y enviar de a BUFFER_SIZE cantidad de caracteres, en definitiva se trata de una cadena.'''
		try:
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Transmitimos la instancia serializada al destino correspondiente
			transmissionSocket.sendto(serializedMessage, (destinationIp, destinationPort))
			logger.write('INFO', '[NETWORK-UDP] Instancia de mensaje enviada correctamente!')
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[NETWORK-UDP] Instancia de mensaje no enviada: %s' % str(errorMessage))
			return False
		finally:
			# Cerramos el socket que permitió la conexión con el cliente
			transmissionSocket.close()