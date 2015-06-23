 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import time
import socket
import inspect
import threading

import contactList

class Ethernet(object):

	localHost = contactList.LOCAL_HOST
	localPort = contactList.UDP_PORT
	transmitterSocket = socket.socket
	receiverSocket = socket.socket
	isActive = False

	receptionBuffer = list()
	processNotifications = True
	warningNotifications = True
	errorNotifications = True

	def __init__(self, _receptionBuffer, _processNotifications, _warningNotifications, _errorNotifications):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		self.receptionBuffer = _receptionBuffer
		self.processNotifications = _processNotifications
		self.warningNotifications = _warningNotifications
		self.errorNotifications = _errorNotifications
		try:
			self.transmitterSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.receiverSocket	   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			self.receiverSocket.bind((self.localHost, self.localPort))
			self.receiverSocket.settimeout(2)
		except socket.error , msg:
			print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
		#if (self.warningNotifications): print '[MODO ETHERNET] Listo para usarse.'

	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		puertos ocupados en el Host"""
		self.transmitterSocket.close()
		self.receiverSocket.close()
		print 'Objeto ' + self.__class__.__name__ + ' destruido.'

	def connect(self):
		pass

	def send(self, destinationIp, destinationPort, messageToSend):
		""" Envia una cadena de texto.
		@param detinationIP: dirección IP del destinatario
		@type emailDestination: str
		@param destinationPort: N° de puerto del destinatario
		@type destinationPort: int
		@param message: cadena de texto a enviar
		@type message: str """
		try:
			self.transmitterSocket.sendto(messageToSend, (destinationIp, destinationPort))
			return True
		except socket.error , msg:
			return False
			#if (self.processNotifications): print '[MODO ETHERNET] Se envio un mensaje.'

	def receive(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		que llegen al puerto establecido para guardarlos en el buffer.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """	
		while self.isActive:
			try:
				data, addr = self.receiverSocket.recvfrom(1024) # buffer size is 1024 bytes
				self.receptionBuffer.append(data)
			except socket.error , msg:
				# Para que el bloque 'try' no se quede esperando indefinidamente
				pass
		print '[ETHERNET] Funcion \'%s\' terminada.' % inspect.stack()[0][3]
		#if (self.warningNotifications): print '[MODO ETHERNET] Ya no se estan recibiendo paquetes.'
