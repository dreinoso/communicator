 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import contactList

import time
import socket

class Ethernet(object):

	processingResponseList = list()
	inBuffer = list()

	contRead = 0

	def __init__(self):
		""" Configura el protocolo SMTP y el protocolo IMAP. El primero se encargara
		de enviar correos electronicos, mientras que el segungo a recibirlos.
		mbos disponen de una misma cuenta asociada a GMAIL para tales fines (y
		que esta dada en el archivo 'contactList.py'. """
		#print 'Configurando el modulo ETHERNET...'
		socket.setdefaulttimeout(10)                                                   # Establecemos tiempo maximo antes de reintentar lectura
		print '[MODO ETHERNET] Listo para usarse.'

	def __del__(self):
		#self.closeEmail()
		print '[MODO ETHERNET] Se terminó la sesión.'

	def closeEthernet(self):
		""" Finaliza la sesion iniciada"""
		print '[MODO ETHERNET] Se termino la sesión.'

	def sendPacket(self, emailDestination, emailSubject, emailMessage):
		""" Envia un mensaje de correo electronico.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """
		print '[MODO ETHERNET] Se envio un mensaje.'

	def recievePacket(self):
		""" Envia un mensaje de correo electronico.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """
		print '[MODO ETHERNET] Se estan recibiendo paquetes.'
	
