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

import configReader
import checkerClass
import emailClass
import modemClass
import ethernetClass
import contactList 
import logger

currentPath = ''.join(( os.popen('pwd').readlines())) # Se busca el Path del modo bluetooth para añadirlo al sistema
currentPath = currentPath[0:len(currentPath)-1]
bluetoothPath = currentPath + '/Bluetooth'
sys.path.append(bluetoothPath)
import bluetoothClass

receptionBuffer = Queue.Queue()
modemSemaphore = threading.Semaphore(value = 1)

checkerInstance = checkerClass.Checker
ethernetInstance = ethernetClass.Ethernet
bluetoothInstance = bluetoothClass.Bluetooth
smsInstance = modemClass.Sms
emailInstance = emailClass.Email

contactExists = False
ethernetPriority = 0
bluetoothPriority = 0
emailPriority = 0
smsPriority = 0

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, ethernetInstance, bluetoothInstance, smsInstance, emailInstance
	
	logger.set('communicatorLogger') # Solo se setea una vez, todos los objetos usan esta misma configuración
	
	resultOk = configReader.readConfigFile() # Se determina el resultado de la configuración 
	if resultOk:
		logger.write('INFO', '[CONFIG-READER] Archivo de configuración cargado correctamente.')
	else:
		logger.write('ERROR', '[CONFIG-READER] Imposible leer \'properties.conf\'. Se usará la configuración por defecto.')
	# Creamos las instancias de los periféricos
	ethernetInstance = ethernetClass.Ethernet(receptionBuffer)
	bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)
	smsInstance = modemClass.Sms(receptionBuffer, modemSemaphore)
	emailInstance = emailClass.Email(receptionBuffer)
	# Creamos la instancia del checker y lanzamos el hilo
	checkerInstance = checkerClass.Checker(smsInstance, ethernetInstance, bluetoothInstance, emailInstance, modemSemaphore)
	checkerThread = threading.Thread(target = checkerInstance.verifyConnections, name = 'checkerThread')
	checkerThread.start()

def send(contact, message):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global contactExists, ethernetPriority, bluetoothPriority, emailPriority, smsPriority

	# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
	if not contactExists:
		ethernetPriority = 0
		bluetoothPriority = 0
		emailPriority = 0
		smsPriority = 0
		contactExists = True
		if contactList.allowedIpAddress.has_key(contact) and checkerInstance.availableEthernet:
			ethernetPriority = configReader.priorityLevels['ethernet']
		if contactList.allowedMacAddress.has_key(contact) and checkerInstance.availableBluetooth:
			bluetoothPriority = configReader.priorityLevels['bluetooth']
		if contactList.allowedEmails.has_key(contact) and checkerInstance.availableEmail:
			emailPriority = configReader.priorityLevels['email']
		if contactList.allowedNumbers.has_key(contact) and checkerInstance.availableSms:
			smsPriority = configReader.priorityLevels['sms']
		#logger.write('WARNING', '[COMUNICADOR] El contacto \'%s\' no se encuentra registrado.' % contact)

	# Intentamos transmitir por ETHERNET
	if checkerInstance.availableEthernet and ethernetPriority != 0:
		if ethernetPriority >= bluetoothPriority and ethernetPriority >= emailPriority and ethernetPriority >= smsPriority:
			destinationIp = contactList.allowedIpAddress[contact][0]
			destinationPort = contactList.allowedIpAddress[contact][1]
			resultOk = ethernetInstance.send(destinationIp, destinationPort, message)
			if resultOk:
				logger.write('INFO', '[ETHERNET] Mensaje enviado a \'%s\'.' % contact)
				contactExists = False
				return
			else:
				logger.write('WARNING', '[ETHERNET] Envio fallido. Reintentando con otro periférico.')
				ethernetPriority = 0   # Entonces se descarta para la proxima selección
				send(contact, message) # Se reintenta con otros perifericos
	# Intentamos transmitir por BLUETOOTH
	if checkerInstance.availableBluetooth and bluetoothPriority != 0:
		if bluetoothPriority >= emailPriority and bluetoothPriority >= smsPriority:
			destinationServiceName = contactList.allowedMacAddress[contact][0]
			destinationMAC = contactList.allowedMacAddress[contact][1]
			destinationUUID = contactList.allowedMacAddress[contact][2]
			resultOk = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, message)
			if resultOk:
				logger.write('INFO', '[BLUETOOTH] Mensaje enviado a \'%s\'.' % contact)
				contactExists = False
				return
			else:
				logger.write('WARNING', '[BLUETOOTH] Envio fallido. Reintentando con otro periférico.')
				bluetoothPriority = 0  # Entonces se descarta para la proxima selección
				send(contact, message) # Se reintenta con otros perifericos
	# Intentamos transmitir por EMAIL
	if checkerInstance.availableEmail and emailPriority != 0:
		if emailPriority >= smsPriority:
			destinationEmail = contactList.allowedEmails[contact]
			resultOk  = emailInstance.send(destinationEmail, 'Proyecto Datalogger - Comunicador', message)
			if resultOk:
				logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'.' % contact)
				contactExists = False
				return
			else:
				logger.write('WARNING', '[EMAIL] Envio fallido. Reintentando con otro periférico.')
				emailPriority = 0      # Entonces se descarta para la proxima selección
				send(contact, message) # Se reintenta con otros perifericos
	# Intentamos transmitir por SMS
	if checkerInstance.availableSms and smsPriority != 0:
		destinationNumber = contactList.allowedNumbers[contact]
		resultOk = smsInstance.send(destinationNumber, message)
		if resultOk:
			logger.write('INFO', '[SMS] Mensaje enviado a \'%s\'.' % contact)
			contactExists = False
			return
		else:
			logger.write('WARNING', '[SMS] Envio fallido. Reintentando con otro periférico.')
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(contact, message)
	# No fue posible transmitir por ningún medio
	else:
		logger.write('WARNING', '[COMUNICADOR] No hay módulos para el envío de mensajes a \'%s\'.' % contact)
		contactExists = False
		return

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
	global receptionBuffer, checkerInstance, smsInstance, ethernetInstance, bluetoothInstance, emailInstance
	receptionBuffer.queue.clear()
	checkerInstance.killChecker = True
	del checkerInstance
	del smsInstance
	del ethernetInstance
	del emailInstance
	del bluetoothInstance
