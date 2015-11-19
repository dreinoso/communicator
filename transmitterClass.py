# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import time
import json
import Queue
import pickle
import inspect
import threading

import logger
import contactList

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Transmitter(threading.Thread):

	smsPriority = 0
	emailPriority = 0
	networkPriority = 0
	bluetoothPriority = 0

	isActive = False
	contactExists = False
	transmissionBuffer = Queue.PriorityQueue()

	def __init__(self, _transmissionBuffer, _networkInstance, _bluetoothInstance, _emailInstance, _smsInstance, _checkerInstance):
		"""Creación de la clase de transmisión de paquetes TCP.
		@param _threadName: nombre del hilo
		@type: string
		@param socket para el envio del archivo
		@type: socket
		@param message: mensaje que puede corresponder a una instancia o un String 
		@type: string
		@type: Message"""
		threading.Thread.__init__(self, name = 'TransmitterThread')
		self.smsInstance = _smsInstance 
		self.emailInstance = _emailInstance
		self.networkInstance = _networkInstance
		self.bluetoothInstance = _bluetoothInstance
		# Instancias de checker y transmisor
		self.checkerInstance = _checkerInstance
		self.transmissionBuffer = _transmissionBuffer

	def __del__(self):
		logger.write('INFO', '[TRANSMITTER] Objeto destruido.')

	def run(self):
 		'''Toma del buffer una instancia mensaje (la de mayor prioridad) con parametros 
 		adicionales en la instancia para determinar si el mensaje es válido en relación 
 		al timeout. De ser posible'''
 		self.isActive = True
		while self.isActive:
			try:
				# El elemento 0 es la prioridad, por eso sacamos el 1 porque es el mensaje
				messageInstance = self.transmissionBuffer.get(True, 1.5)[1]
				# Calculamos el tiempo transcurrido desde que se insertó el mensaje en el buffer hasta ahora
				elapsedTime = time.time() - messageInstance.timeStamp
				# Actualizamos el tiempo de vida restante del mensaje que está almacenado en el buffer
				messageInstance.timeOut = messageInstance.timeOut - elapsedTime
				# Si todavía no vence el 'timeout', el mensaje es válido y debe ser enviado...
				if messageInstance.timeOut > 0:
					transmitterThread = threading.Thread(target = self.expectTransmission, args = (messageInstance,), name = 'ExpectThread')
					transmitterThread.start()
				# ... sino, el tiempo expiro y el mensaje debe ser descartado.
				else:
					logger.write('WARNING', '[COMUNICADOR] Mensaje para \'%s\' descartado (el tiempo expiró).' % messageInstance.receiver)
					# Eliminamos la instancia de mensaje, dado que ya no está en el buffer de transmisión
					del messageInstance
			# Para que el bloque 'try' (en la funcion 'get') no se quede esperando indefinidamente
			except Queue.Empty:
				pass
		logger.write('WARNING', '[TRANSMITTER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def expectTransmission(self, messageInstance):
		'''Esta función es lanzada por un nuevo hilo, entonces puede quedarse esperando
		el resultado del envio, sin generar una parada en el programa controlador.
		En caso de que se reciva True no implica que el mensaje se ha enviado, solo 
		que debe descartarse del buffer (por error en el mensaje o por envio correcto).
		Si en cambio se recibe False el mensaje no se pudo enviar, pero el mensaje
		es correcto entonces debe volverse a guardar en el buffer. Los controles sobre
		el envio se hacen en cada uno de los modos, estos deciden y notifican'''
		resultOk = self.send(messageInstance, messageInstance.receiver, messageInstance.device)
		# Se vuelve a colocar el mensaje en buffer para ser enviado nuevamente
		if not resultOk:
			time.sleep(JSON_CONFIG["COMMUNICATOR"]["RETRANSMISSION_TIME"]) # Intervalo de tiempo entre envios sucesivos del mismo paquete
			self.transmissionBuffer.put((100 - messageInstance.priority, messageInstance), True)
		# Mensaje enviado por lo que se elimina
		else:
			del messageInstance

	def send(self, message, receiver, device = ''):
		"""Se envia de modo inteligente un paquete de datos a un contacto previamente 
		registrado el mensaje se envia por el medio mas óptimo encontrado o por la
		selección preferente del usuario para el mensaje de se posible.
		@param message: Mensaje a ser enviado
		@type message: str
		@param receiver: Nombre de contacto previamente registrado
		@type receiver: str
		@param device: Dispositivo de envio preferente
		@type device: str"""
		# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
		if not self.contactExists:
			# Se resetean las prioridades
			self.networkPriority = 0
			self.bluetoothPriority = 0
			self.emailPriority = 0
			self.smsPriority = 0
			if contactList.allowedIpAddress.has_key(receiver) and self.checkerInstance.availableNetwork:
				self.networkPriority = JSON_CONFIG["PRIORITY_LEVELS"]["NETWORK"]
				if device == 'Network':		# En caso de preferencia de Red se da máxima prioridad
					self.networkPriority = 10 
				self.contactExists = True
			if contactList.allowedMacAddress.has_key(receiver) and self.checkerInstance.availableBluetooth:
				self.bluetoothPriority = JSON_CONFIG["PRIORITY_LEVELS"]["BLUETOOTH"]
				if device == 'Bluetooth':
					self.bluetoothPriority = 10
				self.contactExists = True
			if contactList.allowedEmails.has_key(receiver) and self.checkerInstance.availableEmail:
				self.emailPriority = JSON_CONFIG["PRIORITY_LEVELS"]["EMAIL"]
				if device == 'Email':
					self.emailPriority = 10
				self.contactExists = True
			if contactList.allowedNumbers.has_key(receiver) and self.checkerInstance.availableSms and not isinstance(message, messageClass.FileMessage): 
				# Solo se habilita SMS si no es un archivo, o si la cantidad de caracteres 
				# a enviar no supera el limite (que depende si es instancia o mensaje simple)
				if message.sendInstance:
					messageLength = len(pickle.dumps(message))
				else:
					messageLength = len(message.textMessage)
				if messageLength < JSON_CONFIG["SMS"]["CHARACTER_LIMIT"]:
					self.smsPriority = JSON_CONFIG["PRIORITY_LEVELS"]["SMS"]
					if device == 'SMS':
						self.smsPriority = 10
					self.contactExists = True
			if not self.contactExists:
				logger.write('WARNING', '[COMUNICADOR] El contacto \'%s\' no se encuentra registrado.' % receiver)
				return True # Para eliminar el mensaje y no seguir intentando
		# Intentamos transmitir por NETWORK
		if self.networkPriority != 0 and self.networkPriority >= self.bluetoothPriority and self.networkPriority >= self.emailPriority and self.networkPriority >= self.smsPriority:
			destinationIp = contactList.allowedIpAddress[receiver][0]
			destinationTcpPort = contactList.allowedIpAddress[receiver][1]
			destinationUdpPort = contactList.allowedIpAddress[receiver][2]
			resultOk = self.networkInstance.send(message, destinationIp, destinationTcpPort, destinationUdpPort)
			if resultOk: 
				# Aunque la respuesta sea True no significa que el mensaje fue enviado
				# significa que el mensaje se debe eliminar porque fue enviado o porque
				# no era corecto, cada módo se encarga de comunicar el envio.
				self.contactExists = False
				return True
			else:
				logger.write('DEBUG', '[NETWORK] Envio fallido. Reintentando con otro periférico.')
				self.networkPriority = 0   # Entonces se descarta para la proxima selección
				self.send(message, receiver, device) # Se reintenta con otros perifericos, el device no importa porque solo se usa en la primer llamada
		# Intentamos transmitir por BLUETOOTH
		elif self.bluetoothPriority != 0 and self.bluetoothPriority >= self.emailPriority and self.bluetoothPriority >= self.smsPriority:
			destinationServiceName = contactList.allowedMacAddress[receiver][0]
			destinationMAC = contactList.allowedMacAddress[receiver][1]
			destinationUUID = contactList.allowedMacAddress[receiver][2]
			resultOk = self.bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, message)
			if resultOk:
				self.contactExists = False
				return True
			else:
				logger.write('DEBUG', '[BLUETOOTH] Envio fallido. Reintentando con otro periférico.')
				self.bluetoothPriority = 0  # Entonces se descarta para la proxima selección
				self.send(message, receiver) # Se reintenta con otros perifericos, el device no importa porque solo se usa en la primer llamada
		# Intentamos transmitir por EMAIL
		elif self.emailPriority != 0 and self.emailPriority >= self.smsPriority:
			destinationEmail = contactList.allowedEmails[receiver]
			resultOk  = self.emailInstance.send(message, destinationEmail)
			if resultOk:
				self.contactExists = False
				return True
			else:
				logger.write('DEBUG', '[EMAIL] Envio fallido. Reintentando con otro periférico.')
				self.emailPriority = 0      # Entonces se descarta para la proxima selección
				self.send(message, receiver) # Se reintenta con otros perifericos
		# Intentamos transmitir por SMS
		elif self.smsPriority != 0:
			destinationNumber = contactList.allowedNumbers[receiver]
			resultOk = self.smsInstance.send(destinationNumber, message)
			if resultOk:
				self.contactExists = False
				return True
			else:
				logger.write('DEBUG', '[SMS] Envio fallido. Reintentando con otro periférico.')
				self.smsPriority = 0 # Entonces se descarta para la proxima selección
				self.send(message, receiver)
		# No fue posible transmitir por ningún medio
		else:
			logger.write('WARNING', '[COMUNICADOR] No hay módulos para el envío de mensajes a \'%s\'.' % receiver)
			self.contactExists = False
			return False

