# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	de paquetes de datos y mensajes en la red local por el protocolo TCP.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import inspect
import json
import pickle
import Queue
import threading
import time

import logger
import contactList

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Transmitter(threading.Thread):

	transmissionBuffer = Queue.PriorityQueue()
	isActive = False
	networkPriority = 0
	smsPriority = 0
	emailPriority = 0
	bluetoothPriority = 0
	contactExists = False

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
		self.transmissionBuffer = _transmissionBuffer
		self.networkInstance = _networkInstance
		self.bluetoothInstance = _bluetoothInstance
		self.emailInstance = _emailInstance
		self.smsInstance = _smsInstance
		self.checkerInstance = _checkerInstance

	def __del__(self):
		logger.write('INFO', '[TRANSMITTER] Objeto destruido.')
		#TODO: Determinar si hacer algo aca..

	def run(self):
 		'''Toma del buffer una instancia mensaje (la de mayor prioridad) con parametros 
 		adicionales en la instancia para determinar si el mensaje es válido en relación 
 		al timeout. De ser posible'''
		while self.isActive: 
			if not self.transmissionBuffer.empty():
				# Por ser una cola de prioridad, automaticamente entrega el elemeneto de mayor prioridad
				message = self.transmissionBuffer.get_nowait()[2] # Devuelve una tupla, el tercer elemento es el mensaje 
				elapsedTime = time.time() - message.timeStamp
				message.timeOut = message.timeOut - elapsedTime
				if message.timeOut > 0: # Todavia no vence el timeout y el mensaje es válido
					transmitterThread = threading.Thread(target = self.expectTransmission(message), name = 'transmitterThread')
					transmitterThread.start()
					transmitterThread.join() # Este hilo no termina hasta que terminen sus hijos
				else: # El tiempo expiro se debe descartar el mensaje
					logger.write('WARNING', '[COMUNICADOR] Se descarta mensaje para el contacto "%s", expiro el tiempo .' % message.receiver)
					del message # Como ya no esta en el buffer el mensaje se elimina
			time.sleep(1) 
			# Para no preguntar constantemente en el while, además da tiempo a que 
			# el mensaje tome alguno de los modos, sin que se los quite el siguiente
			# TODO cambiar el sleep por un monitor que envie un signal en caso que se 
			# vuelva a cargar el buffer
		logger.write('WARNING', '[TRANSMITTER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])


	def expectTransmission(self,message):
		'''Esta función es lanzada por un nuevo hilo, entonces puede quedarse esperando
		el resultado del envio, sin generar una parada en el programa controlador.
		En caso de que se reciva True no implica que el mensaje se ha enviado, solo 
		que debe descartarse del buffer (por error en el mensaje o por envio correcto).
		Si en cambio se recibe False el mensaje no se pudo enviar, pero el mensaje
		es correcto entonces debe volverse a guardar en el buffer. Los controles sobre
		el envio se hacen en cada uno de los modos, estos deciden y notifican'''
		# Se almacenan los campos auxiliares en caso de que se borren y el mensaje no se envie
		timeStampTemp = message.timeStamp
		sendInstanceTemp = message.sendInstance
		resultOk = self.send(message, message.receiver, message.device)
		if resultOk:
			del message # Mensaje enviado por lo que se elimina
		else: # Se vuelve a colocar el mensaje en buffer para ser enviado nuevamente
			message.timeStamp = timeStampTemp
			message.sendInstance = sendInstanceTemp
			time.sleep(10) # Intervalo de tiempo entre envios sucesivos del mismo paquete
			while self.transmissionBuffer.full():
				time.sleep(2) # Espera a que haya lugar
			self.transmissionBuffer.put((100 - message.priority, message.timeOut, message)) 

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
		# Se debe almacenar el tamño para determinar si es demasiado grande para SMS
		messageLength = len(pickle.dumps(message))
		# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
		if not self.contactExists:
			del message.timeStamp # Se elimina el campo auxiliar
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
			if contactList.allowedNumbers.has_key(receiver) and self.checkerInstance.availableSms: 
				# Para SMS solo se habilita el modo si la cantidad de caracteres a enviar no supera el limite
				# y el mensaje no es un archivo
				if messageLength < JSON_CONFIG["SMS"]["CLARO_CHARACTER_LIMIT"] and not isinstance(message, messageClass.FileMessage):
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
			resultOk  = self.emailInstance.send(destinationEmail, 'Proyecto Datalogger - Comunicador', message)
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

