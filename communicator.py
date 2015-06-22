 # coding=utf-8
import sys
import threading
import os

import configReader
import checkerClass
import emailClass
import modemClass
import ethernetClass
import contactList

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
ethernetPriority = True
bluetoothPriority = True
emailPriority = True
smsPriority = True

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, ethernetInstance, bluetoothInstance, smsInstance, emailInstance
	ethernetInstance = ethernetClass.Ethernet(receptionBuffer, configReader.processNotifications, configReader.warningNotifications, configReader.errorNotifications)
	bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer, configReader.processNotifications, configReader.warningNotifications, configReader.errorNotifications)
	smsInstance = modemClass.Sms()
	emailInstance = emailClass.Email(receptionBuffer, configReader.processNotifications, configReader.warningNotifications, configReader.errorNotifications)
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
	global emailInstance, ethernetInstance, bluetoothInstance, firstTry, ethernetPriority, bluetoothPriority, emailPriority, smsPriority

	if firstTry: # Solo la primer vez que intente enviar incia las prioridades, para poder modificar temporalmente
		ethernetPriority = configReader.priorityLevels['ethernet'] # Variable temporal para determinar la prioridad de ethernet
		if not (contactList.allowedIpAddress.has_key(contact) and checkerInstance.availableEthernet)  : ethernetPriority = 0 # Se deshabilitan modos no registrados para el contacto o por no contar con el modo
		bluetoothPriority = configReader.priorityLevels['bluetooth']
		if not (contactList.destinationBluetooth.has_key(contact) and checkerInstance.availableBluetooth) : bluetoothPriority = 0 
		emailPriority = configReader.priorityLevels['email']
		if not (contactList.allowedEmails.has_key(contact) and checkerInstance.availableEmail) : emailPriority = 0
		smsPriority = configReader.priorityLevels['sms']
		if not (contactList.allowedNumbers.has_key(contact) and checkerInstance.availableSms) : smsPriority = 0
		firstTry = False

	if ((ethernetPriority >= bluetoothPriority) and (ethernetPriority >= emailPriority) and 	
	(ethernetPriority >= smsPriority) and (ethernetPriority != 0)):
		destinationIp = contactList.allowedIpAddress[contact]
		destinationPort = contactList.allowedPorts[contact]
		ethernetInstance.send(destinationIp, destinationPort, message)
		acknowledge = True  #TODO True si el envio es correcto, de otro modo es False y en ese caso debe llamarse nuevamente a la función
		if acknowledge:
			firstTry = True # Se limpia la bandera
		else:
			ethernetPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif ((bluetoothPriority >= emailPriority) and (bluetoothPriority >= smsPriority) and (bluetoothPriority != 0)):
		destinationServiceName = contactList.destinationBluetooth[contact][0]
		destinationMAC = contactList.destinationBluetooth[contact][1]
		destinationUUID = contactList.destinationBluetooth[contact][2]
		acknowledge = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, message)
		if acknowledge:
			firstTry = True # Se limpia la bandera
		else:
			bluetoothPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif (emailPriority >= smsPriority) and (emailPriority != 0):
		destination = contactList.allowedEmails[contact]
		#TODO configurar el asunto desde properties.conf
		acknowledge  = emailInstance.send(destination, contact + ' - Proyecto Datalogger', message)
		if acknowledge:
			firstTry = True # Se limpia la bandera
		else:
			emailPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	elif smsPriority != 0:
		acknowledge = True
		if acknowledge:
			firstTry = True # Se limpia la bandera
		else:
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(contact,message)

	else:
		if (configReader.warningNotifications): print '[COMUNICADOR] No hay modulos para el envio de mensajes a ' + contact

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	global emailInstance, ethernetInstance, receptionBuffer
	if not(checkerInstance.availableEthernet or checkerInstance.availableBluetooth or checkerInstance.availableEmail or checkerInstance.availableSms):
		if (configReader.warningNotifications): print '[COMUNICADOR] No hay modulos para la recepción de mensajes'
	if len(receptionBuffer) > 0:
		message = receptionBuffer.pop()
		#print 'Mensaje leido: ' + message
		return message
	else:
	    if (configReader.warningNotifications): print '[COMUNICADOR] El buffer de mensajes esta vacio.'
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
