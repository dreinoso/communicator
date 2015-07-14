 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de emails a través de una conexión a internet.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import configReader
import contactList
import logger

import time
import email
import socket
import inspect
import smtplib
import imaplib
import threading
import Queue

from email.header import decode_header
from email.header import make_header
from email.mime.text import MIMEText

TIMEOUT = 5

class Email(object):

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL
	isActive = False

	receptionBuffer = Queue.Queue()

	def __init__(self, _receptionBuffer):
		""" Configura el protocolo SMTP y el protocolo IMAP. El primero se encargara
		de enviar correos electronicos, mientras que el segungo a recibirlos.
		mbos disponen de una misma cuenta asociada a GMAIL para tales fines (y
		que esta dada en el archivo 'contactList.py'. 
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		self.receptionBuffer = _receptionBuffer
		socket.setdefaulttimeout(TIMEOUT) # Establecemos tiempo maximo antes de reintentar lectura

	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		conexiones ocupados en el Host"""
		self.smtpServer.close()  # Cerramos la sesion con el servidor SMTP
		self.imapServer.logout() # Cerramos la sesion con el servidor IMAP
		logger.write('INFO','[EMAIL] Objeto destruido.' )
		#print 'Objeto ' + self.__class__.__name__ + ' destruido.'

	def connect(self):
		self.smtpServer = smtplib.SMTP(configReader.SMTP_SERVER, configReader.SMTP_PORT)      # Establecemos servidor y puerto SMTP
		self.imapServer = imaplib.IMAP4_SSL(configReader.IMAP_SERVER, configReader.IMAP_PORT) # Establecemos servidor y puerto IMAP
		self.smtpServer.starttls()
		self.smtpServer.ehlo()
		self.smtpServer.login(configReader.EMAIL_SERVER, configReader.PASS_SERVER)            # Nos logueamos en el servidor SMTP
		self.imapServer.login(configReader.EMAIL_SERVER, configReader.PASS_SERVER)            # Nos logueamos en el servidor IMAP
		self.imapServer.select('INBOX')                                                     # Seleccionamos la Bandeja de Entrada

	def send(self, emailDestination, emailSubject, emailMessage):
		""" Envia un mensaje de correo electronico.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """
		# Se construye un mensaje simple
		simpleMessage = MIMEText(emailMessage)
		simpleMessage['From'] = configReader.EMAIL_SERVER
		simpleMessage['To'] = emailDestination
		simpleMessage['Subject'] = emailSubject
		# Se envia el mensaje, al correo destino correspondiente
		try:
			self.smtpServer.sendmail(simpleMessage['From'], simpleMessage['To'], simpleMessage.as_string())
			return True
		except Exception, e:
			return False

	def receive(self):
		""" Funcion que se encarga de consultar el correo electronico asociado al modulo
		por algun EMAIL entrante. Envia al servidor IMAP una peticion de solicitud
		de mensajes no leidos (que por ende seran los nuevos) y que en caso de obtenerlos,
		los almacenrá en el buffer, si el remitente del mensaje se encuentra registrado (en el 
		archivo 'contactList.py') o en caso contrario, se enviara una notificacion al usuario 
 		informandole que no es posible realizar la operacion solicitada."""
		while self.isActive:
			emailIds = ['']
			# Mientras no se haya recibido ningun correo electronico, el temporizador no haya expirado y no se haya detectado movimiento...
			while emailIds[0] == '' and self.isActive:
				try:
					self.imapServer.recent() # Actualizamos la Bandeja de Entrada
					#result, emailIds = self.imapServer.search(None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
					result, emailIds = self.imapServer.uid('search', None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
					# Ejemplo de emailIds: ['35 36 37']
				except Exception as e:
					pass
			# Comprobamos si se termino la funcion (el modo EMAIL dejo de funcionar)...
			if not self.isActive:
				break
			# ... sino, leemos los mensajes recibidos
			else:
				emailIdsList = emailIds[0].split()
				emailAmount = len(emailIdsList) # Cantidad de emails no leidos
				logger.write('DEBUG', '[EMAIL] Ha(n) llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico!')
				# Recorremos los emails recibidos...
				for i in emailIdsList:
					#result, emailData = self.imapServer.fetch(i, '(RFC822)')
					result, emailData = self.imapServer.uid('fetch', i, '(RFC822)')
					# Retorna un objeto 'message', y podemos acceder a los items de su cabecera como un diccionario.
					emailReceived = email.message_from_string(emailData[0][1])
					headerList = self.processEmailHeader(emailReceived) # Almacenamos una lista con los elementos del email recibido
					sourceName = headerList[0]                          # Almacenamos el nombre del remitente
					sourceEmail = headerList[1]                         # Almacenamos el correo del remitente
					emailSubject = headerList[2]                        # Almacenamos el asunto correspondiente
					logger.write('DEBUG', '[EMAIL] Procesando correo de ' + sourceName + ' - ' + sourceEmail)
					# Comprobamos si el remitente del mensaje (un correo) esta registrado...
					if sourceEmail in contactList.allowedEmails.values():
						emailBody = self.getEmailBody(emailReceived) # Obtenemos el cuerpo del email
						self.receptionBuffer.put(emailBody)
					else:
						logger.write('WARNING', '[EMAIL] Imposible procesar la solicitud. El correo no se encuentra registrado!')
						emailMessage = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
						self.send(sourceEmail, emailSubject, emailMessage)
		logger.write('WARNING', '[EMAIL] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def processEmailHeader(self, emailReceived):
		""" Procesa la cabecera del EMAIL.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: elementos de la cabecera (nombre del remitente, asunto y cuerpo del email)
		@rtype: list """
		headerList = list()
		senderInformation = self.getSource(emailReceived)
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		senderSubject = self.getSubject(emailReceived)
		# Ejemplo de senderSubject: Importante!
		senderInformationList = senderInformation.split(' <')
		# Ejemplo senderInformationList: ['Mauricio Gonzalez', 'mauriciolg.90@gmail.com>']
		sourceEmail = senderInformationList[1].replace('>', '')
		# Ejemplo sourceEmail: mauriciolg.90@gmail.com
		headerList.append(senderInformationList[0])
		headerList.append(sourceEmail)
		headerList.append(senderSubject)
		# Ejemplo headerList: ['Mauricio Gonzalez', 'mauriciolg.90@gmail.com', 'Importante!']
		return headerList

	def getSource(self, emailReceived):
		""" Obtiene la direccion de correo del remitente.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: direccion de correo del remitente
		@rtype: str """
		h = decode_header(emailReceived.get('From'))
		return unicode(make_header(h)).encode('utf-8')
		
	def getSubject(self, emailReceived):
		""" Obtiene el asunto del correo entrante.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: asunto del correo entrante
		@rtype: str """
		h = decode_header(emailReceived.get('subject'))
		return unicode(make_header(h)).encode('utf-8')

	def getEmailBody(self, emailReceived):
		""" Decodifica el cuerpo del email. Detecta el conjunto de caracteres si la cabecera no esta
		configurada. Primero se busca texto plano si no esta, se busca texto/html.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: cuerpo del mensaje como string unicode
		@rtype: str """
		text = ""
		if emailReceived.is_multipart():
			html = None
			for part in emailReceived.get_payload():
				#print "%s, %s" % (part.get_content_type(), part.get_content_charset())
				if part.get_content_charset() is None:
					# We cannot know the character set, so return decoded "something"
					text = part.get_payload(decode=True)
					continue	 
				charset = part.get_content_charset()
				if part.get_content_type() == 'text/plain':
					text = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')
				if part.get_content_type() == 'text/html':
					html = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')
			if text is not None:
				return text.strip()
			else:
				return html.strip()
		else:
			text = unicode(emailReceived.get_payload(decode=True), emailReceived.get_content_charset(), 'ignore').encode('utf8', 'replace')
			return text.strip()

	def deleteEmail(self, emailId):
		self.imapServer.copy(emailId, '[Gmail]/Trash')
		self.imapServer.store(emailId, '+FLAGS', r'(\Deleted)')
		self.imapServer.expunge()

	def cleanEmailBox(self):
		"""Se limpia el buzón de la cuenta de correo porque los correos anteriores no son importantes
		para el control."""
		try:
			self.imapServer.recent()				       # Actualizamos la Bandeja de Entrada
			result, emailIds = self.imapServer.search(None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
				# Ejemplo de emailIds: ['35 36 37']
		except Exception as e:					       # Timeout or something else
			print '[MODO EMAIL] Error: en "recieve()" No hay conexion a Internet.'
			time.sleep(5)           # ... sigo esperando por alguno de los anteriores.
		emailIdsList = emailIds[0].split()
		emailAmount = len(emailIdsList) # Cantidad de emails no leidos
		for i in emailIdsList: 		# Recorremos los emails recibidos, se marcan como leidos
			result, emailData = self.imapServer.fetch(i, '(RFC822)')
			emailAmount -= 1 # Decrementamos la cantidad de emails no leidos
			if emailAmount == 0:
				break
