 # coding=utf-8
import configReader
import checkerClass
import emailClass
import ethernetClass
import prioritySelector
import contactList

checker = checkerClass.Checker() #Al iniciar determina el estado de las conexiones
receptionBuffer = list()
emailInstance = ''
ethernetInstance = ''

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global emailInstance, ethernetInstance
	if(checker.emailAvailability):
		emailInstance = emailClass.Email(receptionBuffer, configReader.processNotifications, configReader.warningNotifications, configReader.errorNotifications)
	if(checker.ethernetAvailability):
		ethernetInstance = ethernetClass.Ethernet(receptionBuffer, configReader.processNotifications, configReader.warningNotifications, configReader.errorNotifications)

def send(contact, message):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global emailInstance, ethernetInstance
	if((configReader.ethernetPriority >= configReader.bluetoothPriority) and (configReader.ethernetPriority >= configReader.emailPriority) and (configReader.ethernetPriority >= configReader.smsPriority) and checker.ethernetAvailability):
		if contactList.allowedEmails.has_key(contact):
			destination = contactList.allowedEmails[contact]
			#TODO configurar el asunto desde properties.conf
			emailInstance.sendEmail(destination, contact + ' - Proyecto Datalogger', message) 
		else:
			if (configReader.warningNotifications): print '[COMUNICADOR] El contacto a enviar mensaje no esta configurado para Modo Email.'
	elif((configReader.bluetoothPriority >= configReader.emailPriority) and (configReader.bluetoothPriority >= configReader.smsPriority) and checker.bluetoothAvaliability):
		pass
	elif((configReader.emailPriority >= configReader.smsPriority) and checker.emailAvailability):
		if contactList.allowedIpAddress.has_key(contact):
			destinationIp = contactList.allowedIpAddress[contact]
			destinationPort = contactList.allowedPorts[contact]
			ethernetInstance.sendPacket(destinationIp, destinationPort, message)
		else:
			if (configReader.warningNotifications): print '[COMUNICADOR] El contacto a enviar mensaje no esta configurado para Modo Ethernet.'
	elif(checker.smsAvailability):
		pass
	else:
		if (configReader.warningNotifications): print '[COMUNICADOR] No hay modulos para el envio de mensajes'

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	global emailInstance, ethernetInstance, receptionBuffer
	if not(checker.emailAvailability or checker.ethernetAvailability):
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

def length():
	"""Devuelve la cantidad de elementos en el Buffer de Recepción.
	@return: Cantidad de elementos en Buffer de Recepción.
	@rtype: Int"""
	return len(receptionBuffer)

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global emailInstance, ethernetInstance, receptionBuffer
	receptionBuffer = list() #Se limpia el buffer de recepción
	if checker.emailAvailability:
		emailInstance.stopReception()
		del(emailInstance)
		#emailInstance.closeEmail()
	if checker.ethernetAvailability:
		ethernetInstance.stopReception()
		del(ethernetInstance)
		#ethernetInstance.closeEthernet()