# coding=utf-8

import json
import time
import shlex
import serial
import pickle
import inspect
import subprocess

import logger
import contactList
import messageClass

from curses import ascii # Para enviar el Ctrl-Z

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Modem(object):

	successfulConnection = None
	receptionQueue = None
	serialPort = None

	def __init__(self):
		self.modemInstance = serial.Serial()
		self.modemInstance.xonxoff = False # Deshabilitamos el control de flujo por software
		self.modemInstance.rtscts = False  # Deshabilitamos el control de flujo por hardware RTS/CTS
		self.modemInstance.dsrdtr = False  # Deshabilitamos el control de flujo por hardware DSR/DTR
		self.modemInstance.bytesize = serial.EIGHTBITS
		self.modemInstance.parity = serial.PARITY_NONE
		self.modemInstance.stopbits = serial.STOPBITS_ONE
		self.modemInstance.timeout = JSON_CONFIG["MODEM"]["TIME_OUT"]
		self.modemInstance.baudrate = JSON_CONFIG["MODEM"]["BAUD_RATE"]

	def sendAT(self, atCommand):
		self.modemInstance.write(atCommand + '\r')	 # Envio el comando AT al modem
		modemOutput = self.modemInstance.readlines() # Espero la respuesta
		# El módem devuelve una respuesta ante el comando AT
		if len(modemOutput) > 0 and atCommand.startswith('AT'):
			# Verificamos si se produjo algún tipo de error relacionado con el comando AT
			for outputElement in modemOutput:
				# El 'AT+CNMA' sólo es soportado en Dongles USB que requieren confirmación de SMS
				if outputElement.startswith(('ERROR', '+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
					errorMessage = outputElement.replace('\r\n', '')
					logger.write('ERROR', '[GSM] %s - %s.' % (atCommand, errorMessage))
					raise
				# El comando AT para llamadas de voz (caracterizado por su terminacion en ';') no es soportado
				elif outputElement.startswith('NO CARRIER') and atCommand.startswith('ATD') and atCommand.endswith(';'):
					raise
		# Esto ocurre cuando el puerto 'ttyUSBx' no es un módem
		elif len(modemOutput) is 0:
			raise
		# Si la respuesta al comando AT no era un mensaje de error, retornamos la salida
		return modemOutput

	def closePort(self):
		self.modemInstance.close()

class Gsm(Modem):

	successfulSending = None
	isActive = False

	def __init__(self, _receptionQueue):
		Modem.__init__(self)
		self.receptionQueue = _receptionQueue

	def __del__(self):
		self.modemInstance.close()
		logger.write('INFO', '[GSM] Objeto destruido.')

	def connect(self, _serialPort):
		self.serialPort = _serialPort
		try:
			self.modemInstance.port = _serialPort
			self.modemInstance.open()
			time.sleep(1.5)
			self.sendAT('ATZ')				 # Enviamos un reset
			self.sendAT('ATE1')				 # Habilitamos el echo
			self.sendAT('AT+CMEE=2')		 # Habilitamos reporte de error
			self.sendAT('AT+CMGF=1')		 # Establecemos el modo para SMS
			self.sendAT('AT+CLIP=1')		 # Habilitamos identificador de llamadas
			self.sendAT('AT+CNMI=1,2,0,0,0') # Habilitamos notificacion de mensaje entrante
			self.successfulConnection = True
			return True
		except:
			self.successfulConnection = False
			return False

	def receive(self):
		try:
			smsAmount = 0
			smsBodyList = list()
			smsHeaderList = list()
			unreadList = self.sendAT('AT+CMGL="REC UNREAD"')
		except:
			pass
		# Ejemplo de unreadList[0]: AT+CMGL="REC UNREAD"\r\r\n
		# Ejemplo de unreadList[1]: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
		# Ejemplo de unreadList[2]: Primer mensaje.\r\n
		# Ejemplo de unreadList[3]: +CMGL: 1,"REC UNREAD","+5493512560536",,"14/10/26,17:15:10-12"\r\n
		# Ejemplo de unreadList[4]: Segundo mensaje.\r\n
		# Ejemplo de unreadList[5]: \r\n
		# Ejemplo de unreadList[6]: OK\r\n
		for unreadIndex, unreadData in enumerate(unreadList):
			if unreadData.startswith('+CMGL'):
				smsHeaderList.append(unreadList[unreadIndex])
				smsBodyList.append(unreadList[unreadIndex + 1])
				smsAmount += 1
			elif unreadData.startswith('OK'):
				break
		# Ejemplo de smsHeaderList[0]: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
		# Ejemplo de smsBodyList[0]  : Primer mensaje.\r\n
		# Ejemplo de smsHeaderList[1]: +CMGL: 1,"REC UNREAD","+5493512560536",,"14/10/26,17:15:10-12"\r\n
		# Ejemplo de smsBodyList[1]  : Segundo mensaje.\r\n
		self.isActive = True
		while self.isActive:
			# Leemos los mensajes de texto recibidos...
			if smsAmount is not 0:
				logger.write('DEBUG', '[SMS] Ha(n) llegado ' + str(smsAmount) + ' nuevo(s) mensaje(s) de texto!')
				for smsHeader, smsBody in zip(smsHeaderList, smsBodyList):
					# Ejemplo smsHeader: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
					# Ejemplo smsBody  : Primer mensaje.\r\n
					# Ejemplo smsHeader: +CMT: "+543512641040",,"15/12/29,11:19:38-12"\r\n
					# Ejemplo smsBody  : Nuevo SMS.\r\n
					telephoneNumber = self.getTelephoneNumber(smsHeader) # Obtenemos el numero de telefono
					# Comprobamos si el remitente del mensaje (un teléfono) está registrado...
					if telephoneNumber in contactList.allowedNumbers.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
						# Quitamos el '\r\n' del final y obtenemos el mensaje de texto
						smsMessage = smsBody.replace('\r\n', '')
						if smsMessage.startswith('INSTANCE'):
							# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
							serializedMessage = smsMessage[len('INSTANCE'):]
							# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
							messageInstance = pickle.loads(serializedMessage)
							self.receptionQueue.put((messageInstance.priority, messageInstance))
						else: 
							self.receptionQueue.put((10, smsMessage))
						#self.sendOutput(telephoneNumber, smsMessage) # -----> SOLO PARA LA DEMO <-----
						logger.write('INFO', '[GSM] Mensaje de ' + str(telephoneNumber) + ' recibido correctamente!')
					# ... sino, rechazamos el mensaje entrante.
					else:
						logger.write('WARNING', '[GSM] Mensaje de ' + str(telephoneNumber) + 'rechazado!')
					# Si el mensaje fue leído desde la memoria, entonces lo borramos
					if smsHeader.startswith('+CMGL'):
						# Obtenemos el índice del mensaje en memoria
						smsIndex = self.getSmsIndex(smsHeader.split(',')[0])
						# Eliminamos el mensaje desde la memoria porque ya fue leído
						self.removeSms(smsIndex)
					# Eliminamos la cabecera y el cuerpo del mensaje de las listas correspondientes
					smsHeaderList.remove(smsHeader)
					smsBodyList.remove(smsBody)
					# Decrementamos la cantidad de mensajes a procesar
					smsAmount -= 1
			elif self.modemInstance.inWaiting() is not 0:
				bytesToRead = self.modemInstance.inWaiting()
				receptionList = self.modemInstance.read(bytesToRead).split('\r\n')
				# Ejemplo receptionList: ['+CMT: "+543512641040","","16/01/31,05:00:08-12"', 'Nuevo SMS.']
				# Ejemplo receptionList: ['RING', '', '+CLIP: "+543512641040",145,"",0,"",0']
				# Ejemplo receptionList: ['+CMS ERROR: Requested facility not subscribed']
				# Ejemplo receptionList: ['NO CARRIER']
				for index, data in enumerate(receptionList):
					# Significa un mensaje entrante
					if receptionList[index].startswith('+CMT'):
						try:
							smsHeaderList.append(receptionList[index])
							smsBodyList.append(receptionList[index + 1])
							self.sendAT('AT+CNMA') # Enviamos el ACK (ńecesario sólo para los Dongle USB)
						except:
							pass # La excepción aparece cuando el módem no soporta (no necesita) el ACK
						finally:
							smsAmount += 1
					# Significa que no se pudo enviar el mensaje
					elif receptionList[index].startswith('+CMS ERROR'):
						self.successfulSending = False
					############################### LLAMADAS DE VOZ ###############################
					# Significa una llamade entrante
					elif receptionList[index].startswith('RING'):
						self.callerID = self.getTelephoneNumber(receptionList[index + 2])
						logger.write('INFO', '[GSM] El número %s está llamando...' % self.callerID)
					# Significa que el destino se encuentra en otra llamada
					elif receptionList[index].startswith('BUSY'):
						logger.write('WARNING', '[GSM] El télefono destino se encuentra ocupado.')
					# Significa que la llamada saliente pasó al buzón de voz
					elif receptionList[index].startswith('NO ANSWER'):
						logger.write('WARNING', '[GSM] No hubo respuesta durante la llamada de voz.')
					# Significa que la llamada entrante se perdió (llamada perdida) o que el extremo colgo
					elif receptionList[index].startswith('NO CARRIER'):
						self.callerID = None
						logger.write('WARNING', '[GSM] Se perdió la conexión con el otro extremo.')
					############################# FIN LLAMADAS DE VOZ #############################
			else:
				time.sleep(1)
		logger.write('WARNING', '[GSM] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def send(self, message, telephoneNumber):
		# Comprobación de envío de texto plano
		if isinstance(message, messageClass.Message) and hasattr(message, 'plainText'):
			return self.sendMessage(message.plainText, telephoneNumber)
		# Comprobación de envío de archivo
		elif isinstance(message, messageClass.Message) and hasattr(message, 'fileName'):
			logger.write('ERROR', '[GSM] Imposible enviar \'%s\' por este medio!' % message.fileName)
			return False
		# Entonces se trata de enviar una instancia de mensaje
		else:
			return self.sendMessageInstance(message, telephoneNumber)

	def sendMessage(self, plainText, telephoneNumber):
		try:
			#############################
			timeCounter = 0
			self.successfulSending = None
			#############################
			# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
			info01 = self.sendAT('AT+CMGS="' + str(telephoneNumber) + '"') # Numero al cual enviar el SMS
			info02 = self.sendAT(plainText + ascii.ctrl('z'))              # Mensaje de texto terminado en Ctrl+z
			# ------------------ Caso de envío EXITOSO ------------------
			# Ejemplo de info02[0]: Mensaje enviado desde el Modem.\x1a\r\n
			# Ejemplo de info02[1]: +CMGS: 17\r\n
			# Ejemplo de info02[3]: OK\r\n
			# Comprobamos si el envío fue exitoso
			for i in info02:
				if i.startswith('OK'):
					self.successfulSending = True
					break
				elif i.startswith('+CMS ERROR'):
					self.successfulSending = False
					break
			# Esperamos respuesta de la red si es que no la hubo
			while self.successfulSending is None and timeCounter < 15:
				time.sleep(1)
				timeCounter += 1
			# Comprobamos si hubo respuesta de la red y cual fue..
			if self.successfulSending is True:
				logger.write('INFO', '[GSM] Mensaje de texto enviado a %s.' % str(telephoneNumber))
				# Borramos el mensaje enviado almacenado en la memoria
				self.removeAllSms()
				return True
			else:
				logger.write('WARNING', '[GSM] No se pudo enviar el mensaje a %s.' % str(telephoneNumber))
				return False
		except:
			logger.write('ERROR', '[GSM] Error al enviar el mensaje de texto a %s.' % str(telephoneNumber))
			return False

	def sendMessageInstance(self, message, telephoneNumber):
		try:
			#############################
			timeCounter = 0
			self.successfulSending = None
			#############################
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
			info01 = self.sendAT('AT+CMGS="' + str(telephoneNumber) + '"') # Numero al cual enviar el SMS
			info02 = self.sendAT(serializedMessage + ascii.ctrl('z'))      # Mensaje de texto terminado en Ctrl+Z
			# ------------------ Caso de envío EXITOSO ------------------
			# Ejemplo de info02[0]: Mensaje enviado desde el Modem.\x1a\r\n
			# Ejemplo de info02[1]: +CMGS: 17\r\n
			# Ejemplo de info02[3]: OK\r\n
			# Comprobamos si el envío fue exitoso
			for i in info02:
				if i.startswith('OK'):
					self.successfulSending = True
					break
				elif i.startswith('+CMS ERROR'):
					self.successfulSending = False
					break
			# Esperamos respuesta de la red si es que no la hubo
			while self.successfulSending is None and timeCounter < 15:
				time.sleep(1)
				timeCounter += 1
			# Comprobamos si hubo respuesta de la red y cual fue..
			if self.successfulSending is True:
				logger.write('INFO', '[GSM] Instancia de mensaje enviada a %s.' % str(telephoneNumber))
				# Borramos el mensaje enviado almacenado en la memoria
				self.removeAllSms()
				return True
			else:
				logger.write('WARNING', '[GSM] No se pudo enviar la instancia a %s.' % str(telephoneNumber))
				return False
		except:
			logger.write('ERROR', '[GSM] Error al enviar la instancia de mensaje a %s.' % str(telephoneNumber))
			return False

	def sendVoiceCall(self, telephoneNumber):
		try:
			self.sendAT('ATD' + str(telephoneNumber) + ';') # Numero al cual se quiere llamar
			logger.write('INFO', '[GSM] Llamando al número %s...' % str(telephoneNumber))
			return True
		except:
			logger.write('ERROR', '[GSM] Se produjo un error al intentar realizar la llamada!')
			return False

	def answerVoiceCall(self):
		try:
			self.sendAT('ATA') # Atiende la llamada entrante
			logger.write('INFO', '[GSM] Conectado con el número %s.' % self.callerID)
			return True
		except:
			return False

	def hangUpVoiceCall(self):
		try:
			self.sendAT('ATH') # Cuelga la llamada en curso
			if self.callerID is not None:
				logger.write('INFO', '[GSM] Conexión con el número %s finalizada.' % self.callerID)
				self.callerID = None
			return True
		except:
			return False

	def removeSms(self, smsIndex):
		try:
			self.sendAT('AT+CMGD=' + str(smsIndex)) # Elimina el mensaje especificado
			return True
		except:
			return False

	def removeAllSms(self):
		try:
			self.sendAT('AT+CMGD=1,2') # Elimina todos los mensajes leidos y enviados (1,4 es TODO)
			return True
		except:
			return False

	def getSmsIndex(self, atOutput):
		# Ejemplo de 'atOutput' (para un mensaje enviado) : +CMGS: 17
		# Ejemplo de 'atOutput' (para un mensaje recibido): +CMGL: 2
		# Quitamos el comando AT, dejando solamente el índice del mensaje en memoria
		if atOutput.startswith('+CMGS'):
			atOutput = atOutput.replace('+CMGS: ', '')
		elif atOutput.startswith('+CMGL'):
			atOutput = atOutput.replace('+CMGL: ', '')
		smsIndex = int(atOutput)
		return smsIndex

	def getTelephoneNumber(self, smsHeader):
		# Ejemplo de smsHeader recibido de un movil   : +CLIP: "+543512641040",145,"",0,"",0
		# Ejemplo de smsHeader recibido de un movil   : +CMT: "+543512641040",,"15/12/29,11:41:23-12"
		# Ejemplo de smsHeader recibido de un movil   : +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"
		# Ejemplo de smsHeader recibido de la web     : +CMGL: 2,"REC UNREAD","876966",,"14/10/26,19:36:42-12"
		# Ejemplo de smsHeader recibido de un operador: +CMGL: 4,"REC UNREAD","100",,"16/04/14,11:15:51-12"
		# Ejemplo de smsHeader recibido de un operador: +CMGL: 6,"REC UNREAD","PromRecarga",,"16/04/14,09:20:44-12"
		telephoneNumber = None
		headerList = smsHeader.split(',') # Separamos smsHeader por comas
		if headerList[0].startswith(('+CLIP', '+CMT')):
			# Ejemplo de headerList[0]: +CMT: "+543512641040"
			# Ejemplo de headerList[0]: +CLIP: "+543512641040"
			telephoneNumber = headerList[0].split()[1].replace('"', '') # Quitamos las comillas
		elif headerList[0].startswith('+CMGL'):
			# Ejemplo de headerList[2]: "+5493512560536" | "876966" | "100" | "PromRecarga"
			telephoneNumber = headerList[2].replace('"', '') # Quitamos las comillas
		############################### QUITAMOS EL CODIGO DE PAIS ###############################
		# Ejemplo de telephoneNumber: +543512641040 | +5493512560536 | 876966 | 100 | PromRecarga
		if telephoneNumber.startswith('+549'):
			telephoneNumber = telephoneNumber.replace('+549', '')
			# Ejemplo de telephoneNumber: 3512560536
			return int(telephoneNumber)
		elif telephoneNumber.startswith('+54'):
			telephoneNumber = telephoneNumber.replace('+54', '')
			# Ejemplo de telephoneNumber: 3512641040
			return int(telephoneNumber)
		################################### FIN CODIGO DE PAIS ###################################
		else:
			# Entonces es 876966 | 100 | PromRecarga
			return telephoneNumber

	def sendOutput(self, telephoneNumber, smsMessage):
		try:
			subprocess.Popen(['gnome-terminal', '-x', 'sh', '-c', smsMessage + '; exec bash'], stderr = subprocess.PIPE)
			#subprocess.check_output(shlex.split(smsMessage), stderr = subprocess.PIPE)
			smsMessage = 'El comando se ejecuto exitosamente!'
		except subprocess.CalledProcessError as e: # El comando es correcto pero le faltan parámetros
			smsMessage = 'El comando es correcto pero le faltan parámetros!'
		except OSError as e: # El comando no fue encontrado (el ejecutable no existe)
			smsMessage = 'El comando es incorrecto! No se encontró el ejecutable.'
		finally:
			#self.send(telephoneNumber, smsMessage)
			pass