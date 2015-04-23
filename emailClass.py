 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de correos electronicos.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import contactList

import time
import email
import socket
import smtplib
import imaplib

from email.header import decode_header
from email.header import make_header
from email.mime.text import MIMEText

class Email(object):

	processingResponseList = list()
	inBuffer = list()

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL
	isAvaible = False# Sobre si la conexión con email esta disponible
	contRead = 0

	def __init__(self):
		pass

	def __del__(self):
		#self.closeEmail()
		pass

	def initializeEmail(self):
		""" Configura el protocolo SMTP y el protocolo IMAP. El primero se encargara
		de enviar correos electronicos, mientras que el segungo a recibirlos.
		mbos disponen de una misma cuenta asociada a GMAIL para tales fines (y
		que esta dada en el archivo 'contactList.py'. """
		#print 'Configurando el modulo EMAIL...'
		self.smtpServer = smtplib.SMTP(contactList.SMTP_SERVER, contactList.SMTP_PORT)      # Establecemos servidor y puerto SMTP
		self.smtpServer.starttls()
		self.smtpServer.ehlo()
		self.smtpServer.login(contactList.EMAIL_SERVER, contactList.PASS_SERVER)            # Nos logueamos en el servidor SMTP
		self.imapServer = imaplib.IMAP4_SSL(contactList.IMAP_SERVER, contactList.IMAP_PORT) # Establecemos servidor y puerto IMAP
		self.imapServer.login(contactList.EMAIL_SERVER, contactList.PASS_SERVER)            # Nos logueamos en el servidor IMAP
		self.imapServer.select('INBOX')                                                     # Seleccionamos la Bandeja de Entrada
		socket.setdefaulttimeout(10)                                                   # Establecemos tiempo maximo antes de reintentar lectura
		print 'El modo EMAIL esta listo para usarse.'

	def closeEmail(self):
		""" Finaliza la sesion iniciada con ambos servidores, es decir, SMTP e IMAP
		respectivamente. """
		self.smtpServer.close()  # Cerramos la sesion con el servidor SMTP
		self.imapServer.logout() # Cerramos la sesion con el servidor IMAP

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

	def processEmailHeader(self, emailReceived):
		""" Procesa la cabecera del EMAIL.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: elementos de la cabecera (nombre del remitente, asunto y cuerpo del email)
		@rtype: list """
		headerList = list()
		#print 'emailReceived (processEmailHeader): ' 
		#print emailReceived
		senderInformation = self.getSource(emailReceived)
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		senderSubject = self.getSubject(emailReceived)
		# Ejemplo de senderSubject: Importante!
		senderInformationList = senderInformation.split(' <')
		#print senderInformationList
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
	#	print 'emailReceived (getSource): ' 
	#	print emailReceived
		h = decode_header(emailReceived.get('From'))
	#	print 'esto es h:'
	#	print h
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

	def verifyConnection(self):
		REMOTE_SERVER = "www.google.com"
		try:
			host = socket.gethostbyname(REMOTE_SERVER) # Obtiene el DNS
			s = socket.create_connection((host, 80), 2) # Se determina si es alcanzable
			return True
		except:
			print 'No hay conexión a inet?'
		return False

	def recieve(self):

		emailIds =''
		emailIdsList = list()
		emailAmount = 0
		emailData = list()

		try:
			self.imapServer.recent()				       # Actualizamos la Bandeja de Entrada
			result, emailIds = self.imapServer.search(None, '(UNSEEN)') # Buscamos emails sin leer (nuevos)
			# Ejemplo de emailIds: ['35 36 37']
		except Exception as e:					       # Timeout or something else
			print 'MODO EMAIL: No hay conexion a Internet?'
		
		emailIdsList = emailIds[0].split()
		emailAmount = len(emailIdsList) # Cantidad de emails no leidos

		#print 'MODO EMAIL: Han llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico.'
		if emailAmount == 0:
			return None
		i = emailIdsList[0]
		result, emailData = self.imapServer.fetch(i, '(RFC822)')
		if self.contRead == 0:
			rawEmail = emailData[0][1]
		else:
			rawEmail = emailData[1][1] #Cambia el orden de la "matriz" para el segundo mensaje leido, despues de otra llamada a recent()
		emailReceived = email.message_from_string(rawEmail)
		# message_from_string() devuelve un objeto 'message', y podemos acceder a los items de su cabecera como...
		# ... si fuese un diccionario.
		self.contRead = self.contRead + 1
		headerList = self.processEmailHeader(emailReceived) # Almacenamos una lista con los elementos del email recibido
		sourceName = headerList[0]                     # Almacenamos el nombre del remitente
		sourceEmail = headerList[1]                    # Almacenamos el correo del remitente
		emailSubject = headerList[2]                   # Almacenamos el asunto correspondiente
		#print 'Procesando correo electronico de ' + sourceName + ' - ' + sourceEmail
		# Comprobamos si el remitente del mensaje (un correo) esta registrado y tiene permiso de ejecucion...
		for key in contactList.allowedEmails:
			if(contactList.allowedEmails[key] == sourceEmail):
				emailBody = self.getDecodedEmailBody(emailReceived) # Obtenemos el cuerpo del email
				return emailBody
		allowedEmailsValues = contactList.allowedEmails.values()
		if(not(sourceEmail in allowedEmailsValues)):
			print 'Se recibió un email de una cuenta de correo no registrada... Se descarta el mensaje.'
			emailMessage = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
			self.sendEmail(sourceEmail, emailSubject, emailMessage)
			return self.recieve()
