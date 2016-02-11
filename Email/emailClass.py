 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de emails a través de una conexión a internet.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import os
import json
import copy
import shlex
import email
import Queue
import pickle
import socket
import inspect
import smtplib
import imaplib
import mimetypes
import subprocess

from email import encoders
from email.header import decode_header
from email.header import make_header

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage

import logger
import contactList
import messageClass

TIMEOUT = 5
ATTACHMENTS = 'Attachments'

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Email(object):

	smtpServer = smtplib.SMTP
	imapServer = imaplib.IMAP4_SSL

	receptionBuffer = Queue.PriorityQueue()
	successfulConnection = None
	emailAccount = None
	isActive = False

	def __init__(self, _receptionBuffer):
		""" Configura el protocolo SMTP y el protocolo IMAP. El primero se encargara
		de enviar correos electronicos, mientras que el segungo a recibirlos.
		mbos disponen de una misma cuenta asociada a GMAIL para tales fines (y
		que esta dada en el archivo 'contactList.py'. 
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		self.receptionBuffer = _receptionBuffer
		# Establecemos tiempo maximo antes de reintentar lectura (válido para 'imapServer')
		socket.setdefaulttimeout(TIMEOUT)

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
			smtpHost = JSON_CONFIG["EMAIL"]["SMTP_SERVER"]
			smtpPort = JSON_CONFIG["EMAIL"]["SMTP_PORT"]
			imapHost = JSON_CONFIG["EMAIL"]["IMAP_SERVER"]
			imapPort = JSON_CONFIG["EMAIL"]["IMAP_PORT"]
			emailPassword = JSON_CONFIG["EMAIL"]["PASSWORD"]
			self.emailAccount = JSON_CONFIG["EMAIL"]["ACCOUNT"]
			# El 'timeout' siguiente es para la función 'sendmail' de 'smtpServer'
			self.smtpServer = smtplib.SMTP(smtpHost, smtpPort, timeout = 30) # Establecemos servidor y puerto SMTP
			self.imapServer = imaplib.IMAP4_SSL(imapHost, imapPort)          # Establecemos servidor y puerto IMAP
			self.smtpServer.starttls()
			self.smtpServer.ehlo()
			self.smtpServer.login(self.emailAccount, emailPassword) # Nos logueamos en el servidor SMTP
			self.imapServer.login(self.emailAccount, emailPassword) # Nos logueamos en el servidor IMAP
			self.imapServer.select('INBOX')                         # Seleccionamos la Bandeja de Entrada
			self.successfulConnection = True
			return True
		# Error con los servidores (probablemente estén mal escritos o los puertos son incorrectos)
		except Exception as errorMessage:
			logger.write('ERROR', '[EMAIL] Error al intentar conectar con los servidores SMTP e IMAP!')
			self.successfulConnection = False
			return False

	def send(self, message, emailDestination):
		""" Envia un mensaje de correo electronico. Debe determinar el tipo de mensaje
		para determinar si enviar o no un archivo adjunto.
		@param message: correo electronico a enviar
		@type message: str
		@param emailDestination: correo electronico del destinatario
		@type emailDestination: str """
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.SimpleMessage) and not message.isInstance:
			return self.sendMessage(message.plainText, emailDestination)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.FileMessage) and not message.isInstance:
			return self.sendAttachment(message.fileName, emailDestination)
		# Entonces se trata de enviar una instancia de mensaje
		else:
			# Copiamos el objeto antes de borrar el campo 'isInstance', por un posible fallo de envío
			tmpMessage = copy.copy(message)
			# Eliminamos el último campo del objeto, ya que el receptor no lo necesita
			delattr(tmpMessage, 'isInstance')
			# Serializamos el objeto para poder transmitirlo
			messageSerialized = 'INSTANCE' + pickle.dumps(tmpMessage)
			if isinstance(message, messageClass.SimpleMessage):
				return self.sendMessage(messageSerialized, emailDestination)
			elif isinstance(message, messageClass.FileMessage):
				return self.sendAttachment(message.fileName, emailDestination, messageSerialized)

	def sendMessage(self, plainText, emailDestination):
		try:
			# Se construye un mensaje simple
			mimeText = MIMEText(plainText)
			mimeText['From'] = '%s <%s>' % (JSON_CONFIG["COMMUNICATOR"]["NAME"], JSON_CONFIG["EMAIL"]["ACCOUNT"])
			mimeText['To'] = emailDestination
			mimeText['Subject'] = JSON_CONFIG["EMAIL"]["SUBJECT"]
			self.smtpServer.sendmail(mimeText['From'], mimeText['To'], mimeText.as_string())
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'' % emailDestination)
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[EMAIL] Mensaje no enviado: %s' % str(errorMessage))
			return False

	def sendAttachment(self, fileName, emailDestination, messageToSend = 'Este email tiene un archivo adjunto.'):
		try:
			absoluteFilePath = os.path.abspath(fileName)
			fileDirectory, fileName = os.path.split(absoluteFilePath)
			cType = mimetypes.guess_type(absoluteFilePath)[0]
			mainType, subType = cType.split('/', 1)
			mimeMultipart = MIMEMultipart()
			mimeMultipart['Subject'] = JSON_CONFIG["EMAIL"]["SUBJECT"]
			mimeMultipart['From'] = '%s <%s>' % (JSON_CONFIG["COMMUNICATOR"]["NAME"], JSON_CONFIG["EMAIL"]["ACCOUNT"])
			mimeMultipart['To'] = emailDestination
			if mainType == 'text':
				fileObject = open(absoluteFilePath)
				# Note: we should handle calculating the charset
				attachmentFile = MIMEText(fileObject.read(), _subtype = subType)
				fileObject.close()
			elif mainType == 'image':
				fileObject = open(absoluteFilePath, 'rb')
				attachmentFile = MIMEImage(fileObject.read(), _subtype = subType)
				fileObject.close()
			elif mainType == 'audio':
				fileObject = open(absoluteFilePath, 'rb')
				attachmentFile = MIMEAudio(fileObject.read(), _subtype = subType)
				fileObject.close()
			else:
				fileObject = open(absoluteFilePath, 'rb')
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
			logger.write('INFO', '[EMAIL] Archivo \'%s\' enviado correctamente!' % fileName)
			return True
		except Exception as errorMessage:
			logger.write('WARNING', '[EMAIL] Archivo \'%s\' no enviado: %s' % (fileName, str(errorMessage)))
			return False

	def receive(self):
		""" Funcion que se encarga de consultar el correo electronico asociado al modulo
		por algun EMAIL entrante. Envia al servidor IMAP una peticion de solicitud
		de mensajes no leidos (que por ende seran los nuevos) y que en caso de obtenerlos,
		los almacenrá en el buffer, si el remitente del mensaje se encuentra registrado (en el 
		archivo 'contactList.py') o en caso contrario, se enviara una notificacion al usuario 
 		informandole que no es posible realizar la operacion solicitada."""
 		self.isActive = True
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
					logger.write('DEBUG', '[EMAIL] Procesando correo de \'%s\'' % sourceEmail)
					# Comprobamos si el remitente del mensaje (un correo) está registrado...
					if sourceEmail in contactList.allowedEmails.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
						for emailHeader in emailReceived.walk():
							if emailHeader.get('Content-Disposition') is not None:
								self.receiveAttachment(emailHeader)
						emailBody = self.getEmailBody(emailReceived) # Obtenemos el cuerpo del email
						if emailBody is not None:
							#self.sendOutput(sourceEmail, emailSubject, emailBody) # -----> SOLO PARA LA DEMO <-----
							if emailBody.startswith('INSTANCE'):
								messageInstance = emailBody[len('INSTANCE'):]
								messageInstance = pickle.loads(messageInstance)
								self.receptionBuffer.put((100 - messageInstance.priority, messageInstance))
								logger.write('INFO', '[EMAIL] Instancia de mensaje recibida correctamente!')
							else:
								emailBody = emailBody[:emailBody.rfind('\r\n')] # Elimina el salto de línea del final
								self.receptionBuffer.put((10, emailBody))
								logger.write('INFO', '[EMAIL] Mensaje de texto plano recibido correctamente!')
					else:
						logger.write('WARNING', '[EMAIL] Imposible procesar la solicitud. El correo no se encuentra registrado!')
						messageToSend = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
						self.sendMessage(messageToSend, sourceEmail)
			# ... sino, dejamos de esperar mensajes
			else:
				break
		logger.write('WARNING', '[EMAIL] Función \'%s\' terminada.' % inspect.stack()[0][3])

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
			logger.write('INFO', '[EMAIL] Archivo adjunto \'%s\' descargado correctamente!' % fileName)
			return True
		else:
			logger.write('WARNING', '[EMAIL] El archivo \'%s\' ya existe! Imposible descargar.' % fileName)
			return False

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
		sourceEmail = None
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
			# Enviamos la respuesta del SO al remitente
			self.sendMessage(emailBody, sourceEmail)
