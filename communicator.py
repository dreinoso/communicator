 # coding=utf-8
import emailClass
import contactList

emailInstance = emailClass.Email()

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global emailInstance
	if(emailInstance.verifyConnection()):
		emailInstance.isAvaible = True
		emailInstance.initializeEmail()

def send(contact, message):
	"""Se envia de modo "inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param contact: Nombre de contacto previamente registrado
	@type contact: str
	@param message: Mensaje a ser enviado
	@type contact: str"""
	global emailInstance
	if emailInstance.isAvaible:
		if contactList.allowedEmails.has_key(contact):
			destination = contactList.allowedEmails[contact]
			emailInstance.sendEmail(destination, contact + ' - Proyecto Datalogger', message)
		else:
			print 'El contacto a enviar mensaje no esta configurado'
	else:
		print 'No hay modulos para el envio de mensajes'
	# TODO: decidir entre varias interfaces de comunicación

def recieve():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return Mensaje recibido"""
	global emailInstance
	if emailInstance.isAvaible:
		message = emailInstance.recieve()
		#print 'mensaje: ' + message
		return message
	else:
		print 'No hay modulos para la recepción de mensajes'
		return ''
	# TODO: obtener el mensaje de un buffer circular, 
	# determinar de quien es el mensaje que se quiere leer?

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	if emailInstance.isAvaible:
		emailInstance.closeEmail()
