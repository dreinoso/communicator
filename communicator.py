 # coding=utf-8

"""Modulo principal que se encarga del control de los demás objetos y submódulos
	para permitir la comunicación. 
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import re
import os
import sys
import time
import json
import Queue
import pickle
import threading
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
import checkerClass
import messageClass
import transmitterClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

os.chdir(currentDirectory)

logger.set() # Solo se setea una vez, todos los objetos usan esta misma configuración

receptionBuffer = Queue.PriorityQueue
transmissionBuffer = Queue.PriorityQueue

smsInstance = modemClass.Sms
gprsInstance = modemClass.Gprs
emailInstance = emailClass.Email
networkInstance = networkClass.Network
bluetoothInstance = bluetoothClass.Bluetooth

checkerInstance = checkerClass.Checker             # Instancia que va a verificar las conexiones
transmitterInstance = transmitterClass.Transmitter # Instancia para la transmisión de paquetes

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global receptionBuffer, transmissionBuffer 
	global networkInstance, gprsInstance, emailInstance, smsInstance, bluetoothInstance
	global checkerInstance, transmitterInstance

	# Creamos los buffers de recepción y transmisión, respectivamente
	receptionBuffer = Queue.PriorityQueue(JSON_CONFIG["COMMUNICATOR"]["RECEPTION_BUFFER"])
	transmissionBuffer = Queue.PriorityQueue(JSON_CONFIG["COMMUNICATOR"]["TRANSMISSION_BUFFER"])

	# Creamos las instancias de los periféricos
	gprsInstance = modemClass.Gprs()
	smsInstance = modemClass.Sms(receptionBuffer)
	emailInstance = emailClass.Email(receptionBuffer)
	networkInstance = networkClass.Network(receptionBuffer)
	bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)

	# Creamos la instancia del checker y el hilo que va a verificar las conexiones
	checkerInstance = checkerClass.Checker(networkInstance, gprsInstance, emailInstance, smsInstance, bluetoothInstance)

	# Creamos la instancia para la transmisión de paquetes
	transmitterInstance = transmitterClass.Transmitter(transmissionBuffer, networkInstance, bluetoothInstance, emailInstance, smsInstance, checkerInstance)

	# Ponemos en marcha la comprobación de medios de comunicación y la transmisión de mensajes
	checkerInstance.start()
	transmitterInstance.start()

	return True

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global receptionBuffer, transmissionBuffer, checkerInstance, transmitterInstance
	global smsInstance, networkInstance, gprsInstance, bluetoothInstance, emailInstance

	# Frenamos la transmisión de mensajes
	transmitterInstance.isActive = False
	transmitterInstance.join()

	# Frenamos la verificación de las conexiones
	checkerInstance.isActive = False
	checkerInstance.join()

	# Destruimos todas las instancias de comunicación
	del smsInstance
	del gprsInstance
	del emailInstance
	del networkInstance
	del bluetoothInstance

	# Destruimos las instancias de manejo del comunicador
	del transmitterInstance
	del receptionBuffer
	del checkerInstance

	return True

def send(message, receiver = None, device = None):
	"""Se almacena en el buffer de transmisión el paquete a ser enviado, se guardara
	en caso de que se hayan establecido parametros correctos. En caso de tratarse 
	de un mensaje simple o archivo simple, se los convierte en Instancias para simplificar
	el manejo del mensaje por el transmisor. Pero se envia unicamente la cadena de
	texto o el archivo
	@param message: paquete a ser enviado, ya sea mensaje (o instancia) o un archivo (o instancia)
	@param receiver: es el contacto al que se envia el mensaje
	@param device: modo de envío preferente para ese mensaje en particular (puede no definirse)"""
	global transmissionBuffer

	if not transmissionBuffer.full():
		# Si el mensaje no es una instancia, la creamos para poder hacer el manejo de transmisión con prioridad
		if not isinstance(message, messageClass.Message):
			# Al no tratarse de una instancia, no podemos conocer el destino salvo que el usuario lo especifique
			if receiver is not None:
				# Si el mensaje es una ruta a un archivo, creamos la instancia de archivo correspondiente...
				if os.path.isfile(message):
					# 'message' puede ser un path relativo, o bien un path absoluto
					message = messageClass.FileMessage('', receiver, message)
				else:
				# ... sino, creamos una instancia de mensaje simple.
					message = messageClass.SimpleMessage('', receiver, message)
				# Marcamos la instancia para indicar que se trataba de un mensaje que no necesitaba ser objeto
				setattr(message, 'isInstance', False)
			else:
				logger.write('ERROR', '[COMMUNICATOR] No se especificó un destino para el mensaje!')
				return False
		# Si el mensaje es una instancia de archivo, verificamos que la ruta hacia el mismo sea la correcta
		elif isinstance(message, messageClass.FileMessage):
			if not os.path.isfile(message.fileName):
				logger.write('ERROR', '[COMMUNICATOR] La ruta hacia el archivo a enviar es incorrecta!')
				return False
		# Comprobamos si el campo 'isInstance' no existe, para crearlo
		if not hasattr(message, 'isInstance'):
			setattr(message, 'isInstance', True)
		# Establecemos el tiempo que permanecerá el mensaje en el buffer antes de ser desechado en caso de no ser enviado
		setattr(message, 'timeOut', 20)
		# Damos mayor prioridad al dispositivo referenciado por 'device' (si es que hay alguno)
		setattr(message, 'device', device)
		# Indicamos con una marca de tiempo, la hora exacta en la que se almacenó el mensaje en el buffer de transmisión
		setattr(message, 'timeStamp', time.time())
		# Almacenamos el mensaje en el buffer de transmisión, con la prioridad correspondiente
		transmissionBuffer.put((100 - message.priority, message))
		logger.write('INFO', '[COMMUNICATOR] Mensaje almacenado en transmisor esperando ser enviado...')
		return True
	else:
		logger.write('WARNING', '[COMMUNICATOR] El buffer de transmisión esta lleno, imposible enviar!')
		return False

def receive():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	if receptionBuffer.qsize() > 0:
		message = receptionBuffer.get_nowait()
		return message[1] # Es una tupla y el primer elemento corresponde a la prioridad
	else:
		logger.write('INFO', '[COMMUNICATOR] El buffer de mensajes esta vacio.')
		return None

def lenght():
	"""Devuelve el tamaño del buffer de recepción.
	@return: Cantidad de elementos en el buffer
	@rtype: int"""
	if receptionBuffer.qsize() == None:
		return 0
	else:
		return receptionBuffer.qsize()

def connectGprs():
	if not gprsInstance.isActive:
		return gprsInstance.connect()
	else:
		logger.write('WARNING', '[GRPS] Ya existe una conexión activa con la red!')
		return True

def disconnectGprs():
	return gprsInstance.disconnect()
