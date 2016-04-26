 # coding=utf-8

"""Modulo principal que se encarga del control de los demás objetos y submódulos
	para permitir la comunicación. 
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import os
import io
import sys
import time
import json
import Queue
import subprocess

currentDirectory = os.getcwd() 
if not currentDirectory.endswith('Communicator'):
	os.chdir(currentDirectory + '/Communicator')

sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Network/'))
sys.path.append(os.path.abspath('Bluetooth/'))

import emailClass
import modemClass
import networkClass
import bluetoothClass

import logger
import contactList
import messageClass
import controllerClass
import transmitterClass

os.chdir(currentDirectory)

alreadyOpen = False

gsmInstance = modemClass.Gsm
emailInstance = emailClass.Email
gprsInstance = networkClass.Network
wifiInstance = networkClass.Network
ethernetInstance = networkClass.Network
bluetoothInstance = bluetoothClass.Bluetooth

controllerInstance = controllerClass.Controller    # Instancia que controla los medios
transmitterInstance = transmitterClass.Transmitter # Instancia para la transmisión de paquetes

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

# Creamos el logger de eventos
FILE_LOG = JSON_CONFIG["LOGGER"]["FILE_LOG"]
FILE_LOGGING_LEVEL = JSON_CONFIG["LOGGER"]["FILE_LOGGING_LEVEL"]
CONSOLE_LOGGING_LEVEL = JSON_CONFIG["LOGGER"]["CONSOLE_LOGGING_LEVEL"]
logger.set(FILE_LOG, FILE_LOGGING_LEVEL, CONSOLE_LOGGING_LEVEL)

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global alreadyOpen
	global receptionQueue, transmissionQueue
	global controllerInstance, transmitterInstance
	global gsmInstance, gprsInstance, wifiInstance, ethernetInstance, bluetoothInstance, emailInstance

	if not alreadyOpen:
		logger.write('INFO', 'Abriendo el Comunicador...')
		# Creamos las colas de recepción y transmisión, respectivamente
		RECEPTION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["RECEPTION_QSIZE"]
		TRANSMISSION_QSIZE = JSON_CONFIG["COMMUNICATOR"]["TRANSMISSION_QSIZE"]
		receptionQueue = Queue.PriorityQueue(RECEPTION_QSIZE)
		transmissionQueue = Queue.PriorityQueue(TRANSMISSION_QSIZE)
		# Creamos las instancias de los periféricos
		gsmInstance = modemClass.Gsm(receptionQueue)
		gprsInstance = networkClass.Network(receptionQueue, 'GPRS')
		wifiInstance = networkClass.Network(receptionQueue, 'WIFI')
		ethernetInstance = networkClass.Network(receptionQueue, 'ETHERNET')
		bluetoothInstance = bluetoothClass.Bluetooth(receptionQueue)
		emailInstance = emailClass.Email(receptionQueue)
		# Creamos la instancia que levantará las conexiones
		REFRESH_TIME = JSON_CONFIG["COMMUNICATOR"]["REFRESH_TIME"]
		controllerInstance = controllerClass.Controller(REFRESH_TIME)
		controllerInstance.gsmInstance = gsmInstance
		controllerInstance.gprsInstance = gprsInstance
		controllerInstance.wifiInstance = wifiInstance
		controllerInstance.ethernetInstance = ethernetInstance
		controllerInstance.bluetoothInstance = bluetoothInstance
		controllerInstance.emailInstance = emailInstance
		# Creamos la instancia para la transmisión de paquetes
		transmitterInstance = transmitterClass.Transmitter(transmissionQueue)
		transmitterInstance.gsmInstance = gsmInstance
		transmitterInstance.gprsInstance = gprsInstance
		transmitterInstance.wifiInstance = wifiInstance
		transmitterInstance.ethernetInstance = ethernetInstance
		transmitterInstance.bluetoothInstance = bluetoothInstance
		transmitterInstance.emailInstance = emailInstance
		# Ponemos en marcha el controlador de medios de comunicación y la transmisión de mensajes
		controllerInstance.start()
		transmitterInstance.start()
		logger.write('INFO', 'Comunicador abierto exitosamente!')
		# Indicamos que inicio la sesión
		alreadyOpen = True
		return True
	else:
		logger.write('WARNING', 'El Comunicador ya se encuentra abierto!')
		return False

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global alreadyOpen
	global receptionQueue, transmissionQueue
	global controllerInstance, transmitterInstance
	global gsmInstance, gprsInstance, wifiInstance, ethernetInstance, bluetoothInstance, emailInstance

	if alreadyOpen:
		logger.write('INFO', 'Cerrando el Comunicador...')
		if gprsInstance.isActive:
			disconnectGprs()
		# Frenamos la transmisión de mensajes
		transmitterInstance.isActive = False
		transmitterInstance.join()
		# Frenamos la verificación de las conexiones
		controllerInstance.isActive = False
		controllerInstance.join()
		# Destruimos todas las instancias de comunicación
		del gsmInstance
		del gprsInstance
		del wifiInstance
		del ethernetInstance
		del bluetoothInstance
		del emailInstance
		# Destruimos las colas de recepción y transmisión
		del receptionQueue
		del transmissionQueue
		# Destruimos las instancias de manejo del comunicador
		del controllerInstance
		del transmitterInstance
		logger.write('INFO', 'Comunicador cerrado exitosamente!')
		# Indicamos que terminó la sesion
		alreadyOpen = False
		return True
	else:
		logger.write('WARNING', 'El Comunicador ya se encuentra cerrado!')
		return False

def send(message, receiver = None, media = None):
	"""Se almacena en la cola de transmisión el paquete a ser enviado, se guardara
	en caso de que se hayan establecido parametros correctos. En caso de tratarse 
	de un mensaje simple o archivo simple, se los convierte en Instancias para simplificar
	el manejo del mensaje por el transmisor. Pero se envia unicamente la cadena de
	texto o el archivo
	@param message: paquete a ser enviado, ya sea mensaje (o instancia) o un archivo (o instancia)
	@param receiver: es el contacto al que se envia el mensaje
	@param media: modo de envío preferente para ese mensaje en particular (puede no definirse)"""

	if alreadyOpen:
		if not transmissionQueue.full():
			# Si el mensaje no es una instancia, la creamos para poder hacer el manejo de transmisión con prioridad
			if not isinstance(message, messageClass.Message):
				# Al no tratarse de una instancia, no podemos conocer el destino salvo que el usuario lo especifique
				if receiver is not None:
					tmpMessage = message
					# Creamos la instancia general de un mensaje
					message = messageClass.Message('', receiver, 10)
					# Verificamos si el mensaje es una ruta a un archivo (path relativo o path absoluto)...
					if os.path.isfile(tmpMessage):
						# Insertamos el campo 'fileName'
						setattr(message, 'fileName', tmpMessage)
					# Entonces es un mensaje de texto plano
					else:
						# Insertamos el campo 'plainText'
						setattr(message, 'plainText', tmpMessage)
				else:
					logger.write('ERROR', '[COMMUNICATOR] No se especificó un destino para el mensaje!')
					return False
			################################## VERIFICACIÓN DE CONTACTO ##################################
			# Antes de poner el mensaje en la cola, comprobamos que el cliente esté en algún diccionario
			clientList = list() + contactList.allowedHosts.keys()
			clientList += contactList.allowedMacAddress.keys()
			clientList += contactList.allowedEmails.keys()
			clientList += contactList.allowedNumbers.keys()
			# Quitamos los clientes repetidos
			clientList = list(set(clientList))
			# Buscamos por lo menos una coincidencia, para luego intentar hacer el envío
			if message.receiver not in clientList:
				# El cliente fue encontrado como entrada de un diccionario
				logger.write('WARNING', '[COMMUNICATOR] \'%s\' no registrado! Mensaje descartado...' % message.receiver)
				return False
			################################ FIN VERIFICACIÓN DE CONTACTO ################################
			# Ponemos en maýusculas el dispositivo preferido, si es que se estableció alguno
			if media is not None:
				media = media.upper()
			# Damos mayor prioridad al dispositivo referenciado por 'media' (si es que hay alguno)
			setattr(message, 'media', media)
			# Indicamos con una marca de tiempo, la hora exacta en la que se almacenó el mensaje en la cola de transmisión
			setattr(message, 'timeStamp', time.time())
			# Establecemos el tiempo que permanecerá el mensaje en la cola antes de ser desechado en caso de no ser enviado
			setattr(message, 'timeToLive', JSON_CONFIG["COMMUNICATOR"]["TIME_TO_LIVE"])
			# Almacenamos el mensaje en la cola de transmisión, con la prioridad correspondiente
			transmissionQueue.put((message.priority, message))
			logger.write('INFO', '[COMMUNICATOR] Mensaje almacenado en la cola esperando ser enviado...')
			return True
		else:
			logger.write('WARNING', '[COMMUNICATOR] La cola de transmisión esta llena, imposible enviar!')
			return False
	else:
		logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		return False

def receive():
	"""Se obtiene de una cola el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	if alreadyOpen:
		if receptionQueue.qsize() > 0:
			# El elemento 0 es la prioridad, por eso sacamos el 1 porque es el mensaje
			return receptionQueue.get_nowait()[1]
		else:
			logger.write('INFO', '[COMMUNICATOR] La cola de mensajes esta vacía!')
			return None
	else:
		logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		return False

def length():
	"""Devuelve el tamaño de la cola de recepción.
	@return: Cantidad de elementos en la cola
	@rtype: int"""
	if alreadyOpen:
		if receptionQueue.qsize() == None:
			return 0
		else:
			return receptionQueue.qsize()
	else:
		logger.write('WARNING', 'El Comunicador no se encuentra abierto!')
		return False

def sendVoiceCall(telephoneNumber):
	if gsmInstance.isActive:
		return gsmInstance.sendVoiceCall(telephoneNumber)
	else:
		logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		return False

def answerVoiceCall():
	if gsmInstance.isActive:
		return gsmInstance.answerVoiceCall()
	else:
		logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		return False

def hangUpVoiceCall():
	if gsmInstance.isActive:
		return gsmInstance.hangUpVoiceCall()
	else:
		logger.write('WARNING', '[COMMUNICATOR] No hay un módulo para el manejo de llamadas de voz!')
		return False

def connectGprs():
	# Si no existe una conexión GPRS activa, intentamos conectarnos a la red
	if not gprsInstance.isActive:
		try:
			logger.write('INFO', '[COMMUNICATOR] Intentando conectar con la red GPRS...')
			ponProcess = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			ponOutput, ponError = ponProcess.communicate()
			# Si no se produjo ningún error, entonces se intenta iniciar la conexión con el APN
			if ponError == '':
				syslogFile = io.open('/var/log/syslog', 'a+')
				syslogFile.seek(0, 2) # Apuntamos al final del archivo
				while True:
					syslogOutput = syslogFile.readline()
					if syslogOutput.find('local  IP address ') > 0:
						# Se asignó una direccion IP...
						local_IP_Address = syslogOutput.split()[8].encode('utf-8')
						logger.write('DEBUG', '[COMMUNICATOR] Dirección IP: %s' % local_IP_Address)
						continue
					elif syslogOutput.find('remote IP address ') > 0:
						# Se asignó una puerta de enlace...
						remote_IP_Address = syslogOutput.split()[8].encode('utf-8')
						logger.write('DEBUG', '[COMMUNICATOR] Puerta de enlace: %s' % remote_IP_Address)
						continue
					elif syslogOutput.find('primary   DNS address ') > 0:
						# Se asignó un servidor DNS primario...
						primary_DNS_Address = syslogOutput.split()[8].encode('utf-8')
						logger.write('DEBUG', '[COMMUNICATOR] DNS Primario: %s' % primary_DNS_Address)
						continue
					elif syslogOutput.find('secondary DNS address ') > 0:
						# Se asignó un servidor DNS secundario (último parámetro)...
						secondary_DNS_Address = syslogOutput.split()[8].encode('utf-8')
						logger.write('DEBUG', '[COMMUNICATOR] DNS Secundario: %s' % secondary_DNS_Address)
						continue
					elif syslogOutput.find('Script /etc/ppp/ip-up finished') > 0:
						#logger.write('DEBUG', '[COMMUNICATOR] Parámetros de red configurados exitosamente!')
						return True
					elif syslogOutput.find('Connection terminated') > 0:
						logger.write('DEBUG', '[COMMUNICATOR] No se pudo establecer la conexión con la red GPRS!')
						return False
			# El puerto serial en '/etc/ppp/options-mobile' está mal configurado
			else:
				logger.write('WARNING', '[COMMUNICATOR] Ningún módem conectado para realizar la conexión!')
				return False
		except Exception as error:
			print error
			logger.write('ERROR', '[COMMUNICATOR] Se produjo un error al intentar realizar la conexión!')
			return False
	else:
		logger.write('WARNING', '[COMMUNICATOR] Ya existe una conexión GPRS activa!')
		return True

def disconnectGprs():
	# Si ya existe una conexión GPRS activa, intentamos desconectarnos de la red
	if gprsInstance.isActive:
		try:
			poffProcess = subprocess.Popen('poff', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			poffOutput, poffError = poffProcess.communicate()
			if poffOutput.find('No pppd is running') > 0:
				logger.write('WARNING', '[COMMUNICATOR] El demonio pppd no está ejecutándose y no hay conexión!')
				return False
			else:
				logger.write('INFO', '[COMMUNICATOR] La red GPRS ha sido desconectada correctamente!')
				return True
		except:
			logger.write('ERROR', '[COMMUNICATOR] Se produjo un error al intentar desconectarse de la red GPRS!')
			return False
	else:
		logger.write('WARNING', '[COMMUNICATOR] No existe una conexión GPRS activa para desconectar!')
		return False