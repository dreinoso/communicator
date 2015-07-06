 # coding=utf-8

"""Modulo principal que se encarga del control de los demás objetos y submódulos
	para permitir la comunicación. 
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import sys
import threading
import os

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

receptionBuffer = list()

checkerInstance = checkerClass.Checker
ethernetInstance = ethernetClass.Ethernet
bluetoothInstance = bluetoothClass.Bluetooth
smsInstance = modemClass.Sms
emailInstance = emailClass.Email

firstTry = True # Para el control de envio recursivo por prioridades
ethernetPriority = 0 # Por defecto se deshabilitan los modos de envio
bluetoothPriority = 0
emailPriority = 0
smsPriority = 0

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, ethernetInstance, bluetoothInstance, smsInstance, emailInstance
	
	logger.set('communicatorLogger') # Solo se setea una vez, todos los objetos usan esta misma configuración.
	
	configResult = configReader.readConfigFile() # Se determina el resultado de la configuración 
	if configResult != None: logger.write('INFO', configResult)
	else: logger.write('ERROR', '[CONFIG READER] El archivo properties.conf no esta bien configurado,\
	se usa la configuración por defecto.')

	ethernetInstance = ethernetClass.Ethernet(receptionBuffer)
	bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)
	smsInstance = modemClass.Sms()
	emailInstance = emailClass.Email(receptionBuffer)
	checkerInstance = checkerClass.Checker(smsInstance, ethernetInstance, bluetoothInstance, emailInstance) # Al iniciar determina el estado de las conexiones
	checkerThread = threading.Thread(target = checkerInstance.verifyConnections, name = 'checkerThread')
	checkerThread.start()

def send(contact, message):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global ethernetInstance, bluetoothInstance, emailInstance, smsInstance, firstTry, ethernetPriority, bluetoothPriority, emailPriority, smsPriority

	if firstTry: # Solo la primer vez que intente enviar incia las prioridades, para poder modificar temporalmente
		if (contactList.allowedIpAddress.has_key(contact) and checkerInstance.availableEthernet): # Si esta registrado el contacto y disponible el modo se habilita y carga la prioridad
			ethernetPriority = configReader.priorityLevels['ethernet'] 
		if (contactList.allowedMacAddress.has_key(contact) and checkerInstance.availableBluetooth): 
			bluetoothPriority = configReader.priorityLevels['bluetooth']
		if (contactList.allowedEmails.has_key(contact) and checkerInstance.availableEmail): 
			emailPriority = configReader.priorityLevels['email']
		if (contactList.allowedNumbers.has_key(contact) and checkerInstance.availableSms):
			smsPriority = configReader.priorityLevels['sms']
		firstTry = False

	if ((ethernetPriority >= bluetoothPriority) and (ethernetPriority >= emailPriority) and 	
	(ethernetPriority >= smsPriority) and (ethernetPriority != 0)):
		destinationIp = contactList.allowedIpAddress[contact][0]
		destinationPort = contactList.allowedIpAddress[contact][1]
		ethernetInstance.send(destinationIp, destinationPort, message)
		acknowledge = True  #TODO True si el envio es correcto, de otro modo es False y en ese caso debe llamarse nuevamente a la función
		if acknowledge:
			firstTry = True # Se limpia la bandera
			logger.write('INFO', '[ETHERNET] Se envio mensaje al contacto: ' + contact)
		else:
			ethernetPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif ((bluetoothPriority >= emailPriority) and (bluetoothPriority >= smsPriority) and (bluetoothPriority != 0)):
		destinationServiceName = contactList.allowedMacAddress[contact][0]
		destinationMAC = contactList.allowedMacAddress[contact][1]
		destinationUUID = contactList.allowedMacAddress[contact][2]
		acknowledge = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, message)
		if acknowledge:
			firstTry = True # Se limpia la bandera
			logger.write('INFO', '[BLUETOOTH] Se envio mensaje al contacto: ' + contact)
		else:
			bluetoothPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif (emailPriority >= smsPriority) and (emailPriority != 0):
		destination = contactList.allowedEmails[contact]
		#TODO configurar el asunto desde properties.conf
		acknowledge  = emailInstance.send(destination, contact + ' - Proyecto Datalogger', message)
		if acknowledge:
			firstTry = True # Se limpia la bandera
			logger.write('INFO', '[EMAIL] Se envio mensaje al contacto: ' + contact)
		else:
			emailPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif smsPriority != 0:
		acknowledge = True #TODO cambiar esta linea a envio de SMS
		if acknowledge:
			firstTry = True # Se limpia la bandera
			logger.write('INFO', '[SMS] Se envio mensaje al contacto: ' + contact)
		else:
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	else:
		#print '[COMUNICADOR] No hay modulos para el envio de mensajes a ' + contact
		logger.write('WARNING', '[COMUNICADOR] No hay modulos para el envio de mensajes a ' + contact)

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	global emailInstance, ethernetInstance, receptionBuffer
	if not(checkerInstance.availableEthernet or checkerInstance.availableBluetooth or checkerInstance.availableEmail or checkerInstance.availableSms):
		logger.write('WARNING','[COMUNICADOR] No hay modulos para la recepción de mensajes')
		#print '[COMUNICADOR] No hay modulos para la recepción de mensajes'
	if len(receptionBuffer) > 0:
		message = receptionBuffer.pop()
		#print 'Mensaje leido: ' + message
		return message
	else:
		logger.write('INFO','[COMUNICADOR] El buffer de mensajes esta vacio.')
		#print '[COMUNICADOR] El buffer de mensajes esta vacio.'
		return None
	# determinar de quien es el mensaje que se quiere leer?
	#TODO: puede que se hallan agregado mensajes y que se hayan deshabilitado los modulos, se deberia poder tomar el mensaje.

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global receptionBuffer, checkerInstance, smsInstance, ethernetInstance, bluetoothInstance, emailInstance
	receptionBuffer = list() #Se limpia el buffer de recepción
	checkerInstance.killChecker = True
	del(checkerInstance)
	del smsInstance
	del(ethernetInstance)
	del(emailInstance)
	del(bluetoothInstance)