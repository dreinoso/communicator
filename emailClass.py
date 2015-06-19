 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de emails a través de una conexión a internet.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import contactList

import time
import email
import socket
import inspect
import smtplib
import imaplib
import threading

from email.header import decode_header
from email.header import make_header
from email.mime.text import MIMEText

class Email(object):

	processingResponseList = list()
	inBuffer = list()

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL
	countRead = 0
	isActive = False
	receptionBuffer = list()
	processNotifications = True
	warningNotifications = True
	errorNotifications = True

	def __init__(self, _receptionBuffer, _processNotifications, _warningNotifications, _errorNotifications):
		""" Configura el protocolo SMTP y el protocolo IMAP. El primero se encargara
		de enviar correos electronicos, mientras que el segungo a recibirlos.
		mbos disponen de una misma cuenta asociada a GMAIL para tales fines (y
		que esta dada en el archivo 'contactList.py'. 
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		#print 'Configurando el modulo EMAIL...'
		self.smtpServer = smtplib.SMTP(contactList.SMTP_SERVER, contactList.SMTP_PORT)      # Establecemos servidor y puerto SMTP
		self.imapServer = imaplib.IMAP4_SSL(contactList.IMAP_SERVER, contactList.IMAP_PORT) # Establecemos servidor y puerto IMAP
		socket.setdefaulttimeout(10)                                                   # Establecemos tiempo maximo antes de reintentar lectura
		self.receptionBuffer = _receptionBuffer
		self.processNotifications = _processNotifications
		self.warningNotifications = _warningNotifications
		self.errorNotifications = _errorNotifications

	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		conexiones ocupados en el Host"""
		#self.receptionThread.stop()
		self.smtpServer.close()  # Cerramos la sesion con el servidor SMTP
		self.imapServer.logout() # Cerramos la sesion con el servidor IMAP
		print 'Objeto ' + self.__class__.__name__ + ' destruido.'
		#if (self.warningNotifications): print '[MODO EMAIL] Se terminó la sesión.'

	def connect(self):
		self.smtpServer.starttls()
		self.smtpServer.ehlo()
		self.smtpServer.login(contactList.EMAIL_SERVER, contactList.PASS_SERVER)            # Nos logueamos en el servidor SMTP
		self.imapServer.login(contactList.EMAIL_SERVER, contactList.PASS_SERVER)            # Nos logueamos en el servidor IMAP
		self.imapServer.select('INBOX')                                                     # Seleccionamos la Bandeja de Entrada
		
	def cleanMailBox(self):
		"""Se limpia el buzón de la cuenta de correo porque los correos anteriores no son importantes
		para el control."""
		try:
			self.imapServer.recent()				       # Actualizamos la Bandeja de Entrada
			result, emailIds = self.imapServer.search(None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
				# Ejemplo de emailIds: ['35 36 37']
		except Exception as e:					       # Timeout or something else
			if (self.errorNotifications): print '[MODO EMAIL] Error: en "recieve()" No hay conexion a Internet.'
			time.sleep(5)           # ... sigo esperando por alguno de los anteriores.
		emailIdsList = emailIds[0].split()
		emailAmount = len(emailIdsList) # Cantidad de emails no leidos
		for i in emailIdsList: 		# Recorremos los emails recibidos, se marcan como leidos
			result, emailData = self.imapServer.fetch(i, '(RFC822)')
			emailAmount -= 1 # Decrementamos la cantidad de emails no leidos
			if emailAmount == 0:
				break

	def receivePacket(self):
		""" Funcion que se encarga de consultar el correo electronico asociado al modulo
		por algun EMAIL entrante. Envia al servidor IMAP una peticion de solicitud
		de mensajes no leidos (que por ende seran los nuevos) y que en caso de obtenerlos,
		los almacenrá en el buffer, si el remitente del mensaje se encuentra registrado (en el 
		archivo 'contactList.py') o en caso contrario, se enviara una notificacion al usuario 
 		informandole que no es posible realizar la operacion solicitada."""
		while self.isActive:
			emailAmount = 0
			emailIds = ['']
			# Mientras no se haya recibido ningun correo electronico, el temporizador no haya expirado y no se haya detectado movimiento...
			while emailIds[0] == '' and self.isActive:
				try:
					self.imapServer.recent()				       # Actualizamos la Bandeja de Entrada
					result, emailIds = self.imapServer.search(None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
					# Ejemplo de emailIds: ['35 36 37']
				except Exception as e:					       # Timeout or something else
					print '[MODO EMAIL] Error: en "recieve()" No hay conexion a Internet.'
				time.sleep(5)           # ... sigo esperando por alguno de los anteriores.
			if(not self.isActive): break #Para no ejecutar instrucciones innecesarias si el modo email se detuvó.
			emailIdsList = emailIds[0].split()
			emailAmount = len(emailIdsList) # Cantidad de emails no leidos
			if (self.processNotifications): print '[MODO EMAIL] Ha(n) llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico.'
			for i in emailIdsList:	# Recorremos los emails recibidos...
				result, emailData = self.imapServer.fetch(i, '(RFC822)')
				rawEmail = emailData[0][1]
				if self.countRead == 0: 	   #Cambia el orden de la "matriz" para el segundo mensaje leido, despues de otra 
					rawEmail = emailData[0][1] #llamada a recent() para evitar desbordamiento de buffer
				else:
					rawEmail = emailData[1][1] 
				self.countRead = self.countRead + 1
				emailReceived = email.message_from_string(rawEmail) # Retorna un objeto 'message', y podemos acceder a los items de su cabecera como un diccionario.
				headerList = self.processEmailHeader(emailReceived) # Almacenamos una lista con los elementos del email recibido
				sourceName = headerList[0]                          # Almacenamos el nombre del remitente
				sourceEmail = headerList[1]                         # Almacenamos el correo del remitente
				emailSubject = headerList[2]                        # Almacenamos el asunto correspondiente
				if (self.processNotifications): print '[MODO EMAIL] Procesando correo electronico de ' + sourceName + ' - ' + sourceEmail
				# Comprobamos si el remitente del mensaje (un correo) esta registrado y tiene permiso de ejecucion...
				for key in contactList.allowedEmails:
					if(contactList.allowedEmails[key] == sourceEmail):
						emailBody = self.getDecodedEmailBody(emailReceived) # Obtenemos el cuerpo del email
						self.receptionBuffer.append(emailBody)
				allowedEmailsValues = contactList.allowedEmails.values()
				if(not(sourceEmail in allowedEmailsValues)):
					if (self.warningNotifications): print '[MODO EMAIL] Se recibió un email de una cuenta de correo no registrada... Se descarta el mensaje.'
					emailMessage = 'Imposible procesar la solicitud. Usted no se encuentra registrado.'
					self.sendEmail(sourceEmail, emailSubject, emailMessage)
				emailAmount -= 1 # Decrementamos la cantidad de emails no leidos
				if emailAmount == 0:
					break
		print '[EMAIL] Funcion \'%s\' terminada.' % inspect.stack()[0][3]
		#if (self.warningNotifications): print '[MODO EMAIL] Este modo ha dejado de esperar mensajes.'

	def sendEmailPacket(self, contact, message):
		if contactList.allowedEmails.has_key(contact):
			destination = contactList.allowedEmails[contact]
			emailInstance.sendEmail(destination, contact + ' - Proyecto Datalogger', message)
			#TODO que el asunto se configure en el archivo properties.conf
		else:
			if (self.warningNotifications): print '[MODO EMAIL] El contacto a enviar mensaje no esta configurado para Modo Email.'

	def sendEmail(self, emailDestination, emailSubject, emailMessage):
		""" Envia un mensaje de correo electronico.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """
		# Se construye un mensaje simple
		simpleMessage = MIMEText(emailMessage)
		simpleMessage['From'] = contactList.EMAIL_SERVER
		simpleMessage['To'] = emailDestination
		simpleMessage['Subject'] = emailSubject
		# Se envia el mensaje, al correo destino correspondiente
		self.smtpServer.sendmail(simpleMessage['From'], simpleMessage['To'], simpleMessage.as_string())

	def send(self, emailDestination, emailSubject, emailMessage):
		""" Envia un mensaje de correo electronico.
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param emailMessage: correo electronico a enviar
		@type emailMessage: str """
		#return False 
		# Se construye un mensaje simple
		simpleMessage = MIMEText(emailMessage)
		simpleMessage['From'] = contactList.EMAIL_SERVER
		simpleMessage['To'] = emailDestination
		simpleMessage['Subject'] = emailSubject
		# Se envia el mensaje, al correo destino correspondiente
		try:
			self.smtpServer.sendmail(simpleMessage['From'], simpleMessage['To'], simpleMessage.as_string())
			return True
		except Exception, e:
			return False

	def processEmailHeader(self, emailReceived):
		""" Procesa la cabecera del EMAIL.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: elementos de la cabecera (nombre del remitente, asunto y cuerpo del email)
		@rtype: list """
		headerList = list()
		#print 'emailReceived (processEmailHeader): ' 
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

	def getDecodedEmailBody(self, emailReceived):
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