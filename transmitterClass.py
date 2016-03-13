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
	transmissionBuffer = None

	def __init__(self, _smsInstance, _emailInstance, _networkInstance, _bluetoothInstance, _transmissionBuffer):
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
					transmitterThread = threading.Thread(target = self.trySend, args = (messageInstance,), name = 'TransmitterThread')
					transmitterThread.start()
				# ... sino, el tiempo expiro y el mensaje debe ser descartado.
				else:
					logger.write('WARNING', '[COMMUNICATOR] Mensaje para \'%s\' descartado (el tiempo expiró).' % messageInstance.receiver)
					# Eliminamos la instancia de mensaje, dado que ya no está en el buffer de transmisión
					del messageInstance
			# Para que el bloque 'try' (en la funcion 'get') no se quede esperando indefinidamente
			except Queue.Empty:
				pass
		logger.write('WARNING', '[TRANSMITTER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def trySend(self, messageInstance):
		'''Esta función es lanzada por un nuevo hilo, entonces puede quedarse esperando
		el resultado del envio, sin generar una parada en el programa controlador.
		En caso de que se reciva True no implica que el mensaje se ha enviado, solo 
		que debe descartarse del buffer (por error en el mensaje o por envio correcto).
		Si en cambio se recibe False el mensaje no se pudo enviar, pero el mensaje
		es correcto entonces debe volverse a guardar en el buffer. Los controles sobre
		el envio se hacen en cada uno de los modos, estos deciden y notifican'''
		self.setPriorities(messageInstance.receiver, messageInstance.device)
		# Hacemos una copia de los campos del objeto
		device = messageInstance.device
		timeOut = messageInstance.timeOut
		timeStamp = messageInstance.timeStamp
		# Eliminamos los campos del objeto, ya que el receptor no los necesita
		delattr(messageInstance, 'device')
		delattr(messageInstance, 'timeOut')
		delattr(messageInstance, 'timeStamp')
		# Si el envío falla, se vuelve a colocar el mensaje en el buffer para ser enviado nuevamente
		if not self.send(messageInstance):
			# Insertamos nuevamente los campos eliminados para manejar el próximo envío
			setattr(messageInstance, 'device', device)
			setattr(messageInstance, 'timeOut', timeOut)
			setattr(messageInstance, 'timeStamp', timeStamp)
			# Intervalo de tiempo entre envios sucesivos del mismo paquete
			time.sleep(JSON_CONFIG["COMMUNICATOR"]["RETRY_TIME"])
			self.transmissionBuffer.put((100 - messageInstance.priority, messageInstance), True)
		# Mensaje enviado por lo que se elimina
		else:
			del messageInstance

	def setPriorities(self, receiver, device):
		self.smsPriority = 0
		self.emailPriority = 0
		self.networkPriority = 0
		self.bluetoothPriority = 0
		# Para SMS
		if contactList.allowedNumbers.has_key(receiver) and self.smsInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if device == 'SMS':
				self.smsPriority = 10
			else:
				self.smsPriority = JSON_CONFIG["PRIORITY_LEVELS"]["SMS"]
		# Para EMAIL
		if contactList.allowedEmails.has_key(receiver) and self.emailInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if device == 'EMAIL':
				self.emailPriority = 10
			else:
				self.emailPriority = JSON_CONFIG["PRIORITY_LEVELS"]["EMAIL"]
		# Para NETWORK
		if contactList.allowedIpAddress.has_key(receiver) and self.networkInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if device == 'NETWORK':
				self.networkPriority = 10
			else:
				self.networkPriority = JSON_CONFIG["PRIORITY_LEVELS"]["NETWORK"]
		# Para BLUETOOTH
		if contactList.allowedMacAddress.has_key(receiver) and self.bluetoothInstance.isActive:
			# En caso de preferencia se da máxima prioridad
			if device == 'BLUETOOTH':
				self.bluetoothPriority = 10
			else:
				self.bluetoothPriority = JSON_CONFIG["PRIORITY_LEVELS"]["BLUETOOTH"]

	def send(self, messageInstance):
		"""Se envia de modo inteligente un paquete de datos a un contacto previamente 
		registrado el mensaje se envia por el medio mas óptimo encontrado o por la
		selección preferente del usuario para el mensaje de se posible.
		@param messageInstance: Mensaje a ser enviado
		@type messageInstance: str"""
		# Intentamos transmitir por SMS
		if all(self.smsPriority != 0 and self.smsPriority >= x for x in(self.emailPriority, self.networkPriority, self.bluetoothPriority)):
			destinationNumber = contactList.allowedNumbers[messageInstance.receiver]
			if not self.smsInstance.send(messageInstance, destinationNumber):
				logger.write('DEBUG', '[COMMUNICATOR-SMS] Falló. Reintentando con otro periférico.')
				self.smsPriority = 0              # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otros periféricos
			else:
				return True
		# Intentamos transmitir por EMAIL
		elif all(self.emailPriority != 0 and self.emailPriority >= x for x in(self.networkPriority, self.bluetoothPriority)):
			destinationEmail = contactList.allowedEmails[messageInstance.receiver]
			if not self.emailInstance.send(messageInstance, destinationEmail):
				logger.write('DEBUG', '[COMMUNICATOR-EMAIL] Falló. Reintentando con otro periférico.')
				self.emailPriority = 0            # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otros periféricos
			else:
				return True
		# Intentamos transmitir por NETWORK
		elif self.networkPriority != 0 and self.networkPriority >= self.bluetoothPriority:
			destinationIp, destinationTcpPort, destinationUdpPort = contactList.allowedIpAddress[messageInstance.receiver]
			if not self.networkInstance.send(messageInstance, destinationIp, destinationTcpPort, destinationUdpPort):
				logger.write('DEBUG', '[COMMUNICATOR-NETWORK] Falló. Reintentando con otro periférico.')
				self.networkPriority = 0          # Se descarta para la próxima selección
				return self.send(messageInstance) # Se reintenta con otros periféricos
			else:
				return True
		# Intentamos transmitir por BLUETOOTH
		elif self.bluetoothPriority != 0:
			destinationServiceName, destinationMAC, destinationUUID = contactList.allowedMacAddress[messageInstance.receiver]
			if not self.bluetoothInstance.send(messageInstance, destinationServiceName, destinationMAC, destinationUUID):
				logger.write('DEBUG', '[COMMUNICATOR-BLUETOOTH] Falló. Reintentando con otro periférico.')
				self.bluetoothPriority = 0        # Entonces se descarta para la proxima selección
				return self.send(messageInstance) # Se reintenta con otros periféricos
			else:
				return True
		# No fue posible transmitir por ningún medio
		else:
			logger.write('WARNING', '[COMMUNICATOR] No hay módulos para el envío a \'%s\'...' % messageInstance.receiver)
			return False