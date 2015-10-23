 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de emails a través de una conexión a internet.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import logger
import contactList
import messageClass

import os
import time
import shlex
import Queue
import email
import pickle
import socket
import inspect
import smtplib
import imaplib
import threading
import mimetypes
import subprocess
import json

from email import encoders
from email.header import decode_header
from email.header import make_header

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage

TIMEOUT = 5
ATTACHMENTS = 'attachments'

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Email(object):

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL

	receptionBuffer = Queue.Queue()
	isActive = False

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
		try:
			self.smtpServer.quit()   # Terminamos la sesión SMTP y cerramos la conexión
			self.smtpServer.close()  # Cerramos el buzón seleccionado actualmente
			self.imapServer.logout() # Cerramos la conexión IMAP
		except:
			pass
		finally:
			logger.write('INFO','[EMAIL] Objeto destruido.' )

	def connect(self):
		try:
			self.smtpServer = smtplib.SMTP(JSON_CONFIG["EMAIL"]["SMTP_SERVER"], JSON_CONFIG["EMAIL"]["SMTP_PORT"])      # Establecemos servidor y puerto SMTP
			self.imapServer = imaplib.IMAP4_SSL(JSON_CONFIG["EMAIL"]["IMAP_SERVER"], JSON_CONFIG["EMAIL"]["IMAP_PORT"]) # Establecemos servidor y puerto IMAP
			self.smtpServer.starttls()
			self.smtpServer.ehlo()
			self.smtpServer.login(JSON_CONFIG["EMAIL"]["ACCOUNT"], JSON_CONFIG["EMAIL"]["PASSWORD"]) # Nos logueamos en el servidor SMTP
			self.imapServer.login(JSON_CONFIG["EMAIL"]["ACCOUNT"], JSON_CONFIG["EMAIL"]["PASSWORD"])            # Nos logueamos en el servidor IMAP
			self.imapServer.select('INBOX') # Seleccionamos la Bandeja de Entrada
		except socket.error as emailError:
			logger.write('ERROR','[EMAIL] %s.' % emailError)

	def send(self, emailDestination, emailSubject, message):
		""" Envia un mensaje de correo electronico. Debe determinar el tipo de mensaje
		para determinar si enviar o no un archivo adjunto
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str
		@param emailSubject: asunto del mensaje
		@type emailSubject: str
		@param message: correo electronico a enviar
		@type message: str """
		if isinstance(message, messageClass.FileMessage) and message.sendInstance:
			del message.sendInstance  # Se elimina el campo auxiliar, no es info útil
			emailMessage = 'START_OF_FILE_INSTANCE ' + pickle.dumps(message)
			message.sendInstance = True
			return self.sendAttachment(emailDestination, message.fileName, emailMessage) 
		elif isinstance(message, messageClass.FileMessage) and not message.sendInstance:
			return self.sendAttachment(emailDestination, message.fileName, 'START_OF_FILE ' + message.fileName)
		elif isinstance(message, messageClass.Message) and message.sendInstance:
			del message.sendInstance  # Se elimina el campo auxiliar, no es info útil
			emailMessage = 'START_OF_MESSAGE_INSTANCE ' + pickle.dumps(message)
			message.sendInstance = True
			return self.sendText(emailDestination, emailSubject, emailMessage) 
		else: #isinstance(message, messageClass.Message) and not message.sendInstance:
			emailMessage = message.textMessage 
			return self.sendText(emailDestination, emailSubject, emailMessage) 

	def sendText(self, emailDestination, emailSubject, message):
		try:
			# Se construye un mensaje simple
			mimeText = MIMEText(message)
			mimeText['From'] = '%s <%s>' % (JSON_CONFIG["EMAIL"]["NAME"], JSON_CONFIG["EMAIL"]["ACCOUNT"])
			mimeText['To'] = emailDestination
			mimeText['Subject'] = emailSubject
			self.smtpServer.sendmail(mimeText['From'], mimeText['To'], mimeText.as_string())
			logger.write('INFO', '[EMAIL] Mensaje enviado correctamente a ' + emailDestination)
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[EMAIL] Mensaje no enviado, error: ' + str(errorMessage))
			return False

	def sendAttachment(self, emailDestination, fileToSend, messageToSend = 'Este email tiene un archivo adjunto.'):
		relativePath = fileToSend
		absolutePath = os.path.abspath(relativePath)
		if os.path.isfile(absolutePath):
			try:
				fileDirectory, fileName = os.path.split(absolutePath)
				cType = mimetypes.guess_type(absolutePath)[0]
				mainType, subType = cType.split('/', 1)
				mimeMultipart = MIMEMultipart()
				mimeMultipart['Subject'] = 'Contenido de %s' % fileDirectory
				mimeMultipart['From'] = '%s <%s>' % (JSON_CONFIG["EMAIL"]["NAME"], JSON_CONFIG["EMAIL"]["ACCOUNT"])
				mimeMultipart['To'] = emailDestination
				if mainType == 'text':
					fileObject = open(absolutePath)
					# Note: we should handle calculating the charset
					attachmentFile = MIMEText(fileObject.read(), _subtype = subType)
					fileObject.close()
				elif mainType == 'image':
					fileObject = open(absolutePath, 'rb')
					attachmentFile = MIMEImage(fileObject.read(), _subtype = subType)
					fileObject.close()
				elif mainType == 'audio':
					fileObject = open(absolutePath, 'rb')
					attachmentFile = MIMEAudio(fileObject.read(), _subtype = subType)
					fileObject.close()
				else:
					fileObject = open(absolutePath, 'rb')
					attachmentFile = MIMEBase(mainType, subType)
					attachmentFile.set_payload(fileObject.read())
					fileObject.close()
					# Codificamos el payload (carga útil) usando Base64
					encoders.encode_base64(attachmentFile)
				# Agregamos una cabecera al email, de nombre 'Content-Disposition' y valor 'attachment' ('filename' es el parámetro)
				attachmentFile.add_header('Content-Disposition', 'attachment', filename = fileName)
				mimeText = MIMEText(messageToSend, _subtype = 'plain')
				mimeMultipart.attach(attachmentFile)
				mimeMultipart.attach(mimeText)
				self.smtpServer.sendmail(mimeMultipart['From'], mimeMultipart['To'], mimeMultipart.as_string())
				logger.write('INFO', '[EMAIL] Archivo ('+ fileName + ') enviado correctamente a ' + emailDestination)
				return True
			except Exception as errorMessage:
				logger.write('WARNING', '[EMAIL] Archivo no enviado, error: ' + str(errorMessage))
				return False
		else:
			print 'El archivo no existe!' # TODO borrar
			return False

	def receiveAttachment(self, emailHeader):
		currentDirectory = os.getcwd()                                   # Obtenemos el directorio actual de trabajo
		fileName = emailHeader.get_filename()                            # Obtenemos el nombre del archivo adjunto
		filePath = os.path.join(currentDirectory, ATTACHMENTS, fileName) # Obtenemos el path relativo del archivo a descargar
		# Verificamos si el directorio 'ATTACHMENTS' no está creado en el directorio actual
		if ATTACHMENTS not in os.listdir(currentDirectory):
			os.mkdir(ATTACHMENTS)
		# Verificamos si el archivo a descargar no existe en la carpeta 'ATTACHMENTS'
		if not os.path.isfile(filePath):
			fileObject = open(filePath, 'w+')
			fileObject.write(emailHeader.get_payload(decode = True))
			fileObject.close()
			logger.write('INFO', '[EMAIL] Archivo adjunto \'%s\' descargado.' % fileName)
		else:
			logger.write('WARNING', '[EMAIL] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)

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
			# Si no se terminó la función (el modo EMAIL no dejó de funcionar), leemos los mensajes recibidos...
			if self.isActive:
				emailIdsList = emailIds[0].split()
				emailAmount = len(emailIdsList) # Cantidad de emails no leidos
				logger.write('DEBUG', '[EMAIL] Ha(n) llegado ' + str(emailAmount) + ' nuevo(s) mensaje(s) de correo electronico!')
				# Recorremos los emails recibidos...
				for i in emailIdsList:
					result, emailData = self.imapServer.uid('fetch', i, '(RFC822)')
					# Retorna un objeto 'message', y podemos acceder a los items de su cabecera como un diccionario.
					emailReceived = email.message_from_string(emailData[0][1])
					sourceName = self.getSourceName(emailReceived)     # Almacenamos el nombre del remitente
					sourceEmail = self.getSourceEmail(emailReceived)   # Almacenamos el correo del remitente
					emailSubject = self.getEmailSubject(emailReceived) # Almacenamos el asunto correspondiente
					logger.write('DEBUG', '[EMAIL] Procesando correo de ' + sourceName + ' - ' + sourceEmail)
					# Comprobamos si el remitente del mensaje (un correo) esta registrado...
					#self.sendOutput(sourceEmail, emailSubject, emailBody) # -----> SOLO PARA LA DEMO <-----
					if sourceEmail in contactList.allowedEmails.values():
						for emailHeader in emailReceived.walk():
							if emailHeader.get('Content-Disposition') is not None:
								self.receiveAttachment(emailHeader)
						emailBody = self.getEmailBody(emailReceived) # Obtenemos el cuerpo del email
						#self.sendOutput(sourceEmail, emailSubject, emailBody) # -----> SOLO PARA LA DEMO <-----
						if emailBody.startswith('START_OF_FILE_INSTANCE '):
							emailBody = emailBody[len('START_OF_FILE_INSTANCE '):]
							message = pickle.loads(emailBody)
							self.receptionBuffer.put((100 - message.priority, message))	
						elif emailBody.startswith('START_OF_FILE '):
							emailBody = emailBody[len('START_OF_FILE '):]
							self.receptionBuffer.put((100 - JSON_CONFIG["COMMUNICATOR"]["FILE_PRIORITY"], 'ARCHIVO_RECIBIDO: ' + emailBody))
						elif emailBody.startswith('START_OF_MESSAGE_INSTANCE '):
							emailBody = emailBody[len('START_OF_MESSAGE_INSTANCE '):]
							message = pickle.loads(emailBody)
							self.receptionBuffer.put((100 - message.priority, message))	
						elif emailBody != None:
							emailBody = emailBody[:emailBody.rfind('\r\n')] # Elimina el salto de línea del final
							self.receptionBuffer.put((100 - JSON_CONFIG["COMMUNICATOR"]["MESSAGE_PRIORITY"], emailBody))
					else:
						logger.write('WARNING', '[EMAIL] Imposible procesar la solicitud. El correo no se encuentra registrado!')
						messageToSend = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
						self.sendText(sourceEmail, emailSubject, messageToSend)
			# ... sino, dejamos de esperar mensajes
			else:
				break
		logger.write('WARNING', '[EMAIL] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def getSourceName(self, emailReceived):
		sourceNameList = list()
		decodedHeader = decode_header(emailReceived.get('From'))
		senderInformation = unicode(make_header(decodedHeader)).encode('utf-8')
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		for senderElement in senderInformation.split():
			if not senderElement.startswith('<') and not senderElement.endswith('>'):
				sourceNameList.append(senderElement)
		# Ejemplo de sourceNameList: ['Mauricio', 'Gonzalez']
		sourceName = ' '.join(sourceNameList)
		# Ejemplo de sourceName: Mauricio Gonzalez
		return sourceName

	def getSourceEmail(self, emailReceived):
		sourceEmail = ''
		decodedHeader = decode_header(emailReceived.get('From'))
		senderInformation = unicode(make_header(decodedHeader)).encode('utf-8')
		# Ejemplo de senderInformation: Mauricio Gonzalez <mauriciolg.90@gmail.com>
		for senderElement in senderInformation.split():
			if senderElement.startswith('<') and senderElement.endswith('>'):
				sourceEmail = senderElement.replace('<', '').replace('>', '')
		# Ejemplo sourceEmail: mauriciolg.90@gmail.com
		return sourceEmail
		
	def getEmailSubject(self, emailReceived):
		""" Obtiene el asunto del correo entrante.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: asunto del correo entrante
		@rtype: str """
		decodedHeader = decode_header(emailReceived.get('subject'))
		return unicode(make_header(decodedHeader)).encode('utf-8')

	def getEmailBody(self, emailReceived):
		""" Decodifica el cuerpo del email. Detecta el conjunto de caracteres si la cabecera no esta
		configurada. Primero se busca texto plano si no esta, se busca texto/html.
		@param emailReceived: correo electronico entrante
		@type emailReceived: message
		@return: cuerpo del mensaje como string unicode
		@rtype: str """
		plainText = None
		for emailHeader in emailReceived.walk():
			if emailHeader.get_content_type() == 'text/plain':
				plainText = emailHeader.get_payload()
				# Se debe convertir texto de DOS(windows) a UNIX (LINUX) porque 
				# de la forma que lo devulve email, da errores en pickle
				plainText = plainText.replace('\r\n', '\n')
				break
		# Si el cuerpo del email no está vacío, retornamos el texto plano
		if plainText:
			return plainText
		else:
			return None

	def deleteEmail(self, emailId):
		self.imapServer.copy(emailId, '[Gmail]/Trash')
		self.imapServer.store(emailId, '+FLAGS', r'(\Deleted)')
		self.imapServer.expunge()

	def sendOutput(self, sourceEmail, emailSubject, emailBody):
		try:
			unixProcess = subprocess.Popen(shlex.split(emailBody), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			unixOutput, unixError = unixProcess.communicate()
			if len(unixOutput) > 0:
				emailBody = unixOutput[:unixOutput.rfind('\n')] # Quita la ultima linea en blanco
			else:
				emailBody = unixError[:unixError.rfind('\n')] # Quita la ultima linea en blanco
		except OSError as e: # El comando no fue encontrado (el ejecutable no existe)
			emailBody = str(e)
		finally:
			self.sendText(sourceEmail, emailSubject, emailBody)
