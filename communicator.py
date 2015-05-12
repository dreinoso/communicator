 # coding=utf-8
import configReader
import checkerClass
import emailClass
import ethernetClass
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
		emailInstance = emailClass.Email(receptionBuffer)
	if(checker.ethernetAvailability):
		ethernetInstance = ethernetClass.Ethernet()

def send(contact, message):
	"""Se envia de modo "inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global emailInstance, ethernetInstance
	if checker.emailAvailability:
		if contactList.allowedEmails.has_key(contact):
			destination = contactList.allowedEmails[contact]
			emailInstance.sendEmail(destination, contact + ' - Proyecto Datalogger', message)
		else:
			print 'El contacto a enviar mensaje no esta configurado.'
	elif checker.ethernetAvailability:
		if contactList.allowedIpAddress.has_key(contact):
			destination = contactList.allowedIp[contact]
			ethernetInstance.sendPaquet(destination, message)
		else:
			print 'El contacto a enviar mensaje no esta configurado.'
	else:
		print 'No hay modulos para el envio de mensajes'
	# TODO: decidir entre varias interfaces de comunicación

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return Mensaje recibido"""
	global emailInstance, ethernetInstance, receptionBuffer
	if checker.emailAvailability or checker.ethernetAvailability:
		if len(receptionBuffer) > 0:
			message = receptionBuffer.pop()
			#print 'Mensaje leido: ' + message
			return message
		else:
		    print 'El buffer de mensajes esta vacio.'
		    return None
	else:
		print 'No hay modulos para la recepción de mensajes'
		return None
	# determinar de quien es el mensaje que se quiere leer?

def length():
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
		del(ethernetInstance)
		#ethernetInstance.closeEthernet()