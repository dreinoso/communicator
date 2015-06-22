 # coding=utf-8
import sys
import threading

import configReader
import checkerClass
import emailClass
import modemClass
import ethernetClass
import contactList

sys.path.append('/home/mauri/Communicator/Bluetooth')
import bluetoothClass

receptionBuffer = list()

checkerInstance = checkerClass.Checker
ethernetInstance = ethernetClass.Ethernet
bluetoothInstance = bluetoothClass.Bluetooth
smsInstance = modemClass.Sms
emailInstance = emailClass.Email

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
	global emailInstance, ethernetInstance, bluetoothInstance
	if((configReader.ethernetPriority >= configReader.bluetoothPriority) and 
		(configReader.ethernetPriority >= configReader.emailPriority) and 
		(configReader.ethernetPriority >= configReader.smsPriority) and 
		checkerInstance.availableEthernet):
		if contactList.allowedIpAddress.has_key(contact):
			destinationIp = contactList.allowedIpAddress[contact]
			destinationPort = contactList.allowedPorts[contact]
			ethernetInstance.sendPacket(destinationIp, destinationPort, message)
		else:
			if (configReader.warningNotifications): print '[COMUNICADOR] El contacto a enviar mensaje no esta configurado para Modo Ethernet.'
	elif((configReader.bluetoothPriority >= configReader.emailPriority) and 
		 (configReader.bluetoothPriority >= configReader.smsPriority) and 
		  checkerInstance.availableBluetooth):
		if contactList.destinationBluetooth.has_key(contact):
			destinationServiceName = contactList.destinationBluetooth[contact][0]
			destinationMAC = contactList.destinationBluetooth[contact][1]
			destinationUUID = contactList.destinationBluetooth[contact][2]
			bluetoothInstance.sendPacket(destinationServiceName, destinationMAC, destinationUUID, message)
		else:
			if (configReader.warningNotifications): print '[BLUETOOTH] El contacto a enviar mensaje BLUETOOTH no esta configurado.'
	elif((configReader.emailPriority >= configReader.smsPriority) and checkerInstance.availableEmail):
		if contactList.allowedEmails.has_key(contact):
			destination = contactList.allowedEmails[contact]
			#TODO configurar el asunto desde properties.conf
			emailInstance.sendEmail(destination, contact + ' - Proyecto Datalogger', message) 
		else:
			if (configReader.warningNotifications): print '[COMUNICADOR] El contacto a enviar mensaje no esta configurado para Modo Email.'
	elif(checkerInstance.availableSms):
		pass
	else:
		if (configReader.warningNotifications): print '[COMUNICADOR] No hay modulos para el envio de mensajes'

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
