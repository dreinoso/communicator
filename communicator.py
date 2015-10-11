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
import json
import Queue
import pickle
import threading
import subprocess

sys.path.append(os.path.abspath('Network/'))
sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Bluetooth/'))

import networkClass
import modemClass
import emailClass
import bluetoothClass

import messageClass
#import fileMessageClass

import logger
import contactList
import checkerClass

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

receptionBuffer = Queue.Queue()
modemSemaphore = threading.Semaphore(value = 1)

# Creamos las instancias de los periféricos
networkInstance = networkClass.Network(receptionBuffer)
gprsInstance = modemClass.Gprs(modemSemaphore)
emailInstance = emailClass.Email(receptionBuffer)
smsInstance = modemClass.Sms(receptionBuffer, modemSemaphore)
bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)

#TODO el módulo se pueda importar desde otra carpeta y aún asi poder hacer los imports relativos al módulo

# Creamos la instancia del checker y el hilo que va a verificar las conexiones
checkerInstance = checkerClass.Checker(modemSemaphore, networkInstance, gprsInstance, emailInstance, smsInstance, bluetoothInstance)
checkerThread = threading.Thread(target = checkerInstance.verifyConnections, name = 'checkerThread')

networkPriority = 0
smsPriority = 0
emailPriority = 0
bluetoothPriority = 0
contactExists = False

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, checkerThread

	logger.set() # Solo se setea una vez, todos los objetos usan esta misma configuración
	checkerInstance.verifyNetworkConnection()
	checkerInstance.verifySmsConnection()
	checkerInstance.verifyEmailConnection()
	checkerInstance.verifyBluetoothConnection()
	# Lanzamos el hilo que comprueba las conexiones
	checkerInstance.isActive = True
	checkerThread.start()


def send(messageToSend, receiver = '', device = ''):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param receiver: Nombre de contacto previamente registrado
	@type receiver: str
	@param messageToSend: Mensaje a ser enviado
	@type receiver: str"""
	global contactExists, networkPriority, bluetoothPriority, emailPriority, smsPriority
	# Se establecen los parametros en caso de tratarse de una instancia
	if isinstance(messageToSend, messageClass.Message): 
		receiver = messageToSend.receiver
		device = messageToSend.device
		# Se debe almacenar el tamño para determinar si es demasiado grande para SMS
		messageLength = len(pickle.dumps(messageToSend))
	else:
		messageLength = len(messageToSend)
	# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
	if not contactExists:
		networkPriority = 0
		bluetoothPriority = 0
		emailPriority = 0
		smsPriority = 0
		if contactList.allowedIpAddress.has_key(receiver) and checkerInstance.availableNetwork:
			networkPriority = JSON_CONFIG["PRIORITY_LEVELS"]["NETWORK"]
			if device == 'Network':		# En caso de preferencia de Red se da máxima prioridad
				networkPriority = 10 
			contactExists = True
		if contactList.allowedMacAddress.has_key(receiver) and checkerInstance.availableBluetooth:
			bluetoothPriority = JSON_CONFIG["PRIORITY_LEVELS"]["BLUETOOTH"]
			if device == 'Bluetooth':
				bluetoothPriority = 10
			contactExists = True
		if contactList.allowedEmails.has_key(receiver) and checkerInstance.availableEmail:
			emailPriority = JSON_CONFIG["PRIORITY_LEVELS"]["EMAIL"]
			if device == 'Email':
				emailPriority = 10
			contactExists = True
		# Para SMS solo se habilita el modo si la cantidad de caracteres a enviar no supera el limite
		if contactList.allowedNumbers.has_key(receiver) and checkerInstance.availableSms and (messageLength < JSON_CONFIG["SMS"]["CLARO_CHARACTER_LIMIT"]):
			smsPriority = JSON_CONFIG["PRIORITY_LEVELS"]["SMS"]
			if device == 'SMS':
				smsPriority = 10
			contactExists = True
		if not contactExists:
			logger.write('WARNING', '[COMUNICADOR] El contacto \'%s\' no se encuentra registrado.' % receiver)
			return False
	# Intentamos transmitir por NETWORK
	if networkPriority != 0 and networkPriority >= bluetoothPriority and networkPriority >= emailPriority and networkPriority >= smsPriority:
		destinationIp = contactList.allowedIpAddress[receiver][0]
		destinationTcpPort = contactList.allowedIpAddress[receiver][1]
		destinationUdpPort = contactList.allowedIpAddress[receiver][2]
		resultOk = networkInstance.send(destinationIp, destinationTcpPort, destinationUdpPort, messageToSend)
		if resultOk:
			logger.write('INFO', '[NETWORK] Mensaje enviado a \'%s\'.' % receiver)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[NETWORK] Envio fallido. Reintentando con otro periférico.')
			networkPriority = 0   # Entonces se descarta para la proxima selección
			send(messageToSend, receiver) # Se reintenta con otros perifericos
	# Intentamos transmitir por BLUETOOTH
	elif bluetoothPriority != 0 and bluetoothPriority >= emailPriority and bluetoothPriority >= smsPriority:
		destinationServiceName = contactList.allowedMacAddress[receiver][0]
		destinationMAC = contactList.allowedMacAddress[receiver][1]
		destinationUUID = contactList.allowedMacAddress[receiver][2]
		resultOk = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, messageToSend)
		if resultOk:
			logger.write('INFO', '[BLUETOOTH] Mensaje enviado a \'%s\'.' % receiver)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[BLUETOOTH] Envio fallido. Reintentando con otro periférico.')
			bluetoothPriority = 0  # Entonces se descarta para la proxima selección
			send(messageToSend, receiver) # Se reintenta con otros perifericos
	# Intentamos transmitir por EMAIL
	elif emailPriority != 0 and emailPriority >= smsPriority:
		destinationEmail = contactList.allowedEmails[receiver]
		resultOk  = emailInstance.send(destinationEmail, 'Proyecto Datalogger - Comunicador', messageToSend)
		if resultOk:
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'.' % receiver)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[EMAIL] Envio fallido. Reintentando con otro periférico.')
			emailPriority = 0      # Entonces se descarta para la proxima selección
			send(messageToSend, receiver) # Se reintenta con otros perifericos
	# Intentamos transmitir por SMS
	elif smsPriority != 0:
		destinationNumbsmsPriorityer = contactList.allowedNumbers[receiver]
		resultOk = smsInstance.send(destinationNumber, messageToSend)
		if resultOk:
			logger.write('INFO', '[SMS] Mensaje enviado a \'%s\'.' % receiver)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[SMS] Envio fallido. Reintentando con otro periférico.')
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(messageToSend, receiver)
	# No fue posible transmitir por ningún medio
	else:
		logger.write('WARNING', '[COMUNICADOR] No hay módulos para el envío de mensajes a \'%s\'.' % receiver)
		contactExists = False
		return False

def receive():
	"""Se obtiene de un buffer circular el mensaje recibido mas antiguo.
	@return: Mensaje recibido
	@rtype: str"""
	if receptionBuffer.qsize() > 0:
		message = receptionBuffer.get(False) # False implica que no se bloquee esperando un elemento
		return message
	else:
		logger.write('INFO', '[COMUNICADOR] El buffer de mensajes esta vacio.')
		return None

def lenght():
	"""Devuelve el tamaño del buffer de recepción.
	@return: Cantidad de elementos en el buffer
	@rtype: int"""
	if receptionBuffer.qsize() == None: return 0
	else: return receptionBuffer.qsize()

def connectGprs():
	ttyUSBPattern = re.compile('ttyUSB[0-9]+')
	lsDevProcess = subprocess.Popen(['ls', '/dev/'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
	lsDevOutput, lsDevError = lsDevProcess.communicate()
	ttyUSBDevices = ttyUSBPattern.findall(lsDevOutput)
	# Se detectaron dispositivos USB conectados
	if len(ttyUSBDevices) > 0:
		if gprsInstance.serialPort not in ttyUSBDevices:
			wvdialProcess = subprocess.Popen('wvdialconf', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			wvdialOutput, wvdialError = wvdialProcess.communicate()
			ttyUSBPattern = re.compile('ttyUSB[0-9]+<Info>')
			modemsList = ttyUSBPattern.findall(wvdialError)
			if len(modemsList) > 0:
				gprsSerialPort = modemsList[0].replace('<Info>','')
				if gprsInstance.connect(gprsSerialPort):
					gprsInstance.isActive = True
					gprsInfo = gprsSerialPort + ' - ' + gprsInstance.local_IP_Address
					gprsThread = threading.Thread(target = gprsInstance.verifyConnection, name = 'gprsVerifyConnection')
					gprsThread.start()
					logger.write('INFO','[GPRS] Listo para usarse (' + gprsInfo + ').')
					return True
				else:
					logger.write('WARNING','[GPRS] Error al intentar conectar con la red GPRS.')
					gprsInstance.serialPort = None
					gprsInstance.closePort()
					return False
		# Si llegamos acá es porque el módem ya esta funcionando en modo GPRS
		elif gprsInstance.getStatus():
			logger.write('WARNING', '[GPRS] El módem ya está funcionando en modo GPRS!')
			return True
	else:
		logger.write('WARNING', '[GPRS] No se encontró ningún módem para trabajar en modo GPRS.')
		return False

def disconnectGprs():
	return gprsInstance.disconnect()

def close():
	"""Se cierran los componentes del sistema, unicamente los abiertos previamente"""
	global checkerThread, receptionBuffer, checkerInstance
	global smsInstance, networkInstance, gprsInstance, bluetoothInstance, emailInstance
	receptionBuffer.queue.clear()
	checkerInstance.isActive = False
	checkerThread.join()
	del checkerInstance
	del smsInstance
	del networkInstance
	del gprsInstance
	del emailInstance
	del bluetoothInstance
