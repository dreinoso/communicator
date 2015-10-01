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
import Queue
import threading
import subprocess
import commentjson

sys.path.append(os.path.abspath('Lan/'))
sys.path.append(os.path.abspath('Email/'))
sys.path.append(os.path.abspath('Modem/'))
sys.path.append(os.path.abspath('Bluetooth/'))

import lanClass
import modemClass
import emailClass
import bluetoothClass

import logger
import contactList
import checkerClass

JSON_FILE = 'config.json'
JSON_CONFIG = commentjson.load(open(JSON_FILE))

receptionBuffer = Queue.Queue()
modemSemaphore = threading.Semaphore(value = 1)

# Creamos las instancias de los periféricos
lanInstance = lanClass.Lan(receptionBuffer)
gprsInstance = modemClass.Gprs(modemSemaphore)
emailInstance = emailClass.Email(receptionBuffer)
smsInstance = modemClass.Sms(receptionBuffer, modemSemaphore)
bluetoothInstance = bluetoothClass.Bluetooth(receptionBuffer)

# Creamos la instancia del checker y el hilo que va a verificar las conexiones
checkerInstance = checkerClass.Checker(modemSemaphore, lanInstance, gprsInstance, emailInstance, smsInstance, bluetoothInstance)
checkerThread = threading.Thread(target = checkerInstance.verifyConnections, name = 'checkerThread')

lanPriority = 0
smsPriority = 0
emailPriority = 0
bluetoothPriority = 0
contactExists = False

def open():
	"""Se realiza la apertura, inicialización de los componentes que se tengan disponibles
	"""
	global checkerInstance, checkerThread

	logger.set() # Solo se setea una vez, todos los objetos usan esta misma configuración
	checkerInstance.verifyLanConnection()
	checkerInstance.verifySmsConnection()
	checkerInstance.verifyEmailConnection()
	checkerInstance.verifyBluetoothConnection()
	# Lanzamos el hilo que comprueba las conexiones
	checkerInstance.isActive = True
	checkerThread.start()

def send(clientToSend, messageToSend):
	"""Se envia de modo inteligente un paquete de datos a un contacto previamente registrado
	el mensaje se envia por el medio mas óptimo encontrado.
	@param clientToSend: Nombre de contacto previamente registrado
	@type clientToSend: str
	@param messageToSend: Mensaje a ser enviado
	@type clientToSend: str"""
	global contactExists, lanPriority, bluetoothPriority, emailPriority, smsPriority

	# Determinamos si el contacto existe. Si no existe, no se intenta enviar por ningún medio.
	if not contactExists:
		lanPriority = 0
		bluetoothPriority = 0
		emailPriority = 0
		smsPriority = 0

		print availableSms

		if contactList.allowedIpAddress.has_key(clientToSend) and checkerInstance.availableLan:
			lanPriority = JSON_CONFIG["PRIORITY_LEVELS"]["LAN"]
			contactExists = True
		if contactList.allowedMacAddress.has_key(clientToSend) and checkerInstance.availableBluetooth:
			bluetoothPriority = JSON_CONFIG["PRIORITY_LEVELS"]["BLUETOOTH"]
			contactExists = True
		if contactList.allowedEmails.has_key(clientToSend) and checkerInstance.availableEmail:
			emailPriority = JSON_CONFIG["PRIORITY_LEVELS"]["EMAIL"]
			contactExists = True
		if contactList.allowedNumbers.has_key(clientToSend) and checkerInstance.availableSms:
			smsPriority = JSON_CONFIG["PRIORITY_LEVELS"]["SMS"]
			contactExists = True
		if not contactExists:
			logger.write('WARNING', '[COMUNICADOR] El contacto \'%s\' no se encuentra registrado.' % clientToSend)
			return False
	# Intentamos transmitir por LAN
	if lanPriority != 0 and lanPriority >= bluetoothPriority and lanPriority >= emailPriority and lanPriority >= smsPriority:
		destinationIp = contactList.allowedIpAddress[clientToSend][0]
		destinationTcpPort = contactList.allowedIpAddress[clientToSend][1]
		destinationUdpPort = contactList.allowedIpAddress[clientToSend][2]
		resultOk = lanInstance.send(destinationIp, destinationTcpPort, destinationUdpPort, messageToSend)
		if resultOk:
			logger.write('INFO', '[LAN] Mensaje enviado a \'%s\'.' % clientToSend)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[LAN] Envio fallido. Reintentando con otro periférico.')
			lanPriority = 0   # Entonces se descarta para la proxima selección
			send(clientToSend, messageToSend) # Se reintenta con otros perifericos
	# Intentamos transmitir por BLUETOOTH
	elif bluetoothPriority != 0 and bluetoothPriority >= emailPriority and bluetoothPriority >= smsPriority:
		destinationServiceName = contactList.allowedMacAddress[clientToSend][0]
		destinationMAC = contactList.allowedMacAddress[clientToSend][1]
		destinationUUID = contactList.allowedMacAddress[clientToSend][2]
		resultOk = bluetoothInstance.send(destinationServiceName, destinationMAC, destinationUUID, messageToSend)
		if resultOk:
			logger.write('INFO', '[BLUETOOTH] Mensaje enviado a \'%s\'.' % clientToSend)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[BLUETOOTH] Envio fallido. Reintentando con otro periférico.')
			bluetoothPriority = 0  # Entonces se descarta para la proxima selección
			send(clientToSend, messageToSend) # Se reintenta con otros perifericos
	# Intentamos transmitir por EMAIL
	elif emailPriority != 0 and emailPriority >= smsPriority:
		destinationEmail = contactList.allowedEmails[clientToSend]
		resultOk  = emailInstance.send(destinationEmail, 'Proyecto Datalogger - Comunicador', messageToSend)
		if resultOk:
			logger.write('INFO', '[EMAIL] Mensaje enviado a \'%s\'.' % clientToSend)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[EMAIL] Envio fallido. Reintentando con otro periférico.')
			emailPriority = 0      # Entonces se descarta para la proxima selección
			send(clientToSend, messageToSend) # Se reintenta con otros perifericos
	# Intentamos transmitir por SMS
	elif smsPriority != 0:
		destinationNumbsmsPriorityer = contactList.allowedNumbers[clientToSend]
		resultOk = smsInstance.send(destinationNumber, messageToSend)
		if resultOk:
			logger.write('INFO', '[SMS] Mensaje enviado a \'%s\'.' % clientToSend)
			contactExists = False
			return True
		else:
			logger.write('WARNING', '[SMS] Envio fallido. Reintentando con otro periférico.')
			smsPriority = 0 # Entonces se descarta para la proxima selección
			send(clientToSend, messageToSend)
	# No fue posible transmitir por ningún medio
	else:
		logger.write('WARNING', '[COMUNICADOR] No hay módulos para el envío de mensajes a \'%s\'.' % clientToSend)
		contactExists = False
		return False

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
	global smsInstance, lanInstance, gprsInstance, bluetoothInstance, emailInstance
	receptionBuffer.queue.clear()
	checkerInstance.isActive = False
	checkerThread.join()
	del checkerInstance
	del smsInstance
	del lanInstance
	del gprsInstance
	del emailInstance
	del bluetoothInstance
