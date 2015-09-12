 # coding=utf-8

"""Modulo principal que se encarga del control de los demás objetos y submódulos
	para permitir la comunicación. 
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import sys
import Queue
import threading

sys.path.append(os.path.abspath('Lan/'))
sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Bluetooth/'))

import lanClass
import modemClass
import emailClass
import bluetoothClass

import logger
import contactList
import configReader
import checkerClass

receptionBuffer = Queue.Queue()
modemSemaphore = threading.Semaphore(value = 1)

# Creamos las instancias de los periféricos
lanInstance = lanClass.Lan(receptionBuffer)
emailInstance = emailClass.Email(receptionBuffer)
smsInstance = modemClass.Sms(receptionBuffer, modemSemaphore)
bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)

# Creamos la instancia del checker y el hilo que va a verificar las conexiones
checkerInstance = checkerClass.Checker(modemSemaphore, lanInstance, smsInstance, emailInstance, bluetoothInstance)
checkerThread = threading.Thread(target = checkerInstance.verifyConnections, name = 'checkerThread')

contactExists = False
lanPriority = 0
bluetoothPriority = 0
emailPriority = 0
smsPriority = 0

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, checkerThread
	
	logger.set('communicatorLogger') # Solo se setea una vez, todos los objetos usan esta misma configuración
	
	resultOk = configReader.readConfigFile() # Se determina el resultado de la configuración 
	if resultOk:
		logger.write('INFO', '[CONFIG READER] Archivo de configuración cargado correctamente.')
	else:
		logger.write('ERROR', '[CONFIG READER] Imposible leer \'properties.conf\'. Se usará la configuración por defecto.')
	# Lanzamos el hilo que comprueba las conexiones
	checkerInstance.isActive = True
	checkerThread.start()

def send(contact, message, isPacket):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global contactExists, lanPriority, bluetoothPriority, emailPriority, smsPriority

	# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
	if not contactExists:
		lanPriority = 0
		bluetoothPriority = 0
		emailPriority = 0
		smsPriority = 0
		if contactList.allowedIpAddress.has_key(contact) and checkerInstance.availableLan:
			lanPriority = configReader.priorityLevels['lan']
			contactExists = True
		if contactList.allowedMacAddress.has_key(contact) and checkerInstance.availableBluetooth:
			bluetoothPriority = configReader.priorityLevels['bluetooth']
			contactExists = True
		if contactList.allowedEmails.has_key(contact) and checkerInstance.availableEmail:
			emailPriority = configReader.priorityLevels['email']
			contactExists = True
		if contactList.allowedNumbers.has_key(contact) and checkerInstance.availableSms:
			smsPriority = configReader.priorityLevels['sms']
			contactExists = True
		if not contactExists:
			logger.write('WARNING', '[COMUNICADOR] El contacto \'%s\' no se encuentra registrado.' % contact)
			return False
	# Intentamos transmitir por LAN
	if lanPriority != 0 and lanPriority >= bluetoothPriority and lanPriority >= emailPriority and lanPriority >= smsPriority:
		destinationIp = contactList.allowedIpAddress[contact][0]
		destinationTcpPort = contactList.allowedIpAddress[contact][1]
		destinationUdpPort = contactList.allowedIpAddress[contact][2]
		if isPacket: resultOk = lanInstance.sendPacket(destinationIp, destinationTcpPort, destinationUdpPort, message) # message corresponde al nombre del paquete
		else: resultOk = lanInstance.send(destinationIp, destinationTcpPort, destinationUdpPort, message)
		if resultOk:
			logger.write('INFO', '[LAN] Mensaje enviado a \'%s\'.' % contact)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[LAN] Envio fallido. Reintentando con otro periférico.')
			lanPriority = 0   # Entonces se descarta para la proxima selección
			send(contact, message, isPacket) # Se reintenta con otros perifericos
	# Intentamos transmitir por BLUETOOTH
	elif bluetoothPriority != 0 and bluetoothPriority >= emailPriority and bluetoothPriority >= smsPriority:
		destinationServiceName = contactList.allowedMacAddress[contact][0]
		destinationMAC = contactList.allowedMacAddress[contact][1]
		destinationUUID = contactList.allowedMacAddress[contact][2]
		resultOk = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, message)
		if resultOk:
			logger.write('INFO', '[BLUETOOTH] Mensaje enviado a \'%s\'.' % contact)
			contactExisms = False
			return True
		else:
			logger.write('WARNING', '[BLUETOOTH] Envio fallido. Reintentando con otro periférico.')
			bluetoothPriority = 0  # Entonces se descarta para la proxima selección
			send(contact, message, isPacket) # Se reintenta con otros perifericos
	# Intentamos transmitir por EMAIL
	elif emailPriority != 0 and emailPriority >= smsPriority:
		destinationEmail = contactList.allowedEmails[contact]
		resultOk  = emailInstance.send(destinationEmail, 'Proyecto Datalogger - Comunicador', message)
		if resultOk:
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'.' % contact)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[EMAIL] Envio fallido. Reintentando con otro periférico.')
			emailPriority = 0      # Entonces se descarta para la proxima selección
			send(contact, message, isPacket) # Se reintenta con otros perifericos
	# Intentamos transmitir por SMS
	elif smsPriority != 0:
		destinationNumbsmsPriorityer = contactList.allowedNumbers[contact]
		resultOk = smsInstance.send(destinationNumber, message)
		if resultOk:
			logger.write('INFO', '[SMS] Mensaje enviado a \'%s\'.' % contact)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[SMS] Envio fallido. Reintentando con otro periférico.')
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(contact, message, isPacket)
	# No fue posible transmitir por ningún medio
	else:
		logger.write('WARNING', '[COMUNICADOR] No hay módulos para el envío de mensajes a \'%s\'.' % contact)
		contactExists = False
		return False

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	if receptionBuffer.qsize() > 0:
		message = receptionBuffer.get(False) # False implica que no se bloquee esperando un elemento
		return message
	else:
		logger.write('INFO', '[COMUNICADOR] El buffer de mensajes esta vacio.')
		return None

def len():
	"""Devuelve el tamaño del buffer de recepción.
	@return: Cantidad de elementos en el buffer
	@rtype: int"""
	if receptionBuffer.qsize() == None: return 0
	else: return receptionBuffer.qsize()

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global checkerThread, receptionBuffer, checkerInstance, smsInstance, lanInstance, bluetoothInstance, emailInstance
	receptionBuffer.queue.clear()
	checkerInstance.isActive = False
	checkerThread.join()
	del checkerInstance
	del smsInstance
	del lanInstance
	del emailInstance
	del bluetoothInstance
