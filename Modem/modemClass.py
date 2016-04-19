# coding=utf-8

"""	Permite crear una instancia que se encargara de proporcionar funciones
	facilitando el manejo del modem. Entre las funcionalidades basicas con
	las que cuenta, tenemos principalmente el envio y recepcion de mensajes
	SMS.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Miercoles 17 de Junio de 2015 """

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
	""" Clase 'Modem'. Permite la creacion de una instancia del dispositivo. """
	successfulConnection = None
	receptionQueue = None
	serialPort = None

	def __init__(self):
		""" Constructor de la clase 'Modem'. Utiliza la API 'pySerial' de
			Python para establecer un medio de comunicacion entre el usuario
			y el puerto donde se encuentra conectado el modem. Establece un
			'baudrate' y un 'timeout', donde este ultimo indica el intervalo
			de tiempo en segundos con el cual se hacen lecturas sobre el
			dispositivo. """
		self.modemInstance = serial.Serial()
		self.modemInstance.bytesize = serial.EIGHTBITS
		self.modemInstance.parity = serial.PARITY_NONE
		self.modemInstance.stopbits = serial.STOPBITS_ONE
		self.modemInstance.timeout = JSON_CONFIG["MODEM"]["TIME_OUT"]
		self.modemInstance.baudrate = JSON_CONFIG["MODEM"]["BAUD_RATE"]

	def sendAT(self, atCommand):
		""" Se encarga de enviarle un comando AT el modem. Espera la respuesta
			a ese comando, antes de continuar.
			@param atCommand: comando AT que se quiere ejecutar
			@type atCommand: str
			@return: respuesta del modem, al comando AT ingresado
			@rtype: list """
		self.modemInstance.write(atCommand + '\r')	 # Envio el comando AT al modem
		modemOutput = self.modemInstance.readlines() # Espero la respuesta
		# Verificamos si se produjo algún tipo de error relacionado con el comando AT
		for outputElement in modemOutput:
			# El 'AT+CNMA' sólo es soportado en Dongles USB que requieren confirmación de SMS
			if outputElement.startswith(('+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
				errorMessage = outputElement.replace('\r\n', '')
				logger.write('ERROR', '[GSM] %s.' % errorMessage)
				raise
			# El comando AT para llamadas de voz (caracterizado por su terminacion en ';') no es soportado
			elif outputElement.startswith('NO CARRIER') and atCommand.startswith('ATD') and atCommand.endswith(';'):
				raise
		return modemOutput

	def closePort(self):
		self.modemInstance.close()

class Gsm(Modem):
	""" Subclase de 'Modem' correspondiente al modo de operacion con el que se va
		a trabajar. """
	successfulSending = None
	isActive = False

	def __init__(self, _receptionQueue):
		""" Constructor de la clase 'Gsm'. Configura el modem para operar en modo mensajes
			de texto, indica el sitio donde se van a almacenar los mensajes recibidos,
			habilita notificacion para los SMS entrantes y establece el numero del centro
			de mensajes CLARO para poder enviar mensajes de texto (este campo puede variar
			dependiendo de la compania de telefonia de la tarjeta SIM). """
		Modem.__init__(self)
		self.receptionQueue = _receptionQueue

	def __del__(self):
		""" Destructor de la clase 'Modem'. Cierra la conexion establecida
			con el modem. """
		self.modemInstance.close()
		logger.write('INFO', '[GSM] Objeto destruido.')

	def connect(self, _serialPort):
		self.serialPort = _serialPort
		try:
			self.modemInstance.port = _serialPort
			self.modemInstance.open()
			#self.modemInstance.flushInput()
			#self.modemInstance.flushOutput()
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
		""" Funcion que se encarga consultar al modem por algun mensaje SMS entrante. Envia al
			mismo el comando AT que devuelve los mensajes de texto no leidos (que por ende seran
			los nuevos) y que en caso de obtenerlos, los envia de a uno al modulo de procesamiento
			para su examen. Si el remitente del mensaje se encuentra registrado (en el archivo
			'contactList') se procede a procesar el cuerpo del SMS, o en caso contrario, se envia
			una notificacion informandole que no es posible realizar la operacion solicitada.
			Tambien cada un cierto tiempo dado por el intervalo de temporizacion, envia a un numero
			de telefono dado por 'DESTINATION_NUMBER' un mensaje de actualizacion, que por el momento
			estara compuesto de un 'TimeStamp'. """
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
				# Quitamos el primer y último elemento, porque no contienen información (espacios en blanco)
				receptionList.pop(len(receptionList) - 1)
				receptionList.pop(0)
				# Ejemplo receptionList: ['+CMT: "+543512641040","","16/01/31,05:00:08-12"', 'Nuevo SMS.']
				# Ejemplo receptionList: ['RING', '', '+CLIP: "+543512641040",145,"",0,"",0']
				# Ejemplo receptionList: ['NO CARRIER']
				# Ejemplo receptionList: ['+CMS ERROR: 500']
				# Significa un mensaje entrante
				if receptionList[0].startswith('+CMT'):
					try:
						smsHeaderList.append(receptionList[0])
						smsBodyList.append(receptionList[1])
						self.sendAT('AT+CNMA') # Enviamos el ACK (ńecesario sólo para los Dongle USB)
					except:
						pass # La excepción aparece cuando el módem no soporta (no necesita) el ACK
					finally:
						smsAmount += 1
				# Significa que no se pudo enviar el mensaje
				elif receptionList[0].startswith('+CMS'):
					self.successfulSending = False
				############################### LLAMADAS DE VOZ ###############################
				# Significa una llamade entrante
				elif receptionList[0].startswith('RING'):
					callerID = self.getTelephoneNumber(receptionList[2])
					logger.write('INFO', '[GSM] El número \'%s\' está llamando...' % callerID)
				# Significa que el destino se encuentra en otra llamada
				elif receptionList[0].startswith('BUSY'):
					logger.write('WARNING', '[GSM] El télefono destino se encuentra ocupado.')
				# Significa que la llamada saliente pasó al buzón de voz
				elif receptionList[0].startswith('NO ANSWER'):
					logger.write('WARNING', '[GSM] No hubo respuesta durante la llamada de voz.')
				# Significa que la llamada entrante se perdió (llamada perdida)
				elif receptionList[0].startswith('NO CARRIER'):
					logger.write('WARNING', '[GSM] No se pudo establecer la llamada de voz.')
				############################# FIN LLAMADAS DE VOZ #############################
			else:
				time.sleep(1)
		logger.write('WARNING', '[GSM] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def send(self, message, telephoneNumber):
		""" Envia el comando AT correspondiente para enviar un mensaje de texto.
			@param telephoneNumber: numero de telefono del destinatario
			@type telephoneNumber: int
			@param messageToSend: mensaje de texto a enviar
			@type messageToSend: str """
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
			self.successfulSending = None
			# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
			info01 = self.sendAT('AT+CMGS="' + str(telephoneNumber) + '"') # Numero al cual enviar el SMS
			info02 = self.sendAT(plainText + ascii.ctrl('z'))              # Mensaje de texto terminado en Ctrl+z
			# Borramos el mensaje enviado almacenado en la memoria
			self.removeAllSms()
			# ------------------ Caso de envío EXITOSO ------------------
			# Ejemplo de info02[0]: Mensaje enviado desde el Modem.\x1a\r\n
			# Ejemplo de info02[1]: +CMGS: 17\r\n
			# Ejemplo de info02[3]: OK\r\n
			for i in info02:
				if i.startswith('OK'):
					logger.write('INFO', '[GSM] Mensaje de texto enviado a \'%s\'.' % str(telephoneNumber))
					return True
			# Esperamos respuesta de la red ante la petición del envío
			while self.successfulSending is None:
				pass
			# Examinamos la confirmación de la red
			if self.successfulSending is False:
				logger.write('WARNING', '[GSM] No se pudo enviar el mensaje a \'%s\'.' % str(telephoneNumber))
				return False
		except:
			logger.write('ERROR', '[GSM] Error al enviar el mensaje de texto a \'%s\'.' % str(telephoneNumber))
			return False

	def sendMessageInstance(self, message, telephoneNumber):
		try:
			self.successfulSending = None
			# Serializamos el objeto para poder transmitirlo
			serializedMessage = 'INSTANCE' + pickle.dumps(message)
			# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
			info01 = self.sendAT('AT+CMGS="' + str(telephoneNumber) + '"') # Numero al cual enviar el SMS
			info02 = self.sendAT(serializedMessage + ascii.ctrl('z'))      # Mensaje de texto terminado en Ctrl+Z
			# Borramos el mensaje enviado almacenado en la memoria
			self.removeAllSms()
			# ------------------ Caso de envío EXITOSO ------------------
			# Ejemplo de info02[0]: Mensaje enviado desde el Modem.\x1a\r\n
			# Ejemplo de info02[1]: +CMGS: 17\r\n
			# Ejemplo de info02[3]: OK\r\n
			for i in info02:
				if i.startswith('OK'):
					logger.write('INFO', '[GSM] Instancia de mensaje enviada a \'%s\'.' % str(telephoneNumber))
					return True
			# Esperamos respuesta de la red ante la petición del envío
			while self.successfulSending is None:
				pass
			# Examinamos la confirmación de la red
			if self.successfulSending is False:
				logger.write('WARNING', '[GSM] No se pudo enviar la instancia a \'%s\'.' % str(telephoneNumber))
				return False
		except:
			logger.write('ERROR', '[GSM] Instancia de mensaje no enviada a \'%s\'.' % str(telephoneNumber))
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
		self.sendAT('ATA') # Atiende la llamada entrante

	def hangUpVoiceCall(self):
		self.sendAT('ATH') # Cuelga la llamada en curso

	def removeSms(self, smsIndex):
		""" Envia el comando AT correspondiente para elimiar todos los mensajes del dispositivo.
			El comando AT tiene una serie de parametros, que dependiendo de cada uno de ellos
			indicara cual de los mensajes se quiere eliminar. En nuestro caso le indicaremos
			que elimine los mensajes leidos y los mensajes enviados, ya que fueron procesados
			y no los requerimos mas (ademas necesitamos ahorrar memoria, debido a que la misma
			es muy limitada). """
		self.sendAT('AT+CMGD=' + str(smsIndex)) # Elimina el mensaje especificado

	def removeAllSms(self):
		self.sendAT('AT+CMGD=1,2') # Elimina todos los mensajes leidos y enviados (1,4 es TODO)

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
		""" Procesa la cabecera del SMS.
			@return: numero de telefono del remitente
			@rtype: int """
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